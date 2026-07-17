<?php
/**
 * CS · Format date _EventStartDate/_EventEndDate + nom de lieu virtuel
 * _EventVenueName (JetEngine) — Code Snippets id 43, scope front-end.
 * Poussé en Code Snippets via Novamira le 2026-07-17, complété le même jour
 * (format A "À la une"/"Ce week-end" desktop : plage de dates + ligne lieu).
 *
 * Diagnostic initial : le réglage "date_format" du bloc jet-engine/dynamic-field
 * n'est jamais consommé par le code de rendu de JetEngine pour
 * dynamic_field_source:"meta" (vérifié en lisant le code source réel du
 * plugin : ni includes/components/listings/render/dynamic-field.php ni
 * includes/components/listings/data.php ne lisent ce réglage pour ce
 * chemin). L'enregistrement du champ comme type "date" dans la Meta Box
 * JetEngine (fait lors d'une session précédente) était donc sans effet — ce
 * n'était pas la cause.
 *
 * Correctif : intercepter la valeur brute au niveau du filtre de données
 * JetEngine plutôt que d'attendre un réglage de bloc inopérant.
 *
 * Deux responsabilités dans ce même filtre :
 *
 * 1) _EventStartDate / _EventEndDate → libellé de date formaté :
 *    - Événement sur un seul jour (même date calendaire, heure ignorée,
 *      pour _EventStartDate et _EventEndDate — souvent stockées 00:00:00 à
 *      23:59:59 même pour un jour unique) : "d/m" (comportement d'origine,
 *      inchangé).
 *    - Plusieurs jours, PAS encore commencé (aujourd'hui < date de début) :
 *      "d/m–d/m" (tiret demi-cadratin, pas un tiret simple).
 *    - Plusieurs jours, EN COURS aujourd'hui (début <= aujourd'hui <= fin) :
 *      "Jusqu'au d/m" (date de FIN).
 *    - Plusieurs jours, déjà terminé (résiduel, ne devrait pas apparaître
 *      dans les listings qui filtrent sur des événements à venir) : on
 *      retombe sur la plage complète "d/m–d/m" par cohérence.
 *    _EventEndDate demandé isolément (si un jour un listing l'affiche seul,
 *      cas non utilisé aujourd'hui) reste formaté en simple "d/m", comme
 *      avant — il n'a pas sa propre logique de plage.
 *
 * 2) _EventVenueName (clé VIRTUELLE, n'existe PAS en base) → nom du lieu.
 *    JetEngine ne peut pas nativement suivre une relation meta→post_title
 *    dans un bloc dynamic-field standard sans configuration avancée.
 *    JetEngine appelle get_post_meta() normalement (qui renvoie vide, la clé
 *    n'existe pas), mais ce filtre intercepte AVANT le rendu et retourne le
 *    post_title du tribe_venue pointé par _EventVenueID. Utilisé par le
 *    nouveau Listing Item "carte-a-la-une-full-blocks" (format A, desktop
 *    "À la une"/"Ce week-end") en binder un dynamic-field dessus.
 */
add_filter('jet-engine/listing/data/get-post-meta', function ($value, $key, $object_id) {
    // --- 2) Nom de lieu virtuel ---------------------------------------
    if ($key === '_EventVenueName') {
        $venue_id = get_post_meta($object_id, '_EventVenueID', true);
        if ($venue_id) {
            $venue = get_post((int) $venue_id);
            if ($venue) {
                return $venue->post_title;
            }
        }
        return '';
    }

    // --- 1) Dates --------------------------------------------------------
    if (!in_array($key, ['_EventStartDate', '_EventEndDate'], true) || empty($value)) {
        return $value;
    }

    $ts = strtotime($value);
    if (!$ts) {
        return $value;
    }

    if ($key === '_EventEndDate') {
        // Pas de logique de plage pour une demande isolée sur la date de fin :
        // simple "d/m", comme avant.
        return date_i18n('d/m', $ts);
    }

    // $key === '_EventStartDate'
    $end_raw = get_post_meta($object_id, '_EventEndDate', true);
    $end_ts  = $end_raw ? strtotime($end_raw) : false;

    $start_day = date_i18n('Y-m-d', $ts);
    $end_day   = $end_ts ? date_i18n('Y-m-d', $end_ts) : $start_day;

    if (!$end_ts || $end_day === $start_day) {
        // Événement sur un seul jour.
        return date_i18n('d/m', $ts);
    }

    $today = current_time('Y-m-d');

    if ($today < $start_day) {
        // Plage à venir, pas encore commencée.
        return date_i18n('d/m', $ts) . '–' . date_i18n('d/m', $end_ts);
    }

    if ($today <= $end_day) {
        // En cours aujourd'hui (start_day <= today <= end_day).
        return "Jusqu'au " . date_i18n('d/m', $end_ts);
    }

    // Résiduel : plage déjà terminée.
    return date_i18n('d/m', $ts) . '–' . date_i18n('d/m', $end_ts);
}, 10, 3);
