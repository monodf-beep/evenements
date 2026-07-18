<?php
/**
 * Header/Footer de marque, site-wide — SANS Theme Builder (JetThemeCore documenté
 * comme peu fiable en automatisation, cf. STATUS.md). Masque le header/footer
 * générique GeneratePress (CSS) et injecte notre propre markup via les hooks
 * WordPress natifs wp_body_open / wp_footer.
 *
 * HEADER : exclut l'Accueil (928) — elle a SON PROPRE masthead (logo réel +
 * nav riche en desktop, burger en mobile) baké dans son contenu
 * (homepage-mobile.gutenberg.html), différent par nature du header compact
 * des autres pages (cf. leurs propres maquettes : Recherche, Page Lieu...).
 *
 * FOOTER : PAS d'exclusion — Franck a demandé un footer strictement
 * identique sur toutes les pages, y compris l'Accueil (contrairement au
 * header, qui a une bonne raison design d'être différent sur la home). Le
 * footer 5 colonnes qui existait dans le contenu de la home a été retiré
 * (cf. homepage-mobile.gutenberg.html) au profit de celui-ci, unique.
 *
 * Réutilise le vrai menu WP "Principal FR" (id 272) déjà construit avec ses
 * sous-menus Catégories/Territoires — pas de lien inventé. Menu mobile en CSS
 * pur (checkbox hack), pas de JS.
 */
add_action('wp_body_open', function () {
    if (is_page(928)) {
        return;
    }
    ?>
    <div class="as-site-header">
      <div class="as-site-header__inner">
        <a href="<?php echo esc_url(home_url('/')); ?>" class="as-site-header__wordmark" aria-label="Agenda Sabauda, accueil">
          <img src="https://agendasabauda.eu/wp-content/uploads/2026/07/masthead-agenda-sabauda-v7.png" alt="Agenda Sabauda" width="778" height="250">
        </a>
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
        <div class="as-site-header__lang">
          <?php
          // Écart mesuré 2026-07-18 : FR|IT n'était que du texte statique (aucun <a href>).
          // On génère maintenant de vrais liens Polylang vers l'URL traduite courante,
          // en conservant le style visuel existant (couleur inline, pas de dépendance à
          // un composant CSS différent) pour zéro régression visuelle.
          $as_langs = function_exists('pll_the_languages') ? pll_the_languages(['raw' => 1, 'hide_if_empty' => 0]) : [];
          if ($as_langs) {
              $as_lang_links = [];
              foreach ($as_langs as $as_lang) {
                  $as_lang_style = 'text-decoration:none;' . ($as_lang['current_lang'] ? 'color:inherit' : 'color:#C9BFAD;font-weight:400');
                  $as_lang_links[] = sprintf(
                      '<a href="%s" style="%s">%s</a>',
                      esc_url($as_lang['url']),
                      esc_attr($as_lang_style),
                      esc_html(strtoupper($as_lang['slug']))
                  );
              }
              echo implode(' <span>|</span> ', $as_lang_links);
          } else {
              // Repli si Polylang est désactivé : ancien texte statique, non cliquable.
              echo 'FR <span>|</span> <span class="muted">IT</span>';
          }
          ?>
        </div>
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
    // Affiché sur TOUTES les pages, y compris l'Accueil (928) — footer unique
    // demandé par Franck. 3 rangées de liens (nav, à propos/légal,
    // territoires+langue) + copyright. Liens vers
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
