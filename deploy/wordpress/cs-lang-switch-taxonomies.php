<?php
/*
Plugin Name: Agenda Sabauda — Fix switch de langue sur les archives de taxonomie
Description: Signale par Franck le 2026-07-20 : sur les Hubs (territoire, categorie TEC,
  type de lieu), les liens FR|IT du header renvoyaient vers la HOME de l'autre langue au
  lieu de l'archive du terme traduit (ex. /territoire/savoie/ -> lien IT
  = /it/home-it/ au lieu de /it/territoire/savoia/). Polylang ne resout pas
  l'URL traduite pour ces taxonomies custom ; on la calcule nous-memes via le filtre
  officiel 'pll_translation_url' (utilise par pll_the_languages, donc corrige d'un coup
  le header ET le footer, sans modifier site-header-footer.php).

  Pour les contenus SANS traduction (ex. fiche evenement non traduite), le repli vers
  la home de l'autre langue reste le comportement voulu (pas de page equivalente a montrer).

  Rollback : supprimer ce fichier.
*/
if (!defined('ABSPATH')) { exit; }

add_filter('pll_translation_url', function ($url, $lang) {
    if (!is_tax(['territoire', 'tribe_events_cat', 'type_de_lieu'])) {
        return $url;
    }
    $term = get_queried_object();
    if (!$term || empty($term->term_id) || !function_exists('pll_get_term')) {
        return $url;
    }
    $translated_id = pll_get_term($term->term_id, $lang);
    if (!$translated_id) {
        return $url;
    }
    $link = get_term_link((int) $translated_id, $term->taxonomy);
    return is_wp_error($link) ? $url : $link;
}, 10, 2);