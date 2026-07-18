<?php
/*
Plugin Name: Agenda Sabauda — Taxonomie « Territoire »
Description: Ajoute la taxonomie hiérarchique « territoire » (l'axe identitaire des
  4 territoires transfrontaliers, absent nativement de The Events Calendar) sur les
  événements TEC (tribe_events) et les articles. URL /territoire/{terr}[/{ville}]/,
  exposée à l'API REST (bloc éditeur + push backoffice). Amorce les 4 territoires
  et quelques villes principales en termes enfants — une seule fois.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer dans  wp-content/mu-plugins/as-territoire-taxo.php
  (à côté de cs-rest-auth.php / cs-seo-meta.php). Actif automatiquement (must-use).
  Après dépôt : Réglages → Permaliens → « Enregistrer » pour purger les règles de
  réécriture (sinon /territoire/... renvoie 404). Slugs URL cohérents avec le plan
  du site ; le préfixe de langue (/fr/, /it/) est ajouté par Polylang.
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Enregistre la taxonomie hiérarchique « territoire ».
 */
add_action('init', function () {

    $labels = array(
        'name'              => 'Territoires',
        'singular_name'     => 'Territoire',
        'search_items'      => 'Rechercher un territoire',
        'all_items'         => 'Tous les territoires',
        'parent_item'       => 'Territoire parent',
        'parent_item_colon' => 'Territoire parent :',
        'edit_item'         => 'Modifier le territoire',
        'update_item'       => 'Mettre à jour le territoire',
        'add_new_item'      => 'Ajouter un territoire',
        'new_item_name'     => 'Nom du nouveau territoire',
        'menu_name'         => 'Territoires',
    );

    register_taxonomy('territoire', array('tribe_events', 'post'), array(
        'labels'            => $labels,
        'public'            => true,
        'hierarchical'      => true,
        'show_ui'           => true,
        'show_admin_column' => true,
        'show_in_rest'      => true,
        'query_var'         => true,
        'rewrite'           => array(
            'slug'         => 'territoire',
            'hierarchical' => true,
            'with_front'   => false,
        ),
    ));
}, 0);

/**
 * Amorce les 4 territoires + quelques villes (termes enfants), une seule fois.
 * Le drapeau d'option évite de retenter l'insertion à chaque chargement.
 */
add_action('init', function () {

    if (get_option('as_territoire_seeded')) {
        return;
    }

    // Territoire parent  =>  villes enfants.
    // Clés = slugs (cohérents avec le plan du site) ; valeurs = libellé + enfants.
    $territoires = array(
        'savoie-haute-savoie' => array(
            'label'   => 'Savoie',
            'enfants' => array(
                'annecy'   => 'Annecy',
                'chambery' => 'Chambéry',
            ),
        ),
        'piemont' => array(
            'label'   => 'Piémont',
            'enfants' => array(
                'turin' => 'Turin',
            ),
        ),
        'vallee-d-aoste' => array(
            'label'   => 'Vallée d\'Aoste',
            'enfants' => array(
                'aoste' => 'Aoste',
            ),
        ),
        'nice-alpes-maritimes' => array(
            'label'   => 'Nice / Alpes-Maritimes',
            'enfants' => array(
                'nice' => 'Nice',
            ),
        ),
    );

    foreach ($territoires as $slug => $data) {

        $parent = term_exists($slug, 'territoire');
        if (!$parent) {
            $parent = wp_insert_term($data['label'], 'territoire', array('slug' => $slug));
        }
        if (is_wp_error($parent) || empty($parent['term_id'])) {
            continue;
        }
        $parent_id = (int) $parent['term_id'];

        foreach ($data['enfants'] as $child_slug => $child_label) {
            if (!term_exists($child_slug, 'territoire')) {
                wp_insert_term($child_label, 'territoire', array(
                    'slug'   => $child_slug,
                    'parent' => $parent_id,
                ));
            }
        }
    }

    update_option('as_territoire_seeded', 1);
}, 11);
