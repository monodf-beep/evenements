<?php
/**
 * Hub territoire / Hub catégorie — rendu complet en PHP (pas de Theme Builder).
 * Complète taxonomy-archive-query.php (qui corrige la query) en prenant le
 * contrôle total du gabarit via template_redirect, pour réutiliser le style
 * .ag-row du design system (identique à carte-evenement-blocks) au lieu du
 * gabarit générique du thème.
 *
 * Manque encore (v2) : intro éditoriale pérenne FR/IT (textes à récupérer
 * auprès de Franck, cf. docs/TEMPLATES_WORDPRESS.md #8), formatage de l'heure
 * (même limitation connue que carte-evenement-blocks), groupement par jour.
 */
add_action('template_redirect', function () {
    if (is_admin() || (!is_tax('territoire') && !is_tax('tribe_events_cat'))) {
        return;
    }

    $term = get_queried_object();
    $title = $term ? $term->name : '';

    get_header();

    $q = new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 30,
        'tax_query' => [[
            'taxonomy' => $term->taxonomy,
            'field' => 'term_id',
            'terms' => $term->term_id,
        ]],
        'meta_key' => '_EventStartDate',
        'orderby' => 'meta_value',
        'order' => 'ASC',
    ]);

    echo '<div class="ag-list"><h1 style="font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;margin-bottom:24px">' . esc_html($title) . '</h1>';

    if (!$q->have_posts()) {
        echo '<p style="font-family:\'Nunito Sans\',sans-serif;color:#6F6B62">Aucun événement à afficher pour l\'instant.</p>';
    }

    while ($q->have_posts()) {
        $q->the_post();
        $cats = get_the_terms(get_the_ID(), 'tribe_events_cat');
        $terrs = get_the_terms(get_the_ID(), 'territoire');
        $cat_name = ($cats && !is_wp_error($cats)) ? $cats[0]->name : '';
        $terr_name = ($terrs && !is_wp_error($terrs)) ? $terrs[0]->name : '';
        $start = get_post_meta(get_the_ID(), '_EventStartDate', true);
        ?>
        <a href="<?php the_permalink(); ?>" class="ag-row" style="text-decoration:none;color:inherit;display:grid">
            <span class="ag-row__time"><?php echo esc_html($start); ?></span>
            <div class="ag-row__main">
                <div class="ag-row__catline">
                    <?php if ($cat_name): ?><span class="cs-ev-cat"><?php echo esc_html($cat_name); ?></span><?php endif; ?>
                    <?php if ($terr_name): ?><span class="cs-terr"><?php echo esc_html($terr_name); ?></span><?php endif; ?>
                </div>
                <h3 class="cs-ev-title ag-row__title"><?php the_title(); ?></h3>
            </div>
        </a>
        <?php
    }
    wp_reset_postdata();

    echo '</div>';

    get_footer();
    exit;
});
