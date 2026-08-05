<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter/[cs_slot]
  gèrent mal : l'HABILLAGE / SKIN (bloc 4, la créative entière posée derrière la page,
  desktop) et les GOUTTIÈRES (blocs 5/6, skyscrapers latéraux sticky, desktop).
  Contrairement aux blocs 1-3, ces emplacements ne vivent pas dans le flux normal du
  thème — impossible de les envelopper avec le shortcode [cs_slot] de cs-regie-serve.php
  — donc ce fichier lit directement le backoffice et les pose lui-même via wp_footer, le
  contenu du site passant par-dessus. La skin défile avec la page (position:absolute) ;
  seules les gouttières restent collées sous le menu (position:fixed).

  RÉUTILISE les fonctions déjà définies par cs-regie-serve.php (même mu-plugin folder,
  chargé avant celui-ci par ordre alphabétique : "cs-regie-serve.php" < "cs-regie.php") :
  cs_regie_serve_fetch() [fetch + cache 5 min de {backoffice}/api/active-ads] et
  cs_regie_host_ok() [allowlist de domaine https-only]. Pas de duplication de cette
  logique ; function_exists() en repli défensif si ce fichier tournait seul.

  Historique : v0.1 (scaffold, jamais déployé) pilotait ses créatives par une option WP
  statique (cs_regie), jamais remplie. v0.2/v0.3 (2026-08-04) : lit le backoffice comme
  cs-regie-serve.php, avec les VRAIS blocs 4/5/6 de app.py AD_BLOCKS (campagnes avec
  dates, pas de simple ON/OFF WP) — pas de kill-switch WP séparé, le statut de la
  campagne backoffice (active/ended, fenêtre de dates) fait déjà foi, comme pour les
  blocs 1-3.

  v0.4 (2026-08-05) : le bloc 4 n'était qu'un fond plein écran en position:fixed — ni
  bandeau haut, ni décalage du contenu, ni arrêt au pied de page (constat Franck en
  test réel : le bandeau chevauchait le menu du site au lieu de passer dessous, et les
  bandes latérales continuaient sous le footer). Remplacé par le format « habillage »
  validé sur maquette : un bandeau plein écran (bloc de flux normal, réinjecté en JS
  juste APRÈS la pile d'en-têtes sticky du thème — jamais avant, jamais par-dessus le
  menu — pour que le corps du site se décale sous lui) qui défile et disparaît avec la
  page, plus deux bandes latérales (position:fixed) qui prennent le relais pendant le
  défilement et s'arrêtent au-dessus du pied de page — même principe de calage que les
  gouttières des blocs 5/6, dupliqué plutôt que factorisé pour ne pas risquer de casser
  leur logique déjà éprouvée (cf. les nombreux correctifs commentés plus bas).

  v0.5 (2026-08-05) : $cs_skin_bp masquait le BANDEAU en même temps que les colonnes
  latérales, alors que lui seul (position fixed) a besoin de cette largeur pour ne pas
  chevaucher le contenu — le bandeau est en flux normal pleine largeur, sans ce risque.
  Constat Franck en test réel : sur un écran 1920×1080 à 175% d'échelle Windows + 80%
  de zoom navigateur (~1370px effectifs), le bandeau — visible dès 1280px avec l'ancien
  fond plein écran — avait disparu avec les colonnes alors qu'il tenait très bien à
  cette largeur. Le bandeau retombe désormais sur le seuil générique de .cs-regie
  (1280px) ; seules les colonnes restent réservées aux écrans ≥$cs_skin_bp.

  v0.6 (2026-08-05) : les colonnes latérales étaient ancrées aux BORDS DE L'ÉCRAN
  (left:0/right:0) alors que le bandeau est centré dans un conteneur de largeur FIXE
  ($cs_skin_container). Ça ne coïncide qu'à la largeur exacte $cs_skin_bp — sur tout
  écran plus large (le cas normal), un vide grandissant s'ouvrait entre bandeau et
  colonnes au lieu de se refermer. Capture Franck à l'appui (grand écran, vide béant de
  chaque côté du bandeau). Corrigé en calant les colonnes sur le bord du CONTENU
  (calc(50% + $cs_skin_container/2)) plutôt que sur le bord de la fenêtre : elles
  suivent désormais le conteneur quelle que soit la largeur d'écran, zéro vide.

  v0.7 (2026-08-05) : colonnes 320px -> 160px. Constat Franck sur son propre poste : meme
  a 130% de mise a l'echelle Windows (confort d'usage courant, pas un cas extreme —
  100% jugé « trop petit » par lui), les colonnes restaient masquées sous $cs_skin_bp
  (1590/1840px avec 320px de large) : « je ne vois pas assez ». Repris a l'identique la
  largeur des gouttieres des blocs 5/6 (deja en prod, deja eprouvee) plutot qu'une valeur
  choisie a vue : abaisse $cs_skin_bp a 1270/1520px, visible sur une part beaucoup plus
  large des ecrans reels sans changer le principe de calage (v0.6 ci-dessus inchangé).

  v0.8 (2026-08-05) — RETOUR A UNE IMAGE UNIQUE, et fin des v0.4 a v0.7. Celles-ci
  découpaient la créative en trois éléments (bandeau haut + deux bandes latérales) qui
  affichaient chacun une ZONE DIFFÉRENTE du même fichier via background-position : le
  bandeau son centre, les bandes ses bords extrêmes. Des pans entiers de l'image
  n'étaient donc affichés nulle part, et le raccord ne pouvait pas tomber juste : « on a
  des trous de partout, ça ne fait pas une skin, c'est n'importe quoi » (Franck, captures
  à l'appui). Les v0.5/v0.6/v0.7 ont chacune corrigé un symptôme de ce découpage (seuil
  du bandeau, ancrage des colonnes, largeur des colonnes) sans voir que le découpage
  LUI-MÊME était le défaut — trois correctifs pour une cause jamais traitée.
  Une skin, c'est l'image entière posée derrière la page, le contenu par-dessus. C'est
  redevenu ça : UN élément position:fixed portant toute la créative, `.site` (sans fond
  propre) au-dessus en z-index, et un décalage du contenu de 12.5vw pour dégager la bande
  haute. Plus aucun raccord à calculer, donc plus aucun trou possible — c'était d'ailleurs
  le principe de la v0.3, abandonné à tort en v0.4.

  v0.9 (2026-08-05) : le décalage du contenu de la v0.8 était un padding-top sur `.site`,
  qui plaçait la bande haute AU-DESSUS du menu sur l'accueil au lieu de dessous. Motif :
  sur l'accueil le menu n'est pas dans l'en-tête injecté (`.as-site-header` y est masqué,
  cf. snippet 62) mais bakè dans le CONTENU de la page, donc à l'intérieur de `.site` —
  un padding sur `.site` poussait donc le menu vers le bas lui aussi. Remplacé par une
  cale insérée en JS juste après la pile menu + barre territoire : elle tombe au bon
  endroit sur l'accueil comme sur les pages intérieures, sans distinguer les deux cas.
  « Le bandeau doit être en dessous du menu. Le corps du site doit se décaler
  suffisamment vers le bas pour que le bandeau ait la place » (Franck).

  v1.0 (2026-08-05) : la skin passe de position:fixed à position:ABSOLUE — elle défile
  donc avec la page et s'efface vers le haut sous le menu et la frise, au lieu de rester
  figée dans la fenêtre. « Le bandeau doit aussi scroller quand on scrolle vers le bas
  [...] on a uniquement les gouttières qui sont sticky, le haut des gouttières correspond
  au bas du menu » (Franck). Corrige du même coup le défaut constaté juste avant — « le
  fond de beige ne suit pas le corps du site » : figée pendant que le contenu défilait, la
  zone crème de la créative se désolidarisait du corps du site et le recouvrait de
  travers. Ancrée dans la page, elle ne peut plus se décaler : les deux bougent ensemble.
  Le bornage au pied de page et le plancher sous la barre collante disparaissent avec le
  position:fixed — la créative a désormais sa hauteur naturelle (56.25vw = 1080/1920).
  Les gouttières des blocs 5/6, elles, restent collées (cs-regie-clamp-js, inchangé).

  v1.1 (2026-08-05) : la v1.0 repositionnait la skin à chaque événement de défilement.
  Inutile — un élément en position:absolute est ancré dans la page et défile tout seul,
  à la vitesse exacte du contenu — et nuisible : le navigateur peint le défilement en
  continu tandis que l'événement JS arrive après coup, si bien que la skin rattrapait sa
  position avec un temps de retard visible. « Un effet de parallaxe entre le corps du site
  et le bandeau », « trop saccadé » (Franck). L'écouteur 'scroll' est donc supprimé : la
  position ne dépend plus que de la mise en page et ne se recalcule que quand celle-ci
  change. Corrigé au passage, même cause : la sélection de l'ancre de la cale testait la
  HAUTEUR des en-têtes, or sur l'accueil `.as-site-header` est un en-tête compact qui
  apparaît en cours de défilement — il entrait et sortait donc de la sélection au fil du
  défilement, déplaçant la cale sous la skin. Remplacé par un test sur `offsetParent`,
  qui ne bouge pas quand on défile.

  Garde-fous : desktop uniquement (skin et gouttières sous leurs seuils respectifs —
  1280px générique pour la skin, $cs_bp pour les gouttières) ; consent-gated Complianz
  (cmplz_marketing=allow) ; coupé sur pages sensibles (légales, « annoncer », 404) ;
  libellé « Publicité » sur chaque emplacement.

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 1.1
*/

