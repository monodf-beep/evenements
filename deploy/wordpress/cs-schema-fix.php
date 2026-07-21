<?php
/*
Plugin Name: Agenda Sabauda — Assainissement du schema Event (JSON-LD)
Description: Nettoie les données structurées Event (Yoast + The Events Calendar) émises
  sur les fiches événement : retire les « description » polluées par le texte de l'encart
  publicitaire (« Publicité — Annoncer sur Agenda Sabauda → ») dans location (Place),
  organizer et performer. Une donnée structurée propre est essentielle pour l'expérience
  « Événements » de Google (levier trafic n°1). N'ajoute rien de faux : en cas de pollution,
  on SUPPRIME la description (mieux vaut pas de description qu'une pub dans le schema).
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION :
   A) Code Snippets : coller SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-schema-fix.php.
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Vrai si un texte ressemble au CTA publicitaire de l'encart (à ne jamais laisser
 * apparaître dans le schema comme « description » de lieu/organisateur).
 */
function cs_schema_is_ad_text($text) {
    if (!is_string($text) || $text === '') { return false; }
    return (stripos($text, 'Annoncer sur') !== false)
        || (stripos($text, 'Publicité') !== false && stripos($text, 'Agenda Sabauda') !== false);
}

/**
 * Nettoie récursivement un nœud du @graph : retire toute « description » polluée.
 */
function cs_schema_clean_node($node) {
    if (!is_array($node)) { return $node; }
    if (isset($node['description']) && cs_schema_is_ad_text($node['description'])) {
        unset($node['description']);
    }
    // Sous-objets susceptibles de porter la pollution.
    foreach (array('location', 'organizer', 'performer', 'address') as $key) {
        if (isset($node[$key])) {
            if (isset($node[$key][0])) {                 // liste d'objets
                foreach ($node[$key] as $i => $sub) {
                    $node[$key][$i] = cs_schema_clean_node($sub);
                }
            } else {                                     // objet unique
                $node[$key] = cs_schema_clean_node($node[$key]);
            }
        }
    }
    return $node;
}

// Yoast : filtre du graphe complet (The Events Calendar y injecte l'Event).
add_filter('wpseo_schema_graph', function ($graph) {
    if (!is_array($graph)) { return $graph; }
    foreach ($graph as $i => $node) {
        $graph[$i] = cs_schema_clean_node($node);
    }
    return $graph;
}, 20);

// Filet de sécurité si The Events Calendar émet SON propre JSON-LD (hors Yoast).
add_filter('tribe_json_ld_event_object', function ($data) {
    if (is_object($data)) {
        $arr = json_decode(wp_json_encode($data), true);
        $arr = cs_schema_clean_node($arr);
        return json_decode(wp_json_encode($arr));       // reconvertit en objet
    }
    return $data;
}, 20);
