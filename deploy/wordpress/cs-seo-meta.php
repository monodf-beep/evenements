<?php
/*
Plugin Name: Cultura Sabauda — Méta SEO exposées à l'API REST
Description: Autorise l'écriture, via l'API REST, des champs SEO Yoast
  (méta description, expression clé, titre SEO, aperçu Open Graph/Twitter) et des
  champs personnalisés « event_* » poussés par le backoffice Agenda. Sans cet
  enregistrement, WordPress IGNORE silencieusement ces méta dans le payload REST
  et Yoast reste vide (pas de méta description, pas d'expression clé, pas
  d'aperçu réseaux sociaux).
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer dans  wp-content/mu-plugins/cs-seo-meta.php
  (à côté de cs-rest-auth.php). Actif automatiquement (must-use plugin).
  Prérequis : l'extension Yoast SEO doit être installée et active.
*/

if (!defined('ABSPATH')) { exit; }

add_action('init', function () {

    // Seuls les utilisateurs pouvant éditer les articles peuvent écrire ces méta.
    $can_edit = function () {
        return current_user_can('edit_posts');
    };

    $register = function ($key, $auth) use ($can_edit) {
        register_post_meta('post', $key, array(
            'show_in_rest'  => true,
            'single'        => true,
            'type'          => 'string',
            'auth_callback' => $auth ? $can_edit : '__return_true',
        ));
    };

    // --- Champs Yoast (préfixe « _ » = méta protégée → auth_callback requis) ---
    foreach (array(
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_title',
        '_yoast_wpseo_opengraph-title',
        '_yoast_wpseo_opengraph-description',
        '_yoast_wpseo_opengraph-image',
        '_yoast_wpseo_twitter-title',
        '_yoast_wpseo_twitter-description',
    ) as $key) {
        $register($key, true);
    }

    // --- Champs personnalisés du backoffice (non protégés) --------------------
    foreach (array(
        'event_date_start', 'event_lieu', 'event_ville', 'event_territoire',
        'event_categorie', 'event_organisateur', 'event_prix', 'event_url_source',
        'event_llm_score', 'event_llm_justification',
    ) as $key) {
        $register($key, false);
    }
});
