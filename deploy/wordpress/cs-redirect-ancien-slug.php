<?php
/**
 * Plugin Name: CS - Redirection des anciens slugs de fiches
 * Description: wp_old_slug_redirect() ne s applique pas aux fiches tribe_events, dont l URL passe par la reecriture du calendrier. Constate le 2026-08-09 : une fiche renommee rendait un 404. Ce garde-fou rattrape le cas a partir du meta _wp_old_slug que WordPress ecrit deja.
 */
if (!defined('ABSPATH')) exit;

// The Events Calendar intercepte template_redirect et coupe avant la priorite 5 :
// on se branche sur 'wp', ou is_404() est deja determine. Verifie le 2026-08-09.
add_action('wp', 'cs_redirect_ancien_slug_fiche', 1);
function cs_redirect_ancien_slug_fiche() {
    if (is_admin() || !is_404()) { return; }
    $chemin = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    $seg = array_values(array_filter(explode('/', (string) $chemin)));
    if (!$seg) { return; }
    $slug = end($seg);
    if ($slug === '' || strlen($slug) > 200) { return; }
    global $wpdb;
    $id = $wpdb->get_var($wpdb->prepare(
        "SELECT pm.post_id FROM {$wpdb->postmeta} pm INNER JOIN {$wpdb->posts} p ON p.ID = pm.post_id WHERE pm.meta_key = '_wp_old_slug' AND pm.meta_value = %s AND p.post_status = 'publish' ORDER BY pm.meta_id DESC LIMIT 1",
        $slug
    ));
    if (!$id) { return; }
    $cible = get_permalink((int) $id);
    if (!$cible) { return; }
    if (untrailingslashit(parse_url($cible, PHP_URL_PATH)) === untrailingslashit($chemin)) { return; }
    wp_redirect($cible, 301);
    exit;
}