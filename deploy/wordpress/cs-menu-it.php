<?php
/*
Plugin Name: Agenda Sabauda — Menus : bascule URL + libellé vers la traduction IT
Description: Filtre wp_nav_menu_objects (s'applique à tout menu WP, wp_nav_menu() ET
  widget Navigation Menu) : pour les items de type post_type/taxonomy dont l'objet
  source a une traduction Polylang dans la langue courante, remplace l'URL par le
  permalien traduit. Le libellé est traduit via une table statique (labels courts,
  volontairement différents des noms de taxonomie complets « Concerts & Musique » etc.)
  pour les entrées listées le 2026-07-20 ; les autres items post_type traduits
  reprennent simplement post_title de la traduction (déjà correct : « Questo weekend »,
  « Eventi », « Informazioni utili »).

  Réversible : supprimer ce fichier pour revenir au comportement Polylang par défaut
  (menus identiques FR/IT, comme avant le 2026-07-20).

  Historique : 1re version (2026-07-20) avait une erreur de syntaxe — les 4 entrées
  « territoire » étaient placées APRÈS le return/la fermeture du tableau → fatale sur
  toutes les pages. Corrigé ici (entrées remises dans le tableau) et validé php -l.
*/
if (!defined('ABSPATH')) { exit; }

function cs_menu_it_short_labels() {
    return array(
        'tribe_events_cat:13'  => 'Concerti',       // Concerts & Musique -> Concerti
        'tribe_events_cat:12'  => 'Mostre',         // Expositions & Patrimoine -> Mostre
        'tribe_events_cat:17'  => 'Gastronomia',    // Gastronomie & Sagre -> Gastronomia
        'tribe_events_cat:22'  => 'In famiglia',    // Jeune public & Famille -> In famiglia
        'tribe_events_cat:344' => 'Curiosità',      // Curiosités -> Curiosità
        // Territoires : items convertis custom -> taxonomy le 2026-07-20 (liens Hub IT
        // cassés). Sans ces entrées, le libellé resterait en français (Savoie, Piémont…)
        // même si l'URL, elle, est déjà correctement traduite par le filtre ci-dessous.
        'territoire:3'  => 'Savoia',                // Savoie / Haute-Savoie -> Savoia
        'territoire:6'  => 'Piemonte',              // Piémont -> Piemonte
        'territoire:8'  => "Valle d'Aosta",         // Vallée d'Aoste -> Valle d'Aosta
        'territoire:10' => 'Nizza',                 // Nice / Alpes-Maritimes -> Nizza
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
