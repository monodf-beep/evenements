<?php
/*
Plugin Name: Agenda Sabauda — Régie (diffusion auto depuis le backoffice)
Description: Affiche les pubs MANUELLES tout seul, sans copier-coller. Interroge
  l'API du backoffice ({backoffice}/api/active-ads) et diffuse la créative active
  du jour dans le bloc correspondant. Ici : Bloc 3 = bandeau bas d'écran (sticky,
  fermable). Créer / modifier / terminer une campagne dans le backoffice suffit :
  la pub apparaît/disparaît sur le site dans les ~5 min (cache).

  Garde-fous : desktop + mobile, consent-gated Complianz (cmplz_marketing=allow),
  libellé « Publicité », clic compté côté backoffice (le lien pointe vers /go/<id>).

  IMPORTANT : si ce module diffuse le Bloc 3, ne configure PAS aussi le Bloc 3 dans
  Ad Inserter (sinon double pub). Ad Inserter reste pour l'AdSense (blocs 1 & 2).

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie-serve.php.
  Config : définir CS_REGIE_BACKOFFICE si l'URL du backoffice diffère.
  Rollback : supprimer ce fichier.
Author: Cultura Sabauda
Version: 0.1
*/

if (!defined('ABSPATH')) { exit; }
if (!defined('CS_REGIE_BACKOFFICE')) {
    define('CS_REGIE_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
}

/** Récupère les pubs actives depuis le backoffice, avec cache 5 min (transient). */
function cs_regie_serve_fetch() {
    $cached = get_transient('cs_regie_ads');
    if ($cached !== false) { return $cached; }
    $ads  = array();
    $resp = wp_remote_get(rtrim(CS_REGIE_BACKOFFICE, '/') . '/api/active-ads',
                          array('timeout' => 4));
    if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
        $body = json_decode(wp_remote_retrieve_body($resp), true);
        if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
    }
    set_transient('cs_regie_ads', $ads, 5 * MINUTE_IN_SECONDS);
    return $ads;
}

/** Purge le cache à la demande : /?cs_regie_refresh=1 (pratique après une modif). */
add_action('init', function () {
    if (!empty($_GET['cs_regie_refresh'])) { delete_transient('cs_regie_ads'); }
});

add_action('wp_footer', function () {
    if (is_admin()) { return; }
    $ads = cs_regie_serve_fetch();
    if (empty($ads['3']) || empty($ads['3']['image']) || empty($ads['3']['link'])) {
        return;  // Bloc 3 (bandeau bas d'écran) : rien d'actif → rien à afficher
    }
    $img  = esc_url($ads['3']['image']);
    $link = esc_url($ads['3']['link']);
    ?>
    <style>
      #cs-sticky{display:none;position:fixed;left:0;right:0;bottom:0;z-index:9999;
        background:#F7F1E8;border-top:1px solid #1D1D1B;padding:8px 34px 8px 12px;text-align:center}
      .cs-consent-mkt #cs-sticky{display:block}
      #cs-sticky .cs-lbl{font:800 8px/1 'Nunito Sans',system-ui,sans-serif;letter-spacing:.1em;
        text-transform:uppercase;color:#6F6B62;margin-bottom:3px}
      #cs-sticky img{max-width:100%;height:auto;vertical-align:middle}
      #cs-sticky .cs-x{position:absolute;top:6px;right:10px;cursor:pointer;border:0;background:none;
        color:#6F6B62;font-size:18px;line-height:1;padding:0}
    </style>
    <div id="cs-sticky" role="complementary" aria-label="Publicité">
      <button class="cs-x" type="button" aria-label="Fermer"
        onclick="this.parentNode.style.display='none'">&times;</button>
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $link; ?>" target="_blank" rel="noopener sponsored"><img
        src="<?php echo $img; ?>" alt="Publicité"></a>
    </div>
    <script>
      (function(){
        var r = document.documentElement;
        function ok(){ return /(?:^|;)\s*cmplz_marketing=allow(?:;|$)/.test(document.cookie); }
        function apply(){ if (ok()) r.classList.add('cs-consent-mkt'); else r.classList.remove('cs-consent-mkt'); }
        apply();
        document.addEventListener('cmplz_status_change', apply);
      })();
    </script>
    <?php
}, 30);
