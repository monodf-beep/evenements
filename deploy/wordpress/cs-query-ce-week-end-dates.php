<?php
/*
Plugin Name: Agenda Sabauda — Query Builder : langue + fenêtre de dates "Ce week-end"
Description: Deux filtres sur 'jet-engine/query-builder/types/posts-query/args' :

  1) FORCAGE DE LANGUE (générique, s'applique à TOUTE requête JetEngine Query
     Builder de type "posts") : lang = pll_current_language(), avec garde `if
     ($lang)` pour ne rien casser hors contexte de langue (admin, CLI, REST).
     Pourquoi (test explicite à l'étape 5/7, 2026-07-19) : sans ce forçage, une
     requête JetEngine dynamique mélange les langues quelle que soit la langue
     courante — Crocoblock/JetEngine est certifié WPML, pas Polylang. Règle à
     appliquer à TOUS les futurs formats de query "Sélection" (décision actée) :
     c'est pourquoi ce filtre est générique et pas scopé à un seul ID de requête.

  2) FENÊTRE DE DATES "CE WEEK-END" (spécifique à la requête Query Builder ID 3,
     "evenements-ce-week-end") : bornes samedi 00:00 -> dimanche 23:59 de la
     SEMAINE ISO courante sur _EventStartDate, sans date en dur. Calculé par
     arithmétique sur le numéro ISO du jour (format 'N', 1=lundi..7=dimanche)
     dans le fuseau du site (wp_timezone() via current_datetime()), PAS via
     strtotime('this saturday'/'this sunday') — bug corrigé le 2026-07-19 :
     strtotime('this X') tourne au fuseau serveur (UTC) et se comporte comme
     "next X" pour la plupart des jours, ce qui avait inversé les bornes un
     dimanche soir. Vérifié par simulation sur les 7 jours de la semaine ISO.

Requêtes connues à ce jour (état au 2026-07-20, à tenir à jour si de nouvelles
requêtes "Sélection" sont créées) :
  - ID 3 "evenements-ce-week-end"            : événements TEC du week-end courant, langue forcée.
  - ID 4 "selections-home"                   : posts "selection" avec sel_home=1, triés
    sel_ordre ASC, langue forcée (carrousel home).
  - ID 5 "evenements-ca-vaut-le-deplacement" : tax_query territoire IN (vallee-d-aoste, piemont).
  - ID 6 "eventi-vale-il-viaggio"            : tax_query territoire IN (savoie,
    comte-de-nice) — miroir inversé de l'ID 5, côté IT.
  - ID 7 "evenements-sagre"                  : tax_query cat=gastronomie-sagre + territoire=piemont,
    fenêtre du MOIS courant (filtre 3 ci-dessous).
  - ID 8 "eventi-sagra"                      : idem ID 7, termes IT (gastronomia-sagre), fenêtre
    du mois courant.
  - ID 9 "evenements-nouveautes" / ID 10 "eventi-novita" : 8 derniers événements publiés
    (orderby=date DESC), pas de fenêtre de date — pas de filtre supplémentaire nécessaire.

Rollback : supprimer ce fichier (wp-content/mu-plugins/) ; les requêtes Query
Builder retombent alors sans filtre de langue ni de date.
*/
if (!defined('ABSPATH')) { exit; }

// 1) Forcage de langue, generique a toutes les requetes Query Builder "posts".
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args) {
    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    if ($lang) {
        $args['lang'] = $lang;
    }
    return $args;
}, 9, 1);

// 2) Fenetre de dates "ce week-end", scopee a la requete ID 3 uniquement.
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 3 !== (int) $query->id) {
        return $args;
    }

    $now      = current_datetime();
    $iso_dow  = (int) $now->format('N');
    $offset   = 6 - $iso_dow;
    $sign     = $offset >= 0 ? '+' : '';
    $saturday = $now->modify("{$sign}{$offset} days")->setTime(0, 0, 0);
    $sunday   = $saturday->modify('+1 day')->setTime(23, 59, 59);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => [$saturday->format('Y-m-d H:i:s'), $sunday->format('Y-m-d H:i:s')],
        'compare' => 'BETWEEN',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);

