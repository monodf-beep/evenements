/**
 * CS . Home - allocateur centralise (dedup fiable + langue + territoire) -
 * Code Snippets id 44. Version 2026-07-23b (Franck) :
 *  1) Contrainte "photo obligatoire" retiree (deja fait en v2026-07-23a).
 *  2) Lignes toujours completes pour les sections en grille (deja fait).
 *  3) NOUVEAU : exclusivite max mais flexibilite restreinte. Chaque section
 *     essaie d'abord des evenements JAMAIS utilises ailleurs (comme avant).
 *     Si une section manque de contenu (petit territoire + langue filtres),
 *     elle peut PUISER dans les evenements deja alloues a une section
 *     precedente -- mais seulement (a) un evenement ne peut etre reutilise
 *     qu'UNE SEULE fois (jamais dans une 3e section), et (b) au total sur
 *     TOUTE la home, au maximum 2 evenements distincts sont ainsi repetes.
 *     Au-dela de ce budget, une section qui manque de contenu reste courte
 *     (No data was found reste un signal fiable de vraie penurie, jamais
 *     masque artificiellement).
 *
 * Principe general (inchange) : au PREMIER rendu de grille home, on calcule UNE
 * fois un PLAN complet (cs_home_build_allocation) qui attribue a chaque section
 * une tranche d'evenements, dans la langue courante et, si un territoire est
 * actif (cookie/GET, via cs_territoire_actif), scopee a ce territoire. Chaque
 * grille (identifiee par _element_id) recoit ensuite sa tranche via post__in.
 * Deterministe, independant de l'ordre de rendu et du mecanisme interne de
 * JetEngine.
 *
 * Sections (priorite de reservation) : weekend (ce week-end, Fri-Dim) ->
 * jour (= "7 prochains jours", evenements DEMARRANT dans les 7 jours) ->
 * ala-une -> nouveautes (plus recemment ajoutes) -> evidence / evidence-bottom
 * -> venir / venir-bottom (a venir, par date de debut). Un evenement n'apparait
 * dans une 2e section qu'en dernier recours, jamais dans une 3e.
 *
 * Compatibilite : snippet 54 (priorite territoire par langue, posts_clauses)
 * continue de reordonner ; cs-territoire-persistant / cs-home-territoire-filtre
 * ajoutent le meme tax_query territoire -> coherent avec des post__in deja
 * scopes. Le snippet 45 (filtre "aujourd'hui" sur 'jour') est DESACTIVE : la
 * section 'jour' est desormais "7 prochains jours", pas "aujourd'hui".
 */
if (!function_exists('cs_home_row_size')) {
function cs_home_row_size($eid) {
    // Seul 'jour' a une regle metier explicite de multiple (4 ou 8, jamais 5/6/7).
    // 'ala-une' et 'weekend' n'en ont PAS : forcer un multiple pouvait arrondir a 0 un
    // stock reel de 1-3 evenements (bug trouve le 2026-07-25, ex. IT Savoia : 2 evenements
    // jamais utilises ailleurs jetes a tort). Le plafond desktop/mobile est deja gere par le
    // CSS (nth-child, snippet 77), pas besoin de forcer un multiple ici.
    $sizes = ['weekend' => 3, 'ala-une' => 1, 'jour' => 4]; // 2026-08-17 : 'ala-une' passe a 1, conformement au commentaire ci-dessus qui dit qu'elle n a PAS de regle de multiple. Avec le seuil as_deplacement>=8, l arrondi a 3 vidait entierement la section Savoie alors qu il restait des fiches valables. // 'jour' restaure 2026-07-30 : regle documentee "4 ou 8 uniquement" retrouvee absente du tableau alors que le commentaire de ce fichier l'annonce toujours -- ecart code/doc corrige.
    return $sizes[$eid] ?? 1;
}
}

