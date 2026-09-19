<?php
/*
Plugin Name: Cultura Sabauda - Completude editoriale des fiches
Description: Mesure quotidienne de la completude de chaque fiche publiee, production
  d une file de travail typee et priorisee, et garde-fou a la publication.
  Ne 2026-08-08 apres un constat : 138 fiches sur 222 publiees n avaient jamais ete
  relues par le panel persona, 63 n avaient pas de source officielle, et AUCUN cron
  ne surveillait cela. Le seul garde-fou existant comptait les items des grilles.

  Meme principe que cs-extracteur-pages.php : le site se mesure lui-meme, un agent
  qui corrige ne declare pas sa propre victoire, le releve du lendemain tranche.

  TROIS DISPOSITIFS :
   1. Mesure (lecture seule sur le contenu) : ecrit as_completude_manques et
      as_completude_score sur chaque fiche, pour que la file soit requetable en base
      et filtrable dans l admin.
   2. File de travail : option cs_completude_file, triee par gravite puis par date
      d evenement, exposee en REST sur cultura/v1/completude pour qu un agent
      exterieur (pipeline VPS) puisse la consommer et repartir le travail.
   3. Garde-fou de publication : une fiche publiee sans source officielle ou avec un
      corps indigent repasse en brouillon 15 minutes apres sa mise en ligne, avec
      alerte Slack. Le delai evite la course avec le pipeline, qui ecrit ses meta
      juste apres l insertion du post.

  Rollback : supprimer ce fichier. Les meta as_completude_* deviennent inertes.
*/

if (!defined('ABSPATH')) { exit; }

// ---------------------------------------------------------------------------
// Le contrat de completude. Une seule source de verite, utilisee par la mesure,
// la file et le garde-fou.
// ---------------------------------------------------------------------------
if (!function_exists('cs_completude_controler')) {
function cs_completude_controler($id) {
    $p = get_post($id);
    if (!$p) { return array('manques' => array(), 'bloquants' => array()); }

    $corps = trim(wp_strip_all_tags($p->post_content));
    $len   = mb_strlen($corps);
    $lang  = function_exists('pll_get_post_language') ? pll_get_post_language($id) : '';
    $autre = ($lang === 'fr') ? 'it' : 'fr';
    $paire = function_exists('pll_get_post') ? pll_get_post($id, $autre) : 0;

    $verdict  = (string) get_post_meta($id, 'as_panel_verdict', true);
    $revision = (string) get_post_meta($id, 'as_panel_revision', true);
    $score    = get_post_meta($id, 'as_score', true);

    $manques = array();
    $bloquants = array();

    // --- bloquants : ce qui contredit la promesse publique du site ---
    if (trim((string) get_post_meta($id, 'as_source_officielle_url', true)) === '') {
        $manques[] = 'source_officielle';
        $bloquants[] = 'source_officielle';
    }
    if ($len < 400) {
        $manques[] = 'corps_indigent';
        $bloquants[] = 'corps_indigent';
    }

    // --- file de travail : ce qui rend la fiche incomplete sans la rendre fautive ---
    if ($verdict === '')                          { $manques[] = 'panel_jamais_evalue'; }
    if ($verdict === 'revise' && $revision === '') { $manques[] = 'panel_revise_non_traite'; }
    if ($len >= 400 && $len < 900)                { $manques[] = 'corps_court'; }
    if (trim((string) get_post_meta($id, '_yoast_wpseo_metadesc', true)) === '') { $manques[] = 'meta_description'; }
    $org = get_post_meta($id, '_EventOrganizerID', true);
    if (!$org) { $manques[] = 'organisateur'; }
    else {
        // Regression constatee le 2026-08-08, deja corrigee le 2026-07-29 : le champ
        // organisateur recevait un email personnel ou un nom de domaine, expose
        // publiquement dans le JSON-LD. Un organisateur ne peut etre qu un organisme
        // public ou l organisateur reel, jamais un contact ni un artefact d import.
        $nom = trim(html_entity_decode(get_the_title($org), ENT_QUOTES, 'UTF-8'));
        if (strpos($nom, '@') !== false
            || preg_match('/^[a-z0-9\-]+\.(it|fr|com|eu|net|org|ch)$/i', $nom)
            || preg_match('/^(admin|administrateur|amministratore|webmaster|redazione|info|contact)\b/i', $nom)) {
            $manques[] = 'organisateur_fautif';
        }
    }
    if (!get_post_meta($id, '_EventVenueID', true))     { $manques[] = 'lieu'; }
    if (trim((string) $p->post_excerpt) === '')         { $manques[] = 'extrait'; }
    if (!get_post_thumbnail_id($id))                    { $manques[] = 'image'; }
    if (!$paire || get_post_status($paire) !== 'publish') { $manques[] = 'traduction'; }
    if ($score !== '' && (float) $score < 4)            { $manques[] = 'substance_faible'; }
    // Residus d agregation : pieds de page de flux RSS aspires tels quels
    // ("L articolo X proviene da Y", "The post X appeared first on Y", "Lire la suite").
    // Constate sur 8 fiches le 2026-08-08 ; le pipeline les reintroduira.
    if (preg_match('/proviene da\s+[A-Z]|appeared first on|Lire la suite|Leggi tutto|Continua a leggere|\[contact-form-7\]|\[\x{2026}\]/iu', $p->post_excerpt . ' ' . $p->post_content)) {
        $manques[] = 'residu_flux';
    }

    return array('manques' => $manques, 'bloquants' => $bloquants);
}
}

