<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter/[cs_slot]
  gèrent mal : l'HABILLAGE / SKIN (bloc 4, bandeau haut + bandes latérales desktop) et
  les GOUTTIÈRES (blocs 5/6, skyscrapers latéraux sticky, desktop). Contrairement aux
  blocs 1-3, ces emplacements ne vivent pas dans le flux normal du thème — impossible de
  les envelopper avec le shortcode [cs_slot] de cs-regie-serve.php — donc ce fichier lit
  directement le backoffice et se réinjecte lui-même dans le DOM (bandeau) ou en
  position:fixed (bandes/gouttières) via wp_footer.

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

  Garde-fous : desktop uniquement (colonnes masquées sous le seuil calculé — cf.
  $cs_skin_bp ; bandeau sous 1280px comme tout .cs-regie ; gouttières sous $cs_bp) ;
  consent-gated Complianz (cmplz_marketing=allow) ; coupé sur pages sensibles (légales,
  « annoncer », 404) ; libellé « Publicité » sur chaque emplacement.

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 0.6
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

    /* Seuil ET largeur de la SKIN (bloc 4), distincts de ceux des gouttieres ci-dessus :
       une bande laterale de skin n'a de sens que si elle colle au bord du contenu sans le
       chevaucher, donc sa largeur depend du meme conteneur que ci-dessus (950 accueil /
       1200 ailleurs). 320px de bande de chaque cote reconstitue tel quel le seuil de
       1840px deja documente pour les pages interieures (docs/REGIE_MISE_EN_PLACE_SOCLE.md :
       "container + 640px", 1200+640=1840) — pas invente ici, retrouve a l'envers. */
    $cs_skin_container = is_front_page() ? 950 : 1200;
    $cs_skin_col_w      = 320;
    $cs_skin_bp          = $cs_skin_container + 2 * $cs_skin_col_w;

    // Rendu masqué par défaut ; révélé en JS si consentement marketing + viewport desktop.
    ?>
    <style id="cs-regie-css">
      .cs-regie{display:none}
      /* révélé uniquement quand <html> porte la classe de consentement + ≥1280px */
      .cs-consent-mkt .cs-regie{display:block}
      @media (max-width:1279px){ .cs-consent-mkt .cs-regie{display:none !important} }
      /* Bandeau haut (bloc de flux normal — pas fixed : il doit defiler et sortir de
         l'ecran avec la page, cf. cs-regie-skin-js qui le reinjecte juste apres la pile
         d'en-tetes sticky du theme). Fond #F7F1E8 = couleur "zone masquee par le site"
         du gabarit fourni aux annonceurs : tout debordement au-dela de l'image reste
         invisible sur le fond du site. */
      .cs-skin-banner{position:relative;width:100%;height:240px;overflow:hidden;background:#F7F1E8}
      .cs-skin-banner a,.cs-skin-col a{position:absolute;inset:0;display:block;
        background-repeat:no-repeat;background-size:1920px auto}
      .cs-skin-banner a{background-position:center top}
      /* Bandes laterales : position:fixed, calees en JS (cs-regie-skin-js) entre le bas
         du bandeau/en-tete et le haut du pied de page — meme principe que .cs-gutter. */
      .cs-skin-col{position:fixed;z-index:2;width:<?php echo (int) $cs_skin_col_w; ?>px;
        overflow:hidden;background:#F7F1E8}
      /* Calees sur le bord de la colonne de CONTENU (calc(50% + container/2)), pas sur le
         bord de l'ECRAN (left:0/right:0). Bug signale par Franck le 2026-08-05, capture a
         l'appui (vide beant entre le bandeau et les colonnes) : le bandeau est centre dans
         un conteneur de largeur FIXE ($cs_skin_container, 950/1200px) alors que les
         colonnes etaient ancrees aux bords bruts de la fenetre -- au seuil $cs_skin_bp
         pile les deux se touchaient, mais sur tout ecran PLUS LARGE que ce seuil (le cas
         normal, un desktop fait rarement une largeur pile egale au seuil) le conteneur
         central restait centre pendant que les colonnes restaient collees aux bords : le
         vide grandissait avec la largeur d'ecran au lieu de disparaitre. En calant sur le
         bord du conteneur, les colonnes suivent son bord quelle que soit la largeur —
         zero vide, a n'importe quelle taille d'ecran au-dessus de $cs_skin_bp. */
      .cs-skin-col--l{left:auto;right:calc(50% + <?php echo (int) $cs_skin_container / 2; ?>px)}
      .cs-skin-col--l a{background-position:left -240px}
      .cs-skin-col--r{right:auto;left:calc(50% + <?php echo (int) $cs_skin_container / 2; ?>px)}
      .cs-skin-col--r a{background-position:right -240px}
      /* Seul le seuil des COLONNES est ici, pas celui du bandeau : le bandeau est en
         flux normal pleine largeur (aucun risque de chevaucher le contenu, contrairement
         aux colonnes fixed) donc il n'a aucune raison d'exiger la meme largeur qu'elles.
         Bug corrige le 2026-08-05 (Franck, test reel) : les deux etaient masques
         ensemble sous $cs_skin_bp (1590/1840px) alors que l'ancienne skin (fond plein
         ecran) s'affichait des 1280px comme tout le reste de .cs-regie -- un ecran
         1920x1080 a 175% + zoom navigateur a 80% (~1370px effectifs) faisait disparaitre
         le bandeau alors qu'il tenait tres bien a cette largeur. Le bandeau retombe donc
         sur le seuil generique de .cs-regie (1280px, regle plus haut) ; seules les
         colonnes restent reservees aux tres grands ecrans. */
      @media (max-width:<?php echo (int) $cs_skin_bp - 1; ?>px){
        .cs-consent-mkt .cs-skin-col{display:none !important}
      }
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
    <div class="cs-regie cs-skin-banner" id="cs-skin-banner" role="complementary" aria-label="Publicité">
      <a href="<?php echo $skin['link']; ?>" target="_blank" rel="noopener sponsored"
         style="background-image:url('<?php echo $skin['img']; ?>')">
        <span class="cs-lbl" style="position:absolute;left:12px;top:10px">Publicité</span>
      </a>
    </div>
    <div class="cs-regie cs-skin-col cs-skin-col--l" role="complementary" aria-label="Publicité">
      <a href="<?php echo $skin['link']; ?>" target="_blank" rel="noopener sponsored"
         style="background-image:url('<?php echo $skin['img']; ?>')">
        <span class="cs-lbl" style="position:absolute;left:12px;top:10px">Publicité</span>
      </a>
    </div>
    <div class="cs-regie cs-skin-col cs-skin-col--r" role="complementary" aria-label="Publicité">
      <a href="<?php echo $skin['link']; ?>" target="_blank" rel="noopener sponsored"
         style="background-image:url('<?php echo $skin['img']; ?>')">
        <span class="cs-lbl" style="position:absolute;left:12px;top:10px">Publicité</span>
      </a>
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
          } else {
            root.classList.remove('cs-consent-mkt');
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
      /* Place le bandeau de la SKIN et cale ses deux bandes laterales — logique separee
         du clamp des gouttieres ci-dessus (dupliquee plutot que factorisee, cf. note en
         tete de fichier) car le bandeau ajoute une contrainte que les gouttieres n'ont
         pas : il doit defiler avec la page, pas rester fixe.

         Demande Franck (2026-08-05, sur test reel) : « le bandeau doit etre EN DESSOUS
         du menu, et le corps du site doit se decaler vers le bas » — pas l'inverse. Le
         bandeau ne peut donc pas etre le premier element de la page (ce que ferait un
         hook wp_body_open) : il doit s'inserer dans le DOM juste APRES la pile
         d'en-tetes sticky du theme — les memes elements que le clamp des gouttieres,
         cf. leur note pour .as-terr-bar-inline. Une fois la, un simple bloc de flux
         normal (ni fixed ni sticky) suffit a tout faire : il pousse le contenu qui le
         suit vers le bas (etat 1) ET defile hors ecran avec la page des qu'on descend
         (etat 2), sans une ligne de calcul supplementaire. */
      (function(){
        var banner = document.getElementById('cs-skin-banner');
        var cols   = document.querySelectorAll('.cs-skin-col');
        if (!banner && !cols.length) { return; }

        var HEAD_SEL = '.as-site-header, .as-terr-bar, .as-home-desktop__nav, .as-terr-bar-inline';

        if (banner) {
          var heads = document.querySelectorAll(HEAD_SEL);
          var last = null;
          for (var i = 0; i < heads.length; i++) {
            if (!last || (last.compareDocumentPosition(heads[i]) & Node.DOCUMENT_POSITION_FOLLOWING)) {
              last = heads[i];
            }
          }
          if (last) { last.insertAdjacentElement('afterend', banner); }
        }
        if (!cols.length) { return; }

        var GAP = 16;

        // Copie volontaire de footerTop() ci-dessus : voir la note en tete de script.
        function footerTop(){
          var cands = document.querySelectorAll('.site-footer, #footer-widgets, .as-desktop-footer, .as-site-footer, #colophon, footer');
          var docH  = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, 1);
          var scrollY = window.pageYOffset || 0;
          var best = Infinity;
          for (var i = 0; i < cands.length; i++) {
            var el = cands[i];
            if (el.offsetParent === null) { continue; }
            var r = el.getBoundingClientRect();
            if (r.height <= 0) { continue; }
            if ((r.top + scrollY) < docH * 0.4) { continue; }
            if (r.top < best) { best = r.top; }
          }
          return best;
        }

        function headBottom(){
          var heads = document.querySelectorAll(HEAD_SEL);
          var vh = window.innerHeight;
          var b = 0;
          for (var h = 0; h < heads.length; h++) {
            var hr = heads[h].getBoundingClientRect();
            if (hr.height <= 0) { continue; }
            if (hr.top > vh * 0.6) { continue; }
            if (hr.bottom > b) { b = hr.bottom; }
          }
          return b;
        }

        function place(){
          // Le plus bas des deux : la pile d'en-tetes seule (bandeau deja defile hors
          // ecran) OU le bas du bandeau lui-meme (bandeau encore visible, en haut de
          // page) — c'est ce qui fait « apparaitre sous le bandeau puis suivre l'en-tete
          // seul une fois qu'il est parti » sans etat explicite a gerer.
          var top = headBottom();
          if (banner) {
            var br = banner.getBoundingClientRect().bottom;
            if (br > top) { top = br; }
          }
          top += GAP;

          var foot = footerTop();
          var h = isFinite(foot) ? (foot - top - GAP) : (window.innerHeight - top - GAP);
          if (h < 0) { h = 0; }

          for (var i = 0; i < cols.length; i++) {
            cols[i].style.top    = top + 'px';
            cols[i].style.height = h + 'px';
          }
        }

        place();
        addEventListener('scroll', place, { passive: true });
        addEventListener('resize', place, { passive: true });
        addEventListener('load',   place);
        document.addEventListener('cmplz_status_change', function(){ setTimeout(place, 0); });
      })();
    </script>
    <?php endif; ?>
    <?php
}, 40);
