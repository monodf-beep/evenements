<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter gère mal en
  version gratuite : l'HABILLAGE / SKIN (fond de page desktop) et les GOUTTIÈRES
  (skyscrapers latéraux sticky). Tout le reste (leaderboard, pavés, sticky bas) se
  configure en blocs Ad Inserter (cf. docs/REGIE_ANNONCEURS.md).

  Garde-fous intégrés :
   - Desktop uniquement (masqué < 1280 px) — JAMAIS de skin/gouttière sur mobile.
   - Consent-gated : rien ne s'affiche tant que le consentement « marketing » Complianz
     (cookie cmplz_marketing=allow) n'est pas donné. Rendu masqué → révélé en JS.
   - Interrupteurs : cs_regie[enabled] (kill-switch global) + cs_regie[skin_active] +
     [left_active] / [right_active]. TOUT est OFF par défaut.
   - Coupe automatiquement sur pages sensibles (légales, « annoncer », 404).
   - Chaque emplacement porte le libellé « Publicité ».

  Réglage des créatives : option WP `cs_regie` (voir cs_regie_defaults()), ou filtre
  `cs_regie_options` pour alimentation programmatique (back-office) plus tard.

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 0.1 (scaffold)
*/

if (!defined('ABSPATH')) { exit; }

/** Valeurs par défaut — tout OFF, aucune créative → le plugin ne rend RIEN. */
function cs_regie_defaults() {
    return array(
        'enabled'      => 0,      // kill-switch global (skin + gouttières)
        'skin_active'  => 0,      // habillage de fond desktop
        'skin_img'     => '',     // URL image 1920×1080
        'skin_link'    => '',     // URL cliquable
        'left_active'  => 0,      // gouttière gauche 160×600
        'left_img'     => '',
        'left_link'    => '',
        'right_active' => 0,      // gouttière droite 300×600
        'right_img'    => '',
        'right_link'   => '',
    );
}

function cs_regie_opts() {
    $o = wp_parse_args(get_option('cs_regie', array()), cs_regie_defaults());
    /** Permet au back-office / publisher d'injecter les créatives du jour. */
    return apply_filters('cs_regie_options', $o);
}

/** Pages où la pub hors-flux est coupée (légales, tunnel annonceur, 404…). */
function cs_regie_suppressed() {
    if (is_404()) { return true; }
    if (is_page(array('mentions-legales', 'politique-confidentialite', 'cgv',
                      'cgu', 'annoncer', 'contact'))) { return true; }
    return false;
}

add_action('wp_footer', function () {
    $o = cs_regie_opts();
    if (empty($o['enabled']) || cs_regie_suppressed()) { return; }

    $skin  = !empty($o['skin_active'])  && $o['skin_img'];
    $left  = !empty($o['left_active'])  && $o['left_img'];
    $right = !empty($o['right_active']) && $o['right_img'];
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
         style="background-image:url('<?php echo esc_url($o['skin_img']); ?>')"
         onclick="<?php echo $o['skin_link'] ? "window.open('".esc_js($o['skin_link'])."','_blank')" : ''; ?>"></div>
    <?php endif; ?>

    <?php if ($left) : ?>
    <div class="cs-regie cs-gutter cs-gutter--l" style="--w:160px">
      <div class="cs-lbl">Publicité</div>
      <?php echo $o['left_link'] ? '<a href="'.esc_url($o['left_link']).'" target="_blank" rel="noopener sponsored">' : ''; ?>
        <img src="<?php echo esc_url($o['left_img']); ?>" width="160" height="600" alt="Publicité">
      <?php echo $o['left_link'] ? '</a>' : ''; ?>
    </div>
    <?php endif; ?>

    <?php if ($right) : ?>
    <div class="cs-regie cs-gutter cs-gutter--r" style="--w:300px">
      <div class="cs-lbl">Publicité</div>
      <?php echo $o['right_link'] ? '<a href="'.esc_url($o['right_link']).'" target="_blank" rel="noopener sponsored">' : ''; ?>
        <img src="<?php echo esc_url($o['right_img']); ?>" width="300" height="600" alt="Publicité">
      <?php echo $o['right_link'] ? '</a>' : ''; ?>
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
