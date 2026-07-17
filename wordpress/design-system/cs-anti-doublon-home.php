<?php
/**
 * CS · Anti-doublon home (offsets sections dynamiques) — Code Snippets id 44,
 * scope front-end. Poussé via Novamira le 2026-07-17, complété le même jour.
 *
 * Diagnostic initial : toutes les sections dynamiques de la home (À la une,
 * Événements d'aujourd'hui, Ce week-end, En évidence, L'agenda à venir)
 * utilisaient le même jet-engine/listing-grid sans aucun filtre de requête,
 * donc affichaient systématiquement les mêmes premiers événements publiés.
 * Chaque bloc a reçu un attribut "_element_id" distinct (dans
 * homepage-mobile.gutenberg.html) ; ce filtre applique un offset croissant
 * par _element_id pour que chaque section montre une fenêtre différente du
 * même pool d'événements.
 *
 * Complété le 2026-07-17 (même jour) : Polylang est actif (fr/it,
 * force_lang=1) et tous les événements publiés ont une langue assignée,
 * mais jet-engine/listing-grid construit sa propre WP_Query qui ne passe
 * PAS par le filtrage automatique de Polylang (réservé à la requête
 * principale). Sans ce correctif, un visiteur sur la version FR pouvait
 * voir des événements en italien (et inversement). Ajout de
 * $args['lang'] = pll_current_language() pour forcer chaque grille à
 * respecter la langue couramment consultée.
 */
add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    if (function_exists('pll_current_language')) {
        $args['lang'] = pll_current_language();
    }

    $offsets = [
        'jour'            => 4,
        'weekend'         => 8,
        'evidence'        => 14,
        'evidence-bottom' => 17,
        'venir'           => 20,
        'venir-bottom'    => 24,
    ];
    $eid = $settings['_element_id'] ?? '';
    if (isset($offsets[$eid])) {
        $args['offset'] = $offsets[$eid];
    }

    return $args;
}, 10, 3);
