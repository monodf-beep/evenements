<?php
/**
 * Accueil (page 928) — rendu via template_redirect, comme toutes les autres
 * pages custom du site (Hubs, listes, recherche...), pour bypasser le
 * gabarit `page.php` par défaut de GeneratePress (entry-header "Accueil" +
 * barre latérale avec widgets Rechercher/Recent Posts) qui restait visible
 * sous le contenu Gutenberg de la home — invisible auparavant seulement
 * parce que l'ancien masthead/menu baké dans le contenu (retiré, cf.
 * site-header-footer.php) masquait visuellement le haut de page.
 *
 * Contenu actuellement Gutenberg (apply-homepage.mjs), MAIS la reconstruction
 * en cours passe à Elementor + Crocoblock (JetEngine/JetMenu...) — quand
 * Franck sauvegarde depuis Elementor, WordPress stocke le rendu dans les
 * métadonnées `_elementor_data`/`_elementor_edit_mode`, PAS dans post_content
 * (qui garde son ancien contenu Gutenberg, ignoré une fois basculé). Un
 * simple `apply_filters('the_content', $page->post_content)` ne suffit pas à
 * afficher du contenu Elementor de façon fiable en dehors de La Boucle — on
 * utilise donc l'API officielle d'Elementor quand elle gère la page, avec
 * repli sur l'ancien contenu Gutenberg sinon (transition en douceur, rien à
 * casser tant que la reconstruction Elementor n'est pas terminée/publiée).
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(928)) {
        return;
    }

    $page = get_post(928);
    if (!$page) {
        return;
    }

    $is_elementor = class_exists('\Elementor\Plugin')
        && get_post_meta($page->ID, '_elementor_edit_mode', true) === 'builder';

    get_header();
    ?>
    <!-- Un SEUL conteneur racine : sans ça, chaque bloc Gutenberg de la home
         (un div par section) atterrit comme enfant direct du conteneur
         content-area de GeneratePress (flex, prévu pour contenu+sidebar), et
         tous les blocs s'alignent horizontalement au lieu de s'empiler — bug
         réel constaté le 2026-07-13, absent des autres pages custom du site
         qui enveloppent déjà tout leur contenu dans un seul div. -->
    <div class="as-home-root">
      <!-- Gouttières pub desktop (≥1440px seulement, cf. .as-desktop-gutter-ad —
           position fixe, indépendante de la largeur du conteneur 950px de la home).
           Blocs Ad Inserter #1 (gauche) / #2 (droite), 160×600 — à configurer
           dans wp-admin → Réglages → Ad Inserter (code/image + lien). Tant
           qu'un bloc est vide, Ad Inserter n'affiche rien : le repère
           "Publicité" reste visible pour marquer l'emplacement réservé. -->
      <div class="as-desktop-gutter-ad as-desktop-gutter-ad--left">
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase">Publicité</div>
        <?php echo do_shortcode('[adinserter block="1"]'); ?>
      </div>
      <div class="as-desktop-gutter-ad as-desktop-gutter-ad--right">
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase">Publicité</div>
        <?php echo do_shortcode('[adinserter block="2"]'); ?>
      </div>
      <?php
      if ($is_elementor) {
          echo \Elementor\Plugin::instance()->frontend->get_builder_content_for_display($page->ID);
      } else {
          echo apply_filters('the_content', $page->post_content);
      }
      ?>
    </div>
    <?php
    get_footer();
    exit;
});
