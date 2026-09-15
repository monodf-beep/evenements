<?php
/*
Plugin Name: Agenda Sabauda — Nettoyage des métas Rank Math orphelines (one-shot)
Description: Supprime, UNE SEULE FOIS, toutes les métadonnées « rank_math_* » laissées
  en base après le passage de Rank Math à Yoast. Ces métas sont inertes (Rank Math
  désinstallé) mais encombrent l'éditeur. S'exécute une fois puis se met en veille
  (option as_rankmath_cleaned). Après exécution, tu peux désactiver/supprimer ce snippet.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : Code Snippets → Add New → colle le code CI-DESSOUS (SANS « <?php »)
  → « Run everywhere » → Save & Activate. Le nettoyage se fait au premier chargement.
*/

if (!defined('ABSPATH')) { exit; }

add_action('init', function () {
    if (get_option('as_rankmath_cleaned')) { return; }
    global $wpdb;
    $deleted = $wpdb->query(
        "DELETE FROM {$wpdb->postmeta} WHERE meta_key LIKE 'rank_math_%'"
    );
    update_option('as_rankmath_cleaned', 1);
    // Trace discrète dans les logs si WP_DEBUG est actif.
    if (defined('WP_DEBUG') && WP_DEBUG) {
        error_log('[cs-cleanup-rankmath] métas rank_math_* supprimées : ' . (int) $deleted);
    }
});
