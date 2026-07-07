<?php
/*
Plugin Name: Agenda Sabauda — Endpoint de publication TEC (cs/v1/event)
Description: Expose une route REST maison « /wp-json/cs/v1/event » qui crée ou met à
  jour un ÉVÉNEMENT The Events Calendar (post_type tribe_events) à partir d'un JSON
  propre envoyé par le backoffice (scripts/publisher.py). Fait tout le travail TEC
  côté serveur : dates via tribe_create_event(), lieu (Venue), catégorie
  (tribe_events_cat), taxonomie maison « territoire », méta du contrat « as_* »,
  méta SEO Rank Math, image à la une (téléversée depuis l'URL), et AUTEUR selon le
  score (Cultura Sabauda ≥ 7 / Agenda Sabauda < 7). TOUJOURS en status=draft.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION (au choix) :
   A) Code Snippets : coller tout le code SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-publish.php.
  Prérequis : The Events Calendar actif ; authentification via cs-rest-auth.php
  (en-tête X-CS-Auth) OU Application Password classique.

  ROUTAGE AUTEUR (optionnel) : crée deux comptes « Cultura Sabauda » et
  « Agenda Sabauda » (rôle Auteur), puis renseigne leurs IDs :
     update_option('cs_author_id', 12);   // Cultura Sabauda
     update_option('as_author_id', 13);   // Agenda Sabauda
  À défaut, l'auteur reste le compte technique de l'API (rien ne casse).
*/

if (!defined('ABSPATH')) { exit; }

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/event', array(
        'methods'             => 'POST',
        'callback'            => 'cs_publish_event',
        // cs-rest-auth.php authentifie l'utilisateur en amont (X-CS-Auth) ; ici on
        // vérifie seulement la capacité. Seuls les comptes pouvant éditer passent.
        'permission_callback' => function () {
            return current_user_can('edit_posts');
        },
    ));
});

/**
 * Résout un terme par slug PUIS par nom dans une taxonomie. Ne crée RIEN
 * (catégories et territoires sont pré-amorcés). Renvoie l'ID ou 0.
 */
function cs_resolve_term($value, $taxonomy) {
    $value = trim((string) $value);
    if ($value === '') { return 0; }
    $t = get_term_by('slug', sanitize_title($value), $taxonomy);
    if (!$t) { $t = get_term_by('name', $value, $taxonomy); }
    return $t ? (int) $t->term_id : 0;
}

/**
 * Callback principal : crée/met à jour l'événement TEC. Renvoie {id,url,updated}.
 */
