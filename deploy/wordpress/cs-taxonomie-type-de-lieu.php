<?php
/*
Plugin Name: Agenda Sabauda — Taxonomie "Type de lieu" (Musee, Theatre, Exterieur...)
Description: Nouvelle taxonomie sur les lieux (tribe_venue), demandee par Franck le
  2026-07-20 pour la tuile home "Musees" : jusqu'ici impossible de filtrer "les
  evenements qui se passent dans un musee" faute de donnee (les evenements ont une
  categorie thematique, pas un type de lieu). Non hierarchique, visible dans l'admin
  (colonne + filtre sur la liste des lieux), traduite par Polylang comme les autres
  taxonomies du site.

  IMPORTANT : le tagging des lieux existants (assigner "Musee" aux vrais musees) est
  un travail de DONNEE, pas de dev -- à faire un par un dans l'admin, et/ou a ajouter
  au endpoint REST cs/v1/event (backoffice publisher.py) pour que les NOUVEAUX lieux
  crees automatiquement puissent porter ce type des la creation (signale par Franck :
  "faut aussi en backoffice"). Ce fichier ne cree QUE la taxonomie -- pas de termes,
  pas de tagging, pas de modification du endpoint REST (fichier different, hors
  perimetre WordPress pur).

  Rollback : supprimer ce fichier (les eventuels tags deja poses sur des lieux restent
  en base, juste invisibles/inutilises tant que la taxonomie n'est pas re-enregistree).
*/
if (!defined('ABSPATH')) { exit; }

add_action('init', function () {
    if (taxonomy_exists('type_de_lieu')) {
        return;
    }
    register_taxonomy('type_de_lieu', ['tribe_venue'], [
        'labels' => [
            'name' => 'Types de lieu',
            'singular_name' => 'Type de lieu',
            'all_items' => 'Tous les types de lieu',
        ],
        'hierarchical' => false,
        'public' => true,
        'show_ui' => true,
        'show_admin_column' => true,
        'show_in_rest' => true,
        'rewrite' => ['slug' => 'type-de-lieu'],
    ]);
}, 5);
