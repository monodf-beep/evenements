<?php
/**
 * CS · Priorité territoire selon la langue — nouveau snippet DÉDIÉ (ne touche
 * pas au snippet existant #44 "CS · Anti-doublon home", même mécanisme de
 * hook mais fichier séparé — consigne de la session : un nouveau
 * comportement = un nouveau snippet).
 *
 * Demande de Franck (2026-07-18) : quand on bascule FR/IT (sélecteur de
 * langue Polylang, site-header-footer.php), le contenu affiché doit aussi
 * "prioriser les localisations" — pas juste filtrer par langue (déjà fait
 * par #44 via $args['lang']), mais faire remonter en premier les
 * événements des territoires les plus pertinents pour cette langue :
 * - FR → Savoie/Haute-Savoie et Nice/Comté de Nice en premier.
 * - IT → Vallée d'Aoste (Valle d'Aosta) et Piémont (Piemonte) en premier.
 *
 * Contexte découvert en vérifiant la taxonomie territoire en direct
 * (novamira/execute-php, get_terms) : chaque territoire existe en DEUX
 * termes distincts, un par langue Polylang (traductions liées, pas le même
 * term_id) :
 *   Savoie/Haute-Savoie   FR id 3   ↔ Savoia/Alta Savoia  IT id 318
 *   Piémont               FR id 6   ↔ Piemonte            IT id 321
 *   Vallée d'Aoste        FR id 8   ↔ Valle d'Aosta        IT id 324
 *   Comté de Nice / Nice  FR id 10 / 11  ↔ Nizza/Alpi Marittime IT id 327
 * (+ des sous-termes ville : Annecy, Aoste, Chambéry, Turin — non concernés
 * ici, la priorisation porte sur les 4 territoires eux-mêmes.)
 *
 * Comme un événement en langue FR est TOUJOURS étiqueté avec le term_id FR
 * du territoire (quel que soit le territoire réel), la priorité se fait sur
 * les term_id FR de Savoie/Nice quand pll_current_language()==='fr', et sur
 * les term_id IT de Vallée d'Aoste/Piémont quand ==='it' — pas besoin de
 * gérer les paires FR/IT ensemble, chaque langue n'utilise que "ses" ids.
 *
 * Portée : uniquement les grilles JetEngine Listing Grid de la home (hook
 * 'jet-engine/listing/grid/posts-query-args', même hook que #44) — les
 * pages "Ce week-end"/"Tout l'agenda"/"Aujourd'hui"/"Cette semaine"/Hubs
 * utilisent des WP_Query PHP directes (liste-evenements-template.php,
 * taxonomy-archive-template.php, etc.) déjà triées par date, pas par
 * pertinence home ; la priorisation par territoire n'a pas été demandée
 * pour ces pages-là et n'est donc pas appliquée ici pour rester dans le
 * périmètre exact de la demande. À étendre si besoin.
 *
 * Mécanique : on marque la query avec un query var custom
 * 'cs_territoire_priority_lang' (lu uniquement par notre propre filtre
 * posts_clauses ci-dessous, jamais par WordPress/JetEngine), puis on
 * modifie l'ORDER BY via un LEFT JOIN sur wp_term_relationships : les
 * posts liés à un des term_id prioritaires remontent en tête (DESC sur un
 * booléen JOIN matché/pas matché), le tri existant (date, offset anti-
 * doublon de #44) reste le critère secondaire, inchangé.
 */
add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    if (function_exists('pll_current_language')) {
        $args['cs_territoire_priority_lang'] = pll_current_language();
    }
    return $args;
}, 9, 3);

add_filter('posts_clauses', function ($clauses, $query) {
    $lang = $query->get('cs_territoire_priority_lang');
    if (!$lang) {
        return $clauses;
    }

    $priority_term_ids = [
        'fr' => [3, 10, 11],   // Savoie/Haute-Savoie, Comté de Nice, Nice
        'it' => [321, 324],    // Piemonte, Valle d'Aosta
    ];
    $ids = $priority_term_ids[$lang] ?? [];
    if (empty($ids)) {
        return $clauses;
    }

    global $wpdb;
    $ids_sql = implode(',', array_map('intval', $ids));
    $clauses['join'] .= " LEFT JOIN {$wpdb->term_relationships} AS cs_terr_prio ON (
        {$wpdb->posts}.ID = cs_terr_prio.object_id
        AND cs_terr_prio.term_taxonomy_id IN (
            SELECT term_taxonomy_id FROM {$wpdb->term_taxonomy}
            WHERE taxonomy = 'territoire' AND term_id IN ($ids_sql)
        )
    )";
    $clauses['orderby'] = "(cs_terr_prio.object_id IS NOT NULL) DESC, " . $clauses['orderby'];
    $clauses['groupby'] = "{$wpdb->posts}.ID";

    return $clauses;
}, 10, 2);
