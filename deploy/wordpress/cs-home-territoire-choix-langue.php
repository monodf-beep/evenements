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
// repartir. Le MECANISME ne change pas d'un iota (meme interception, memes deux URLs de
// sortie) -- seule la page rendue change :
//   - une carte pleine largeur, filet de 6 px en tete a la couleur DU TERRITOIRE (meme
//     convention que cs_a_lire_couleur, code-snippet 134), et le nom du territoire en
//     grand sur deux lignes : Piemont en noir, Piemonte dans cette couleur -- le
//     bilinguisme se voit avant meme d'avoir lu la question ;
//   - deux panneaux pleins cote a cote, FR a gauche / IT a droite, occupant toute la
//     largeur de la carte : un « FR » et un « IT » geants en Saira Condensed, le libelle,
//     une fleche, et le sous-titre qui dit ou mene le bouton. Cote a cote MEME sur
//     mobile : la symetrie des deux colonnes est ce qui fait lire « choix » et non
//     « alerte ». Etats :hover / :focus-visible -- impossible en style inline, d'ou le
//     <style> ; panneaux de 100 px de haut environ, tres au-dela de la cible de 44 px ;
//   - la phrase qui manquait, sous les panneaux : c'est la LANGUE DU SITE qu'on choisit
//     ici, pas le territoire. C'est l'ambiguite qui faisait ressembler la page a une
//     erreur -- « Piemont / Piemonte » seul ne disait pas de quoi on parlait ;
//   - une sortie de secours vers les 4 territoires, dans les deux langues ;
//   - un <title> a elle : la page est servie par page_id=928, donc l'onglet annoncait
//     « Agenda Sabauda : quoi faire, ou manger » (mesure du 21/09 sur la page en ligne).
//     Le canonical reste celui de la home -- il est deja juste, on n'y touche pas.
//
// Contrastes mesures (WCAG AA, texte normal, sur creme #F7F1E8) : noir #1D1D1B 15,0:1 ;
// rouge Piemont #B3261E 5,8:1 ; vert Vallee d'Aoste 1E7D34 4,6:1. L'accent #DC5D45 du
// bouton italien precedent n'etait qu'a 3,3:1, SOUS le seuil de 4,5 : c'est pour ca que
// le bouton italien prend desormais la couleur du territoire plutot que l'accent.
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

    $fleche = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M5 12h13"/><path d="m12 5 7 7-7 7"/></svg>';

    get_header();
    ?>
    <style id="cs-choix-langue">
    .cs-choix{--cs-coul:#1D1D1B;max-width:860px;margin:0 auto;padding:28px 16px 56px;font-family:'Nunito Sans',sans-serif;color:#1D1D1B}
    .cs-choix__carte{background:#FBF7F0;border:1px solid #E3DCCE;border-top:6px solid var(--cs-coul);border-radius:3px;overflow:hidden}
    .cs-choix__tete{padding:26px 22px 22px;text-align:center}
    .cs-choix__eyebrow{margin:0 0 12px;font-family:'Saira Condensed',sans-serif;font-size:11.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#6F6B62}
    .cs-choix__titre{font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:clamp(30px,8vw,46px);line-height:1.02;margin:0;letter-spacing:-.01em}
    .cs-choix__titre span{display:block}
    .cs-choix__titre .cs-choix__it{color:var(--cs-coul)}
    .cs-choix__q{margin:18px 0 0;font-size:16px;font-weight:700;line-height:1.3}
    .cs-choix__q--it{margin:2px 0 0;font-size:16px;font-weight:600;line-height:1.3;color:#6F6B62}
    .cs-choix__grille{display:grid;grid-template-columns:1fr 1fr;gap:2px;background:#E3DCCE;border-top:1px solid #E3DCCE}
    .cs-choix__btn{display:flex;flex-direction:column;align-items:center;text-align:center;gap:10px;padding:26px 14px 28px;text-decoration:none;color:#F7F1E8;transition:filter .15s ease,padding .15s ease}
    .cs-choix__btn--fr{background:#1D1D1B}
    .cs-choix__btn--it{background:var(--cs-coul)}
    .cs-choix__btn:hover,.cs-choix__btn:focus-visible{color:#F7F1E8;filter:brightness(1.12)}
    .cs-choix__btn:focus-visible{outline:3px solid #1D1D1B;outline-offset:-6px}
    .cs-choix__code{font-family:'Saira Condensed',sans-serif;font-size:clamp(40px,13vw,64px);font-weight:700;line-height:.85;letter-spacing:.02em}
    .cs-choix__label{display:flex;align-items:center;justify-content:center;gap:8px;font-size:clamp(15px,4.2vw,18px);font-weight:800;line-height:1.2}
    .cs-choix__label svg{flex:0 0 auto;transition:transform .15s ease}
    .cs-choix__btn:hover .cs-choix__label svg{transform:translateX(4px)}
    .cs-choix__sous{font-size:13px;line-height:1.4;max-width:22ch}
    .cs-choix__pied{padding:18px 22px 22px;text-align:center;font-size:13px;line-height:1.55;color:#6F6B62}
    .cs-choix__pied span{display:block}
    .cs-choix__sortie{margin:12px 0 0;padding-top:12px;border-top:1px solid #E3DCCE}
    .cs-choix__sortie a{color:#6F6B62;text-decoration:underline;text-underline-offset:2px}
    .cs-choix__sortie a:hover{color:#1D1D1B}
    @media(prefers-reduced-motion:reduce){.cs-choix__btn,.cs-choix__label svg{transition:none}.cs-choix__btn:hover .cs-choix__label svg{transform:none}}
    </style>
    <div class="cs-choix" style="--cs-coul:<?php echo esc_attr($n['coul']); ?>">
      <div class="cs-choix__carte">
        <div class="cs-choix__tete">
          <p class="cs-choix__eyebrow">Territoire bilingue · <span lang="it">Territorio bilingue</span></p>
          <h1 class="cs-choix__titre"><span><?php echo esc_html($n['fr']); ?></span><span class="cs-choix__it" lang="it"><?php echo esc_html($n['it']); ?></span></h1>
          <p class="cs-choix__q">Dans quelle langue veux-tu continuer ?</p>
          <p class="cs-choix__q--it" lang="it">In quale lingua vuoi continuare?</p>
        </div>
        <div class="cs-choix__grille">
          <a class="cs-choix__btn cs-choix__btn--fr" href="<?php echo esc_url('https://agendasabauda.eu/explore/' . $slug . '/'); ?>" hreflang="fr">
            <span class="cs-choix__code" aria-hidden="true">FR</span>
            <span class="cs-choix__label">Continuer en français <?php echo $fleche; ?></span>
            <span class="cs-choix__sous"><?php echo esc_html($n['sous_fr']); ?></span>
          </a>
          <a class="cs-choix__btn cs-choix__btn--it" href="<?php echo esc_url('https://agendasabauda.eu/it/scopri/' . $n['it_slug'] . '/'); ?>" hreflang="it" lang="it">
            <span class="cs-choix__code" aria-hidden="true">IT</span>
            <span class="cs-choix__label">Continua in italiano <?php echo $fleche; ?></span>
            <span class="cs-choix__sous"><?php echo esc_html($n['sous_it']); ?></span>
          </a>
        </div>
        <div class="cs-choix__pied">
          <span><?php echo esc_html($n['note_fr']); ?></span>
          <span lang="it"><?php echo esc_html($n['note_it']); ?></span>
          <span class="cs-choix__sortie">
            <a href="https://agendasabauda.eu/espace-sabaudo/" hreflang="fr">Voir les 4 territoires</a>
            &nbsp;·&nbsp;
            <a href="https://agendasabauda.eu/it/spazio-sabaudo/" hreflang="it" lang="it">Vedi i 4 territori</a>
          </span>
        </div>
      </div>
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