// 3) Fenetre de dates du MOIS courant, scopee aux requetes ID 7 et 8 (Sagre FR/IT).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [7, 8], true)) {
        return $args;
    }

    $now   = current_datetime();
    $start = $now->modify('first day of this month')->setTime(0, 0, 0);
    $end   = $now->modify('last day of this month')->setTime(23, 59, 59);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => [$start->format('Y-m-d H:i:s'), $end->format('Y-m-d H:i:s')],
        'compare' => 'BETWEEN',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 4) Filtrage par VILLE (jointure evenement -> lieu -> _VenueCity), scope a des requetes
// dediees par ville. WP_Query ne sait pas filtrer par la meta d'un CPT lie (tribe_venue) en
// un seul passage : on resout d'abord les ID de lieux dont _VenueCity correspond, puis on
// filtre les evenements par _EventVenueID IN (...).
$cs_ville_par_query = [
    11 => ['Annecy'],
    12 => ['Torino', 'Turin'],
    13 => ['Cuneo'],
];
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) use ($cs_ville_par_query) {
    if (empty($query->id) || !isset($cs_ville_par_query[(int) $query->id])) {
        return $args;
    }

    $villes    = $cs_ville_par_query[(int) $query->id];
    $venue_ids = get_posts([
        'post_type'      => 'tribe_venue',
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'fields'         => 'ids',
        'meta_query'     => [[
            'key'     => '_VenueCity',
            'value'   => $villes,
            'compare' => 'IN',
        ]],
    ]);

    if (empty($venue_ids)) {
        $venue_ids = [0];
    }

    $args['meta_query']   = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventVenueID',
        'value'   => $venue_ids,
        'compare' => 'IN',
    ];

    return $args;
}, 10, 2);


// 5) Fenetre de dates GLISSANTE 7 jours (aujourd'hui 00:00 -> +7j 23:59), scopee a
// la requete ID 14 ("evenements-a-venir-7j", section 'jour' home -> renommee 'a venir').
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 14 !== (int) $query->id) {
        return $args;
    }

    $now   = current_datetime();
    $start = $now->setTime(0, 0, 0);
    $end   = $now->modify('+7 days')->setTime(23, 59, 59);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => [$start->format('Y-m-d H:i:s'), $end->format('Y-m-d H:i:s')],
        'compare' => 'BETWEEN',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 6) Date >= aujourd'hui 00:00, scopee a la requete ID 15 ("evenement-vedette",
// section 'a la une' / 'en vedette', 1 evenement trie par as_score DESC).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 15 !== (int) $query->id) {
        return $args;
    }

    // 2026-07-20 (Franck) : 6 evenements en vedette (grille desktop 3x2 pleine) ;
    // la version mobile n'en affiche que 4 via CSS (.as-home #ala-une nth-child(n+5)).
    $args['as_score_true_limit'] = 6;
    $args['posts_per_page'] = 30;

    $start = current_datetime()->setTime(0, 0, 0);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => $start->format('Y-m-d H:i:s'),
        'compare' => '>=',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 7) Date >= aujourd'hui 00:00, scopee a la requete ID 16 ("evenements-evidence",
// section 'En evidence' : as_score >= 5 deja filtre a la creation de la requete).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 16 !== (int) $query->id) {
        return $args;
    }

    $args['as_score_true_limit'] = (int) $args['posts_per_page'];
    $args['posts_per_page'] = 30;

    $start = current_datetime()->setTime(0, 0, 0);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => $start->format('Y-m-d H:i:s'),
        'compare' => '>=',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 8) Contournement TEC Custom Tables V1 : The Events Calendar reecrit la requete SQL
