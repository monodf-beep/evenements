<?php
/*
Plugin Name: Agenda Sabauda — Filtre territoire du switcher home (?as_territoire=)
Description: Le bandeau «Vous regardez X | Changer : ...» de la home (desktop + dropdown
  mobile) pointait vers les Hubs territoire sans jamais filtrer la home elle-meme. Demande
  de Franck (2026-07-20) : cliquer sur un territoire doit filtrer les sections dynamiques de
  la home sur ce territoire (les liens eux-memes sont corriges separement, edition statique
  du post_content, pour pointer vers home + ?as_territoire=<slug> au lieu des Hubs).

  Ce fichier lit ?as_territoire=<slug> (valide contre la LANGUE courante : un slug IT n'est
  accepte que sur la home IT, un slug FR seulement sur la home FR) et ajoute une clause
  tax_query territoire aux 8 requetes qui alimentent la home (14 a-venir-7j, 15 vedette,
  16 evidence, 17 nouveautes-home, 18-21 par categorie). PAS les requetes 22/23 "autre
  versant", semantiquement incompatibles avec un filtre territoire explicite (leur but est
  justement de montrer l'autre versant).

  PORTEE ASSUMEE : sans ?territoire dans l'URL, RIEN ne change (comportement identique a
  avant — mix de tous les territoires). Seul un clic explicite (URL avec le parametre)
  declenche le filtre.

  Rollback : supprimer ce fichier.
*/
if (!defined('ABSPATH')) { exit; }

add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [14, 15, 16, 17, 18, 19, 20, 21], true)) {
        return $args;
    }
    if (empty($_GET['as_territoire'])) {
        return $args;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    $param = sanitize_title(wp_unslash($_GET['as_territoire']));

    $map_fr = [
        'savoie' => 3,
        'piemont' => 6,
        'vallee-d-aoste' => 8,
        'comte-de-nice' => 10,
    ];
    $map_it = [
        'savoia' => 318,
        'piemonte' => 321,
        'valle-d-aosta' => 324,
        'contea-di-nizza' => 327,
    ];
    $map = $lang === 'it' ? $map_it : $map_fr;

    if (!isset($map[$param])) {
        return $args;
    }

    $args['tax_query'] = $args['tax_query'] ?? [];
    $args['tax_query'][] = [
        'taxonomy' => 'territoire',
        'field'    => 'term_id',
        'terms'    => $map[$param],
    ];

    return $args;
}, 10, 2);