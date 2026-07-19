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
 *
 * 2026-07-18 : Franck a demandé une vraie home IT (agendasabauda.eu/it/ ne
 * chargeait aucune section dynamique — page 928 sans traduction Polylang,
 * pll_get_post(928,'it') === 0). Une page "Home (IT)" a été créée avec son
 * propre post_content Gutenberg traduit
 * (wordpress/design-system/homepage-mobile-it.gutenberg.html) et liée à 928
 * via pll_set_post_language()/pll_save_post_translations(). Ce gabarit gère
 * donc maintenant *la page courante*, quelle qu'elle soit parmi 928 (FR) et
 * sa traduction IT — cf. cs_agenda_home_page_ids() — au lieu de rester câblé
 * en dur sur le seul post 928. Chaque page garde son propre post_content
 * (FR pour 928, IT pour sa traduction), donc le rendu plus bas n'a pas eu
 * besoin de changer : il opère déjà sur $page = la page demandée, jamais sur
 * un ID fixe.
 */
if (!function_exists('cs_agenda_home_page_ids')) {
    /**
     * IDs de page gérés par ce gabarit : 928 (FR, ancre historique) + sa
     * traduction Polylang dans les autres langues actives (IT), résolue
     * dynamiquement pour ne jamais dépendre d'un ID codé en dur ailleurs.
     * Réutilisée par site-header-footer.php pour exclure le header/footer
     * générique de CES MÊMES pages (elles ont leur propre masthead/nav
     * bakés dans leur contenu Gutenberg, cf. commentaire là-bas).
     */
    function cs_agenda_home_page_ids() {
        $ids = [928];
        if (function_exists('pll_get_post')) {
            $it_id = pll_get_post(928, 'it');
            if ($it_id) {
                $ids[] = (int) $it_id;
            }
        }
        return $ids;
    }
}

add_action('template_redirect', function () {
    if (is_admin() || !is_page(cs_agenda_home_page_ids())) {
        return;
    }

    $page = get_queried_object();
    if (!($page instanceof WP_Post)) {
        return;
    }

    $is_elementor = class_exists('\Elementor\Plugin')
        && get_post_meta($page->ID, '_elementor_edit_mode', true) === 'builder';

    // Libellé "Publicité" des gouttières desktop, traduit pour la home IT —
    // seul texte visible en dur dans ce gabarit PHP (le reste du contenu vit
    // dans le post_content Gutenberg de chaque page, déjà traduit là-bas).
    $publicite_label = (function_exists('pll_current_language') && pll_current_language() === 'it')
        ? 'Pubblicità'
        : 'Publicité';

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
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase"><?php echo esc_html($publicite_label); ?></div>
        <?php echo do_shortcode('[adinserter block="1"]'); ?>
      </div>
      <div class="as-desktop-gutter-ad as-desktop-gutter-ad--right">
        <div style="font-family:'Nunito Sans',sans-serif;font-weight:700;font-size:9px;letter-spacing:0.14em;text-transform:uppercase"><?php echo esc_html($publicite_label); ?></div>
        <?php echo do_shortcode('[adinserter block="2"]'); ?>
      </div>
      <?php
      if ($is_elementor) {
          // get_builder_content() a besoin du contexte $post/La Boucle standard
          // (setup_postdata) pour ne pas retourner une chaîne vide — Elementor
          // s'appuie en interne sur get_the_ID()/le post courant, pas seulement
          // sur le paramètre $post_id. Sans ça, rendu vide silencieux (aucune
          // exception), constaté le 2026-07-14.
          global $post;
          $post = $page;
          setup_postdata($post);
          echo \Elementor\Plugin::instance()->frontend->get_builder_content($page->ID, true);
          wp_reset_postdata();
      } else {
          echo apply_filters('the_content', $page->post_content);
      }
      ?>
    </div>
    <?php
    get_footer();
    exit;
});
