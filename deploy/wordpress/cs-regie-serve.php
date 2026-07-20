<?php
/*
Plugin Name: Agenda Sabauda — Régie (diffusion auto depuis le backoffice)
Description: Affiche les pubs manuelles depuis {backoffice}/api/active-ads (Bloc 3,
  bandeau bas d'écran sticky), consent-gated Complianz, clic compté via /go/<id>.
  Durci le 2026-07-18 : allowlist de domaine (https + host exact ou sous-domaine)
  sur l'image ET le lien avant tout affichage — fail-safe si l'API est compromise.

  Récupéré depuis wp-content/mu-plugins/ en production le 2026-07-18 : ce fichier
  existait déjà en LIVE, jamais commité ici auparavant (voir docs/REGIE_MISE_EN_PLACE_SOCLE.md,
  conflit #2). MISE À JOUR 2026-07-20 : l'API répond de nouveau (HTTP 200, DNS + route
  Traefik OK) — le « time-out » du 18/07 est résolu. Allowlist image élargie aux deux
  domaines de l'éditeur (agendasabauda.eu + culturasabauda.eu). À réconcilier avec le
  Bloc 3 Ad Inserter du socle, qui fait doublon sur le même emplacement.
*/
if (!defined('ABSPATH')) { exit; }
if (!defined('CS_REGIE_BACKOFFICE')) {
    define('CS_REGIE_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
}
// Domaines des créatives autorisés (anti supply-chain) : on n'injecte QUE des images
// de domaines que Cultura Sabauda contrôle. Les deux sites de l'éditeur sont admis.
// Liste séparée par des virgules, surchargeable via une constante wp-config.
if (!defined('CS_REGIE_IMG_HOST'))  { define('CS_REGIE_IMG_HOST',  'agendasabauda.eu,culturasabauda.eu'); }
if (!defined('CS_REGIE_LINK_HOST')) { define('CS_REGIE_LINK_HOST', 'backoffice.agendasabauda.eu'); }
/** URL sûre ? https + hôte égal (ou sous-domaine) d'un domaine autorisé.
 *  $allowed : un domaine, une liste séparée par des virgules, ou un tableau. */
function cs_regie_host_ok($url, $allowed) {
    if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') { return false; }
    $host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
    $list = is_array($allowed) ? $allowed : explode(',', (string) $allowed);
    foreach ($list as $a) {
        $a = strtolower(trim($a));
        if ($a === '') { continue; }
        if ($host === $a || substr($host, -strlen('.' . $a)) === '.' . $a) { return true; }
    }
    return false;
}
function cs_regie_serve_fetch() {
    $cached = get_transient('cs_regie_ads');
    if ($cached !== false) { return $cached; }
    $ads  = array();
    $resp = wp_remote_get(rtrim(CS_REGIE_BACKOFFICE, '/') . '/api/active-ads', array('timeout' => 4));
    if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
        $body = json_decode(wp_remote_retrieve_body($resp), true);
        if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
    }
    set_transient('cs_regie_ads', $ads, 5 * MINUTE_IN_SECONDS);
    return $ads;
}
add_action('init', function () {
    if (!empty($_GET['cs_regie_refresh'])) { delete_transient('cs_regie_ads'); }
});
add_action('wp_footer', function () {
    if (is_admin()) { return; }
    $ads = cs_regie_serve_fetch();
    if (empty($ads['3']) || empty($ads['3']['image']) || empty($ads['3']['link'])) { return; }
    $img  = $ads['3']['image'];
    $link = $ads['3']['link'];
    if (!cs_regie_host_ok($img, CS_REGIE_IMG_HOST) || !cs_regie_host_ok($link, CS_REGIE_LINK_HOST)) { return; }
    $img  = esc_url($img);
    $link = esc_url($link);
    echo '<style>'
      . '#cs-sticky{display:none;position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#F7F1E8;border-top:1px solid #1D1D1B;padding:8px 34px 8px 12px;text-align:center}'
      . '.cs-consent-mkt #cs-sticky{display:block}'
      . '#cs-sticky .cs-lbl{font:800 8px/1 sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#6F6B62;margin-bottom:3px}'
      . '#cs-sticky img{max-width:100%;height:auto;vertical-align:middle}'
      . '#cs-sticky .cs-x{position:absolute;top:6px;right:10px;cursor:pointer;border:0;background:none;color:#6F6B62;font-size:18px;line-height:1;padding:0}'
      . '</style>'
      . '<div id="cs-sticky" role="complementary" aria-label="Publicité">'
      . '<button class="cs-x" type="button" aria-label="Fermer" onclick="this.parentNode.style.display=\'none\'">&times;</button>'
      . '<div class="cs-lbl">Publicité</div>'
      . '<a href="' . $link . '" target="_blank" rel="noopener sponsored"><img src="' . $img . '" alt="Publicité"></a>'
      . '</div>'
      . '<script>(function(){var r=document.documentElement;function ok(){return /(?:^|;)\s*cmplz_marketing=allow(?:;|$)/.test(document.cookie);}function ap(){if(ok())r.classList.add(\'cs-consent-mkt\');else r.classList.remove(\'cs-consent-mkt\');}ap();document.addEventListener(\'cmplz_status_change\',ap);})();</script>';
}, 30);
