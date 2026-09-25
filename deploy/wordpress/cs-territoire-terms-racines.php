<?php
/**
 * Cartes : n afficher que le TERRITOIRE, jamais ses provinces.
 *
 * 2026-08-02 (Franck : "province de Turin on peut l enlever"). La taxonomie
 * territoire est hierarchique : 8 termes racines (les 4 territoires x 2 langues)
 * et 20 enfants (provinces et villes). Les cartes affichaient la liste complete,
 * d ou des "Piemont, Province de Turin" sur deux lignes qui cassaient la ligne
 * meta. On ne garde que les racines dans les listings ; les pages hub, qui ont
 * besoin des provinces, passent par un autre rendu et ne sont pas touchees.
 */
add_filter('jet-engine/listings/dynamic-terms/items', function ($terms) {
    if (empty($terms) || !is_array($terms)) { return $terms; }
    $roots = array();
    foreach ($terms as $t) {
        if (is_object($t) && isset($t->taxonomy) && $t->taxonomy === "territoire" && (int) $t->parent !== 0) { continue; }
        $roots[] = $t;
    }
    return !empty($roots) ? $roots : $terms;
}, 10);