<?php
/*
Plugin Name: Agenda Sabauda — Core (taxonomie territoire + catégories + noindex)
Description: Regroupe en UN seul module, installable SANS SSH/SFTP, tout le code
  de lancement : la taxonomie hiérarchique « territoire » (+ amorce des 4 territoires
  & villes), l'amorce des 11 catégories d'événements, et le noindex des vues
  techniques de The Events Calendar. Remplace les mu-plugins as-territoire-taxo /
  as-seed-categories / as-noindex-tech-views (n'utilise PAS les deux à la fois).
Author: Cultura Sabauda
Version: 1.0

  DEUX FAÇONS DE L'INSTALLER, 100 % NAVIGATEUR (aucun terminal) :
  A) Extension « Code Snippets » : Extensions → Ajouter → « Code Snippets » →
     installer + activer. Puis Snippets → Add New → colle TOUT le code CI-DESSOUS
     (SANS la ligne « <?php ») → type « Run everywhere » → Save & Activate.
  B) Comme plugin : mets ce fichier dans un dossier « agenda-sabauda-core/ »,
     zippe le dossier, puis Extensions → Ajouter → Téléverser → active.

  APRÈS activation : Réglages → Permaliens → « Enregistrer » (purge des règles,
  sinon /territoire/... renvoie 404). REQUIERT The Events Calendar actif pour les
  catégories.
*/

if (!defined('ABSPATH')) { exit; }

/* ==========================================================================
 * 1) Taxonomie « territoire » (hiérarchique) sur événements + articles.
 * ========================================================================== */
add_action('init', function () {
    register_taxonomy('territoire', array('tribe_events', 'post'), array(
        'labels' => array(
            'name'          => 'Territoires',
            'singular_name' => 'Territoire',
            'all_items'     => 'Tous les territoires',
            'edit_item'     => 'Modifier le territoire',
            'add_new_item'  => 'Ajouter un territoire',
            'menu_name'     => 'Territoires',
        ),
        'public'            => true,
        'hierarchical'      => true,
        'show_ui'           => true,
        'show_admin_column' => true,
        'show_in_rest'      => true,
        'query_var'         => true,
        'rewrite'           => array('slug' => 'territoire', 'hierarchical' => true, 'with_front' => false),
    ));
}, 0);

/* ==========================================================================
 * 2) Amorce des 4 territoires + villes principales (une seule fois).
 * ========================================================================== */
add_action('init', function () {
    if (get_option('as_territoire_seeded')) { return; }

    $territoires = array(
        'savoie-haute-savoie'  => array('label' => 'Savoie / Haute-Savoie',
            'enfants' => array('annecy' => 'Annecy', 'chambery' => 'Chambéry')),
        'piemont'              => array('label' => 'Piémont',
            'enfants' => array('turin' => 'Turin')),
        'vallee-d-aoste'       => array('label' => "Vallée d'Aoste",
            'enfants' => array('aoste' => 'Aoste')),
        'nice-alpes-maritimes' => array('label' => 'Nice / Alpes-Maritimes',
            'enfants' => array('nice' => 'Nice')),
    );

    foreach ($territoires as $slug => $data) {
        $parent = term_exists($slug, 'territoire');
        if (!$parent) {
            $parent = wp_insert_term($data['label'], 'territoire', array('slug' => $slug));
        }
        if (is_wp_error($parent) || empty($parent['term_id'])) { continue; }
        $parent_id = (int) $parent['term_id'];
        foreach ($data['enfants'] as $child_slug => $child_label) {
            if (!term_exists($child_slug, 'territoire')) {
                wp_insert_term($child_label, 'territoire', array('slug' => $child_slug, 'parent' => $parent_id));
            }
        }
    }
    update_option('as_territoire_seeded', 1);
}, 11);

/* ==========================================================================
 * 3) Amorce des 11 catégories d'événements (requiert TEC actif).
 * ========================================================================== */
add_action('init', function () {
    if (get_option('as_categories_seeded')) { return; }
    if (!taxonomy_exists('tribe_events_cat')) { return; } // TEC pas encore actif → on retentera

    $categories = array(
        'expositions-patrimoine'  => 'Expositions & Patrimoine',
        'concerts-musique'        => 'Concerts & Musique',
        'spectacle-vivant'        => 'Spectacle vivant',
        'festivals'               => 'Festivals',
        'gastronomie-sagre'       => 'Gastronomie & Sagre',
        'marches-foires'          => 'Marchés & Foires',
        'sport'                   => 'Sport',
        'cinema'                  => 'Cinéma',
        'jeune-public-famille'    => 'Jeune public & Famille',
        'conferences-rencontres'  => 'Conférences & Rencontres',
        'fetes-traditions'        => 'Fêtes & Traditions populaires',
    );
    foreach ($categories as $slug => $name) {
        // Anti-doublon : on vérifie l'existence par SLUG *et* par NOM (WordPress
        // suffixe le slug si un terme du même NOM existe déjà → créait un doublon).
        if (!term_exists($slug, 'tribe_events_cat') && !term_exists($name, 'tribe_events_cat')) {
            wp_insert_term($name, 'tribe_events_cat', array('slug' => $slug));
        }
    }
    update_option('as_categories_seeded', 1);
}, 20);

/* ==========================================================================
 * 4) noindex des vues techniques TEC (semaine/photo/jour, params, pages vides).
 * ========================================================================== */
function as_is_tech_view() {
    if (is_admin()) { return false; }
    if (isset($_GET['tribe-bar-date']) || isset($_GET['eventDate'])) { return true; }
    $display = '';
    if (isset($_GET['eventDisplay'])) {
        $display = sanitize_key((string) $_GET['eventDisplay']);
    } else {
        $qv = get_query_var('eventDisplay');
        if (!empty($qv)) { $display = sanitize_key((string) $qv); }
    }
    if ($display !== '' && in_array($display, array('week', 'photo', 'day'), true)) { return true; }
    $uri = isset($_SERVER['REQUEST_URI']) ? (string) $_SERVER['REQUEST_URI'] : '';
    if ($uri !== '' && preg_match('#/(week|photo)(/|$|\?)#i', $uri)) { return true; }
    if (is_paged() && is_archive() && !have_posts()) { return true; }
    return false;
}
add_filter('rank_math/frontend/robots', function ($robots) {
    if (as_is_tech_view()) { $robots['index'] = 'noindex'; $robots['follow'] = 'follow'; }
    return $robots;
});
add_filter('wp_robots', function ($robots) {
    if (as_is_tech_view()) { $robots['noindex'] = true; $robots['follow'] = true; unset($robots['index']); }
    return $robots;
});
