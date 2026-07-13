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
 * Le contenu reste éditable normalement (Gutenberg, page 928,
 * apply-homepage.mjs) — ce hook se contente d'exécuter le rendu des blocs
 * sans passer par le template de page du thème.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(928)) {
        return;
    }

    $page = get_post(928);
    if (!$page) {
        return;
    }

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
           position fixe, indépendante de la largeur du conteneur 950px de la home). -->
      <div class="as-desktop-gutter-ad as-desktop-gutter-ad--left">
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase">Publicité</div>
        <div>Pavé 160×600</div>
      </div>
      <div class="as-desktop-gutter-ad as-desktop-gutter-ad--right">
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase">Publicité</div>
        <div>Pavé 160×600</div>
      </div>
      <?php echo apply_filters('the_content', $page->post_content); ?>
    </div>
    <?php
    get_footer();
    exit;
});
