<?php
/*
Plugin Name: Agenda Sabauda — Amorce des 11 catégories
Description: Crée une seule fois les 11 catégories d'événements (taxonomie native
  de The Events Calendar « tribe_events_cat »), avec les NOMS et SLUGS exacts du
  plan du site (docs/categories.md). Évite la saisie manuelle et garantit des slugs
  immuables. Les libellés italiens se posent ensuite dans Polylang (traduction des
  termes) ; ce plugin ne crée que les termes FR de référence.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer dans  wp-content/mu-plugins/as-seed-categories.php
  (à côté de as-territoire-taxo.php). Actif automatiquement (must-use).
  REQUIERT que The Events Calendar soit actif (sinon la taxonomie n'existe pas
  encore et l'amorce est simplement reportée au prochain chargement).
  Slugs FIGÉS : ne pas les modifier après indexation (casse les URLs et les liens).
*/

if (!defined('ABSPATH')) { exit; }

add_action('init', function () {

    // Déjà fait ? on sort.
    if (get_option('as_categories_seeded')) {
        return;
    }
    // TEC pas encore actif → la taxonomie n'existe pas ; on retentera plus tard.
    if (!taxonomy_exists('tribe_events_cat')) {
        return;
    }

    // Ordre = ordre d'affichage souhaité. slug => nom exact (FR).
    // Ce sont EXACTEMENT les 11 catégories de l'évaluateur (llm_categorie) et du
    // plan du site — mot pour mot. Ne pas diverger.
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
        // term_exists() vérifie le slug DANS la taxonomie : idempotent, ne
        // recrée jamais un terme existant (ni ne renomme un terme déjà là).
        if (!term_exists($slug, 'tribe_events_cat')) {
            wp_insert_term($name, 'tribe_events_cat', array('slug' => $slug));
        }
    }

    update_option('as_categories_seeded', 1);
}, 20); // après l'enregistrement de la taxonomie par The Events Calendar
