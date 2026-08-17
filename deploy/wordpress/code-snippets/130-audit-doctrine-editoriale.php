/**
 * CS - Audit doctrine editoriale (quotidien, rapport Slack)
 *
 * Pourquoi : la doctrine (vault Obsidian, 01-Commun/Vocabulaire interdit.md) prevoit un
 * controle du vocabulaire interdit "en passe-3 avec alerte utilisateur, pas de blocage
 * silencieux" cote pipeline. Cette alerte n'a pas de destinataire : des infractions sont
 * donc parties en publication (tirets cadratins dans les titres Yoast, "espace alpin",
 * "francoprovencal", fiches francaises etiquetees lang=it). Constate le 2026-08-08.
 *
 * Ce fichier ne remplace pas le correctif amont : il constate ce qui est REELLEMENT publie
 * et le signale sur Slack (webhook des formulaires publics, deja configure), pour qu'une
 * derive ne soit plus decouverte trois semaines plus tard.
 *
 * Controles : vocabulaire interdit (avec les exceptions prevues par la doctrine :
 * noms propres, statut "travailleur frontalier"), tirets cadratins en contenu VISIBLE
 * (commentaires HTML exclus), fiches etiquetees italien dont le texte est francais,
 * titres SEO effectifs > 60 caracteres, doublons date+lieu+langue.
 *
 * Resultat dans l'option cs_doctrine_audit (avec last_run, pour qu'un watchdog voie
 * que la tache tourne). Slack uniquement s'il y a quelque chose a signaler.
 * Declenchement manuel : ?cs_dbg_doctrine=sabauda (administrateurs).
 */

if (!function_exists('cs_doctrine_score_fr')) {
    // Marqueurs francais absents de l'italien courant. Sert a reperer une fiche
    // etiquetee IT dont le texte est reste en francais.
    function cs_doctrine_score_fr($texte) {
        $mots = array(' les ',' des ',' une ',' aux ',' avec ',' pour ',' dans ',' est ',' sont ',
            ' cette ',' leur ',' ses ',' qui ',' que ',' ainsi ',' entre ',' depuis ',' jusqu',
            ' chaque ',' sous ',' vers ',' peut ',' propose ',' accueille ');
        $t = ' ' . mb_strtolower($texte) . ' ';
        $s = 0;
        foreach ($mots as $m) { $s += substr_count($t, $m); }
        return $s;
    }
}