if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_regie_serve_fetch')) {
    // Repli si ce fichier tournait sans cs-regie-serve.php (ne devrait pas arriver en
    // usage normal) : mini-fetch local, transient distinct pour ne pas interférer.
    if (!defined('CS_REGIE_BACKOFFICE')) {
        define('CS_REGIE_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
    }
    function cs_regie_serve_fetch() {
        $cached = get_transient('cs_regie_hf_ads_fallback');
        if ($cached !== false) { return $cached; }
        $ads  = array();
        $resp = wp_remote_get(rtrim(CS_REGIE_BACKOFFICE, '/') . '/api/active-ads', array('timeout' => 4));
        if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
            $body = json_decode(wp_remote_retrieve_body($resp), true);
            if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
        }
        set_transient('cs_regie_hf_ads_fallback', $ads, 5 * MINUTE_IN_SECONDS);
        return $ads;
    }
}
if (!function_exists('cs_regie_host_ok')) {
    if (!defined('CS_REGIE_IMG_HOST'))  { define('CS_REGIE_IMG_HOST',  'agendasabauda.eu'); }
    if (!defined('CS_REGIE_LINK_HOST')) { define('CS_REGIE_LINK_HOST', 'backoffice.agendasabauda.eu'); }
    function cs_regie_host_ok($url, $allowed) {
        if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') { return false; }
        $host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
        $allowed = strtolower($allowed);
        return ($host === $allowed) || (substr($host, -strlen('.' . $allowed)) === '.' . $allowed);
    }
}

