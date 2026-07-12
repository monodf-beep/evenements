<?php
/**
 * Fiche événement — mode minimal (docs/TEMPLATES_WORDPRESS.md #7).
 * S'appuie sur le template single-event natif de The Events Calendar (déjà complet :
 * titre, dates, description, "En pratique", DÉTAILS, LIEU+carte) — pas de Theme
 * Builder nécessaire. Ajoute par-dessus, via le filtre the_content, ce que TEC
 * n'a pas nativement : pilule territoire, badge de statut (as_statut), crédit
 * photo (légende média WP si renseignée), date de vérification (post_modified).
 *
 * Pas encore fait (v1 minimale d'abord) : les 3 rails liés (même lieu / catégorie /
 * dates) — nécessitent des requêtes WP_Query dédiées, prévu en v2.
 */
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
