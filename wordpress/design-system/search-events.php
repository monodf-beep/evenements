<?php
/**
 * Recherche — docs/TEMPLATES_WORDPRESS.md #10 : "Résultats orientés événements
 * (date + lieu + pilule), pas des articles bruts". Par défaut, la recherche
 * WordPress ne porte que sur post_type=post/page — les tribe_events (le vrai
 * contenu du site) n'y apparaissaient jamais. Ce snippet élargit la requête de
 * recherche pour inclure les événements, et ajoute une pilule territoire +
 * date sous chaque résultat événement.
 *
 * "Mode minimal" : réutilise le gabarit de recherche natif du thème pour la
 * boucle elle-même (pas de refonte complète), comme pour la fiche événement.
 */
add_action('pre_get_posts', function (WP_Query $query) {
    if (is_admin() || !$query->is_main_query() || !$query->is_search()) {
        return;
    }
    $query->set('post_type', ['post', 'page', 'tribe_events']);
});

add_filter('the_excerpt', function ($excerpt) {
    if (!is_search() || !in_the_loop() || get_post_type() !== 'tribe_events') {
        return $excerpt;
    }
    $post_id = get_the_ID();
    $start = get_post_meta($post_id, '_EventStartDate', true);
    $terms = get_the_terms($post_id, 'territoire');
    $terr = ($terms && !is_wp_error($terms)) ? $terms[0]->name : '';
    $meta = trim(($start ? esc_html($start) : '') . ($terr ? ' · ' . esc_html($terr) : ''));
    $meta_html = $meta ? '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:11px;font-weight:800;color:#1D1D1B;margin-bottom:4px">' . $meta . '</div>' : '';
    return $meta_html . $excerpt;
}, 5);
