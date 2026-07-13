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
    // Même structure/contenu que le footer de la home (homepage-mobile.gutenberg.html) :
    // 3 rangées de liens (nav, à propos/légal, territoires+langue) + copyright. Liens vers
    // pages réelles quand elles existent, sinon # (pages à créer : Dove Mangiare, Infos
    // utiles, Qui sommes-nous, Politique de confidentialité, Cookies, Plan du site, Publicité).
    ?>
    <footer class="as-site-footer">
      <div class="as-site-footer__inner">
        <div class="as-site-footer__row">
          <a href="<?php echo esc_url(home_url('/accueil/')); ?>">Accueil</a>
          <a href="<?php echo esc_url(home_url('/ce-week-end/')); ?>">Ce week-end</a>
          <a href="<?php echo esc_url(home_url('/tout-l-agenda/')); ?>">Événements</a>
          <a href="#">Dove Mangiare</a>
          <a href="#">Curiosités</a>
          <a href="#">Infos utiles</a>
          <a href="<?php echo esc_url(home_url('/?s=')); ?>">Rechercher</a>
          <a href="#">Newsletter</a>
          <a href="<?php echo esc_url(home_url('/proposer-un-evenement/')); ?>">Proposer un événement</a>
        </div>
        <div class="as-site-footer__row as-site-footer__row--rule">
          <a href="<?php echo esc_url(home_url('/a-propos/')); ?>">Qui sommes-nous</a>
          <a href="#">Travailler avec nous</a>
          <a href="#">Politique de confidentialité</a>
          <a href="#">Cookies</a>
          <a href="#">Plan du site</a>
          <a href="#">Publicité</a>
          <a href="mailto:contact@culturasabauda.eu">Contact</a>
        </div>
        <div class="as-site-footer__legal">Savoie · Piémont · Vallée d'Aoste · Nice · FR | IT<br>© Agenda Sabauda — contact@culturasabauda.eu</div>
      </div>
    </footer>
    <?php
}, 5);
