<?php
/*
Plugin Name: Agenda Sabauda — Taxonomies bilingues FR/IT (Polylang)
Description: Rend les taxonomies « tribe_events_cat » (catégories) et « territoire »
  bilingues, pour des archives italiennes propres :
  (A) crée UNE FOIS les termes IT (nom + slug) et les LIE aux termes FR existants comme
      traductions Polylang (pll_save_term_translations) ;
  (B) au push d'un événement (cs/v1/event), si le post est en italien, RÉAFFECTE ses
      catégories/territoires vers leurs équivalents IT (sinon un événement IT reste rangé
      sous des termes FR → invisible dans les archives /it/).
  Indépendant de cs-polylang.php (qui pose la LANGUE du post à la priorité 20 ; ici on
  réaffecte à la priorité 30, donc après). Rollback : supprimer ce fichier.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-taxo-it.php (actif immédiatement).
  Prérequis : Polylang actif avec FR + IT ; termes FR déjà semés (slugs ci-dessous).
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Mapping des traductions : taxonomie => [ slug_FR => [ nom_IT, slug_IT ], ... ].
 * Les slugs FR sont ceux du plan du site (docs/… & as-seed-categories). On repère le
 * terme FR par son slug, on crée/rattache l'IT.
 */
function cs_taxo_it_map() {
    return array(
        'tribe_events_cat' => array(
            'expositions-patrimoine' => array('Mostre & Patrimonio',        'mostre-patrimonio'),
            'concerts-musique'       => array('Concerti & Musica',          'concerti-musica'),
            'spectacle-vivant'       => array('Spettacolo dal vivo',        'spettacolo-dal-vivo'),
            'festivals'              => array('Festival',                   'festival-it'),
            'gastronomie-sagre'      => array('Gastronomia & Sagre',        'gastronomia-sagre'),
            'marches-foires'         => array('Mercati & Fiere',            'mercati-fiere'),
            'sport'                  => array('Sport',                      'sport-it'),
            'cinema'                 => array('Cinema',                     'cinema-it'),
            'jeune-public-famille'   => array('Per bambini & Famiglia',     'per-bambini-famiglia'),
            'conferences-rencontres' => array('Conferenze & Incontri',      'conferenze-incontri'),
            'fetes-traditions'       => array('Feste & Tradizioni popolari','feste-tradizioni'),
        ),
        'territoire' => array(
            'savoie-haute-savoie'  => array('Savoia / Alta Savoia',    'savoia-alta-savoia'),
            'piemont'              => array('Piemonte',                'piemonte'),
            'vallee-d-aoste'       => array("Valle d'Aosta",           'valle-d-aosta'),
            'nice-alpes-maritimes' => array('Nizza / Alpi Marittime',  'nizza-alpi-marittime'),
        ),
    );
}

/**
 * (A) Crée les termes IT et les lie aux termes FR. Idempotent : marqué par une option,
 * et re-jouable sans doublon (on retrouve le terme IT par slug s'il existe déjà).
 */
add_action('init', function () {
    if (get_option('cs_taxo_it_done')) { return; }
    foreach (array('pll_set_term_language', 'pll_get_term_language', 'pll_save_term_translations',
                   'pll_default_language') as $fn) {
        if (!function_exists($fn)) { return; }   // Polylang pas prêt → on retentera au prochain init
    }
    $default = pll_default_language();
    if (!$default) { return; }

    foreach (cs_taxo_it_map() as $tax => $terms) {
        if (!taxonomy_exists($tax)) { continue; }
        foreach ($terms as $fr_slug => $it) {
            $fr = get_term_by('slug', $fr_slug, $tax);
            if (!$fr) { continue; }                       // terme FR absent → on saute
            if (!pll_get_term_language($fr->term_id)) {
                pll_set_term_language($fr->term_id, $default);
            }
            list($it_name, $it_slug) = $it;
            $it_term = get_term_by('slug', $it_slug, $tax);
            if ($it_term) {
                $it_id = (int) $it_term->term_id;
            } else {
                $res = wp_insert_term($it_name, $tax, array('slug' => $it_slug));
                if (is_wp_error($res)) { continue; }
                $it_id = (int) $res['term_id'];
            }
            pll_set_term_language($it_id, 'it');
            pll_save_term_translations(array($default => (int) $fr->term_id, 'it' => $it_id));
        }
    }
    update_option('cs_taxo_it_done', 1);
}, 40);

/**
 * (B) Au push cs/v1/event : si le post est en IT, réaffecte ses catégories/territoires
 * vers leurs équivalents IT. Défensif : à défaut de traduction, on garde le terme
 * d'origine. S'exécute après cs-polylang.php (langue posée en priorité 20).
 */
add_filter('rest_request_after_callbacks', function ($response, $handler, $request) {
    if ($request->get_route() !== '/cs/v1/event') { return $response; }
    if (!function_exists('pll_get_post_language') || !function_exists('pll_get_term')
        || !function_exists('pll_default_language')) { return $response; }
    $data = ($response instanceof WP_REST_Response) ? $response->get_data() : null;
    $pid  = (is_array($data) && !empty($data['id'])) ? (int) $data['id'] : 0;
    if (!$pid) { return $response; }
    $lang = pll_get_post_language($pid);
    if (!$lang || $lang === pll_default_language()) { return $response; }  // FR → rien à faire

    foreach (array('tribe_events_cat', 'territoire') as $tax) {
        $ids = wp_get_object_terms($pid, $tax, array('fields' => 'ids'));
        if (is_wp_error($ids) || !$ids) { continue; }
        $mapped = array();
        foreach ($ids as $tid) {
            $tr = pll_get_term((int) $tid, $lang);         // traduction dans la langue du post
            $mapped[] = $tr ? (int) $tr : (int) $tid;      // repli : terme d'origine
        }
        wp_set_object_terms($pid, array_values(array_unique($mapped)), $tax, false);
    }
    return $response;
}, 30, 3);
