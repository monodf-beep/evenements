<?php
/**
 * Plugin Name: CS - Statut d evenement dans les donnees structurees
 * Description: Un report ou une annulation ne doit JAMAIS donner lieu a une seconde fiche : Google demande de conserver la meme URL et de changer eventStatus, en preservant l ancienne date dans previousStartDate (Search Central, mars 2020). Ce plugin lit deux metas et corrige le noeud Event du graphe Yoast.
 */
if (!defined('ABSPATH')) exit;

function cs_event_statuts() {
    return array(
        'reporte'   => 'https://schema.org/EventRescheduled',
        'ajourne'   => 'https://schema.org/EventPostponed',
        'annule'    => 'https://schema.org/EventCancelled',
        'en_ligne'  => 'https://schema.org/EventMovedOnline',
    );
}

add_filter('wpseo_schema_graph', 'cs_event_statut_graphe', 20, 2);
function cs_event_statut_graphe($graphe, $contexte) {
    if (!is_array($graphe) || !is_singular('tribe_events')) { return $graphe; }
    $id = get_queried_object_id();
    $statut = get_post_meta($id, 'as_event_statut', true);
    $prec   = get_post_meta($id, 'as_event_date_precedente', true);
    $table  = cs_event_statuts();
    if (!$statut || !isset($table[$statut])) { return $graphe; }
    foreach ($graphe as $i => $noeud) {
        $type = isset($noeud['@type']) ? $noeud['@type'] : '';
        $type = is_array($type) ? implode('/', $type) : $type;
        if (stripos($type, 'event') === false) { continue; }
        $graphe[$i]['eventStatus'] = $table[$statut];
        if ($prec) { $graphe[$i]['previousStartDate'] = $prec; }
    }
    return $graphe;
}