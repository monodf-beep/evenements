<?php
/**
 * CS · Filtre date rail Aujourd'hui — nouveau snippet DÉDIÉ, ne touche PAS au
 * snippet existant #44 "CS · Anti-doublon home" (même hook JetEngine, même
 * _element_id "jour", mais fichier/snippet séparé — consigne de la session :
 * un nouveau comportement = un nouveau snippet, jamais une modif d'un
 * snippet partagé avec d'autres agents).
 *
 * --- Diagnostic (2026-07-18) ---
 * Franck a signalé le 17/07 que le rail mobile "Événements d'aujourd'hui" de
 * la home "sera à revoir", sans détail. Investigation :
 * - `components.css` documente déjà le bug depuis le 2026-07-17 (lignes
 *   ~517-521) : "Filtre par date pas encore câblé... les 4 derniers
 *   événements, pas seulement ceux du jour".
 * - `homepage-mobile.gutenberg.html` confirme : le bloc est un
 *   `jet-engine/listing-grid` natif (`{"lisitng_id":"1696","posts_num":4,
 *   "custom_post_types":["tribe_events"],"_element_id":"jour"}`), PAS un
 *   gabarit PHP dédié — donc PAS une WP_Query de la query principale
 *   interceptable via `pre_get_posts` (qui ne s'applique qu'à la query
 *   principale de la page). JetEngine construit sa propre requête pour ce
 *   widget/bloc.
 * - Le snippet #44 (existant) prouve que le point d'accroche correct pour
 *   modifier les $args de CETTE requête est le filtre
 *   'jet-engine/listing/grid/posts-query-args', avec `$settings['_element_id']`
 *   pour cibler précisément le bon bloc (partagé entre les rendus mobile ET
 *   desktop de la home, qui utilisent le même _element_id "jour" — cf.
 *   commentaire ligne ~526 de components.css).
 * - Confirmé en live via curl que le HTML public expose bien
 *   `_element_id="jour"` deux fois (mobile + desktop) sur `/`.
 *
 * --- Correctif ---
 * Pour `_element_id === 'jour'` uniquement : ajoute une meta_query de
 * CHEVAUCHEMENT avec la journée en cours (pas seulement _EventStartDate dans
 * la journée — un événement commencé hier soir et qui se termine ce soir doit
 * apparaître) : _EventStartDate <= aujourd'hui 23:59:59 ET _EventEndDate >=
 * aujourd'hui 00:00:00. Même logique de chevauchement que le filtre "Ce
 * week-end" (liste-evenements-template.php, snippet #22).
 *
 * --- Effet de bord assumé sur l'offset anti-doublon (#44) ---
 * Le snippet #44 applique un offset fixe de +4 pour "jour" (pour éviter
 * d'afficher les mêmes premiers événements que "À la une"/"Ce week-end").
 * Une fois le pool réellement restreint aux seuls événements DU JOUR MÊME
 * (potentiellement 0 à quelques événements), un offset fixe de 4 risque de
 * sauter tous les résultats et afficher un rail vide même quand des
 * événements du jour existent. Le filtre de date rend cet offset inutile
 * pour cette section précise (la distinction avec les autres pools vient
 * maintenant de la date, plus besoin d'un décalage artificiel) — ce snippet
 * remet donc `offset` à 0 pour "jour" SEULEMENT, en s'exécutant en priorité
 * 20 (après le 10 du snippet #44) pour agir sur les $args déjà enrichis
 * (langue Polylang, filtre photo) sans les écraser. Aucun autre
 * _element_id n'est touché — le comportement du snippet #44 pour
 * "weekend"/"evidence"/"evidence-bottom"/"venir"/"venir-bottom" est
 * inchangé.
 */
add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    $eid = $settings['_element_id'] ?? '';
    if ($eid !== 'jour') {
        return $args;
    }

    $today_start = current_time('Y-m-d') . ' 00:00:00';
    $today_end   = current_time('Y-m-d') . ' 23:59:59';

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'relation' => 'AND',
        [
            'key'     => '_EventStartDate',
            'value'   => $today_end,
            'compare' => '<=',
            'type'    => 'DATETIME',
        ],
        [
            'key'     => '_EventEndDate',
            'value'   => $today_start,
            'compare' => '>=',
            'type'    => 'DATETIME',
        ],
    ];

    // Cf. note ci-dessus : l'offset anti-doublon (#44) devient contre-productif
    // une fois le pool réellement filtré par date pour cette section précise.
    $args['offset'] = 0;

    return $args;
}, 20, 3);