// Gravite d un manque, pour trier la file. Plus haut = plus urgent.
if (!function_exists('cs_completude_gravite')) {
function cs_completude_gravite($manque) {
    $g = array(
        'source_officielle'       => 100, // le site promet une source systematique
        'corps_indigent'          => 90,
        'panel_revise_non_traite' => 80,  // le panel a demande une revision, rien n a suivi
        'panel_jamais_evalue'     => 60,
        'substance_faible'        => 50,
        'residu_flux'             => 70,
        'traduction'              => 40,
        'corps_court'             => 30,
        'meta_description'        => 20,
        'organisateur'            => 15,
        'organisateur_fautif'     => 85,
        'lieu'                    => 15,
        'extrait'                 => 10,
        'image'                   => 10,
    );
    return isset($g[$manque]) ? $g[$manque] : 5;
}
}

// ---------------------------------------------------------------------------
// 1 & 2. Mesure quotidienne + file de travail
// ---------------------------------------------------------------------------
if (!function_exists('cs_completude_passe')) {
function cs_completude_passe() {
    global $wpdb;
    $ids = $wpdb->get_col("SELECT ID FROM {$wpdb->posts}
        WHERE post_type='tribe_events' AND post_status='publish'");

    $file = array();
    $compte = array();
    $completes = 0;

    foreach ($ids as $id) {
        $r = cs_completude_controler($id);
        $manques = $r['manques'];

        // Ecriture des meta : la file devient requetable en base et filtrable admin.
        if ($manques) {
            update_post_meta($id, 'as_completude_manques', implode(',', $manques));
            update_post_meta($id, 'as_completude_score', count($manques));
        } else {
            delete_post_meta($id, 'as_completude_manques');
            update_post_meta($id, 'as_completude_score', 0);
            $completes++;
            continue;
        }

        $gravite = 0;
        foreach ($manques as $m) {
            $compte[$m] = (isset($compte[$m]) ? $compte[$m] : 0) + 1;
            $gravite = max($gravite, cs_completude_gravite($m));
        }

        $file[] = array(
            'id'       => (int) $id,
            'titre'    => get_the_title($id),
            'lang'     => function_exists('pll_get_post_language') ? pll_get_post_language($id) : '',
            'debut'    => substr((string) get_post_meta($id, '_EventStartDate', true), 0, 10),
            'manques'  => $manques,
            'gravite'  => $gravite,
            'bloquant' => !empty($r['bloquants']),
        );
    }

    // Tri : gravite decroissante, puis evenement le plus proche d abord.
    usort($file, function ($a, $b) {
        if ($a['gravite'] !== $b['gravite']) { return $b['gravite'] - $a['gravite']; }
        return strcmp($a['debut'] ?: '9999', $b['debut'] ?: '9999');
    });

    arsort($compte);
    $releve = array(
        'last_run'   => current_time('mysql'),
        'analysees'  => count($ids),
        'completes'  => $completes,
        'a_traiter'  => count($file),
        'par_manque' => $compte,
        'file'       => $file,
    );
    update_option('cs_completude_file', $releve, false);

    // Liste des fiches a sortir de l index, consommee par le filtre sitemap.
    $hors = array();
    foreach ($file as $f) { if ($f['bloquant']) { $hors[] = $f['id']; } }
    update_option('cs_completude_hors_index_ids', $hors, false);

    // Historique court, pour voir si la dette se resorbe ou grossit.
    $hist = (array) get_option('cs_completude_historique', array());
    $hist[] = array('date' => current_time('mysql'), 'a_traiter' => count($file), 'completes' => $completes);
    if (count($hist) > 60) { $hist = array_slice($hist, -60); }
    update_option('cs_completude_historique', $hist, false);

    // Digest Slack : l ecart par rapport a la veille, pas seulement l etat.
    // Anti-repetition : ne pas renvoyer un digest identique au precedent. Utile
    // pendant une mise au point, ou la passe est relancee a la main plusieurs fois.
    $signature = md5(wp_json_encode(array(count($file), $completes, $compte)));
    $deja = (string) get_option('cs_completude_signature', '');
    update_option('cs_completude_signature', $signature, false);
    if ($signature === $deja) { return $releve; }

    if (function_exists('cs_slack_notify_form')) {
        $veille = count($hist) > 1 ? $hist[count($hist) - 2]['a_traiter'] : null;
        $delta = ($veille === null) ? '' : sprintf(' (%+d depuis hier)', count($file) - $veille);
        $lignes = array();
        foreach ($compte as $m => $n) { $lignes[] = "  {$m} : {$n}"; }
        $bloquantes = array_filter($file, function ($f) { return $f['bloquant']; });
        cs_slack_notify_form(
            ":clipboard: *Completude des fiches - agendasabauda.eu*\n"
            . count($ids) . " fiches publiees, " . $completes . " completes, "
            . count($file) . " a traiter" . $delta . "\n"
            . (count($bloquantes) ? '*' . count($bloquantes) . " bloquantes* (source absente ou corps indigent)\n" : '')
            . implode("\n", array_slice($lignes, 0, 12))
        );
    }
    return $releve;
}
}

add_action('cs_completude_event', 'cs_completude_passe');
if (!wp_next_scheduled('cs_completude_event')) {
    wp_schedule_event(time() + 900, 'daily', 'cs_completude_event');
}

// ---------------------------------------------------------------------------
// 3. Garde-fou de publication, en differe
// ---------------------------------------------------------------------------
add_action('transition_post_status', function ($nouveau, $ancien, $post) {
    if ($nouveau !== 'publish' || $ancien === 'publish') { return; }
    if (!$post || $post->post_type !== 'tribe_events') { return; }
    // Differe : le pipeline ecrit ses meta juste apres l insertion du post. Verifier
    // immediatement produirait un faux positif systematique.
    wp_schedule_single_event(time() + 900, 'cs_completude_gate_event', array((int) $post->ID));
}, 10, 3);

add_action('cs_completude_gate_event', function ($id) {
    $p = get_post($id);
    if (!$p || $p->post_status !== 'publish') { return; }
    $r = cs_completude_controler($id);
    if (empty($r['bloquants'])) { return; }

    remove_action('transition_post_status', 'cs_completude_gate_relais', 10);
    wp_update_post(array('ID' => $id, 'post_status' => 'draft'));
    update_post_meta($id, 'as_completude_refus', implode(',', $r['bloquants']) . ' @ ' . current_time('mysql'));

    if (function_exists('cs_slack_notify_form')) {
        cs_slack_notify_form(
            ":no_entry: *Publication refusee* - fiche #{$id} repassee en brouillon\n"
            . '*' . get_the_title($id) . "*\n"
            . 'Manque : ' . implode(', ', $r['bloquants']) . "\n"
            . 'Le site promet une source officielle sur chaque fiche : une fiche sans source ne peut pas rester en ligne.'
        );
    }
});

// ---------------------------------------------------------------------------
// Exposition REST : permet a un agent exterieur de tirer la file et de repartir
// le travail. Lecture seule, reservee aux comptes capables d editer.
// ---------------------------------------------------------------------------
add_action('rest_api_init', function () {
    register_rest_route('cultura/v1', '/completude', array(
        'methods'  => 'GET',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
        'callback' => function ($req) {
            $releve = get_option('cs_completude_file', array());
            $limite = (int) $req->get_param('limite');
            $filtre = (string) $req->get_param('manque');
            if (!empty($releve['file'])) {
                if ($filtre !== '') {
                    $releve['file'] = array_values(array_filter($releve['file'], function ($f) use ($filtre) {
                        return in_array($filtre, $f['manques'], true);
                    }));
                }
                if ($limite > 0) { $releve['file'] = array_slice($releve['file'], 0, $limite); }
            }
            return rest_ensure_response($releve);
        },
    ));
});

// Declenchement manuel : ?cs_dbg_completude=sabauda (administrateurs).
add_action('init', function () {
    if (empty($_GET['cs_dbg_completude']) || $_GET['cs_dbg_completude'] !== 'sabauda') { return; }
    if (!current_user_can('manage_options')) { wp_die('Acces reserve.', 403); }
    header('Content-Type: text/plain; charset=utf-8');
    $r = cs_completude_passe();
    unset($r['file']);
    print_r($r);
    exit;
});
// ---------------------------------------------------------------------------
// 4. Garde-fou d indexation (protection de l evaluation AdSense / Google)
//
// Une fiche sans source officielle ou au corps indigent est du contenu mince :
// laissee dans l index, elle tire vers le bas l evaluation de tout le domaine.
// On la sort de l index et du sitemap SANS la retirer du site : un visiteur qui
// arrive dessus la voit toujours, mais elle ne pese plus dans le jugement global.
// Le retrait est automatiquement leve des que la fiche est completee, puisqu il
// se lit sur as_completude_manques, recalcule a chaque passe quotidienne.
// ---------------------------------------------------------------------------
if (!function_exists('cs_completude_hors_index')) {
function cs_completude_hors_index($id) {
    $m = (string) get_post_meta($id, 'as_completude_manques', true);
    if ($m === '') { return false; }
    $l = explode(',', $m);
    return in_array('source_officielle', $l, true) || in_array('corps_indigent', $l, true);
}
}

// Balise robots : noindex, follow (les liens sortants restent suivis).
add_filter('wpseo_robots_array', function ($robots) {
    if (!is_singular('tribe_events')) { return $robots; }
    if (!cs_completude_hors_index(get_queried_object_id())) { return $robots; }
    $robots['index'] = 'noindex';
    return $robots;
}, 20);

// Repli si le theme n utilise pas le tableau Yoast.
add_filter('wpseo_robots', function ($chaine) {
    if (!is_singular('tribe_events')) { return $chaine; }
    if (!cs_completude_hors_index(get_queried_object_id())) { return $chaine; }
    return 'noindex, follow';
}, 20);

// Exclusion du sitemap : liste calculee une fois par jour, pas a chaque requete.
add_filter('wpseo_exclude_from_sitemap_by_post_ids', function ($ids) {
    $hors = (array) get_option('cs_completude_hors_index_ids', array());
    return array_values(array_unique(array_merge((array) $ids, $hors)));
});
// Emission directe de la balise robots. Constate le 2026-08-08 : Yoast n emet
// AUCUNE balise robots sur ce site, les filtres wpseo_robots* n avaient donc
// rien a intercepter. On l ecrit nous-memes, tot dans le head.
add_action('wp_head', function () {
    if (!is_singular('tribe_events')) { return; }
    if (!cs_completude_hors_index(get_queried_object_id())) { return; }
    echo '<meta name="robots" content="noindex, follow" data-cs="cs-completude-noindex">' . "\n";
}, 1);
