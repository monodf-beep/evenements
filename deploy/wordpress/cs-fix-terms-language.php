<?php
/*
Plugin Name: Agenda Sabauda — Assigne la langue par défaut aux termes (Polylang)
Description: Corrige la boîte de taxonomie VIDE dans l'éditeur d'événement : les
  catégories (tribe_events_cat) et territoires (territoire) créés par snippet n'ont
  AUCUNE langue Polylang → Polylang les masque de la sélection. On leur assigne, UNE
  FOIS, la langue par défaut (FR) pour les termes qui n'en ont pas. Sans effet sur les
  termes déjà traduits. Après exécution, tu peux désactiver ce snippet.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : Code Snippets → Add New → colle le code CI-DESSOUS (SANS « <?php »)
  → « Run everywhere » → Save & Activate. Puis recharge un événement : les cases
  Catégories / Territoires réapparaissent (avec la bonne cochée).
*/

if (!defined('ABSPATH')) { exit; }

add_action('init', function () {
    if (get_option('as_terms_lang_fixed')) { return; }
    if (!function_exists('pll_set_term_language')
        || !function_exists('pll_get_term_language')
        || !function_exists('pll_default_language')) {
        return; // Polylang pas encore chargé — on retentera au prochain init.
    }
    $default = pll_default_language();
    if (!$default) { return; }

    foreach (array('tribe_events_cat', 'territoire') as $tax) {
        $terms = get_terms(array('taxonomy' => $tax, 'hide_empty' => false));
        if (is_wp_error($terms) || !$terms) { continue; }
        foreach ($terms as $t) {
            if (!pll_get_term_language($t->term_id)) {
                pll_set_term_language($t->term_id, $default);
            }
        }
    }
    update_option('as_terms_lang_fixed', 1);
}, 30);
