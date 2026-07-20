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
 * 2026-07-18 : l'exclusion couvre maintenant aussi la traduction IT de 928
 * (page "Home (IT)", cf. homepage-template.php) — même raison exacte, cette
 * page a elle aussi son propre masthead/nav bakés dans son contenu Gutenberg
 * (homepage-mobile-it.gutenberg.html). Résolue dynamiquement via
 * cs_agenda_home_page_ids() (définie dans homepage-template.php, snippet
 * "CS · Gabarit Accueil (928)") pour ne pas dupliquer l'ID en dur ici — sans
 * ça, la home IT afficherait CE header générique EN PLUS de son propre
 * masthead (double header).
 *
 * FOOTER : géré nativement par GeneratePress (widgets .site-info / .site-footer,
 * 5 colonnes + as-footer__themes + as-footer__legal) depuis le 2026-07-14
 * (cf. components.css, commentaire "FOOTER natif GeneratePress ... remplace
 * l'ancien HTML figé"). Le hook wp_footer ci-dessous qui injectait un second
 * <footer class="as-site-footer"> (3 rangées de liens + copyright, dupliquant
 * intégralement le footer natif) a été supprimé le 2026-07-19 — écart mesuré :
 * deux <footer> consécutifs sur chaque page (#1 .site-info, #2 .as-site-footer,
 * top #2 == bottom #1). Voir historique git pour l'ancien code si besoin.
 *
 * Réutilise le vrai menu WP "Principal FR" (id 272) déjà construit avec ses
 * sous-menus Catégories/Territoires — pas de lien inventé. Menu mobile en CSS
 * pur (checkbox hack), pas de JS.
 */
add_action('wp_body_open', function () {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (is_page($home_ids)) {
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

/**
 * FOOTER MOBILE (2026-07-20) — la grille 5 colonnes (widgets GeneratePress,
 * cf. commentaire FOOTER ci-dessus) reste la version desktop. Sur mobile, la
 * maquette ("Agenda Sabaudo - Mobile.dc.html", bloc FOOTER lignes 369-391)
 * n'a PAS de colonnes à en-têtes : des liens en flux qui reviennent à la
 * ligne, groupés en 3 blocs (découverte+pratique / à propos+légal /
 * territoires+langue), puis le copyright. Injecté ici en wp_footer, masqué
 * en desktop par CSS (.as-footer-mobile, cf. components.css) — la grille
 * 5 colonnes est symétriquement masquée sous le même seuil.
 *
 * Réutilise les 4 vrais menus WP déjà construits (280 Catégories, 281
 * Territoires, 282 Le projet, 340 Infos & légal) — mêmes items que la
 * grille desktop, pas de lien inventé. Passés par le même filtre
 * wp_nav_menu_objects (cs-menu-it.php) pour la bascule URL/libellé IT.
 */
add_action('wp_footer', function () {
    $get_items = function ($menu_id) {
        $items = wp_get_nav_menu_items($menu_id);
        if (!$items) {
            return [];
        }
        return apply_filters('wp_nav_menu_objects', $items, (object) ['theme_location' => null]);
    };

    $categories = $get_items(280);
    $projet = $get_items(282);
    $infos = $get_items(340);
    $territoires = $get_items(281);

    $render_links = function ($items) {
        foreach ($items as $item) {
            printf('<a href="%s">%s</a>', esc_url($item->url), esc_html($item->title));
        }
    };
    ?>
    <div class="as-footer-mobile">
      <div class="as-footer-mobile__group">
        <a href="<?php echo esc_url(home_url('/')); ?>">Accueil</a>
        <?php $render_links($categories); ?>
        <?php $render_links($infos); ?>
      </div>
      <div class="as-footer-mobile__group">
        <?php $render_links($projet); ?>
      </div>
      <div class="as-footer-mobile__group as-footer-mobile__group--meta">
        <?php
        $territoire_names = array_map(fn($t) => esc_html($t->title), $territoires);
        $as_langs = function_exists('pll_the_languages') ? pll_the_languages(['raw' => 1, 'hide_if_empty' => 0]) : [];
        $lang_str = 'FR | IT';
        if ($as_langs) {
            $lang_parts = [];
            foreach ($as_langs as $as_lang) {
                $lang_parts[] = sprintf('<a href="%s">%s</a>', esc_url($as_lang['url']), esc_html(strtoupper($as_lang['slug'])));
            }
            $lang_str = implode(' | ', $lang_parts);
        }
        echo implode(' · ', $territoire_names) . ' · ' . $lang_str;
        ?>
      </div>
      <div class="as-footer-mobile__copyright">&copy; Agenda Sabauda &mdash; contact@culturasabauda.eu</div>
    </div>
    <?php
}, 20);