if (!function_exists('cs_doctrine_run_audit')) {
function cs_doctrine_run_audit() {
    global $wpdb;
    $em = json_decode('"—"');

    $rows = $wpdb->get_results(
        "SELECT ID, post_type, post_title, post_content, post_excerpt FROM {$wpdb->posts}
         WHERE post_status='publish' AND post_type IN ('tribe_events','post','page','selection')",
        ARRAY_A
    );

    // Exceptions explicitement prevues par la doctrine : noms propres d'institutions et
    // d'evenements, et le statut administratif "travailleur frontalier". On les masque
    // avant de chercher les termes interdits, sinon on signale du legitime.
    $exceptions = array(
        '/travailleu(?:r|se)s?\s+frontali[e\x{e8}]re?s?/iu',
        '/sans\s+Fronti[e\x{e8}]res/iu',
        '/Centre\s+d[\x{2019}\']\x{e9}tudes\s+francoproven\x{e7}ales[^.<]*/iu',
        '/F\x{ea}te\s+internationale\s+du\s+francoproven\x{e7}al/iu',
        '/F\x{ea}te\s+vald\x{f4}taine\s+et\s+internationale\s+des\s+patois/iu',
        '/Interreg[^.<]{0,40}|Alcotra|GECT/iu',
    );

    $termes = array(
        'transfrontalier'    => '/transfrontali[e\x{e8}]r\w*/iu',
        'frontiere'          => '/fronti\x{e8}re\w*/iu',
        'frontalier'         => '/frontali[e\x{e8}]r\w*/iu',
        'patois'             => '/patois/iu',
        'francoprovencal'    => '/francoproven\w*/iu',
        'arpitan'            => '/arpitan\w*/iu',
        'langues regionales' => '/langues?\s+r\x{e9}gionales?/iu',
        'espace alpin'       => '/espace\s+alpin|spazio\s+alpino/iu',
        // Equivalents italiens, decision du 8 aout 2026 (cf. Vocabulaire interdit.md).
        'confine (it)'       => '/\bconfin[ei]\b/iu',
        'transfrontaliero'   => '/transfrontalier[oaie]\w*/iu',
        'lingue regionali'   => '/lingue\s+regionali/iu',
        // Gentiles : Lexique sabaud l.41 et l.90. En italien on ecrit "Savoia" avec
        // la province (prov. Annecy pour le 74), jamais "Alta Savoia".
        'alta savoia'        => '/Alta\s+Savoia/iu',
        'haut-savoyard'      => '/haut[- ]savoyard|altosavoiard\w*/iu',
        'francais de Savoie' => '/fran\x{e7}ais\s+de\s+Savoie/iu',
    );

    // Occurrences examinees et validees comme legitimes (metaphores, noms propres) :
    // option cs_doctrine_audit_ignore_vocab, format array('terme' => array(ids)).
    $ignore_vocab = (array) get_option('cs_doctrine_audit_ignore_vocab', array());

    $vocab = array();
    $cadratins = array();
    $langue = array();
    $index = array();

    foreach ($rows as $r) {
        // Les commentaires HTML sont des notes de developpement, invisibles pour le
        // lecteur : ils ne relevent pas de la doctrine editoriale et sont retires
        // avant tout controle (sinon les gabarits d'accueil ressortent en boucle).
        $contenu_visible = preg_replace('/<!--.*?-->/s', '', $r['post_content']);
        $brut = $r['post_title'] . "\n" . $contenu_visible . "\n" . $r['post_excerpt'];
        $texte = html_entity_decode($brut, ENT_QUOTES, 'UTF-8');

        // --- vocabulaire interdit, exceptions masquees ---
        $masque = $texte;
        foreach ($exceptions as $ex) { $masque = preg_replace($ex, ' ', $masque); }
        foreach ($termes as $nom => $re) {
            if (preg_match($re, $masque)) {
                $valides = isset($ignore_vocab[$nom]) ? (array) $ignore_vocab[$nom] : array();
                if (!in_array((int) $r['ID'], $valides, true)) {
                    $vocab[$nom][] = (int) $r['ID'];
                }
            }
        }

        // --- tirets cadratins : contenu VISIBLE seulement ---
        $visible = $texte;
        if (mb_strpos($visible, $em) !== false) { $cadratins[] = (int) $r['ID']; }

        // --- fiche etiquetee italien dont le texte est francais ---
        if (function_exists('pll_get_post_language') && pll_get_post_language($r['ID']) === 'it') {
            if (cs_doctrine_score_fr(wp_strip_all_tags($texte)) >= 12) { $langue[] = (int) $r['ID']; }
        }

        // --- doublons date + lieu + langue (evenements seulement) ---
        if ($r['post_type'] === 'tribe_events') {
            $d = get_post_meta($r['ID'], '_EventStartDate', true);
            $v = get_post_meta($r['ID'], '_EventVenueID', true);
            if ($d && $v) {
                $lg = function_exists('pll_get_post_language') ? pll_get_post_language($r['ID']) : 'x';
                $index[$d . '|' . $v . '|' . $lg][] = (int) $r['ID'];
            }
        }
    }

    // Doublons deja examines et juges legitimes (evenements distincts au meme lieu
    // le meme jour) : listes dans l'option cs_doctrine_audit_ignore, format "597+2211".
    $ignores = (array) get_option('cs_doctrine_audit_ignore', array());
    $doublons = array();
    foreach ($index as $cle => $ids) {
        if (count($ids) < 2) { continue; }
        sort($ids);
        if (in_array(implode('+', $ids), $ignores, true)) { continue; }
        $doublons[] = implode(' + ', $ids);
    }

    // --- titres SEO effectifs > 60 caracteres ---
    $titres = $wpdb->get_results(
        "SELECT p.ID, p.post_title, m.meta_value AS y FROM {$wpdb->posts} p
         LEFT JOIN {$wpdb->postmeta} m ON m.post_id = p.ID AND m.meta_key = '_yoast_wpseo_title'
         JOIN {$wpdb->postmeta} f ON f.post_id = p.ID AND f.meta_key = '_EventEndDate'
         WHERE p.post_type = 'tribe_events' AND p.post_status = 'publish'
           AND SUBSTRING(f.meta_value, 1, 10) >= '" . current_time('Y-m-d') . "'",
        ARRAY_A
    );
    $trop_longs = 0; $sans_titre_seo = 0;
    foreach ($titres as $t) {
        $a_titre = ($t['y'] !== null && $t['y'] !== '');
        if (!$a_titre) { $sans_titre_seo++; }
        $eff = $a_titre ? $t['y'] : $t['post_title'];
        if (mb_strlen(html_entity_decode($eff, ENT_QUOTES, 'UTF-8')) > 60) { $trop_longs++; }
    }

    $res = array(
        'last_run'       => current_time('mysql'),
        'analyses'       => count($rows),
        'vocabulaire'    => $vocab,
        'cadratins'      => $cadratins,
        'langue_it_fr'   => $langue,
        'doublons'       => $doublons,
        'titres_longs'   => $trop_longs,
        'sans_titre_seo' => $sans_titre_seo,
    );
    update_option('cs_doctrine_audit', $res, false);

    // PERIMETRE DU RAPPORT (2026-08-17) : voir cs-audit-perimetre.php. L'option
    // ci-dessus garde TOUT ; seul le message est reduit a ce sur quoi un geste est
    // encore possible. Verifie ce jour-la sur les 25 fiches signalees par les trois
    // audits : 12 passees (six depuis juillet), 3 a la corbeille. Le compte des titres
    // SEO est filtre dans sa requete, plus haut, pour la meme raison.
    $mention_perimetre = '';
    if (function_exists('cs_audit_devant_nous')) {
        $stats = array();
        foreach ($vocab as $nom => $ids_v) {
            $fv = cs_audit_devant_nous($ids_v);
            if ($fv['gardes']) { $vocab[$nom] = $fv['gardes']; } else { unset($vocab[$nom]); }
            $stats[] = $fv;
        }
        $fc = cs_audit_devant_nous($cadratins); $cadratins = $fc['gardes']; $stats[] = $fc;
        $fg = cs_audit_devant_nous($langue);    $langue    = $fg['gardes']; $stats[] = $fg;
        // Un doublon ne compte que si au moins une de ses deux fiches est encore devant
        // nous : defusionner un doublon passe ne rend service a personne.
        $gardes_doublons = array();
        foreach ($doublons as $paire) {
            $ids_d = array_map('intval', preg_split('/\s*\+\s*/', $paire));
            $fd = cs_audit_devant_nous($ids_d);
            if ($fd['gardes']) { $gardes_doublons[] = $paire; }
        }
        // Compte a part : un doublon ecarte ne se voit dans aucune des listes
        // ci-dessus, donc sans ce compteur le total passerait de 7 a 6 sans le dire.
        $doublons_ecartes = count($doublons) - count($gardes_doublons);
        $doublons = $gardes_doublons;
        if ($stats) {
            $cumul = call_user_func_array('cs_audit_cumuler', $stats);
            $mention_perimetre = function_exists('cs_audit_mention_ecartes')
                ? cs_audit_mention_ecartes($cumul) : '';
            if ($doublons_ecartes > 0) {
                $mention_perimetre .= ($mention_perimetre === '' ? '' : "\n")
                    . '_Et ' . $doublons_ecartes . ' doublon(s) dont aucune des deux fiches'
                    . ' n est encore devant nous._';
            }
            if ($mention_perimetre !== '') { $mention_perimetre = "\n" . $mention_perimetre; }
        }
    }

    // --- rapport Slack, uniquement s'il y a quelque chose a signaler ---
    $lignes = array();
    foreach ($vocab as $nom => $ids) {
        $lignes[] = '*' . $nom . '* : ' . count($ids) . ' fiche(s) -> ' . implode(', ', array_slice($ids, 0, 8));
    }
    if ($cadratins)  { $lignes[] = '*tirets cadratins visibles* : ' . count($cadratins) . ' -> ' . implode(', ', array_slice($cadratins, 0, 8)); }
    if ($langue)     { $lignes[] = '*etiquetees IT mais texte FR* : ' . count($langue) . ' -> ' . implode(', ', array_slice($langue, 0, 8)); }
    if ($doublons)   { $lignes[] = '*doublons date+lieu+langue* : ' . implode(' | ', array_slice($doublons, 0, 6)); }
    if ($trop_longs) { $lignes[] = '*titres SEO > 60 car., evenements encore devant nous* : ' . $trop_longs . ' (dont ' . $sans_titre_seo . ' sans titre Yoast ecrit par le pipeline)'; }

    if ($lignes && function_exists('cs_slack_notify_form')) {
        cs_slack_notify_form(
            ":triangular_ruler: *Audit doctrine — agendasabauda.eu*\n"
            . $res['analyses'] . " contenus publies analyses\n"
            . implode("\n", $lignes)
            . $mention_perimetre
        );
    }
    return $res;
}
}

add_action('cs_doctrine_audit_event', 'cs_doctrine_run_audit');
if (!wp_next_scheduled('cs_doctrine_audit_event')) {
    wp_schedule_event(time() + 600, 'daily', 'cs_doctrine_audit_event');
}

// Declenchement manuel : ?cs_dbg_doctrine=sabauda (administrateurs uniquement).
add_action('init', function () {
    if (empty($_GET['cs_dbg_doctrine']) || $_GET['cs_dbg_doctrine'] !== 'sabauda') { return; }
    if (!current_user_can('manage_options')) { wp_die('Acces reserve.', 403); }
    header('Content-Type: text/plain; charset=utf-8');
    print_r(cs_doctrine_run_audit());
    exit;
});