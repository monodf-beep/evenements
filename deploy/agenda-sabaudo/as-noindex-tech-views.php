<?php
/*
Plugin Name: Agenda Sabaudo — noindex des vues techniques TEC
Description: Pose « noindex, follow » sur les vues techniques de The Events Calendar
  (semaine /week/, photo /photo/, jour /day/, et paramètres ?eventDisplay= /
  ?tribe-bar-date= / ?eventDate=) ainsi que sur les pages paginées vides. Ces URLs
  ne sont PAS visibles dans l'UI de RankMath : sans ce mu-plugin, TEC génère une
  pagination quasi-infinie = index bloat. Complète les Disallow du robots.txt.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer dans  wp-content/mu-plugins/as-noindex-tech-views.php
  (à côté des autres mu-plugins). Actif automatiquement (must-use).
  Rappel : IndexNow reste ON dans RankMath ; ici on empêche seulement l'indexation
  des vues sans valeur, pas des fiches ni des hubs.
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Vrai si la requête courante est une vue technique TEC à ne pas indexer.
 *
 * @return bool
 */
function as_is_tech_view() {

    if (is_admin()) {
        return false;
    }

    // 1) Paramètres d'URL des vues TEC (?eventDisplay=, ?tribe-bar-date=, ?eventDate=).
    if (isset($_GET['tribe-bar-date']) || isset($_GET['eventDate'])) {
        return true;
    }

    // 2) Vues « display » techniques : semaine, photo, jour (list/month = calendrier utile).
    $display = '';
    if (isset($_GET['eventDisplay'])) {
        $display = sanitize_key((string) $_GET['eventDisplay']);
    } else {
        $qv = get_query_var('eventDisplay');
        if (!empty($qv)) {
            $display = sanitize_key((string) $qv);
        }
    }
    $tech_displays = array('week', 'photo', 'day');
    if ($display !== '' && in_array($display, $tech_displays, true)) {
        return true;
    }

    // 3) Segments d'URL /week/ et /photo/ (permaliens des vues TEC).
    $uri = isset($_SERVER['REQUEST_URI']) ? (string) $_SERVER['REQUEST_URI'] : '';
    if ($uri !== '' && preg_match('#/(week|photo)(/|$|\?)#i', $uri)) {
        return true;
    }

    // 4) Pages paginées vides (pagination au-delà du contenu réel).
    if (is_paged() && is_archive() && !have_posts()) {
        return true;
    }

    return false;
}

/**
 * Signale la vue à RankMath (source de vérité SEO du site).
 */
add_filter('rank_math/frontend/robots', function ($robots) {
    if (as_is_tech_view()) {
        $robots['index']  = 'noindex';
        $robots['follow'] = 'follow';
    }
    return $robots;
});

/**
 * Filet de sécurité natif (WP >= 5.7) au cas où RankMath serait absent/inactif.
 */
add_filter('wp_robots', function ($robots) {
    if (as_is_tech_view()) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
        unset($robots['index']);
    }
    return $robots;
});