function cs_publish_event(WP_REST_Request $req) {
    if (!function_exists('tribe_create_event')) {
        return new WP_Error('tec_absent', 'The Events Calendar inactif.', array('status' => 500));
    }

    $b = $req->get_json_params();
    if (!is_array($b)) {
        return new WP_Error('bad_json', 'Corps JSON invalide.', array('status' => 400));
    }

    $title = trim((string) ($b['title'] ?? ''));
    if ($title === '') {
        return new WP_Error('no_title', 'Titre manquant.', array('status' => 400));
    }

    // --- Arguments TEC (dates gérées proprement par tribe_create_event) --------
    $args = array(
        'post_title'   => $title,
        'post_content' => (string) ($b['content'] ?? ''),
        'post_status'  => 'draft',            // TOUJOURS brouillon — jamais publish auto
    );
    if (!empty($b['start_date'])) { $args['EventStartDate'] = (string) $b['start_date']; }
    if (!empty($b['end_date']))   { $args['EventEndDate']   = (string) $b['end_date']; }
    else if (!empty($b['start_date'])) { $args['EventEndDate'] = (string) $b['start_date']; }
    $args['EventAllDay'] = !empty($b['all_day']) ? 'yes' : 'no';

    // --- Auteur selon le score (routage éditorial) ----------------------------
    $score   = isset($b['score']) ? (float) $b['score'] : null;
    $cs_auth = (int) get_option('cs_author_id', 0);
    $as_auth = (int) get_option('as_author_id', 0);
    if ($score !== null) {
        $wanted = ($score >= 7) ? $cs_auth : $as_auth;
        if ($wanted > 0) { $args['post_author'] = $wanted; }
    }

    // --- Lieu (Venue) : réutilise s'il existe, sinon crée ----------------------
    $venue_id = 0;
    $venue = $b['venue'] ?? null;
    if (is_string($venue) && trim($venue) !== '') { $venue = array('Venue' => trim($venue)); }
    if (is_array($venue) && !empty($venue['Venue'])) {
        $existing = get_page_by_title($venue['Venue'], OBJECT, 'tribe_venue');
        if ($existing) {
            $venue_id = (int) $existing->ID;
        } elseif (function_exists('tribe_create_venue')) {
            $venue_id = (int) tribe_create_venue(array(
                'Venue'   => $venue['Venue'],
                'Address' => $venue['Address'] ?? '',
                'City'    => $venue['City']    ?? '',
                'Country' => $venue['Country'] ?? '',
                'Zip'     => $venue['Zip']     ?? '',
            ));
        }
        if ($venue_id > 0) { $args['EventVenueID'] = $venue_id; }
    }

    // --- Création ou mise à jour ----------------------------------------------
    $existing_id = isset($b['wp_post_id']) ? (int) $b['wp_post_id'] : 0;
    $updated = false;
    if ($existing_id > 0 && get_post_type($existing_id) === 'tribe_events') {
        tribe_update_event($existing_id, $args);
        $post_id = $existing_id;
        $updated = true;
    } else {
        $post_id = (int) tribe_create_event($args);
    }
    if (!$post_id) {
        return new WP_Error('tec_fail', 'Création TEC échouée.', array('status' => 500));
    }

    // --- Catégorie (tribe_events_cat) + territoire (taxo maison) ---------------
    $cat_id = cs_resolve_term($b['category'] ?? '', 'tribe_events_cat');
    if ($cat_id) { wp_set_object_terms($post_id, array($cat_id), 'tribe_events_cat', false); }
    $terr_id = cs_resolve_term($b['territoire'] ?? '', 'territoire');
    if ($terr_id) { wp_set_object_terms($post_id, array($terr_id), 'territoire', false); }

    // --- Méta du contrat « as_* » (voir docs/CONTRAT_META_AS.md) ---------------
    $meta = isset($b['meta']) && is_array($b['meta']) ? $b['meta'] : array();
    $allowed = array('as_score', 'as_gratuit', 'as_tarif', 'as_horaire',
        'as_billetterie_url', 'as_source_officielle_url', 'as_verifie_le', 'as_image_credit');
    foreach ($allowed as $k) {
        if (array_key_exists($k, $meta)) {
            update_post_meta($post_id, $k, sanitize_text_field((string) $meta[$k]));
        }
    }

    // --- SEO Rank Math (clés natives) -----------------------------------------
    $seo = isset($b['seo']) && is_array($b['seo']) ? $b['seo'] : array();
    if (!empty($seo['title']))         { update_post_meta($post_id, 'rank_math_title', sanitize_text_field($seo['title'])); }
    if (!empty($seo['description']))   { update_post_meta($post_id, 'rank_math_description', sanitize_text_field($seo['description'])); }
    if (!empty($seo['focus_keyword'])) { update_post_meta($post_id, 'rank_math_focus_keyword', sanitize_text_field($seo['focus_keyword'])); }

    // --- Image à la une : téléversée depuis l'URL (jamais bloquant) ------------
    if (!empty($b['image_url']) && !has_post_thumbnail($post_id)) {
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $att_id = media_sideload_image((string) $b['image_url'], $post_id,
            $b['image_alt'] ?? $title, 'id');
        if (!is_wp_error($att_id) && $att_id) {
            set_post_thumbnail($post_id, $att_id);
            if (!empty($b['image_alt'])) {
                update_post_meta($att_id, '_wp_attachment_image_alt', sanitize_text_field($b['image_alt']));
            }
            if (!empty($b['meta']['as_image_credit'])) {
                wp_update_post(array('ID' => $att_id,
                    'post_excerpt' => sanitize_text_field($b['meta']['as_image_credit'])));
            }
        }
    }

    return new WP_REST_Response(array(
        'id'      => $post_id,
        'url'     => get_permalink($post_id),
        'updated' => $updated,
    ), 200);
}
