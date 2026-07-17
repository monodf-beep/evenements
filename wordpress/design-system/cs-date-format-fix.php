<?php
/**
 * CS · Format date _EventStartDate/_EventEndDate (JetEngine)
 * Poussé en Code Snippets (id 43, scope front-end) via Novamira le 2026-07-17.
 *
 * Diagnostic : le réglage "date_format" du bloc jet-engine/dynamic-field n'est
 * jamais consommé par le code de rendu de JetEngine pour dynamic_field_source:"meta"
 * (vérifié en lisant le code source réel du plugin : ni
 * includes/components/listings/render/dynamic-field.php ni
 * includes/components/listings/data.php ne lisent ce réglage pour ce chemin).
 * L'enregistrement du champ comme type "date" dans la Meta Box JetEngine (fait
 * lors d'une session précédente) était donc sans effet — ce n'était pas la cause.
 *
 * Correctif : intercepter la valeur brute au niveau du filtre de données JetEngine
 * plutôt que d'attendre un réglage de bloc inopérant.
 */
add_filter('jet-engine/listing/data/get-post-meta', function ($value, $key, $object_id) {
    if (!in_array($key, ['_EventStartDate', '_EventEndDate'], true) || empty($value)) {
        return $value;
    }
    $ts = strtotime($value);
    if (!$ts) {
        return $value;
    }
    return date_i18n('d/m', $ts);
}, 10, 3);