if (!function_exists('cs_home_category_pick')) {
function cs_home_category_pick($cat_slug, $count, $lang, $terr_tax, $now, &$claimed) {
    // 2026-07-31 (Franck) : get_term_by() est filtre par Polylang selon la langue
    // COURANTE de la requete -- sur une page IT, chercher un slug FR (cat_slug est
    // toujours FR) echoue silencieusement (retourne false), et la fonction sortait
    // ici avant meme d'atteindre la traduction plus bas. get_terms() avec 'lang' => ''
    // contourne ce filtre pour cette recherche initiale du terme canonique.
    $terms_lookup = get_terms(['taxonomy' => 'tribe_events_cat', 'slug' => $cat_slug, 'hide_empty' => false, 'lang' => '']);
    $term = (!is_wp_error($terms_lookup) && !empty($terms_lookup)) ? $terms_lookup[0] : null;
    if (!$term) { return []; }
    // 2026-07-31 (Franck) : $cat_slug est toujours le slug FR -- sur la home IT, le
    // terme IT a un slug DIFFERENT (ex. jeune-public-famille -> per-bambini-famiglia),
    // donc get_term_by() ne trouvait jamais le bon terme et les 4 sections categorie
    // etaient vides sur TOUTE la home IT. On traduit via Polylang vers la langue
    // courante avant de construire la requete.
    if ($lang && function_exists('pll_get_term')) {
        $translated_id = pll_get_term($term->term_id, $lang);
        if ($translated_id) { $term = get_term($translated_id, 'tribe_events_cat'); }
    }
    if (!$term || is_wp_error($term)) { return []; }
    $tax = [['taxonomy' => 'tribe_events_cat', 'field' => 'term_id', 'terms' => $term->term_id]];
    if ($terr_tax) { $tax[] = $terr_tax; $tax['relation'] = 'AND'; }
    $q = new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'fields' => 'ids',
        'lang' => $lang, 'no_found_rows' => true,
        'tax_query' => $tax,
        'meta_query' => [
            'relation' => 'AND',
            ['key' => '_EventEndDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'],
            ['relation' => 'OR', ['key' => 'as_home_override', 'compare' => 'NOT EXISTS'], ['key' => 'as_home_override', 'value' => 'excluded', 'compare' => '!=']],
        ],
        'post__not_in' => $claimed ?: [0],
        'posts_per_page' => 60,
    ]);
    $pool = $q->posts;
    if (empty($pool)) { return []; }
    update_postmeta_cache($pool);
    $scored = [];
    foreach ($pool as $pid) {
        $sc = get_post_meta($pid, 'as_score', true);
        $sd = get_post_meta($pid, '_EventStartDate', true);
        $scored[] = ['id' => $pid, 'score' => ($sc === '' ? -1 : (float) $sc), 'start' => ($sd ?: '9999-12-31')];
    }
    usort($scored, function ($a, $b) {
        if ($a['score'] !== $b['score']) { return $b['score'] <=> $a['score']; }
        return $a['start'] <=> $b['start'];
    });
    $ids = array_slice(array_column($scored, 'id'), 0, $count);
    $claimed = array_values(array_unique(array_merge($claimed, $ids)));
    return $ids;
}
}

