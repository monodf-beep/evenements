<?php
/*
Plugin Name: Agenda Sabauda — Choix de langue Piémont/Vallée d'Aoste + libellé dynamique
Description: Correctifs demandes par Franck le 2026-07-20 sur le switcher territoire de la
  home :
  1) Cliquer sur Piémont/Vallee d'Aoste (territoires bilingues) ne doit PLUS basculer
     automatiquement en italien -- une page de choix intermediaire demande la langue.
  2) Le libelle "Vous regardez X" / "Stai guardando X" doit refleter la vraie selection
     courante (?as_territoire=), pas rester fige sur Savoie/Savoia.
  3) Le filtre FR (cs-home-territoire-filtre.php) est etendu pour accepter piemont/
     vallee-d-aoste cote FR (choix "continuer en francais"), pas seulement Savoie/Nice.

  Rollback : supprimer ce fichier. Les liens "Piemont"/"Vallee d'Aoste" du switcher
  retomberaient alors sur une page de choix inexistante (404) -- remettre aussi les hrefs
  directs vers /it/ si rollback total souhaite (cf. historique git du post_content).
*/
if (!defined('ABSPATH')) { exit; }

// 1) Page de choix de langue, interceptee sur les home FR/IT via ?choix_territoire=<slug fr>.
//
// 2026-09-21 (Franck, capture de /choisir/piemont/) : « ca semble presque un message
// d'erreur, si tu peux rendre plus comprehensible, plus visuel ces pages ». Trois reprises
// ont ete necessaires, et chacune a appris quelque chose qui vaut d'etre ecrit ici.
//
// (1) LA CHARTE NE S'INVENTE PAS. J'avais d'abord pose deux grands aplats pleins cote a
// cote. Refus : « c'est pas dans la charte cultura sabauda > agenda sabauda -- irregulier,
// pas forcement droit ». Elle etait lisible depuis le debut dans le HTML de la home,
// mesuree ce jour-la : tuiles INCLINEES, chacune d'un angle different (douze rotate()
// entre -1,3 et +1,3 degre, jusqu'au bloc newsletter a -0,6) ; carte a fond blanc, BORD
// D'ENCRE 1.5px #1D1D1B, rayon 4px ; sur-titre en petites capitales tres espacees
// (letter-spacing .18em) a l'accent #DC5D45 ; titre en 'La Semplicita'/'Saira Condensed' ;
// filet 1px pour separer ; pictos SVG au trait tremble (stroke 2.3, bouts ronds), d'ou la
// fleche dessinee plutot qu'un trait droit ; et l'accent RARE, jamais un aplat.
//
// (2) LE VISUEL NE SUFFISAIT PAS, C'EST L'INFORMATION QUI MANQUAIT. « visuellement elles
// sont top, c'est dans l'information qu'on ne comprend pas » : les deux cartes disaient
// quatre fois la meme chose, une fois par langue. Rien n'y disait ce qui CHANGE. D'ou
// l'apercu : les prochains evenements du territoire, dans la langue de la carte. Le
// prochain etant en general le meme des deux cotes, les deux cartes montrent le MEME
// evenement dans les deux langues -- on voit la difference mot a mot, sans l'expliquer.
// Le nombre exact d'evenements a venir a ete ecarte par Franck (mesure du 21/09 : 34
// cote FR contre 26 cote IT pour le Piemont -- l'ecart est reel, l'afficher etait une
// decision editoriale, pas technique).
//
// (3) SUR MOBILE, MOINS. Premiere version mobile : cartes empilees avec trois evenements
// chacune, 849 px de haut, la carte italienne sous la ligne de flottaison. « en mobile ca
// marche pas, c'est trop d'infos et 1 carte l'une sur l'autre ». Donc : les deux cartes
// restent COTE A COTE quelle que soit la largeur -- c'est la symetrie des deux colonnes
// qui fait lire « choix » et non « alerte » -- et c'est la QUANTITE qui s'adapte : un seul
// evenement et un libelle court sous 620 px (bloc de 420 px, les deux options tiennent
// sans defiler), trois evenements et le libelle complet au-dessus.
//
// Deux defauts mesures et corriges au passage, plutot que supposes :
//   - <title> : la page est servie par page_id=928, donc l'onglet annoncait « Agenda
//     Sabauda : quoi faire, ou manger ». Elle a desormais le sien. Le canonical reste
//     celui de la home -- il est deja juste, on n'y touche pas ;
//   - DEBORDEMENT HORIZONTAL : '.site-content' du theme est en display:flex, donc un
//     enfant prend sa largeur de CONTENU et depasse l'ecran. A 390 px la page en ligne
//     mesurait 415 px (elle scrollait lateralement) ; width:100% + min-width:0 la ramene
//     a 375. Le defaut existait avant ce correctif, il n'est pas ne ici.

