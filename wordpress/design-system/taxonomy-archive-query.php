<?php
/**
 * Hub territoire / Hub catégorie — débloque les archives de taxonomie custom.
 * Constat (STATUS.md) : l'archive de `territoire` ou `tribe_events_cat` retombe
 * sur le template générique du thème, qui ne requête QUE post_type=post — page
 * vide. Ce snippet force la query principale de ces archives sur tribe_events.
 * Pas de Theme Builder nécessaire (même logique que la fiche événement).
 */
add_action('pre_get_posts', function (WP_Query $query) {
    if (is_admin() || !$query->is_main_query()) {
        return;
    }
    if ($query->is_tax('territoire') || $query->is_tax('tribe_events_cat')) {
        $query->set('post_type', 'tribe_events');
        $query->set('posts_per_page', 30);
    }
});
