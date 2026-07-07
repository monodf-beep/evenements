<?php
/*
Plugin Name: Agenda Sabauda — Endpoint de mise à la CORBEILLE (cs/v1/trash)
Description: Route REST maison « /wp-json/cs/v1/trash » qui met à la CORBEILLE
  (wp_trash_post — RÉVERSIBLE) un ÉVÉNEMENT The Events Calendar (post_type
  tribe_events) par son id. Sert au ménage piloté depuis le backoffice
  (scripts/cleanup_as_trash.py). SÉCURITÉ : ne touche QUE des tribe_events, et
  JAMAIS un contenu déjà publié (seulement draft/pending/future) — on ne peut donc
  pas détruire par erreur un événement mis en ligne à la main. Rien n'est supprimé
  définitivement : tout part à la corbeille et peut être restauré.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION (comme cs-publish.php) :
   A) Code Snippets : coller tout le code SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-trash.php.
  Auth : X-CS-Auth (cs-rest-auth.php) OU Application Password. Capacité requise :
  delete_posts.
*/

if (!defined('ABSPATH')) { exit; }

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/trash', array(
        'methods'             => 'POST',
        'callback'            => 'cs_trash_event',
        'permission_callback' => function () {
            return current_user_can('delete_posts');
        },
    ));
});

function cs_trash_event(WP_REST_Request $req) {
    $b  = $req->get_json_params();
    $id = is_array($b) && isset($b['id']) ? (int) $b['id'] : 0;
    if ($id <= 0) {
        return new WP_Error('no_id', 'Paramètre « id » manquant.', array('status' => 400));
    }
    $post = get_post($id);
    if (!$post) {
        return new WP_Error('not_found', 'Événement introuvable.', array('status' => 404));
    }
    // Garde-fou 1 : uniquement des événements TEC.
    if ($post->post_type !== 'tribe_events') {
        return new WP_Error('wrong_type', 'Ce n\'est pas un événement TEC.', array('status' => 409));
    }
    // Garde-fou 2 : jamais un contenu déjà PUBLIÉ en ligne (on ne nettoie que les
    // brouillons/planifiés créés par le bot). Un publish manuel est intouchable.
    if (in_array($post->post_status, array('publish', 'private'), true)) {
        return new WP_Error('published', 'Événement publié — non touché (sécurité).',
            array('status' => 409));
    }
    // Déjà en corbeille ? Idempotent.
    if ($post->post_status === 'trash') {
        return new WP_REST_Response(array('id' => $id, 'trashed' => true, 'already' => true), 200);
    }
    $res = wp_trash_post($id);   // RÉVERSIBLE — restaurable depuis la corbeille WP.
    if (!$res) {
        return new WP_Error('trash_fail', 'Mise à la corbeille échouée.', array('status' => 500));
    }
    return new WP_REST_Response(array(
        'id'      => $id,
        'trashed' => true,
        'title'   => get_the_title($id),
    ), 200);
}