// des tribe_events (jointure sur wp_tec_occurrences) et remplace SYSTEMATIQUEMENT tout
// orderby demande par son propre tri start_date ASC -- confirme par inspection directe
// des clauses SQL (posts_clauses), meme avec WP_Query natif, meme hors JetEngine.
// Impossible a corriger en amont (le rewrite ne passe pas par le filtre posts_clauses
// normal sur son 2e passage). Fix : re-trier les resultats DEJA recuperes par as_score
// DESC (contournement TEC), scope aux requetes post_type=tribe_events + meta_key=as_score
// (evenement-vedette ID 15, evenements-evidence ID 16, evenements-par-categorie a venir).
add_filter('the_posts', function ($posts, $query) {
    if ($query->get('meta_key') !== 'as_score' || $query->get('post_type') !== 'tribe_events') {
        return $posts;
    }
    usort($posts, function ($a, $b) {
        $score_cmp = (int) get_post_meta($b->ID, 'as_score', true) <=> (int) get_post_meta($a->ID, 'as_score', true);
        if ($score_cmp !== 0) {
            return $score_cmp;
        }
        // tri secondaire (egalite de score) : date de debut la plus proche d'abord.
        $date_a = strtotime(get_post_meta($a->ID, '_EventStartDate', true));
        $date_b = strtotime(get_post_meta($b->ID, '_EventStartDate', true));
        return $date_a <=> $date_b;
    });
    $true_limit = $query->get('as_score_true_limit');
    if ($true_limit) {
        $posts = array_slice($posts, 0, $true_limit);
    }
    return $posts;
}, 10, 2);


// 9) Date >= aujourd'hui 00:00, scopee a la requete ID 17 ("evenements-nouveautes-home",
// section home 'Nouveautes' -- distincte de la requete ID 9 'evenements-nouveautes' deja
// existante pour la Selection 'Les nouveautes'). Tri par fraicheur post_date DESC deja
// natif -- pas de contournement TEC necessaire ici, orderby=date fonctionne correctement
// (seul meta_value_num etait casse par le rewrite Custom Tables V1).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 17 !== (int) $query->id) {
        return $args;
    }

    $start = current_datetime()->setTime(0, 0, 0);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => $start->format('Y-m-d H:i:s'),
        'compare' => '>=',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 10) Date >= aujourd'hui 00:00, scopee aux requetes ID 18-21 ("evenements-cat-*",
// section home 'Par categorie'). Tri principal as_score DESC deja gere par le
// contournement TEC generique (filtre the_posts scope meta_key=as_score, cf. plus haut) ;
// tri secondaire _EventStartDate ASC ajoute dans ce meme filtre pour les egalites de score.
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [18, 19, 20, 21], true)) {
        return $args;
    }

    $args['as_score_true_limit'] = (int) $args['posts_per_page'];
    $args['posts_per_page'] = 50;

    $start = current_datetime()->setTime(0, 0, 0);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => $start->format('Y-m-d H:i:s'),
        'compare' => '>=',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);


// 11) REGLE IMAGE OBLIGATOIRE SUR LA HOME -- RETIREE le 2026-07-23 (demande Franck) :
// desormais que cs_fallback_visual() (couleur + monogramme + categorie) est presentable,
// exclure les evenements sans photo reduisait artificiellement le nombre d'evenements
// affiches par territoire sur la home. Prochaine etape actee avec Franck : traiter la
// couverture photo a la source (garantir une photo par evenement), pas ici.
// Rollback : reintroduire le filtre ci-dessous si besoin (voir historique git).


// 12) Date >= aujourd'hui 00:00, scopee aux requetes ID 22 et 23 ("autre versant",
// section home 'Ca vaut le deplacement'). Meme contournement TEC (pool elargi, re-tri
// as_score DESC dans le filtre the_posts deja en place) que les requetes 15/16/18-21.
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [22, 23], true)) {
        return $args;
    }

    $args['as_score_true_limit'] = (int) $args['posts_per_page'];
    $args['posts_per_page'] = 50;

    $start = current_datetime()->setTime(0, 0, 0);

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => '_EventStartDate',
        'value'   => $start->format('Y-m-d H:i:s'),
        'compare' => '>=',
        'type'    => 'DATETIME',
    ];

    return $args;
}, 10, 2);
