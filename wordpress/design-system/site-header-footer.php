<?php
/**
 * Header/Footer de marque, site-wide — SANS Theme Builder (JetThemeCore documenté
 * comme peu fiable en automatisation, cf. STATUS.md). Masque le header/footer
 * générique GeneratePress (CSS) et injecte notre propre markup via les hooks
 * WordPress natifs wp_body_open / wp_footer — fonctionne sur TOUTES les pages.
 *
 * Exclut la page Accueil (928) : elle a déjà son propre masthead/nav/footer
 * "desktop + mobile" bakés dans son contenu (voir homepage-mobile.gutenberg.html) —
 * les dupliquer ici créerait un header/footer en double sur cette page précise.
 *
 * Réutilise le vrai menu WP "Principal FR" (id 272) déjà construit avec ses
 * sous-menus Catégories/Territoires — pas de lien inventé.
 */
add_action('wp_body_open', function () {
    if (is_page(928)) {
        return;
    }
    ?>
    <div class="as-site-header">
      <div class="as-site-header__inner">
        <a href="<?php echo esc_url(home_url('/')); ?>" class="as-site-header__wordmark">Agenda Sabauda</a>
        <nav class="as-site-header__nav">
          <?php
          wp_nav_menu([
              'menu' => 'Principal FR',
              'container' => false,
              'items_wrap' => '<ul class="as-site-header__menu">%3$s</ul>',
              'fallback_cb' => false,
          ]);
          ?>
        </nav>
        <div class="as-site-header__lang">FR <span>|</span> <span class="muted">IT</span></div>
      </div>
    </div>
    <?php
}, 5);

add_action('wp_footer', function () {
    if (is_page(928)) {
        return;
    }
    ?>
    <footer class="as-site-footer">
      <div class="as-site-footer__inner">
        <nav class="as-site-footer__nav">
          <?php
          wp_nav_menu([
              'menu' => 'Principal FR',
              'container' => false,
              'depth' => 1,
              'items_wrap' => '<ul class="as-site-footer__menu">%3$s</ul>',
              'fallback_cb' => false,
          ]);
          ?>
        </nav>
        <div class="as-site-footer__legal">© Agenda Sabauda — édité par Cultura Sabauda — <a href="mailto:contact@culturasabauda.eu">contact@culturasabauda.eu</a></div>
      </div>
    </footer>
    <?php
}, 5);
