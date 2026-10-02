<?php
/*
Plugin Name: Agenda Sabauda — étiquettes dans la langue de la fiche
Description: Après chaque publication via cs/v1/event, remplace toute étiquette (post_tag)
  d'une AUTRE langue que la fiche par sa traduction Polylang, quand elle existe.
Author: Cultura Sabauda
Version: 1.0
*/

/*
 * POURQUOI. `post_tag` est une taxonomie traduite par Polylang sur ce site. Le publisher
 * envoie l'étiquette par son NOM (« Giornate Europee del Patrimonio »), et cs-publish
 * (Code Snippets, id 6) la résout avec wp_set_object_terms() — donc par slug puis par nom,
 * SANS connaître la langue de la fiche : celle-ci n'est posée qu'APRÈS le callback, par
 * le snippet Polylang (id 33, filtre rest_request_after_callbacks, priorité 20).
 *
 * Mesuré le 22/09 au soir, sur les fiches des Journées du patrimoine :
 *   - le terme 900 « Giornate Europee del Patrimonio » est de langue FRANÇAISE pour
 *     Polylang, apparié au terme italien 902 (slug suffixé « -it ») ;
 *   - la traduction de 22h a posé le 900 sur 22 fiches italiennes ; la précédente avait
 *     posé le 902 sur 21 autres. Pourquoi l'une et pas l'autre n'est PAS établi ;
 *   - une requête `lang=it` ne voit que les termes italiens : ces 22 fiches étaient en
 *     ligne, étiquetées, et absentes de la page dédiée comme de la strate d'accueil.
 *
 * CE QUI EST FAIT. Une fois la langue posée (priorité 30 > 20), chaque étiquette dont la
 * langue diffère de celle de la fiche est remplacée par sa traduction dans la langue de
 * la fiche. Une étiquette SANS traduction est gardée telle quelle : on ne retire jamais
 * une étiquette, on la corrige ou on n'y touche pas. Aucune autre taxonomie, aucune
 * autre route.
 *
 * C'est une contre-épreuve APRÈS coup, au sens de CLAUDE.md : elle ne suppose pas de
 * savoir pourquoi la résolution par nom a choisi le mauvais terme — elle constate le
 * résultat et le remet d'aplomb.
 */

if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_etiquettes_dans_la_langue')) {
/**
 * Remet les étiquettes d'une fiche dans sa langue. Renvoie la liste des remplacements
 * effectués, array(ancien_id => nouvel_id), vide si rien n'a bougé.
 */
function cs_etiquettes_dans_la_langue($post_id, $lang) {
    if (!$post_id || !$lang) { return array(); }
    if (!function_exists('pll_get_term_language') || !function_exists('pll_get_term')) { return array(); }
    $ids = wp_get_object_terms($post_id, 'post_tag', array('fields' => 'ids'));
    if (!is_array($ids) || !$ids) { return array(); }

    $nouveaux = array();
    $changes  = array();
    foreach ($ids as $tid) {
        $tid = (int) $tid;
        $l = pll_get_term_language($tid);
        if ($l && $l !== $lang) {
            $trad = (int) pll_get_term($tid, $lang);
            if ($trad) {
                $changes[$tid] = $trad;
                $tid = $trad;
            }
        }
        if (!in_array($tid, $nouveaux, true)) { $nouveaux[] = $tid; }
    }
    if ($changes) {
        wp_set_object_terms($post_id, $nouveaux, 'post_tag', false);
    }
    return $changes;
}
}

add_filter('rest_request_after_callbacks', function ($response, $handler, $request) {
    if ($request->get_route() !== '/cs/v1/event') { return $response; }
    $data = ($response instanceof WP_REST_Response) ? $response->get_data() : null;
    $pid  = (is_array($data) && !empty($data['id'])) ? (int) $data['id'] : 0;
    if (!$pid || get_post_type($pid) !== 'tribe_events') { return $response; }
    // La langue que le snippet Polylang vient de poser — relue, pas supposée.
    $lang = function_exists('pll_get_post_language') ? pll_get_post_language($pid) : '';
    cs_etiquettes_dans_la_langue($pid, $lang);
    return $response;
}, 30, 3);
