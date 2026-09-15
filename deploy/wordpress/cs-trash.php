<?php
/*
⚠️ CE FICHIER N'EST PAS CE QUI TOURNE (vérifié le 2026-08-18).

  Il n'existe AUCUN `wp-content/mu-plugins/cs-trash.php` sur le serveur : les routes
  `cs/v1/trash` et `cs/v1/list` sont servies par le **snippet Code Snippets #10 « CS
  Trash »**, actif, portée globale. Modifier ce fichier-ci ne change donc rien au site —
  je l'ai fait ce jour-là avant de vérifier, et c'était la faute du 12/08 refaite à
  l'identique (cf. docs/ERREURS_2026-08-17.md, « conclure sur un indice de surface »).

  La copie FIDÈLE du code exécuté, empreinte vérifiée, est dans
  `deploy/wordpress/code-snippets/10-cs-trash.php`. C'est elle qu'il faut lire, et c'est
  la BASE qu'il faut modifier.

  Ce fichier est conservé parce que son en-tête documente les deux installations
  possibles, et parce qu'un déploiement futur en mu-plugin repartirait de lui.

Plugin Name: Agenda Sabauda — Endpoint de mise à la CORBEILLE (cs/v1/trash)
Description: Route REST maison « /wp-json/cs/v1/trash » qui met à la CORBEILLE
  (wp_trash_post — RÉVERSIBLE) un ÉVÉNEMENT The Events Calendar (post_type
  tribe_events) par son id. Sert au ménage piloté depuis le backoffice
  (scripts/cleanup_as_trash.py). SÉCURITÉ : ne touche QUE des tribe_events, et
  JAMAIS un contenu déjà publié (seulement draft/pending/future) — on ne peut donc
  pas détruire par erreur un événement mis en ligne à la main. Rien n'est supprimé
  définitivement : tout part à la corbeille et peut être restauré.
Author: Cultura Sabauda
Version: 1.1

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
    // Inventaire des événements (pour détecter les doublons CÔTÉ WordPress — ceux
    // qui ne sont pas tracés comme doublons dans la base du backoffice).
    register_rest_route('cs/v1', '/list', array(
        'methods'             => 'GET',
        'callback'            => 'cs_list_events',
        'permission_callback' => function () {
            return current_user_can('edit_posts');
        },
    ));
});

/**
 * Liste les événements TEC (hors corbeille) avec de quoi juger les doublons et la
 * complétude : titre, date de début, statut, présence d'un lieu et d'une image.
 */
function cs_list_events(WP_REST_Request $req) {
    $posts = get_posts(array(
        'post_type'   => 'tribe_events',
        'post_status' => array('draft', 'pending', 'future', 'publish', 'private'),
        'numberposts' => -1,
        'orderby'     => 'ID',
        'order'       => 'ASC',
    ));
    $out = array();
    foreach ($posts as $p) {
        $out[] = array(
            'id'     => $p->ID,
            'title'  => get_the_title($p->ID),
            'status' => $p->post_status,
            'start'  => get_post_meta($p->ID, '_EventStartDate', true),
            'venue'  => (int) get_post_meta($p->ID, '_EventVenueID', true),
            'thumb'  => has_post_thumbnail($p->ID) ? 1 : 0,
        );
    }
    return new WP_REST_Response($out, 200);
}

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
    // brouillons/planifiés créés par le bot) — SAUF si l'appelant passe "force":true
    // de façon délibérée (ex. retrait d'un article de presse publié par erreur via
    // scripts/audit_non_events.py). Reste réversible (corbeille), pas de suppression.
    $force = is_array($b) && !empty($b['force']);
    if (in_array($post->post_status, array('publish', 'private'), true) && !$force) {
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