if (!function_exists('cs_home_build_allocation')) {
function cs_home_build_allocation() {
    // 2026-08-04 : le cache est INDEXE PAR LANGUE. Avant, un simple `static $plan`
    // sans cle rendait le plan de la PREMIERE langue calculee a toutes les suivantes.
    // Inoffensif en production, ou chaque requete est monolingue — mais tout code qui
    // construit les deux plans dans un meme processus (audit, diagnostic, cron bilingue)
    // recevait le mauvais. Constate en direct ce jour-la : une mesure comparant FR et IT
    // dans la meme requete a lu des ids francais dans le plan italien, et a fait conclure
    // a tort que la section « Les 7 prochains jours » proposait des fiches francaises a la
    // home italienne. Verification refaite en requete monolingue : le plan italien ne
    // contient que des fiches italiennes, et les quatre sont rendues. Le defaut n etait
    // pas dans l allocateur, il etait dans le cache — et il a produit un faux diagnostic.
    static $plans = [];

    $lang  = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    if (isset($plans[$lang])) { return $plans[$lang]; }
    $now   = current_time('Y-m-d H:i:s');
    $today = current_time('Y-m-d');
    $dow   = (int) current_time('N'); // 1=lun .. 7=dim
    $fri   = date('Y-m-d', strtotime($today . ' ' . ($dow >= 5 ? ('-' . ($dow - 5) . ' days') : ('+' . (5 - $dow) . ' days'))));
    $sun   = date('Y-m-d', strtotime($fri . ' +2 days'));
    $wkStart = $fri . ' 00:00:00';
    $wkEnd   = $sun . ' 23:59:59';
    $todayStart = $today . ' 00:00:00';
    $d7    = date('Y-m-d', strtotime($today . ' +7 days')) . ' 23:59:59';

    $terr_tax = null;
    if (function_exists('cs_territoire_actif') && ($canon = cs_territoire_actif()) && function_exists('cs_terr_canon_data')) {
        $data = cs_terr_canon_data();
        if (isset($data[$canon])) {
            $tid = ($lang === 'it') ? $data[$canon]['it_term'] : $data[$canon]['fr_term'];
            $terr_tax = ['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $tid];
        }
    }

    $claimed = [];
    $reused  = [];
    // 2026-09-06 (Franck), REVU LE MEME JOUR : le premier correctif (budget a 0) etait
    // TROP large -- il a vide « A la une » sur les petits territoires (Savoie :
    // « Aucun evenement pour le moment ») au lieu de viser le vrai bug. Regle
    // reformulee par Franck : JAMAIS 2x le meme article DANS LA MEME SECTION, mais
    // JUSQU'A 2 FOIS SUR TOUTE LA HOME reste accepte (c'est exactement le budget du
    // 23/07, remis tel quel). Le vrai bug (widgets jumeaux d'une meme section, plus
    // bas dans ce fichier) est distinct et reste corrige.
    $reuse_budget = 2;

    $take = function ($count, $mode, $eid, $max_reuse = null) use (&$claimed, &$reused, &$reuse_budget, $lang, $now, $wkStart, $wkEnd, $todayStart, $d7, $terr_tax) {
        $meta = [
            'relation' => 'AND',
            'up'    => ['key' => '_EventEndDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'],
            'start' => ['key' => '_EventStartDate', 'compare' => 'EXISTS'],
        ];
        if ($mode === 'weekend') {
            $meta['wk1'] = ['key' => '_EventStartDate', 'value' => $wkEnd, 'compare' => '<=', 'type' => 'DATETIME'];
            $meta['wk2'] = ['key' => '_EventEndDate', 'value' => $wkStart, 'compare' => '>=', 'type' => 'DATETIME'];
        } elseif ($mode === 'next7') {
            // 2026-08-03 : la section annonce ce qui DEMARRE dans les 7 jours,
            // comme l entete de ce fichier le documente depuis l origine. Le
            // filtre ne bornait que la fin de fenetre, donc tout evenement en
            // cours la traversait : le rendu ouvrait sur 442 et 344 jours.
            // Le classement ongoing du 2026-08-02 les mettait bien en dernier
            // dans le plan, mais The Events Calendar reordonne les grilles par
            // date de debut et annulait ce classement -- d ou une correction
            // sur la SELECTION, seule robuste, et non sur l ordre.
            // Conséquence assumee : la section peut devenir plus courte. C est
            // le principe pose en tete de fichier, une penurie reelle ne se
            // masque pas.
            $meta['n0'] = ['key' => '_EventStartDate', 'value' => $todayStart, 'compare' => '>=', 'type' => 'DATETIME'];
            $meta['n1'] = ['key' => '_EventStartDate', 'value' => $d7, 'compare' => '<=', 'type' => 'DATETIME'];
        } elseif ($mode === 'upcoming' || $mode === 'nouveautes' || $mode === 'vedette') {
            $meta['u1'] = ['key' => '_EventStartDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'];
        }
        // 2026-07-31 (Franck) : exclusion etendue a TOUTES les sections de la home (pas
        // seulement les 3 "vedette") -- un evenement "Exclu de la home" disparait
        // desormais partout, pas seulement de A la une \/ En evidence \/ En evidence bas.
        $meta['excl'] = ['relation' => 'OR', ['key' => 'as_home_override', 'compare' => 'NOT EXISTS'], ['key' => 'as_home_override', 'value' => 'excluded', 'compare' => '!=']];
        if ($mode === 'vedette') {
            // 2026-07-31 (Franck) : as_home_score seul ne suffisait pas -- une fiche jamais
            // redigee a as_home_score="" (~0 au tri) donc classee derniere, mais
            // l'allocateur se repliait quand meme dessus faute de mieux. On EXCLUT (pas
            // seulement declasse) du pool "vedette" tout ce qui n'est pas explicitement
            // as_enrich_status='enriched'. Absent/vide = non eligible (comportement sur par
            // defaut pour les fiches anciennes, pas encore repassees par le pipeline). La
            // section peut devenir plus courte que sa cible, voire vide -- voulu.
            $meta['enrich'] = ['key' => 'as_enrich_status', 'value' => 'enriched', 'compare' => '='];
            // 2026-08-17 (Franck) : la une ne montre pas ce qui ne vaut pas le
            // deplacement. Seuil sur as_deplacement, en FILTRE et non en note :
            // une note basse remontait quand meme en dernier recours (cas du
            // cours de pilates, note 6, premier sur la home Savoie). La section
            // peut devenir vide, c'est voulu.
            $meta['une'] = ['key' => 'as_deplacement', 'value' => 8, 'compare' => '>=', 'type' => 'NUMERIC'];
        }
        if ($mode === 'une_now') {
            // 2026-08-18 : PAS de borne sur la date de DEBUT pour ce mode. La clause
            // 'up' plus haut (fin >= maintenant) suffit comme filet de securite si la
            // meta n'etait pas a jour. as_une_now decide seule de l'eligibilite, et
            // retient volontairement les evenements EN COURS dont la fin approche
            // (derniere chance). Une borne de debut serait un second portillon qui
            // contredit le premier : elle ecartait 6311 et 7209, notes 11.
            $meta['unenow'] = ['key' => 'as_une_now', 'value' => 0, 'compare' => '>', 'type' => 'NUMERIC'];
        }
        $base = [
            'post_type' => 'tribe_events', 'post_status' => 'publish',
            'fields' => 'ids', 'lang' => $lang, 'meta_query' => $meta,
            'orderby' => ['start' => 'ASC'], 'no_found_rows' => true,
        ];
        if ($terr_tax) { $base['tax_query'] = [$terr_tax]; }
        if ($mode === 'nouveautes') { $base['orderby'] = 'date'; $base['order'] = 'DESC'; }

        if ($mode === 'vedette') {
            $args = $base;
            $args['posts_per_page'] = 60;
            $args['post__not_in'] = $claimed ?: [0];
            unset($args['orderby'], $args['order']);
            $q = new WP_Query($args);
            $pool = $q->posts;
            if (!empty($pool)) { update_postmeta_cache($pool); }
            $scored = [];
            foreach ($pool as $pid) {
                $ov = get_post_meta($pid, 'as_home_override', true);
                $or = get_post_meta($pid, 'as_home_order', true);
                $sc = function_exists('cs_une_note') ? cs_une_note($pid) : get_post_meta($pid, 'as_home_score', true);
                $sd = get_post_meta($pid, '_EventStartDate', true);
                $scored[] = ['id' => $pid, 'featured' => ($ov === 'featured' ? 0 : 1), 'order' => ($or === '' ? PHP_INT_MAX : (int) $or), 'score' => ($sc === '' ? -1 : (float) $sc), 'start' => ($sd ?: '9999-12-31')];
            }
            usort($scored, function ($a, $b) {
                if ($a['featured'] !== $b['featured']) { return $a['featured'] <=> $b['featured']; }
                if ($a['featured'] === 0 && $a['order'] !== $b['order']) { return $a['order'] <=> $b['order']; }
                if ($a['score'] !== $b['score']) { return $b['score'] <=> $a['score']; }
                return $a['start'] <=> $b['start'];
            });
            $ids = array_slice(array_column($scored, 'id'), 0, $count);
        } elseif ($mode === 'une_now') {
            // 2026-08-18 (Franck) : la une trie sur as_une_now, ecrite par le pipeline.
            // Le vide n'est pas une egalite mais une EXCLUSION, faite en amont par la
            // clause meta 'unenow'. Traite en egalite, il ferait retomber le tri sur la
            // date, defaut deja constate avec as_home_score fige a 8.1.
            // Mode distinct de 'vedette' : evidence et evidence-bottom sont inchanges.
            $args = $base;
            $args['posts_per_page'] = 60;
            $args['post__not_in'] = $claimed ?: [0];
            unset($args['orderby'], $args['order']);
            $q = new WP_Query($args);
            $pool = $q->posts;
            if (!empty($pool)) { update_postmeta_cache($pool); }
            $scored = [];
            foreach ($pool as $pid) {
                $ov = get_post_meta($pid, 'as_home_override', true);
                $un = get_post_meta($pid, 'as_une_now', true);
                $sd = get_post_meta($pid, '_EventStartDate', true);
                $scored[] = ['id' => $pid, 'featured' => ($ov === 'featured' ? 0 : 1), 'une' => (int) $un, 'start' => ($sd ?: '9999-12-31')];
            }
            usort($scored, function ($a, $b) {
                if ($a['featured'] !== $b['featured']) { return $a['featured'] <=> $b['featured']; }
                if ($a['une'] !== $b['une']) { return $b['une'] <=> $a['une']; }
                return $a['start'] <=> $b['start'];
            });
            $ids = array_slice(array_column($scored, 'id'), 0, $count);
        } elseif ($mode === 'weekend' || $mode === 'next7') {
            // 2026-08-02 (Franck) : PRIORITE A CE QUI COMMENCE dans la fenetre.
            // Avant, le tri par date de debut croissante remontait les evenements deja
            // en cours (expos demarrees des mois plus tot) : les 8 vignettes de
            // "Les 7 prochains jours" etaient a 100% des evenements longue duree, de 91
            // a 213 jours -- la section ne changeait donc JAMAIS d une semaine sur
            // l autre, alors que c est precisement sa raison d etre. Il y a pourtant de
            // la matiere : 18 evenements demarrent dans les 7 jours cote FR.
            // Les evenements en cours restent eligibles, mais en second rideau : ils ne
            // remplissent que ce que les ponctuels ne remplissent pas.
            $args = $base;
            $args['posts_per_page'] = 60;
            $args['post__not_in'] = $claimed ?: [0];
            unset($args['orderby'], $args['order']);
            $q = new WP_Query($args);
            $pool = $q->posts;
            if (!empty($pool)) { update_postmeta_cache($pool); }
            $seuil = ($mode === 'weekend') ? substr($wkStart, 0, 10) : substr($todayStart, 0, 10);
            $ranked = [];
            foreach ($pool as $pid) {
                $sd = substr((string) get_post_meta($pid, '_EventStartDate', true), 0, 10);
                $ranked[] = ['id' => $pid, 'ongoing' => ($sd !== '' && $sd < $seuil) ? 1 : 0, 'start' => $sd];
            }
            usort($ranked, function ($a, $b) {
                if ($a['ongoing'] !== $b['ongoing']) { return $a['ongoing'] <=> $b['ongoing']; }
                return strcmp($a['start'], $b['start']);
            });
            $ids = array_slice(array_column($ranked, 'id'), 0, $count);
        } else {
            $args = $base;
            $args['posts_per_page'] = $count;
            $args['post__not_in'] = $claimed ?: [0];
            $q = new WP_Query($args);
            $ids = $q->posts;
        }

        $shortfall = $count - count($ids);
        if ($shortfall > 0 && (($max_reuse !== null) ? (int)$max_reuse : $reuse_budget) > 0 && !empty($claimed)) {
            $reuse_pool = array_values(array_diff($claimed, $reused, $ids));
            if (!empty($reuse_pool)) {
                $args2 = $base;
                $args2['posts_per_page'] = -1;
                $args2['post__in'] = $reuse_pool;
                $q2 = new WP_Query($args2);
                $candidates = $q2->posts;
                $take_n = min($shortfall, (($max_reuse !== null) ? (int)$max_reuse : $reuse_budget), count($candidates));
                if ($take_n > 0) {
                    $extra = array_slice($candidates, 0, $take_n);
                    $ids = array_merge($ids, $extra);
                    $reused = array_merge($reused, $extra);
                    if ($max_reuse === null) { $reuse_budget -= count($extra); }
                }
            }
        }

        $row = cs_home_row_size($eid);
        if ($row > 1) {
            // Toujours un multiple de la ligne -- y compris VERS 0 si on n'a
            // pas de quoi remplir ne serait-ce qu'une seule ligne complete
            // (ex. jour=3 sur un petit territoire : on prefere 0/"No data"
            // qu'un affichage partiel qui violerait la regle "4 ou 8 uniquement").
            $keep = (int) (floor(count($ids) / $row) * $row);
            $ids = array_slice($ids, 0, $keep);
        }

        $claimed = array_values(array_unique(array_merge($claimed, $ids)));
        return $ids;
    };

    $plan = [
        'weekend'         => $take(6, 'weekend', 'weekend'),
        'jour'            => $take(8, 'next7', 'jour'),
        'ala-une'         => $take(3, 'une_now', 'ala-une', 0),
        'nouveautes'      => $take(3, 'nouveautes', 'nouveautes'),
        'evidence'        => $take(3, 'vedette', 'evidence'),
        'evidence-bottom' => $take(3, 'vedette', 'evidence-bottom'),
        'venir'           => $take(4, 'upcoming', 'venir', 4),
        'venir-bottom'    => $take(4, 'upcoming', 'venir-bottom', 4),
        'deplacement'     => cs_home_deplacement_pick($lang, $now),
        'cat-concerts'     => cs_home_category_pick('concerts-musique', 4, $lang, $terr_tax, $now, $claimed),
        'cat-expositions'  => cs_home_category_pick('expositions-patrimoine', 4, $lang, $terr_tax, $now, $claimed),
        'cat-gastronomie'  => cs_home_category_pick('gastronomie-sagre', 4, $lang, $terr_tax, $now, $claimed),
    ];
    $plans[$lang] = $plan;
    return $plan;
}
}

if (!function_exists('cs_home_deplacement_pick')) {
function cs_home_deplacement_pick($lang, $now) {
    static $cache = [];
    if (isset($cache[$lang])) { return $cache[$lang]; }
    $terr_ids = ($lang === 'it') ? [318, 327] : [6, 8]; // it: savoia+contea-di-nizza ; fr: piemont+vallee-d-aoste

    $base = [
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'fields' => 'ids',
        'lang' => $lang, 'no_found_rows' => true,
        'tax_query' => [['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $terr_ids]],
        'meta_query' => [
            'relation' => 'AND',
            ['key' => '_EventEndDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'],
            ['relation' => 'OR', ['key' => 'as_home_override', 'compare' => 'NOT EXISTS'], ['key' => 'as_home_override', 'value' => 'excluded', 'compare' => '!=']],
        ],
        // ON RAMENE TOUT (-1), et le tri se fait en PHP juste apres. Mesure du 2026-08-03 :
        // The Events Calendar SUPPRIME le ORDER BY de cette requete et regroupe par
        // occurrence_id. Le SQL reellement execute ne contenait AUCUN ORDER BY, donc les
        // resultats revenaient dans l ordre des ID : la section affichait les deux plus
        // petits ID parmi les candidats, pas les deux meilleures notes (2186 note 8 devant
        // 2190 note 9). C est l avertissement du cahier au paragraphe 8 : ne pas corriger
        // un ORDRE que TEC retire, corriger la SELECTION.
        // Et demander LIMIT 2 ici ne marcherait pas davantage : on trierait les deux plus
        // petits ID au lieu des deux meilleures notes. Le vivier notE tient en quelques
        // dizaines de fiches (47 le 2026-08-03), le cout est negligeable.
        'posts_per_page' => -1,
    ];

    // Classe des ids par note DECROISSANTE. Egalite departagee par la date de debut la
    // plus proche, puis par l id : le resultat doit etre STABLE d un rendu a l autre,
    // sinon la home change d ordre sans que rien n ait bouge.
    $classer = function (array $ids, $cle) {
        $lignes = [];
        foreach ($ids as $id) {
            $lignes[] = [
                'id'    => (int) $id,
                'note'  => (float) get_post_meta($id, $cle, true),
                'debut' => (string) get_post_meta($id, '_EventStartDate', true),
            ];
        }
        usort($lignes, function ($x, $y) {
            if ($x['note'] != $y['note'])   { return ($x['note'] < $y['note']) ? 1 : -1; }
            if ($x['debut'] !== $y['debut']) { return strcmp($x['debut'], $y['debut']); }
            return $x['id'] - $y['id'];
        });
        $out = [];
        foreach ($lignes as $l) { $out[] = $l['id']; }
        return $out;
    };

    // PASSE 1 - les fiches MESUREES, classees sur as_deplacement_now (0-12).
    $a = $base;
    $a['meta_query'][] = ['key' => 'as_deplacement_now', 'value' => '', 'compare' => '!='];
    $q   = new WP_Query($a);
    $ids = array_slice($classer($q->posts, 'as_deplacement_now'), 0, 2);

    // PASSE 2 - COMPLEMENT quand la MESURE manque, pas quand les evenements manquent.
    // Meme traitement : TEC retire aussi l ORDER BY de cette requete-la.
    if (count($ids) < 2) {
        $b = $base;
        $b['post__not_in'] = $ids;
        $q2    = new WP_Query($b);
        $reste = $classer($q2->posts, 'as_score');
        $ids   = array_merge($ids, array_slice($reste, 0, 2 - count($ids)));
    }

    $cache[$lang] = $ids;
    return $cache[$lang];
}
}

add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    if (function_exists('pll_current_language')) {
        $args['lang'] = pll_current_language();
    }
    $eid  = $settings['_element_id'] ?? '';
    if ($eid === '') { return $args; }

    $plan = cs_home_build_allocation();
    if (array_key_exists($eid, $plan)) {
        // 2026-09-06 (Franck) : « je ne veux plus autoriser 2x le meme article » --
        // constate en direct sur /explore/savoie/ : « A la une » et « Jour » sont chacune
        // rendues par DEUX widgets JetEngine distincts (plein format + compact) partageant
        // le MEME _element_id -- l'allocateur (plus haut) dedoublonne ENTRE sections, pas
        // entre deux widgets de la MEME section. Registre partage entre TOUS les appels de
        // ce filtre sur une page : un id deja rendu (n'importe ou) ne se represente plus.
        // Registre PAR SECTION ($eid), pas global : deux widgets de la MEME section
        // (plein format + compact) ne montrent jamais le meme article, mais un article
        // deja montre dans UNE section reste eligible dans une AUTRE (c'est le budget
        // de repli ci-dessus qui plafonne ce total-la, a 2).
        // ANNULE LE SOIR MEME (06/09) : ce registre vidait « A la une » sur DESKTOP pour tous
        // les territoires. Mesure sur la page rendue : les deux widgets d'une section ne sont
        // pas concurrents mais ALTERNATIFS -- le bloc .as-home (listing 1696, mobile) est
        // masque a partir de 900px, le bloc .as-home-desktop (1695) en dessous. Rendu en
        // premier, le mobile consommait les ids et le desktop recevait [0] -> « Aucun
        // evenement pour le moment ». Le plan de l'allocateur garantit deja qu'un id n'est
        // qu'une fois PAR section : chaque widget de la section recoit le plan entier.
        $args['post__in'] = !empty($plan[$eid]) ? $plan[$eid] : [0];
        $args['orderby']  = 'post__in';
        unset($args['post__not_in']);

        // 2026-08-03 : sur les sections DATEES, l ordre du plan fait foi.
        // Constate en direct : le plan de 'jour' sortait bien 6334, 1677, 6342,
        // 3765, 1680, 1686 puis les deux evenements deja en cours EN DERNIER,
        // conformement au classement ongoing du 2026-08-02. A l affichage, la
        // priorite territoire du snippet 54 (posts_clauses) reordonnait le tout
        // et remontait ces deux longues durees, 442 et 344 jours, aux deux
        // premieres places d une section intitulee "Les 7 prochains jours".
        // On neutralise donc la priorite territoire pour ces seules sections :
        // ailleurs (a la une, en evidence, categories) elle reste en place, la
        // demande du 2026-07-18 n est pas annulee.
        if (in_array($eid, array('weekend', 'jour'), true)) {
            unset($args['cs_territoire_priority_lang']);
        }
    }
    return $args;
}, 10, 3);