/** Un bloc backoffice → (image, lien) si actif ET conforme à l'allowlist, sinon null. */
function cs_regie_hf_slot($bloc) {
    $ads  = cs_regie_serve_fetch();
    $bloc = (string) $bloc;
    if (empty($ads[$bloc]['image']) || empty($ads[$bloc]['link'])) { return null; }
    $img  = $ads[$bloc]['image'];
    $link = $ads[$bloc]['link'];
    if (!cs_regie_host_ok($img, CS_REGIE_IMG_HOST) || !cs_regie_host_ok($link, CS_REGIE_LINK_HOST)) {
        return null;
    }
    return array('img' => esc_url($img), 'link' => esc_url($link));
}

/** Pages où la pub hors-flux est coupée (légales, tunnel annonceur, 404…). */
function cs_regie_suppressed() {
    if (is_404()) { return true; }
    if (is_page(array('mentions-legales', 'politique-confidentialite', 'cgv',
                      'cgu', 'annoncer', 'contact'))) { return true; }
    return false;
}

add_action('wp_footer', function () {
    if (is_admin() || cs_regie_suppressed()) { return; }

    $skin  = cs_regie_hf_slot('4');
    $left  = cs_regie_hf_slot('5');
    $right = cs_regie_hf_slot('6');
    if (!$skin && !$left && !$right) { return; }

    /* Seuil d'affichage calcule SELON LA PAGE : la colonne de contenu ne fait pas la
       meme largeur partout, donc un seuil unique est forcement faux quelque part.
         - accueil        : .as-home-desktop = 950px  -> 950  + 2*(160+24) = 1318
         - reste du site  : container GeneratePress = 1200px (verifie en direct via
                            generate_get_option) -> 1200 + 2*(160+24) = 1568
       L'ancien seuil unique de 1440px faisait les deux erreurs a la fois : il privait
       l'accueil de 120px d'ecran utile (gouttieres invisibles a 100% de zoom sur un
       portable ~1366px, constat Franck 2026-08-04) ET laissait les gouttieres mordre
       sur le contenu des fiches entre 1440 et 1568px. */
    $cs_bp = is_front_page() ? 1320 : 1570;

    /* La SKIN (bloc 4) n'a plus ni largeur de bande ni seuil propre depuis la v0.8 :
       l'image entiere est posee derriere la page et le contenu passe dessus, donc il n'y
       a plus de bande a dimensionner ni de place a reserver a cote du contenu. Elle suit
       le seuil generique de .cs-regie (1280px) comme les autres emplacements.
       Les trois variables $cs_skin_container / $cs_skin_col_w / $cs_skin_bp qui vivaient
       ici pilotaient le decoupage en bandeau + bandes laterales : elles sont mortes avec
       lui. Leur histoire (320px puis 160px, seuils 1590/1840 puis 1270/1520) est dans les
       notes de version en tete de fichier — inutile de la rejouer ici. */

    // Rendu masqué par défaut ; révélé en JS si consentement marketing + viewport desktop.
    ?>
    <style id="cs-regie-css">
      .cs-regie{display:none}
      /* révélé uniquement quand <html> porte la classe de consentement + ≥1280px */
      .cs-consent-mkt .cs-regie{display:block}
      @media (max-width:1279px){ .cs-consent-mkt .cs-regie{display:none !important} }
      /* UNE SEULE IMAGE, JAMAIS DECOUPEE (v0.8, 2026-08-05).
         v0.4 a v0.7 decoupaient la creative en trois elements — un bandeau haut + deux
         bandes laterales — chacun affichant une ZONE DIFFERENTE du meme fichier via
         background-position (centre pour le bandeau, bords extremes pour les bandes).
         Entre ce que montrait le bandeau et ce que montraient les bandes, des pans
         entiers de l'image n'etaient affiches nulle part : "on a des trous de partout,
         ca ne fait pas une skin, c'est n'importe quoi" (Franck, captures a l'appui, apres
         trois tentatives de rafistolage des seuils qui ne pouvaient pas marcher — le
         defaut n'etait pas dans les seuils mais dans le decoupage lui-meme).
         Une skin, c'est l'image ENTIERE posee derriere la page, le contenu par-dessus.
         D'ou : un seul element, en position:fixed, image complete, et le contenu du site
         au-dessus (z-index). Aucun raccord a calculer, donc aucun trou possible. */
      /* position:ABSOLUE, donc ancree dans la PAGE et pas dans la fenetre : la skin defile
         avec le contenu et disparait vers le haut sous le menu/la frise quand on descend.
         "Le bandeau doit aussi scroller quand on scrolle vers le bas [...] on a uniquement
         les gouttieres qui sont sticky" (Franck, 2026-08-05).
         C'est aussi ce qui reglait le defaut precedent : en position:fixed la skin restait
         immobile pendant que le contenu defilait, donc la zone creme de la creative se
         desolidarisait du corps du site — "le fond de beige ne suit pas le corps du site".
         Ancree dans la page, elle ne peut plus se decaler : les deux bougent ensemble.
         height:56.25vw = 1080/1920, la hauteur naturelle de la creative une fois mise a la
         largeur de l'ecran — l'image entiere, ni etiree ni coupee. */
      .cs-skin{position:absolute;left:0;right:0;height:56.25vw;z-index:0;cursor:pointer;
        background-repeat:no-repeat;background-position:center top;
        /* 100% auto : l'image occupe TOUJOURS exactement la largeur de l'ecran, donc ses
           decors lateraux restent visibles quelle que soit la taille — contrairement a un
           "1920px auto" qui rognerait les bords sous 1920px, ou a "cover" qui zoome et
           finit par cacher le decor derriere le contenu. */
        background-size:100% auto}
      /* Le contenu du site passe AU-DESSUS de la skin. .site n'a aucun fond propre
         (verifie en direct : c'est body qui porte --beige), donc la skin reste visible
         partout ou le contenu ne peint pas — les marges laterales, essentiellement. */
      .cs-consent-mkt.cs-skin-on .site{position:relative;z-index:1}
      /* Cale vide inseree en JS JUSTE APRES la pile menu + barre territoire, pour degager
         la bande haute de la creative (celle qui porte le titre de l'annonceur) SOUS le
         menu : "le bandeau doit etre en dessous du menu, le corps du site doit se decaler
         suffisamment vers le bas pour que le bandeau ait la place" (Franck, 2026-08-05).
         Pourquoi une cale et pas un padding-top sur .site (ce que faisait la v0.8) : sur
         l'ACCUEIL le menu n'est pas dans l'en-tete injecte (.as-site-header y est masque,
         cf. snippet 62) mais bake dans le CONTENU de la page, donc a l'interieur de .site.
         Un padding sur .site poussait donc le menu vers le bas lui aussi, et la bande
         s'affichait AU-DESSUS de lui — l'inverse de la demande. Une cale placee apres la
         pile d'en-tetes marche sur les deux types de page sans distinction de cas.
         12.5vw = 240/1920 : exactement la hauteur de cette bande une fois l'image mise a
         la largeur de l'ecran (background-size:100% auto ci-dessus). Proportionnel, donc
         juste a toutes les largeurs — une valeur en px fixes ne collerait qu'a une seule.
         Hauteur nulle hors skin : pas de trou blanc quand la campagne s'arrete. */
      #cs-skin-spacer{height:0}
      .cs-consent-mkt.cs-skin-on #cs-skin-spacer{height:12.5vw}
      @media (max-width:1279px){ .cs-consent-mkt.cs-skin-on #cs-skin-spacer{height:0} }
      /* 160×600 DES DEUX COTES, ancrees a 24px des bords — valeurs du design system
         maison (.as-desktop-gutter-ad, components.css), pas une invention locale.
         L'ancienne formule calait la gouttiere sur une colonne fantome de 1160px et
         soustrayait sa propre largeur : avec une 160 a gauche et une 300 a droite, les
         marges exterieures etaient forcement inegales (constat Franck 2026-08-04). */
      .cs-gutter{position:fixed;top:120px;z-index:2;width:160px}
      .cs-gutter--l{left:24px}
      .cs-gutter--r{right:24px}
      .cs-gutter a{display:block}
      .cs-lbl{font:800 8px/1 'Nunito Sans',system-ui,sans-serif;letter-spacing:.1em;
              text-transform:uppercase;color:#6F6B62;margin-bottom:3px}
      .cs-gutter img{display:block;max-width:100%;height:auto}
      /* Pas assez large pour loger la gouttiere sans chevaucher le contenu : on cache.
         ⚠️ Selecteur .cs-consent-mkt .cs-gutter et pas .cs-gutter seul : il doit BATTRE
         « .cs-consent-mkt .cs-regie{display:block} » (0,2,0). L'ancienne regle
         « .cs-gutter--l{display:none} » (0,1,0) perdait la cascade et ne masquait donc
         rien du tout sous 1440px — bug latent jamais vu, corrige ici. */
      @media (max-width:<?php echo (int) $cs_bp - 1; ?>px){ .cs-consent-mkt .cs-gutter{display:none !important} }
    </style>

    <?php if ($skin) : ?>
    <div class="cs-regie cs-skin" id="cs-skin" role="complementary" aria-label="Publicité"
         style="background-image:url('<?php echo $skin['img']; ?>')"
         onclick="window.open('<?php echo esc_js($skin['link']); ?>','_blank')">
      <span class="cs-lbl" style="position:absolute;left:12px;top:10px">Publicité</span>
    </div>
    <?php endif; ?>

    <?php if ($left) : ?>
    <div class="cs-regie cs-gutter cs-gutter--l">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $left['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $left['img']; ?>" width="160" height="600" alt="Publicité">
      </a>
    </div>
    <?php endif; ?>

    <?php if ($right) : ?>
    <div class="cs-regie cs-gutter cs-gutter--r">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $right['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $right['img']; ?>" width="160" height="600" alt="Publicité">
      </a>
    </div>
    <?php endif; ?>

    <script id="cs-regie-js">
      (function(){
        var root = document.documentElement;
        function consented(){
          // Complianz : cookie cmplz_marketing=allow (adapter si CMP différent)
          return /(?:^|;)\s*cmplz_marketing=allow(?:;|$)/.test(document.cookie);
        }
        function apply(){
          if (consented()){
            root.classList.add('cs-consent-mkt');
            <?php if ($skin) : ?>root.classList.add('cs-skin-on');<?php endif; ?>
          } else {
            root.classList.remove('cs-consent-mkt','cs-skin-on');
          }
        }
        apply();
        // Complianz émet cet évènement au changement de consentement
        document.addEventListener('cmplz_status_change', apply);
        window.addEventListener('cmplz_cookie_warning', apply);
      })();
    </script>

    <script id="cs-regie-clamp-js">
      /* Cale verticalement les gouttieres entre le BAS des barres sticky et le HAUT du
         footer (demandes Franck 2026-08-04 : « elles passent en dessous du menu et
         depassent vers le haut », puis « quand on arrive au footer, le bas de la
         publicite doit s'arreter en haut du footer »).

         Pourquoi du JS et pas du CSS : en position:fixed l'element ignore le flux, donc
         aucune regle CSS ne peut lui faire connaitre la position du footer. position:
         sticky le ferait, mais exigerait d'injecter les gouttieres DANS la colonne de
         contenu — or elles vivent volontairement hors flux (wp_footer), justement parce
         que le gabarit ne leur offre aucun point d'ancrage lateral.

         Sélecteurs multiples et tolerants : .as-site-footer a ete retire le 2026-07-14
         au profit du footer natif GeneratePress, et plusieurs elements sont sticky en
         haut (.as-site-header, .as-terr-bar, .as-home-desktop__nav) — on prend le plus
         bas de tous plutot que d'en coder un seul en dur.
         .as-terr-bar-inline (ajoute 2026-08-05, constate en lisant le HTML servi) :
         sur la home DESKTOP, la barre territoire n'est PAS .as-terr-bar (masquee la,
         display:none !important, cf. components.css) mais un second element distinct
         .as-terr-bar-inline, place APRES .as-home-desktop__nav dans le DOM. Sans lui
         dans la liste, headBottom s'arretait au nav et ignorait la barre "Vous regardez
         X" qui le suit — gouttieres et skin auraient mordu dessus sur la home. */
      (function(){
        var ads = document.querySelectorAll('.cs-gutter');
        if (!ads.length) { return; }
        var GAP = 16;
        var heads = document.querySelectorAll('.as-site-header, .as-terr-bar, .as-home-desktop__nav, .as-terr-bar-inline');

        /* Le footer doit etre cherche a CHAQUE passage et VALIDE, pas resolu une fois
           pour toutes. Bug du 2026-08-04 (gouttieres invisibles partout, y compris en
           navigation normale) : querySelector('.site-footer, #colophon, …') renvoie le
           premier element dans l'ORDRE DU DOM correspondant a n'importe lequel des
           selecteurs — pas le premier selecteur de la liste. Il tombait donc sur le
           footer natif GeneratePress, masque par « display:none !important »
           (components.css). Un element display:none renvoie un rectangle a ZERO, d'ou
           footTop=0, maxTop negatif, et la branche « pas la place » masquait les deux
           gouttieres sur toutes les pages. */
        /* On veut le HAUT de la zone de pied de page, donc le repere le plus HAUT
           parmi les candidats — pas le plus bas. Erreur du premier jet : je gardais le
           plus bas, qui est #colophon (la barre de copyright, position 547062 dans le
           DOM), alors que .site-footer ouvre bien plus tot (415868) et ENGLOBE les
           colonnes. La pub s'arretait donc sur le copyright et recouvrait tout le bloc
           de liens — « elle ne s'arrete pas au debut du footer » (Franck, 2026-08-04).
           Le filtre « moitie basse du document » evite de confondre le pied de page
           avec un <footer> d'article place plus haut. */
        function footerTop(){
          var cands = document.querySelectorAll('.site-footer, #footer-widgets, .as-desktop-footer, .as-site-footer, #colophon, footer');
          var docH  = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, 1);
          var scrollY = window.pageYOffset || 0;
          var best = Infinity;
          for (var i = 0; i < cands.length; i++) {
            var el = cands[i];
            if (el.offsetParent === null) { continue; }        // display:none
            var r = el.getBoundingClientRect();
            if (r.height <= 0) { continue; }                   // pas rendu
            if ((r.top + scrollY) < docH * 0.4) { continue; }  // trop haut pour un pied de page
            if (r.top < best) { best = r.top; }
          }
          return best;   // Infinity si rien de fiable → pas de borne basse (fail-open)
        }

        function place(){
          var vh = window.innerHeight;

          /* Bas de la zone d'en-tete. On teste le bord SUPERIEUR pour decider si un
             element est ancre en haut, puis on retient son bord INFERIEUR.
             Erreur du premier jet : la condition « bottom < vh/2 » ecartait un en-tete
             des que sa BASE depassait la moitie de l'ecran. Or en haut de page la pile
             masthead + menu + barre territoire descend a ~470px sur ~800px de haut :
             les trois etaient donc ignores, headBottom restait a 0, et les gouttieres
             remontaient jusqu'en haut de l'ecran. Invisible en etat defile (l'en-tete
             collant est court), visible des qu'on revenait en haut — exactement ce que
             Franck a constate le 2026-08-04. */
          var headBottom = 0;
          for (var h = 0; h < heads.length; h++) {
            var hr = heads[h].getBoundingClientRect();
            if (hr.height <= 0) { continue; }             // pas rendu
            if (hr.top > vh * 0.6) { continue; }          // pas ancre en haut de l'ecran
            if (hr.bottom > headBottom) { headBottom = hr.bottom; }
          }
          var minTop  = headBottom + GAP;
          var footTop = footerTop();

          for (var i = 0; i < ads.length; i++) {
            var el = ads[i];
            // offsetHeight vaut 0 tant que le consentement n'a pas revele l'encart
            // (.cs-regie est display:none) : on retombe sur la hauteur nominale.
            var adH = el.offsetHeight || 614;
            var top = Math.round((vh - adH) / 2);              // centre par defaut
            if (top < minTop) { top = minTop; }
            var maxTop = footTop - adH - GAP;
            /* Le pied de page a la PRIORITE sur l'en-tete : quand les deux contraintes
               s'opposent, on laisse « top » passer sous minTop, voire devenir negatif.
               La pub sort alors de l'ecran par le haut en meme temps que le footer
               monte — comportement attendu d'un skyscraper.
               Erreur precedente : une ligne « si top < minTop alors top = minTop »
               suivait ce clamp au nom du fail-open, et le defaisait donc integralement.
               Elle se declenchait pile dans le cas qu'elle etait censee traiter, d'ou
               une pub qui continuait de recouvrir le pied de page (Franck, 2026-08-04).
               Le fail-open ne porte plus que sur une mesure IMPOSSIBLE (footTop non
               fini), jamais sur un resultat simplement serre. */
            if (isFinite(maxTop) && top > maxTop) { top = maxTop; }
            if (!isFinite(top)) { top = minTop; }
            el.style.top = top + 'px';
            el.style.visibility = '';
          }
        }

        place();
        addEventListener('scroll', place, { passive: true });
        addEventListener('resize', place, { passive: true });
        addEventListener('load',   place);
        // Le consentement revele l'encart APRES coup : sa hauteur n'est mesurable
        // qu'a ce moment-la, il faut donc recalculer.
        document.addEventListener('cmplz_status_change', function(){ setTimeout(place, 0); });
      })();
    </script>

    <?php if ($skin) : ?>
    <script id="cs-regie-skin-js">
      /* Pose la skin a l'emplacement de sa cale, en coordonnees de PAGE (et non de
         fenetre) : elle defile donc avec le contenu et s'efface sous le menu quand on
         descend, comme demande le 2026-08-05. Seules les gouttieres des blocs 5/6 restent
         collees sous le menu — c'est le script cs-regie-clamp-js ci-dessus, inchange.

         Il n'y a plus ni bornage au pied de page ni plancher sous la barre collante : la
         skin a une hauteur fixe (56.25vw, cf. CSS) et suit la page. Un seul element a
         placer depuis la v0.8, donc aucun raccord entre morceaux a maintenir ici. */
      (function(){
        var skin = document.getElementById('cs-skin');
        if (!skin) { return; }

        var HEAD_SEL = '.as-site-header, .as-terr-bar, .as-home-desktop__nav, .as-terr-bar-inline';

        /* La cale qui degage la bande haute, posee APRES le dernier element de la pile
           d'en-tetes dans l'ordre du DOM (donc sous la barre territoire quand elle existe).
           Recalculee a chaque passage : les gabarits JetEngine reconstruisent des morceaux
           de page en cours de route, et la cale doit rester au bon endroit si ca arrive. */
        var spacer = document.createElement('div');
        spacer.id = 'cs-skin-spacer';
        spacer.setAttribute('aria-hidden', 'true');

        function placeSpacer(){
          var heads = document.querySelectorAll(HEAD_SEL);
          var last = null;
          for (var i = 0; i < heads.length; i++) {
            /* offsetParent plutot que la hauteur mesuree : sur l'accueil, .as-site-header
               est un en-tete COMPACT qui apparait en cours de defilement (position:fixed).
               Le tester sur sa hauteur le faisait entrer et sortir de la selection au fil
               du defilement, donc deplacer la cale, donc sauter la skin. offsetParent est
               null pour un element display:none et ne bouge pas, lui, quand on defile. */
            if (heads[i].offsetParent === null && heads[i] !== document.body) { continue; }
            if (!last || (last.compareDocumentPosition(heads[i]) & Node.DOCUMENT_POSITION_FOLLOWING)) {
              last = heads[i];
            }
          }
          if (last) {
            if (spacer.previousElementSibling !== last) { last.insertAdjacentElement('afterend', spacer); }
          } else if (!spacer.parentNode) {
            // Aucun en-tete trouve : la cale va en tete de .site plutot que nulle part.
            var site = document.querySelector('.site') || document.body;
            site.insertBefore(spacer, site.firstChild);
          }
          return spacer;
        }

        function place(){
          /* La skin commence a l'emplacement de sa cale — c'est-a-dire juste sous le menu,
             puisque c'est la qu'elle est posee. On lit sa position plutot que de refaire
             le calcul de son cote : les deux ne peuvent donc pas diverger.
             + pageYOffset : la position est convertie en coordonnees de PAGE, celles que
             comprend un element en position:absolute. C'est ce qui fait defiler la skin
             avec le contenu au lieu de la figer dans la fenetre. */
          var top = placeSpacer().getBoundingClientRect().top + (window.pageYOffset || 0);
          skin.style.top = top + 'px';
        }

        /* PAS d'ecouteur sur 'scroll' — et c'est le coeur du correctif de la v1.1.
           Un element en position:absolute est ancre dans la PAGE : il defile tout seul,
           exactement a la vitesse du contenu, sans une ligne de JavaScript. Le repositionner
           a chaque evenement de defilement, comme le faisait la v1.0, ne pouvait qu'ajouter
           du retard : le navigateur peint le defilement en continu, l'evenement JS arrive
           apres coup, donc la skin rattrapait sa position avec un temps de retard visible.
           C'est precisement ce que Franck a decrit le 2026-08-05 : "un effet de parallaxe
           entre le corps du site et le bandeau", "trop saccade". La skin ne bougeait pas
           moins vite parce qu'elle etait mal calee — elle bougeait moins vite parce qu'on
           la recalculait.
           La position ne depend donc plus que de la MISE EN PAGE, et se recalcule quand
           celle-ci change : chargement, redimensionnement, consentement. Les recalculs
           differes couvrent les gabarits JetEngine et les images qui arrivent apres coup et
           decalent ce qui se trouve au-dessus de la cale. */
        place();
        addEventListener('resize', place, { passive: true });
        addEventListener('load',   place);
        document.addEventListener('cmplz_status_change', function(){ setTimeout(place, 0); });
        setTimeout(place, 300);
        setTimeout(place, 1200);
      })();
    </script>
    <?php endif; ?>
    <?php
}, 40);