if (!function_exists('cs_choix_langue_evenements')) {
/**
 * Les prochains evenements publies d'un territoire, dans une langue.
 *
 * DEUX FILES, ET C'EST LA LECON DU 21/09 AU SOIR. La premiere version ne posait que le
 * filtre de la regle 5 (CLAUDE.md) : end_date >= maintenant, tri par date de DEBUT. C'est
 * juste au sens de la regle -- une exposition de janvier a decembre est bien en cours --
 * mais la carte affichait alors « 1 janv. », « 10 fev. », « 9 avril » : trois expositions
 * au long cours, et pas une seule des 33 fiches qui commencent dans les jours qui
 * viennent. Le lecteur y lit une date perimee, pas un agenda. Vu sur la page EN LIGNE,
 * pas dans le code : c'est la sortie reelle qui l'a montre.
 *
 * Donc :
 *   (a) d'abord ce qui COMMENCE a partir d'aujourd'hui, du plus proche au plus lointain ;
 *   (b) s'il en manque -- petit territoire, creux de saison --, on complete avec ce qui
 *       est EN COURS, en affichant la date de FIN (« jusqu'au 11 oct. »), qui est la seule
 *       information utile sur une exposition deja commencee. La regle 5 est donc tenue :
 *       rien de termine, et l'en-cours compte.
 *
 * Mesure du 21/09 (commencent / en cours) : piemont 33/23, piemonte 25/14,
 * vallee-d-aoste 10/4, valle-d-aosta 7/2. La file (b) ne sert donc jamais aujourd'hui ;
 * elle existe pour le jour ou un territoire sera a sec.
 *
 * Le terme de territoire porte deja la langue (piemont / piemonte sont deux termes
 * distincts), mais on passe AUSSI 'lang' : la page est servie par la home FR, donc
 * Polylang filtrerait sinon la requete italienne sur le francais et la carte de droite
 * resterait vide.
 *
 * Cache : une heure. Un resultat VIDE n'est garde que 10 minutes -- si le vide vient
 * d'une panne plutot que d'une absence d'evenements, on ne le fige pas pour une heure.
 */
function cs_choix_langue_evenements($terme_slug, $langue, $limite = 3) {
    $cle = 'cs_choix_evts2_' . $terme_slug;
    $cache = get_transient($cle);
    if (is_array($cache)) {
        return $cache;
    }

    $aujourdhui = current_time('Y-m-d') . ' 00:00:00';
    $maintenant = current_time('mysql');
    $base = array(
        'post_type'           => 'tribe_events',
        'post_status'         => 'publish',
        'no_found_rows'       => true,
        'ignore_sticky_posts' => true,
        'lang'                => $langue,
        'tax_query'           => array(array(
            'taxonomy' => 'territoire',
            'field'    => 'slug',
            'terms'    => $terme_slug,
        )),
    );

    $lire = function ($posts, $champ) {
        $out = array();
        foreach ($posts as $p) {
            $d = get_post_meta($p->ID, $champ === 'fin' ? '_EventEndDate' : '_EventStartDate', true);
            if (!$d) {
                continue;
            }
            $out[] = array(
                'titre' => get_the_title($p),
                'jour'  => (int) substr($d, 8, 2),
                'mois'  => (int) substr($d, 5, 2),
                'quand' => $champ,
            );
        }
        return $out;
    };

    // (a) ce qui commence a partir d'aujourd'hui
    $a = $base;
    $a['posts_per_page'] = $limite;
    $a['meta_query'] = array('debut' => array('key' => '_EventStartDate', 'value' => $aujourdhui, 'compare' => '>=', 'type' => 'DATETIME'));
    $a['orderby'] = array('debut' => 'ASC');
    $q = new WP_Query($a);
    $evts = $lire($q->posts, 'debut');

    // (b) complement : ce qui est deja commence mais pas fini, au plus proche de sa fin
    if (count($evts) < $limite) {
        $b = $base;
        $b['posts_per_page'] = $limite - count($evts);
        $b['meta_query'] = array(
            'debut' => array('key' => '_EventStartDate', 'value' => $aujourdhui, 'compare' => '<', 'type' => 'DATETIME'),
            'fin'   => array('key' => '_EventEndDate', 'value' => $maintenant, 'compare' => '>=', 'type' => 'DATETIME'),
        );
        $b['orderby'] = array('fin' => 'ASC');
        $q2 = new WP_Query($b);
        $evts = array_merge($evts, $lire($q2->posts, 'fin'));
    }
    wp_reset_postdata();

    set_transient($cle, $evts, $evts ? HOUR_IN_SECONDS : 10 * MINUTE_IN_SECONDS);
    return $evts;
}
}

