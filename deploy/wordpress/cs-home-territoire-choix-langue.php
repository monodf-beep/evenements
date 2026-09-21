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
// d'erreur, si tu peux rendre plus comprehensible, plus visuel ces pages ». La version de
// juillet posait une question de deux lignes et deux rectangles plats au milieu du vide :
// rien ne disait POURQUOI on demandait, ni ce qu'il y a derriere chaque bouton, ni comment
// repartir. Le MECANISME ne change pas (meme interception, memes deux URLs de sortie,
// verifiees 200 le 21/09) -- seule la page rendue change.
//
// PREMIERE VERSION REFUSEE le meme jour, et la lecon vaut d'etre ecrite : j'avais pose
// deux grands aplats pleins (noir + couleur) cote a cote, en inventant une DA au lieu
// d'aller lire la charte. Franck : « rien ne me va, c'est pas dans la charte cultura
// sabauda > agenda sabauda -- irregulier, pas forcement droit ». La charte etait lisible
// depuis le debut dans le HTML de la home, mesuree ce jour-la :
//   - les tuiles sont INCLINEES, chacune d'un angle different (transform:rotate(), douze
//     occurrences entre -1,3 et +1,3 degre, jusqu'au bloc newsletter a -0,6) ;
//   - carte = fond blanc ou #FBF7F0, BORD D'ENCRE 1.5px #1D1D1B, rayon 4px ;
//   - sur-titre en petites capitales tres espacees (letter-spacing .18em) a l'accent
//     #DC5D45, titre en 'La Semplicita'/'Saira Condensed' 600, texte en Nunito Sans ;
//   - filet 1px #1D1D1B pour separer, pictos SVG au trait tremble (stroke 2.3, bouts
//     ronds) -- d'ou la fleche dessinee ci-dessous plutot qu'un trait droit ;
//   - l'accent est RARE : sur-titres et liens, jamais un aplat qui mange l'ecran.
//
// D'ou cette page : deux cartes a bord d'encre legerement de travers (-1,2 et +1 degre),
// qui SE REDRESSENT au survol et au focus clavier ; le nom du territoire ecrit dans SA
// langue dans chaque carte (Piemont / Piemonte) -- c'est la le visuel, pas un aplat ; la
// phrase qui manquait dessous : ici on choisit la LANGUE DU SITE, pas le territoire,
// l'ambiguite qui faisait ressembler la page a une erreur ; et une sortie de secours vers
// les 4 territoires, dans les deux langues.
//
// Deux mesures faites au passage, plutot que supposees :
//   - <title> : la page est servie par page_id=928, donc l'onglet annoncait « Agenda
//     Sabauda : quoi faire, ou manger ». Elle a desormais le sien. Le canonical reste
//     celui de la home -- il est deja juste, on n'y touche pas ;
//   - DEBORDEMENT HORIZONTAL : '.site-content' du theme est en display:flex, donc un
//     enfant prend sa largeur de CONTENU et depasse l'ecran. A 390 px, la page en ligne
//     mesurait 415 px de large (elle scrollait lateralement) ; avec width:100% et
//     min-width:0 elle tombe a 375, soit l'ecran. Le defaut existait avant ce
//     correctif, il n'est pas ne ici.

