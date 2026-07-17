<?php
/**
 * CS · Anti-doublon home (offsets sections dynamiques) + garantie photo —
 * Code Snippets id 44, scope front-end. Poussé via Novamira le 2026-07-17,
 * complété le même jour (langue Polylang), complété à nouveau le 2026-07-17
 * (garantie photo sur "À la une"/"Ce week-end"/"Événements d'aujourd'hui").
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
 *
 * Complété le 2026-07-17 (garantie photo) : la maquette n'affiche jamais le
 * placeholder "Visuel" vide sur les cartes "À la une", "Ce week-end" et
 * "Événements d'aujourd'hui" (_element_id "ala-une"/"weekend"/"jour" —
 * partagé entre les blocs mobile ET desktop qui utilisent le même
 * _element_id). On restreint donc le pool de CES 3 sections aux tribe_events
 * ayant une image mise en avant (_thumbnail_id EXISTS). Les offsets
 * ci-dessus s'appliquent maintenant DANS ce sous-pool filtré, pas le pool
 * complet — le nombre total disponible baisse en conséquence, c'est normal
 * et acceptable (vérifié en live le 2026-07-17 : 21 tribe_events publiés
 * avec photo sur 39 au total, dont 19 FR / 2 IT après filtrage Polylang —
 * suffisant pour les offsets actuels côté FR ; si un offset dépasse le pool
 * filtré disponible, la section affiche juste moins d'items, pas d'erreur).
 * Les colonnes "Nouveautés"/"En évidence"/"L'agenda à venir" (evidence,
 * evidence-bottom, venir, venir-bottom) NE SONT PAS concernées : elles
 * peuvent continuer à afficher le placeholder "Visuel".
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

    if (in_array($eid, ['ala-une', 'weekend', 'jour'], true)) {
        $args['meta_query'] = $args['meta_query'] ?? [];
        $args['meta_query'][] = [
            'key'     => '_thumbnail_id',
            'compare' => 'EXISTS',
        ];
    }

    return $args;
}, 10, 3);
