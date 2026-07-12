<?php
/**
 * Fiche événement — mode minimal (docs/TEMPLATES_WORDPRESS.md #7).
 * S'appuie sur le template single-event natif de The Events Calendar (déjà complet :
 * titre, dates, description, "En pratique", DÉTAILS, LIEU+carte) — pas de Theme
 * Builder nécessaire. Ajoute par-dessus, via le filtre the_content, ce que TEC
 * n'a pas nativement : pilule territoire, badge de statut (as_statut), crédit
 * photo (légende média WP si renseignée), date de vérification (post_modified),
 * et 3 rails liés en pied de fiche (même lieu / même catégorie / dates proches).
 */

/**
 * Rend un rail de 3 événements liés (titre + date brute — même limitation de
 * formatage que carte-evenement-blocks, cf. STATUS.md).
 */
function cs_render_event_rail($title, WP_Query $q, $current_id) {
    if (!$q->have_posts()) {
        return '';
    }
    $items = '';
    while ($q->have_posts()) {
        $q->the_post();
        if (get_the_ID() === $current_id) {
            continue;
        }
        $start = get_post_meta(get_the_ID(), '_EventStartDate', true);
        $items .= '<a href="' . esc_url(get_permalink()) . '" style="display:block;text-decoration:none;border-bottom:1px solid #E3DCCE;padding:10px 0">'
            . '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:10.5px;font-weight:800;color:#1D1D1B;margin-bottom:2px">' . esc_html($start) . '</div>'
            . '<div style="font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:14.5px;line-height:1.22;color:#1D1D1B">' . esc_html(get_the_title()) . '</div>'
            . '</a>';
    }
    wp_reset_postdata();
    if (!$items) {
        return '';
    }
    return '<div style="margin-top:20px">'
        . '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:8px">' . esc_html($title) . '</div>'
        . $items . '</div>';
}

add_filter('the_content', function ($content) {
    if (!is_singular('tribe_events') || !in_the_loop() || !is_main_query()) {
        return $content;
    }
    $post_id = get_the_ID();

    $venue_id = get_post_meta($post_id, '_EventVenueID', true);
    $rail_lieu = $venue_id ? cs_render_event_rail('Au même endroit', new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
        'post__not_in' => [$post_id], 'meta_key' => '_EventVenueID', 'meta_value' => $venue_id,
    ]), $post_id) : '';

    $cats = get_the_terms($post_id, 'tribe_events_cat');
    $rail_cat = ($cats && !is_wp_error($cats)) ? cs_render_event_rail('Même catégorie', new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
        'post__not_in' => [$post_id],
        'tax_query' => [['taxonomy' => 'tribe_events_cat', 'field' => 'term_id', 'terms' => $cats[0]->term_id]],
    ]), $post_id) : '';

    $rail_dates = cs_render_event_rail('À venir', new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
        'post__not_in' => [$post_id], 'meta_key' => '_EventStartDate', 'orderby' => 'meta_value', 'order' => 'ASC',
    ]), $post_id);

    return $content . $rail_lieu . $rail_cat . $rail_dates;
}, 20);
add_filter('the_content', function ($content) {
    if (!is_singular('tribe_events') || !in_the_loop() || !is_main_query()) {
        return $content;
    }

    $post_id = get_the_ID();

    $terr_html = '';
    $terms = get_the_terms($post_id, 'territoire');
    if ($terms && !is_wp_error($terms)) {
        $terr_html = '<span style="font-family:\'Nunito Sans\',sans-serif;font-size:12px;letter-spacing:0.06em;color:#4A4A48;border:1px solid #C9C4B8;border-radius:3px;padding:2px 8px;margin-right:8px">' . esc_html($terms[0]->name) . '</span>';
    }

    $statut = get_post_meta($post_id, 'as_statut', true);
    $labels = ['complet' => 'Complet', 'annule' => 'Annulé', 'reporte' => 'Reporté'];
    $statut_html = '';
    if (isset($labels[$statut])) {
        $color = $statut === 'annule' ? '#DC5D45' : '#1D1D1B';
        $statut_html = '<span style="font-family:\'Nunito Sans\',sans-serif;font-weight:700;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:' . $color . '">' . esc_html($labels[$statut]) . '</span>';
    }

    $meta_row = '';
    if ($terr_html || $statut_html) {
        $meta_row = '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px">' . $terr_html . $statut_html . '</div>';
    }

    $credit_html = '';
    $thumb_id = get_post_thumbnail_id($post_id);
    if ($thumb_id) {
        $caption = wp_get_attachment_caption($thumb_id);
        if ($caption) {
            $credit_html = '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:11px;color:#6F6B62;margin:-8px 0 16px">Photo : ' . esc_html($caption) . '</div>';
        }
    }

    $verified_html = '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:11px;color:#6F6B62;margin-top:24px;border-top:1px solid #E3DCCE;padding-top:12px">Vérifié le ' . esc_html(get_the_modified_date('j F Y', $post_id)) . '</div>';

    return $meta_row . $credit_html . $content . $verified_html;
}, 5);
