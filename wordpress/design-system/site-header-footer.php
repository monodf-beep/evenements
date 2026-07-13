<?php
/**
 * Header/Footer de marque, site-wide — SANS Theme Builder (JetThemeCore documenté
 * comme peu fiable en automatisation, cf. STATUS.md). Masque le header/footer
 * générique GeneratePress (CSS) et injecte notre propre markup via les hooks
 * WordPress natifs wp_body_open / wp_footer — fonctionne sur TOUTES les pages,
 * y compris l'Accueil (928).
 *
 * Historique : la home avait initialement son propre masthead/nav/footer bakés
 * dans son contenu (mobile+desktop), et ce header site-wide l'excluait pour
 * éviter un doublon. Franck a signalé le doublon inverse (deux menus visibles,
 * celui du conteneur non sticky) — le masthead/nav baké a été retiré de
 * homepage-mobile.gutenberg.html, ce header devient l'unique header du site.
 *
 * Réutilise le vrai menu WP "Principal FR" (id 272) déjà construit avec ses
 * sous-menus Catégories/Territoires — pas de lien inventé. Menu mobile en CSS
 * pur (checkbox hack), pas de JS.
 */
add_action('wp_body_open', function () {
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
        <input type="checkbox" id="as-site-header-burger" class="as-site-header__burger-toggle">
        <label for="as-site-header-burger" class="as-site-header__burger-label" aria-label="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.6"><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
        </label>
        <div class="as-site-header__mobile-menu">
          <div class="as-site-header__mobile-menu-head">
            <div class="as-site-header__mobile-menu-title">Menu</div>
            <label for="as-site-header-burger" style="cursor:pointer;display:flex">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.6" stroke-linecap="round"><line x1="5" y1="5" x2="19" y2="19"></line><line x1="19" y1="5" x2="5" y2="19"></line></svg>
            </label>
          </div>
          <?php
          wp_nav_menu([
              'menu' => 'Principal FR',
              'container' => false,
              'fallback_cb' => false,
          ]);
          ?>
        </div>
      </div>
    </div>
    <?php
}, 5);

add_action('wp_footer', function () {
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
