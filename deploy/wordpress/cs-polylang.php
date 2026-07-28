<?php
/*
Plugin Name: Agenda Sabauda — Polylang FR/IT (langue + liage des traductions)
Description: Site bilingue. Fait DEUX choses, SANS toucher au snippet cs-publish :
  1) pose la LANGUE Polylang de chaque événement publié via cs/v1/event (lue dans le
     champ « language » du JSON), en s'accrochant à la réponse REST (aucune édition de
     l'endpoint existant) ;
  2) expose /wp-json/cs/v1/link-translations pour LIER des fiches FR↔IT comme
     traductions (pll_save_post_translations). Corps : {"translations":{"fr":ID,"it":ID}}.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : Code Snippets → Add New → coller le code CI-DESSOUS (SANS « <?php »)
  → « Run everywhere » → Save & Activate. Prérequis : Polylang actif avec FR + IT.
  Indépendant de cs-publish.php : on peut l'activer/désactiver sans risque pour la
  publication.
*/

if (!defined('ABSPATH')) { exit; }

/**
 * (1) LANGUE AU PUSH — s'accroche à la réponse de cs/v1/event et pose la langue
 * Polylang du post créé/mis à jour, d'après le champ « language » du corps JSON.
 * Filtre core exécuté après le callback REST → aucune modification de l'endpoint.
 */
add_filter('rest_request_after_callbacks', function ($response, $handler, $request) {
    if ($request->get_route() !== '/cs/v1/event') { return $response; }
    if (!function_exists('pll_set_post_language')) { return $response; }
    $data = ($response instanceof WP_REST_Response) ? $response->get_data() : null;
    $pid  = (is_array($data) && !empty($data['id'])) ? (int) $data['id'] : 0;
    $body = $request->get_json_params();
    $lang = (is_array($body) && !empty($body['language']))
        ? sanitize_key((string) $body['language']) : '';
    if ($pid && $lang && get_post_type($pid) === 'tribe_events') {
        pll_set_post_language($pid, $lang);
    }
    return $response;
}, 20, 3);

/**
 * (2) LIAGE DES TRADUCTIONS — route dédiée.
 */
add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/link-translations', array(
        'methods'             => 'POST',
        'callback'            => 'cs_link_translations',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
    ));
});

function cs_link_translations(WP_REST_Request $req) {
    if (!function_exists('pll_save_post_translations') || !function_exists('pll_set_post_language')) {
        return new WP_Error('no_polylang', 'Polylang inactif.', array('status' => 500));
    }
    $b = $req->get_json_params();
    $links = (is_array($b) && isset($b['translations']) && is_array($b['translations']))
        ? $b['translations'] : array();
    $clean = array();
    foreach ($links as $lang => $pid) {
        $lang = sanitize_key((string) $lang);
        $pid  = (int) $pid;
        if ($lang && $pid && get_post_type($pid) === 'tribe_events') {
            pll_set_post_language($pid, $lang);   // garantit la langue avant de lier
            $clean[$lang] = $pid;
        }
    }
    if (count($clean) < 2) {
        return new WP_Error('need_two', 'Au moins deux langues valides requises.',
            array('status' => 400));
    }
    pll_save_post_translations($clean);
    return new WP_REST_Response(array('linked' => $clean), 200);
}

/**
 * (3) SLUG COMMUN À LA PAIRE — route dédiée, DEMANDE EXPLICITE (jamais posée en silence
 * par cs/v1/event, cf. cs-publish.php). Sert à aligner le slug d'une fiche IT/FR déjà
 * publiée sur celui de sa jumelle, une fois les deux appariées (link_translations_as,
 * mécanisme B) : sans URL commune, impossible de retrouver visuellement la paire.
 * wp_update_post() seul — jamais tribe_update_event() — pour ne toucher QUE le slug,
 * rien d'autre du post.
 */
add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/set-slug', array(
        'methods'             => 'POST',
        'callback'            => 'cs_set_slug',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
    ));
});

function cs_set_slug(WP_REST_Request $req) {
    $b = $req->get_json_params();
    $pid  = (int) ($b['post_id'] ?? 0);
    $slug = sanitize_title((string) ($b['slug'] ?? ''));
    if (!$pid || !$slug || get_post_type($pid) !== 'tribe_events') {
        return new WP_Error('bad_request', 'post_id/slug invalide.', array('status' => 400));
    }
    $old_slug = get_post_field('post_name', $pid);
    $result = wp_update_post(array('ID' => $pid, 'post_name' => $slug), true);
    if (is_wp_error($result)) {
        return new WP_Error('update_failed', $result->get_error_message(), array('status' => 500));
    }
    return new WP_REST_Response(array(
        'id' => $pid, 'old_slug' => $old_slug,
        'new_slug' => get_post_field('post_name', $pid),
        'permalink' => get_permalink($pid),
    ), 200);
}
