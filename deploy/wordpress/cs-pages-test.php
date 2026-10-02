<?php
/**
 * Plugin Name: CS - Pages de test faciles à retrouver
 * Description: Menu « Pages de test » dans la barre d'administration et encadré sur le tableau de bord, qui listent les pages marquées cs_page_test=1.
 *
 * POURQUOI (02/10/2026). Franck : « ça pourrait être bien de garder ces pages test, et que
 * le lien soit facilement trouvable dans WordPress ». Sept pages de maquette (lecture des
 * articles, fiche événement Orlando, accueil) sont publiées en noindex/nofollow, hors de
 * tout menu : sans ce plugin, il faut connaître leur adresse ou les chercher dans la liste
 * des pages, au milieu des vraies.
 *
 * CE QUI EST LISTÉ. Les pages qui portent la méta `cs_page_test` = 1, posée à la main à
 * la création de chaque maquette. Pas de règle sur le titre ni sur l'adresse : un titre
 * se réécrit, et un « test » dans un slug peut être une vraie page. Une page qui n'a plus
 * sa place dans la liste : retirer la méta, ou la mettre à la corbeille.
 *
 * QUI LE VOIT. Les comptes qui peuvent modifier les pages (edit_pages). Rien côté public.
 *
 * GARDE-FOU. Chaque page listée est signalée si elle n'est PAS en noindex : une maquette
 * indexable concurrencerait les vraies pages dans Google.
 */
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_pages_test_liste')) {
    /** Les pages de test, de la plus récente à la plus ancienne. */
    function cs_pages_test_liste() {
        return get_posts(array(
            'post_type'      => 'page',
            'post_status'    => array('publish', 'draft', 'private'),
            'posts_per_page' => 50,
            'meta_key'       => 'cs_page_test',
            'meta_value'     => '1',
            'orderby'        => 'date',
            'order'          => 'DESC',
            'lang'           => '',
            'suppress_filters' => true,
        ));
    }

    function cs_pages_test_indexable($id) {
        return get_post_meta($id, '_yoast_wpseo_meta-robots-noindex', true) !== '1';
    }
}

add_action('admin_bar_menu', function ($bar) {
    if (!current_user_can('edit_pages')) { return; }
    $pages = cs_pages_test_liste();
    if (!$pages) { return; }
    $bar->add_node(array(
        'id'    => 'cs-pages-test',
        'title' => 'Pages de test (' . count($pages) . ')',
        'href'  => admin_url('index.php#cs_pages_test'),
    ));
    foreach ($pages as $p) {
        $titre = get_the_title($p);
        if (cs_pages_test_indexable($p->ID)) { $titre .= ' — ATTENTION : indexable'; }
        $bar->add_node(array(
            'parent' => 'cs-pages-test',
            'id'     => 'cs-pages-test-' . $p->ID,
            'title'  => esc_html($titre),
            'href'   => get_permalink($p),
        ));
    }
}, 90);

add_action('wp_dashboard_setup', function () {
    if (!current_user_can('edit_pages')) { return; }
    wp_add_dashboard_widget('cs_pages_test', 'Pages de test (noindex, ne pas diffuser)', function () {
        $pages = cs_pages_test_liste();
        if (!$pages) {
            echo '<p>Aucune page marquée <code>cs_page_test</code>.</p>';
            return;
        }
        echo '<ul style="margin:0">';
        foreach ($pages as $p) {
            $alerte = cs_pages_test_indexable($p->ID) ? ' <strong style="color:#b3261e">indexable !</strong>' : '';
            printf(
                '<li style="margin:0 0 8px"><a href="%s" target="_blank" rel="noopener"><strong>%s</strong></a>%s<br><span style="color:#6F6B62">%s · modifiée le %s</span> · <a href="%s">modifier</a></li>',
                esc_url(get_permalink($p)),
                esc_html(get_the_title($p)),
                $alerte,
                esc_html(wp_make_link_relative(get_permalink($p))),
                esc_html(get_the_modified_date('j M Y', $p)),
                esc_url(get_edit_post_link($p->ID))
            );
        }
        echo '</ul><p style="color:#6F6B62;margin:8px 0 0">' . count($pages) . ' page(s). Retirer une page de la liste : supprimer sa méta <code>cs_page_test</code>, ou la mettre à la corbeille.</p>';
    });
});