if (!function_exists('cs_choix_langue_date')) {
/**
 * « 23 sept. » quand l'evenement commence ; « jusqu'au 11 oct. » / « fino all'11 ott. »
 * quand il est deja en cours -- sur une exposition commencee en janvier, la seule date
 * qui renseigne est celle de la fin.
 *
 * Table de mois en dur plutot que date_i18n() : la page italienne est servie par un
 * WordPress en francais (c'est la home FR qui l'affiche), donc la locale ne donnerait
 * pas les abreviations italiennes.
 *
 * L'italien elide devant une voyelle : « fino all'8 », « fino all'11 » (otto, undici),
 * « fino al 12 » ailleurs. Deux nombres concernes, la regle tient en une ligne.
 */
function cs_choix_langue_date($jour, $mois, $langue, $quand = 'debut') {
    $fr = array(1 => 'janv.', 'fév.', 'mars', 'avril', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.');
    $it = array(1 => 'genn.', 'febbr.', 'mar.', 'apr.', 'magg.', 'giugno', 'luglio', 'ag.', 'set.', 'ott.', 'nov.', 'dic.');
    $mois = (int) $mois;
    $jour = (int) $jour;
    $t = $langue === 'it' ? $it : $fr;
    if (!$mois || !$jour || !isset($t[$mois])) {
        return '';
    }
    $date = $jour . ' ' . $t[$mois];
    if ($quand !== 'fin') {
        return $date;
    }
    if ($langue === 'it') {
        return (in_array($jour, array(8, 11), true) ? "fino all'" : 'fino al ') . $date;
    }
    return "jusqu'au " . $date;
}
}

if (!function_exists('cs_choix_langue_carte')) {
/** Une des deux cartes. $evts vide : la carte garde son nom et son bouton, sans liste. */
function cs_choix_langue_carte($langue, $libelle_langue, $nom, $url, $cta_court, $cta_long, $evts, $classe, $terme_slug) {
    $fleche = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.4 12.3c4.6-.5 11.5-.7 17.1-.6"/><path d="M14.6 6.1c1.9 2.1 4 4.1 5.9 5.6c-2 1.6-4.1 3.6-5.8 5.9"/></svg>';

    $h = '<a class="cs-choix__carte ' . esc_attr($classe) . '" href="' . esc_url($url) . '" hreflang="' . esc_attr($langue) . '"' . ($langue === 'it' ? ' lang="it"' : '') . '>';
    $h .= '<span class="cs-choix__langue">' . esc_html($libelle_langue) . '</span>';
    $h .= '<span class="cs-choix__nom">' . esc_html($nom) . '</span>';

    if ($evts) {
        $h .= '<ul class="cs-choix__liste">';
        foreach ($evts as $e) {
            $d = cs_choix_langue_date($e['jour'], $e['mois'], $langue, isset($e['quand']) ? $e['quand'] : 'debut');
            $h .= '<li><b>' . esc_html($d) . '</b><span>' . esc_html($e['titre']) . '</span></li>';
        }
        $h .= '</ul>';
    } else {
        // Un zero doit dire d'ou il vient (CLAUDE.md) : absence d'evenements a venir, ou
        // requete qui n'a rien rendu ? La source de la page le dit, sans rien montrer au
        // lecteur.
        $h .= '<!-- cs-choix : aucun evenement a venir pour territoire=' . esc_html($terme_slug) . ' lang=' . esc_html($langue) . ' -->';
    }

    $h .= '<span class="cs-choix__cta">' . esc_html($cta_court) . '<i>' . esc_html($cta_long) . '</i> ' . $fleche . '</span>';
    return $h . '</a>';
}
}

add_action('template_redirect', function () {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (is_admin() || !is_page($home_ids) || empty($_GET['choix_territoire'])) {
        return;
    }

    $slug = sanitize_title(wp_unslash($_GET['choix_territoire']));
    $noms = [
        'piemont' => [
            'fr' => 'Piémont', 'it' => 'Piemonte', 'it_slug' => 'piemonte', 'coul' => '#B3261E',
            'note_fr' => 'Ici, tu choisis la langue du site : le territoire, lui, reste le Piémont.',
        ],
        'vallee-d-aoste' => [
            'fr' => "Vallée d'Aoste", 'it' => "Valle d'Aosta", 'it_slug' => 'valle-d-aosta', 'coul' => '#1E7D34',
            'note_fr' => "Ici, tu choisis la langue du site : le territoire, lui, reste la Vallée d'Aoste.",
        ],
    ];
    if (!isset($noms[$slug])) {
        return;
    }
    $n = $noms[$slug];

    add_filter('pre_get_document_title', function () use ($n) {
        return $n['fr'] . ' / ' . $n['it'] . ' — choisir la langue | Agenda Sabauda';
    }, 99);

    $evts_fr = cs_choix_langue_evenements($slug, 'fr');
    $evts_it = cs_choix_langue_evenements($n['it_slug'], 'it');

    get_header();
    ?>
    <style id="cs-choix-langue">
    .cs-choix{--cs-coul:#1D1D1B;width:100%;min-width:0;max-width:820px;margin:0 auto;padding:22px 14px 40px;box-sizing:border-box;font-family:'Nunito Sans',sans-serif;color:#1D1D1B}
    .cs-choix *{box-sizing:border-box}
    .cs-choix__sur{margin:0 0 8px;font-size:9.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#DC5D45;text-align:center}
    .cs-choix__titre{font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:clamp(26px,7vw,38px);line-height:1.04;letter-spacing:.02em;margin:0;text-align:center}
    .cs-choix__titre em{font-style:normal;color:var(--cs-coul)}
    .cs-choix__q{margin:12px 0 0;font-size:14px;font-weight:700;line-height:1.35;text-align:center}
    .cs-choix__q--it{margin:1px 0 0;font-size:14px;font-weight:600;line-height:1.35;color:#6F6B62;text-align:center}
    .cs-choix__grille{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}
    .cs-choix__carte{display:block;min-width:0;background:#fff;border:1.5px solid #1D1D1B;border-radius:4px;padding:14px 13px 13px;text-decoration:none;color:#1D1D1B;transition:transform .16s ease,background-color .16s ease}
    .cs-choix__carte--fr{transform:rotate(-1.2deg)}
    .cs-choix__carte--it{transform:rotate(1deg)}
    .cs-choix__carte:hover,.cs-choix__carte:focus-visible{transform:rotate(0deg);background:#FBF7F0;color:#1D1D1B}
    .cs-choix__carte:focus-visible{outline:2px solid #1D1D1B;outline-offset:3px}
    .cs-choix__langue{display:block;font-size:9px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:#DC5D45;margin-bottom:4px}
    .cs-choix__nom{display:block;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:20px;line-height:1.05;letter-spacing:.02em}
    .cs-choix__liste{list-style:none;margin:10px 0 0;padding:9px 0 0;border-top:1px solid #E3DCCE}
    .cs-choix__liste li{font-size:11.5px;line-height:1.3;margin-bottom:7px}
    .cs-choix__liste b{display:block;color:#DC5D45;font-weight:800;font-size:10px;margin-bottom:1px}
    .cs-choix__liste span{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
    .cs-choix__cta{display:flex;align-items:center;gap:5px;border-top:1px solid #1D1D1B;padding-top:8px;margin-top:11px;font-size:12.5px;font-weight:800}
    .cs-choix__cta i{font-style:normal}
    .cs-choix__pied{margin:20px 0 0;text-align:center;font-size:12.5px;line-height:1.5;color:#6F6B62}
    .cs-choix__pied span{display:block}
    .cs-choix__sortie{margin:11px auto 0;padding-top:10px;max-width:420px;border-top:1px solid #E3DCCE}
    .cs-choix__sortie a{color:#6F6B62;text-decoration:underline;text-underline-offset:2px}
    .cs-choix__sortie a:hover{color:#1D1D1B}
    /* Sous 620 px : un seul evenement, libelle court. La carte italienne doit rester
       visible en meme temps que la francaise, sinon on ne choisit plus, on decouvre. */
    @media(max-width:619px){
      .cs-choix__liste li:nth-child(n+2){display:none}
      .cs-choix__cta i{display:none}
    }
    @media(min-width:620px){
      .cs-choix{padding:26px 22px 48px}
      .cs-choix__grille{gap:20px;margin-top:22px}
      .cs-choix__carte{padding:20px 20px 18px}
      .cs-choix__langue{font-size:9.5px;letter-spacing:.18em;margin-bottom:6px}
      .cs-choix__nom{font-size:26px}
      .cs-choix__q,.cs-choix__q--it{font-size:15px}
      .cs-choix__liste{margin-top:12px;padding-top:11px}
      .cs-choix__liste li{display:flex;gap:9px;font-size:12.5px;margin-bottom:8px}
      .cs-choix__liste b{flex:0 0 76px;font-size:11px;margin:0;padding-top:1px}
      .cs-choix__liste span{-webkit-line-clamp:2}
      .cs-choix__cta{gap:7px;font-size:13.5px;padding-top:9px;margin-top:14px}
      .cs-choix__pied{font-size:13px;margin-top:24px}
    }
    @media(prefers-reduced-motion:reduce){.cs-choix__carte{transition:none}}
    </style>
    <div class="cs-choix" style="--cs-coul:<?php echo esc_attr($n['coul']); ?>">
      <p class="cs-choix__sur">Territoire bilingue · <span lang="it">Territorio bilingue</span></p>
      <h1 class="cs-choix__titre"><?php echo esc_html($n['fr']); ?> / <em lang="it"><?php echo esc_html($n['it']); ?></em></h1>
      <p class="cs-choix__q">Dans quelle langue veux-tu continuer ?</p>
      <p class="cs-choix__q--it" lang="it">In quale lingua vuoi continuare?</p>
      <div class="cs-choix__grille">
        <?php
        echo cs_choix_langue_carte(
            'fr', 'Français', $n['fr'],
            'https://agendasabauda.eu/explore/' . $slug . '/',
            'Continuer', ' en français', $evts_fr, 'cs-choix__carte--fr', $slug
        );
        echo cs_choix_langue_carte(
            'it', 'Italiano', $n['it'],
            'https://agendasabauda.eu/it/scopri/' . $n['it_slug'] . '/',
            'Continua', ' in italiano', $evts_it, 'cs-choix__carte--it', $n['it_slug']
        );
        ?>
      </div>
      <p class="cs-choix__pied">
        <span><?php echo esc_html($n['note_fr']); ?></span>
        <span class="cs-choix__sortie">
          <a href="https://agendasabauda.eu/espace-sabaudo/" hreflang="fr">Voir les 4 territoires</a>
          &nbsp;·&nbsp;
          <a href="https://agendasabauda.eu/it/spazio-sabaudo/" hreflang="it" lang="it">Vedi i 4 territori</a>
        </span>
      </p>
    </div>
    <?php
    get_footer();
    exit;
}, 5);

// 2) Libelle actif dynamique ("Vous regardez X") sur les 2 bandeaux (desktop + mobile), qui
// partagent tous deux exactement le meme balisage <strong style="color:#DC5D45">NOM</strong>.
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (!is_page($home_ids) || empty($_GET['as_territoire'])) {
        return $content;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $param = sanitize_title(wp_unslash($_GET['as_territoire']));

    $names_fr = ['savoie' => 'Savoie', 'piemont' => 'Piémont', 'vallee-d-aoste' => "Vallée d'Aoste", 'comte-de-nice' => 'Comté de Nice'];
    $names_it = ['piemonte' => 'Piemonte', 'valle-d-aosta' => "Valle d'Aosta", 'savoia' => 'Savoia', 'contea-di-nizza' => 'Contea di Nizza'];
    $names = $lang === 'it' ? $names_it : $names_fr;

    if (!isset($names[$param])) {
        return $content;
    }

    $default_name = $lang === 'it' ? 'i 4 territori' : 'les 4 territoires';
    $new_name = $names[$param];
    if ($new_name === $default_name) {
        return $content;
    }

    $content = str_replace(
        '<strong style="color:#DC5D45">' . esc_html($default_name) . '</strong>',
        '<strong style="color:#DC5D45">' . esc_html($new_name) . '</strong>',
        $content
    );

    return $content;
}, 20);

// 3) Extension du filtre FR (cs-home-territoire-filtre.php ne gerait que Savoie/Nice cote FR)
// pour accepter aussi piemont/vallee-d-aoste : cas "continuer en francais" depuis le choix
// de langue ci-dessus. Meme mecanisme (tax_query sur les requetes 14-21), scope different
// (fichier different = nouveau comportement, convention du site).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [14, 15, 16, 17, 18, 19, 20, 21], true)) {
        return $args;
    }
    if (empty($_GET['as_territoire'])) {
        return $args;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    if ($lang !== 'fr') {
        return $args;
    }
    $param = sanitize_title(wp_unslash($_GET['as_territoire']));

    $map = ['piemont' => 6, 'vallee-d-aoste' => 8];
    if (!isset($map[$param])) {
        return $args;
    }

    $args['tax_query'] = $args['tax_query'] ?? [];
    $args['tax_query'][] = [
        'taxonomy' => 'territoire',
        'field'    => 'term_id',
        'terms'    => $map[$param],
    ];

    return $args;
}, 10, 2);

/* 2026-08-02 (Franck) : aligne le LIBELLE DU LIEN de la barre territoire des home
   sur celui des pages internes. Le libelle est fige dans le contenu Gutenberg
   ("Changer de territoire"), alors que la barre globale des pages internes dit
   desormais "Choisir un territoire" tant qu'aucun territoire n'est selectionne
   (l'appel a l'action est porte par le lien, cf. cs-territoire-persistant.php).
   Sans ce filtre, deux libelles differents cohabitaient pour le meme etat selon
   qu'on etait sur une home ou sur le reste du site. */
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928, 1717);
    if (!is_page($home_ids)) { return $content; }
    if (!function_exists('cs_territoire_actif') || cs_territoire_actif()) { return $content; }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $from = $lang === 'it' ? 'Cambia territorio' : 'Changer de territoire';
    $to   = $lang === 'it' ? 'Scegli un territorio' : 'Choisir un territoire';
    return str_replace('>' . $from . '<', '>' . $to . '<', $content);
}, 21);
