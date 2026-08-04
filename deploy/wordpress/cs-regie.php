<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter gère mal en
  version gratuite : l'HABILLAGE / SKIN (fond de page desktop) et les GOUTTIÈRES
  (skyscrapers latéraux sticky). Tout le reste (leaderboard, pavés, sticky bas) se
  configure en blocs Ad Inserter (cf. docs/REGIE_ANNONCEURS.md).

  Créatives pilotées depuis le back-office (utils/ads.py, page /ads), via le même
  endpoint {backoffice}/api/active-ads que cs-regie-serve.php (slot "3"). Ici on lit
  les slots "skin", "left", "right". Fetch + cache 5 min + allowlist de domaine
  dupliqués volontairement (pas de require entre mu-plugins indépendants, pour ne
  pas dépendre de l'ordre de chargement de wp-content/mu-plugins/).

  Garde-fous intégrés :
   - Desktop uniquement (masqué < 1280 px) — JAMAIS de skin/gouttière sur mobile.
   - Consent-gated : rien ne s'affiche tant que le consentement « marketing » Complianz
     (cookie cmplz_marketing=allow) n'est pas donné. Rendu masqué → révélé en JS.
   - Interrupteur cs_regie[enabled] : kill-switch global (skin + gouttières), coupe
     tout même si le back-office a des créatives actives. OFF par défaut.
   - Coupe automatiquement sur pages sensibles (légales, « annoncer », 404).
   - Chaque emplacement porte le libellé « Publicité ».

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 0.2 (créatives back-office, remplace l'option WP statique du scaffold 0.1)
*/

if (!defined('ABSPATH')) { exit; }

if (!defined('CS_REGIE_HF_BACKOFFICE')) {
    define('CS_REGIE_HF_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
}
if (!defined('CS_REGIE_HF_IMG_HOST'))  { define('CS_REGIE_HF_IMG_HOST',  'agendasabauda.eu'); }
if (!defined('CS_REGIE_HF_LINK_HOST')) { define('CS_REGIE_HF_LINK_HOST', 'backoffice.agendasabauda.eu'); }

function cs_regie_hf_host_ok($url, $allowed) {
    if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') { return false; }
    $host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
    $allowed = strtolower($allowed);
    return ($host === $allowed) || (substr($host, -strlen('.' . $allowed)) === '.' . $allowed);
}

/** Kill-switch global : cs_regie[enabled], OFF par défaut même si le back-office a des créatives. */
function cs_regie_enabled() {
    $o = wp_parse_args(get_option('cs_regie', array()), array('enabled' => 0));
    return !empty($o['enabled']);
}

/** Fetch {backoffice}/api/active-ads, caché 5 min (transient dédié, distinct de
 *  cs_regie_ads utilisé par cs-regie-serve.php pour ne pas se marcher dessus). */
function cs_regie_hf_fetch_ads() {
    $cached = get_transient('cs_regie_hf_ads');
    if ($cached !== false) { return $cached; }
    $ads  = array();
    $resp = wp_remote_get(rtrim(CS_REGIE_HF_BACKOFFICE, '/') . '/api/active-ads', array('timeout' => 4));
    if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
        $body = json_decode(wp_remote_retrieve_body($resp), true);
        if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
    }
    set_transient('cs_regie_hf_ads', $ads, 5 * MINUTE_IN_SECONDS);
    return $ads;
}
add_action('init', function () {
    if (!empty($_GET['cs_regie_hf_refresh'])) { delete_transient('cs_regie_hf_ads'); }
});

/** Un slot backoffice → (image, lien) si présent ET conforme à l'allowlist, sinon null. */
function cs_regie_hf_slot($ads, $slot) {
    if (empty($ads[$slot]['image']) || empty($ads[$slot]['link'])) { return null; }
    $img  = $ads[$slot]['image'];
    $link = $ads[$slot]['link'];
    if (!cs_regie_hf_host_ok($img, CS_REGIE_HF_IMG_HOST) || !cs_regie_hf_host_ok($link, CS_REGIE_HF_LINK_HOST)) {
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
    if (!cs_regie_enabled() || cs_regie_suppressed()) { return; }

    $ads   = cs_regie_hf_fetch_ads();
    $skin  = cs_regie_hf_slot($ads, 'skin');
    $left  = cs_regie_hf_slot($ads, 'left');
    $right = cs_regie_hf_slot($ads, 'right');
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
