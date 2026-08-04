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
      .cs-gutter{position:fixed;top:120px;z-index:2;width:var(--w)}
      .cs-gutter--l{left:max(12px,calc((100vw - 1160px)/2 - var(--w) - 18px))}
      .cs-gutter--r{right:max(12px,calc((100vw - 1160px)/2 - var(--w) - 18px))}
      .cs-gutter a,.cs-skin a{display:block}
      .cs-lbl{font:800 8px/1 'Nunito Sans',system-ui,sans-serif;letter-spacing:.1em;
              text-transform:uppercase;color:#6F6B62;margin-bottom:3px}
      .cs-gutter img,.cs-skin img{display:block;max-width:100%;height:auto}
      /* si l'écran n'est pas assez large pour loger la gouttière sans chevaucher, on cache */
      @media (max-width:1439px){ .cs-gutter--l{display:none} } /* la 160 large seulement ≥1440 */
    </style>

    <?php if ($skin) : ?>
    <div class="cs-regie cs-skin" role="complementary" aria-label="Publicité"
         style="background-image:url('<?php echo $skin['img']; ?>')"
         onclick="window.open('<?php echo esc_js($skin['link']); ?>','_blank')"></div>
    <?php endif; ?>

    <?php if ($left) : ?>
    <div class="cs-regie cs-gutter cs-gutter--l" style="--w:160px">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $left['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $left['img']; ?>" width="160" height="600" alt="Publicité">
      </a>
    </div>
    <?php endif; ?>

    <?php if ($right) : ?>
    <div class="cs-regie cs-gutter cs-gutter--r" style="--w:300px">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $right['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $right['img']; ?>" width="300" height="600" alt="Publicité">
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
    <?php
}, 40);