add_action('template_redirect', function () {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (is_admin() || !is_page($home_ids) || empty($_GET['choix_territoire'])) {
        return;
    }

    $slug = sanitize_title(wp_unslash($_GET['choix_territoire']));
    $noms = [
        'piemont' => [
            'fr' => 'Piémont', 'it' => 'Piemonte', 'it_slug' => 'piemonte', 'coul' => '#B3261E',
            'sous_fr' => 'Les événements du Piémont, en français.',
            'sous_it' => 'Gli eventi del Piemonte, in italiano.',
            'note_fr' => 'Ici, tu choisis la langue du site : le territoire, lui, reste le Piémont.',
            'note_it' => 'Qui scegli la lingua del sito: il territorio resta il Piemonte.',
        ],
        'vallee-d-aoste' => [
            'fr' => "Vallée d'Aoste", 'it' => "Valle d'Aosta", 'it_slug' => 'valle-d-aosta', 'coul' => '#1E7D34',
            'sous_fr' => "Les événements de la Vallée d'Aoste, en français.",
            'sous_it' => "Gli eventi della Valle d'Aosta, in italiano.",
            'note_fr' => "Ici, tu choisis la langue du site : le territoire, lui, reste la Vallée d'Aoste.",
            'note_it' => "Qui scegli la lingua del sito: il territorio resta la Valle d'Aosta.",
        ],
    ];
    if (!isset($noms[$slug])) {
        return;
    }
    $n = $noms[$slug];

    add_filter('pre_get_document_title', function () use ($n) {
        return $n['fr'] . ' / ' . $n['it'] . ' — choisir la langue | Agenda Sabauda';
    }, 99);

    // Fleche au trait, tracee a main levee comme les pictos des tuiles de la home
    // (stroke 2.3, bouts ronds, ligne qui ondule legerement) : un trait parfaitement
    // droit jurerait a cote d'eux.
    $fleche = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.4 12.3c4.6-.5 11.5-.7 17.1-.6"/><path d="M14.6 6.1c1.9 2.1 4 4.1 5.9 5.6c-2 1.6-4.1 3.6-5.8 5.9"/></svg>';

    get_header();
    ?>
    <style id="cs-choix-langue">
    .cs-choix{--cs-coul:#1D1D1B;width:100%;min-width:0;max-width:820px;margin:0 auto;padding:26px 22px 60px;box-sizing:border-box;font-family:'Nunito Sans',sans-serif;color:#1D1D1B}
    .cs-choix__tete{text-align:center;margin-bottom:26px}
    .cs-choix__sur{margin:0 0 9px;font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#DC5D45}
    .cs-choix__titre{font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:clamp(28px,7vw,38px);line-height:1.04;letter-spacing:.02em;margin:0}
    .cs-choix__titre em{font-style:normal;color:var(--cs-coul)}
    .cs-choix__q{margin:14px 0 0;font-size:15px;font-weight:700;line-height:1.35}
    .cs-choix__q--it{margin:1px 0 0;font-size:15px;font-weight:600;line-height:1.35;color:#6F6B62}
    .cs-choix__grille{display:grid;gap:16px}
    @media(min-width:620px){.cs-choix__grille{grid-template-columns:1fr 1fr;gap:20px}}
    .cs-choix__carte{display:block;min-width:0;text-decoration:none;color:#1D1D1B;background:#fff;border:1.5px solid #1D1D1B;border-radius:4px;padding:20px 20px 18px;transition:transform .16s ease,background-color .16s ease}
    .cs-choix__carte--fr{transform:rotate(-1.2deg)}
    .cs-choix__carte--it{transform:rotate(1deg)}
    .cs-choix__carte:hover,.cs-choix__carte:focus-visible{transform:rotate(0deg);background:#FBF7F0;color:#1D1D1B}
    .cs-choix__carte:focus-visible{outline:2px solid #1D1D1B;outline-offset:3px}
    .cs-choix__langue{display:block;font-size:9.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#DC5D45;margin-bottom:6px}
    .cs-choix__nom{display:block;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;line-height:1.05;letter-spacing:.02em;margin-bottom:6px}
    .cs-choix__sous{display:block;font-size:13px;line-height:1.45;color:#4A4A48;margin-bottom:14px}
    .cs-choix__cta{display:flex;align-items:center;gap:7px;border-top:1px solid #1D1D1B;padding-top:9px;font-size:13.5px;font-weight:800}
    .cs-choix__cta svg{transition:transform .16s ease}
    .cs-choix__carte:hover .cs-choix__cta svg{transform:translateX(3px)}
    .cs-choix__pied{margin:26px 0 0;text-align:center;font-size:13px;line-height:1.55;color:#6F6B62}
    .cs-choix__pied span{display:block}
    .cs-choix__sortie{margin:13px auto 0;padding-top:12px;max-width:420px;border-top:1px solid #E3DCCE}
    .cs-choix__sortie a{color:#6F6B62;text-decoration:underline;text-underline-offset:2px}
    .cs-choix__sortie a:hover{color:#1D1D1B}
    @media(prefers-reduced-motion:reduce){.cs-choix__carte,.cs-choix__cta svg{transition:none}}
    </style>
    <div class="cs-choix" style="--cs-coul:<?php echo esc_attr($n['coul']); ?>">
      <div class="cs-choix__tete">
        <p class="cs-choix__sur">Territoire bilingue · <span lang="it">Territorio bilingue</span></p>
        <h1 class="cs-choix__titre"><?php echo esc_html($n['fr']); ?> / <em lang="it"><?php echo esc_html($n['it']); ?></em></h1>
        <p class="cs-choix__q">Dans quelle langue veux-tu continuer ?</p>
        <p class="cs-choix__q--it" lang="it">In quale lingua vuoi continuare?</p>
      </div>
      <div class="cs-choix__grille">
        <a class="cs-choix__carte cs-choix__carte--fr" href="<?php echo esc_url('https://agendasabauda.eu/explore/' . $slug . '/'); ?>" hreflang="fr">
          <span class="cs-choix__langue">Français</span>
          <span class="cs-choix__nom"><?php echo esc_html($n['fr']); ?></span>
          <span class="cs-choix__sous"><?php echo esc_html($n['sous_fr']); ?></span>
          <span class="cs-choix__cta">Continuer en français <?php echo $fleche; ?></span>
        </a>
        <a class="cs-choix__carte cs-choix__carte--it" href="<?php echo esc_url('https://agendasabauda.eu/it/scopri/' . $n['it_slug'] . '/'); ?>" hreflang="it" lang="it">
          <span class="cs-choix__langue">Italiano</span>
          <span class="cs-choix__nom"><?php echo esc_html($n['it']); ?></span>
          <span class="cs-choix__sous"><?php echo esc_html($n['sous_it']); ?></span>
          <span class="cs-choix__cta">Continua in italiano <?php echo $fleche; ?></span>
        </a>
      </div>
      <p class="cs-choix__pied">
        <span><?php echo esc_html($n['note_fr']); ?></span>
        <span lang="it"><?php echo esc_html($n['note_it']); ?></span>
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
