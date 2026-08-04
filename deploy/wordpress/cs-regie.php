<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter/[cs_slot]
  gèrent mal : l'HABILLAGE / SKIN (bloc 4, fond de page desktop) et les GOUTTIÈRES
  (blocs 5/6, skyscrapers latéraux sticky, desktop). Contrairement aux blocs 1-3, ces
  emplacements ne vivent pas dans le flux de contenu — impossible de les envelopper avec
  le shortcode [cs_slot] de cs-regie-serve.php — donc ce fichier lit directement le
  backoffice en position:fixed via wp_footer.

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

  Garde-fous : desktop uniquement (masqué < 1280px) ; consent-gated Complianz
  (cmplz_marketing=allow) ; coupé sur pages sensibles (légales, « annoncer », 404) ;
  libellé « Publicité » sur chaque emplacement.

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 0.3
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

    // Rendu masqué par défaut ; révélé en JS si consentement marketing + viewport desktop.
    ?>
    <style id="cs-regie-css">
      .cs-regie{display:none}
      /* révélé uniquement quand <html> porte la classe de consentement + ≥1280px */
      .cs-consent-mkt .cs-regie{display:block}
      @media (max-width:1279px){ .cs-consent-mkt .cs-regie{display:none !important} }
      .cs-skin{position:fixed;inset:0;z-index:0;background-position:center top;
               background-repeat:no-repeat;background-size:cover;cursor:pointer}
      /* le contenu du site doit passer AU-DESSUS du skin : GeneratePress .site est opaque */
      .cs-consent-mkt.cs-skin-on .site{position:relative;z-index:1}
      /* 160×600 DES DEUX COTES, ancrees a 24px des bords — valeurs du design system
         maison (.as-desktop-gutter-ad, components.css), pas une invention locale.
         L'ancienne formule calait la gouttiere sur une colonne fantome de 1160px et
         soustrayait sa propre largeur : avec une 160 a gauche et une 300 a droite, les
         marges exterieures etaient forcement inegales (constat Franck 2026-08-04). */
      .cs-gutter{position:fixed;top:120px;z-index:2;width:160px}
      .cs-gutter--l{left:24px}
      .cs-gutter--r{right:24px}
      .cs-gutter a,.cs-skin a{display:block}
      .cs-lbl{font:800 8px/1 'Nunito Sans',system-ui,sans-serif;letter-spacing:.1em;
              text-transform:uppercase;color:#6F6B62;margin-bottom:3px}
      .cs-gutter img,.cs-skin img{display:block;max-width:100%;height:auto}
      /* Pas assez large pour loger la gouttiere sans chevaucher le contenu : on cache.
         ⚠️ Selecteur .cs-consent-mkt .cs-gutter et pas .cs-gutter seul : il doit BATTRE
         « .cs-consent-mkt .cs-regie{display:block} » (0,2,0). L'ancienne regle
         « .cs-gutter--l{display:none} » (0,1,0) perdait la cascade et ne masquait donc
         rien du tout sous 1440px — bug latent jamais vu, corrige ici. */
      @media (max-width:<?php echo (int) $cs_bp - 1; ?>px){ .cs-consent-mkt .cs-gutter{display:none !important} }
    </style>

    <?php if ($skin) : ?>
    <div class="cs-regie cs-skin" role="complementary" aria-label="Publicité"
         style="background-image:url('<?php echo $skin['img']; ?>')"
         onclick="window.open('<?php echo esc_js($skin['link']); ?>','_blank')"></div>
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
         au profit du footer natif GeneratePress, et TROIS elements sont sticky en haut
         (.as-site-header, .as-terr-bar, .as-home-desktop__nav) — on prend le plus bas
         des trois plutot que d'en coder un seul en dur. */
      (function(){
        var ads = document.querySelectorAll('.cs-gutter');
        if (!ads.length) { return; }
        var GAP = 16;
        var heads = document.querySelectorAll('.as-site-header, .as-terr-bar, .as-home-desktop__nav');

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

          // Bas de la zone sticky : le plus bas des en-tetes, en ignorant ceux qui ont
          // defile loin (> moitie d'ecran) pour ne pas coller les pubs en bas de page.
          var headBottom = 0;
          for (var h = 0; h < heads.length; h++) {
            var hb = heads[h].getBoundingClientRect().bottom;
            if (hb > headBottom && hb < vh / 2) { headBottom = hb; }
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
            if (top > maxTop) { top = maxTop; }
            // FAIL-OPEN : si le calcul ne laisse aucune place (viewport tres court,
            // footer mal mesure…), on colle sous l'en-tete et on AFFICHE quand meme.
            // Faire disparaitre une pub vendue sur un doute de mesure coute plus cher
            // qu'un chevauchement passager — c'est exactement ce qui vient d'arriver.
            if (!isFinite(top) || top < minTop) { top = minTop; }
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
    <?php
}, 40);
