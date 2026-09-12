<?php
/*
Plugin Name: Agenda Sabauda — Menus : bascule URL + libellé vers la traduction IT
Description: Filtre wp_nav_menu_objects pour traduire URL + libellé des items de menu
  post_type/taxonomy en langue courante (Polylang). Table statique pour les libellés
  courts (catégories + territoires) ; sinon post_title de la traduction.
  Réversible : supprimer ce fichier. Corrigé 2026-07-20 (entrées territoire remises
  dans le tableau ; l'ancienne version les avait après le return -> fatale).
*/
if (!defined('ABSPATH')) { exit; }

function cs_menu_it_short_labels() {
    return array(
        'tribe_events_cat:13'  => 'Concerti',
        'tribe_events_cat:12'  => 'Mostre',
        'tribe_events_cat:17'  => 'Gastronomia',
        'tribe_events_cat:22'  => 'In famiglia',
        'tribe_events_cat:344' => 'Curiosità',
        'territoire:3'  => 'Savoia',
        'territoire:6'  => 'Piemonte',
        'territoire:8'  => "Valle d'Aosta",
        'territoire:10' => 'Nizza',
    );
}

add_filter('wp_nav_menu_objects', function ($items) {
    if (!function_exists('pll_current_language')) {
        return $items;
    }
    $lang = pll_current_language();
    if (!$lang || 'fr' === $lang) {
        return $items;
    }

    $labels = cs_menu_it_short_labels();

    foreach ($items as $item) {
        if (!in_array($item->type, array('post_type', 'taxonomy'), true) || empty($item->object_id)) {
            continue;
        }

        $translated_id = null;
        if ('post_type' === $item->type) {
            $translated_id = function_exists('pll_get_post') ? pll_get_post($item->object_id, $lang) : null;
        } elseif ('taxonomy' === $item->type) {
            $translated_id = function_exists('pll_get_term') ? pll_get_term($item->object_id, $lang) : null;
        }
        if (!$translated_id || (int) $translated_id === (int) $item->object_id) {
            continue;
        }

        $new_url = 'taxonomy' === $item->type
            ? get_term_link((int) $translated_id, $item->object)
            : get_permalink((int) $translated_id);
        if (is_wp_error($new_url) || !$new_url) {
            continue;
        }
        $item->url = $new_url;

        $label_key = $item->object . ':' . $item->object_id;
        if (isset($labels[$label_key])) {
            $item->title = $labels[$label_key];
        } elseif ('post_type' === $item->type) {
            $translated_title = get_the_title((int) $translated_id);
            if ($translated_title) {
                $item->title = $translated_title;
            }
        }
    }

    return $items;
}, 10, 1);
