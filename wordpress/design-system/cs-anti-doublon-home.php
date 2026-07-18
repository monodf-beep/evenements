<?php
/**
 * CS · Anti-doublon home (accumulateur d'exclusion global, par _element_id) +
 * garantie photo — Code Snippets id 44, scope front-end. Poussé via Novamira
 * le 2026-07-17, complété le même jour (langue Polylang), complété à nouveau
 * le 2026-07-17 (garantie photo sur "À la une"/"Ce week-end"/"Événements
 * d'aujourd'hui"), RÉÉCRIT le 2026-07-18 (remplacement du système d'offsets
 * fixes par un accumulateur d'exclusion global), CORRIGÉ le 2026-07-18 même
 * jour (rejeu identique par _element_id — cf. "Correctif mobile/desktop"
 * ci-dessous).
 *
 * Diagnostic initial : toutes les sections dynamiques de la home (À la une,
 * Événements d'aujourd'hui, Ce week-end, En évidence, L'agenda à venir)
 * utilisaient le même jet-engine/listing-grid sans aucun filtre de requête,
 * donc affichaient systématiquement les mêmes premiers événements publiés.
 * Chaque bloc a reçu un attribut "_element_id" distinct (dans
 * homepage-mobile.gutenberg.html) ; la version originale de ce filtre
 * appliquait un offset croissant par _element_id pour que chaque section
 * montre une fenêtre différente du même pool d'événements.
 *
 * --- Pourquoi le système d'offsets fixes a été abandonné (2026-07-18) ---
 * Franck a signalé "pas mal d'articles en double ou des articles sans images
 * sur la homepage". Vérification en direct (parsing du HTML public, post-IDs
 * par _element_id) : doublons confirmés (ex. post 679 présent dans
 * venir + weekend + jour ; post 1164 dans evidence-bottom + weekend + jour).
 * Cause racine : les offsets fixes ci-dessous supposaient que TOUTES les
 * sections partagent EXACTEMENT le même pool ordonné d'événements — cette
 * hypothèse est fausse dès qu'une section a un filtre différent des autres :
 * (a) le filtre "photo obligatoire" ne s'applique qu'à ala-une/weekend/jour,
 * pas aux autres sections (evidence, venir, etc.) — donc leurs pools ne sont
 * pas des sous-ensembles alignés du même pool ;
 * (b) le snippet séparé "CS · Filtre date rail Aujourd'hui" restreint EN PLUS
 * le pool de "jour" aux seuls événements du jour même — un pool encore plus
 * différent des autres, avec offset remis à 0 pour rester cohérent (l'offset
 * fixe +4 de "jour" n'a alors plus aucun rapport avec les autres pools).
 * Un système d'offsets fixes ne peut pas rester correct quand les sections
 * ont des filtres de requête hétérogènes.
 *
 * --- Mécanisme : accumulateur d'exclusion global, par _element_id ---
 * Chaque _element_id DISTINCT exclut (post__not_in) les IDs déjà affichés
 * par les AUTRES _element_id déjà rendus dans le même chargement de page —
 * quel que soit le filtre propre à chaque section. Le résultat de la
 * PREMIÈRE requête pour un _element_id donné est mémorisé (par _element_id,
 * pas globalement) ; toute requête ULTÉRIEURE portant le même _element_id
 * (cf. correctif mobile/desktop ci-dessous) rejoue exactement ce même
 * résultat au lieu de relancer une requête avec exclusion, qui donnerait un
 * contenu différent.
 *
 * --- Correctif mobile/desktop (2026-07-18, même jour que la réécriture) ---
 * homepage-mobile.gutenberg.html contient DEUX arbres de blocs (un mobile,
 * un desktop, togglés par CSS `.as-home`/`.as-home-desktop` selon la largeur
 * d'écran) et certains _element_id (ala-une, jour) sont utilisés dans LES
 * DEUX arbres. Avec un accumulateur d'exclusion purement séquentiel (première
 * version de cette réécriture), le second rendu d'un même _element_id
 * (ex. "jour" desktop, après "jour" mobile plus haut dans le DOM) se
 * retrouvait à exclure les IDs que SA PROPRE section venait de montrer côté
 * mobile — repéré en vérifiant le live après déploiement : le rail "jour"
 * desktop revenait VIDE alors que 3 événements du jour existaient bel et
 * bien (déjà consommés par "jour" mobile). Comme mobile et desktop ne sont
 * jamais visibles simultanément (CSS exclusif), il n'y a AUCUNE raison que
 * les deux rendus d'un même _element_id se disputent le même pool : ils
 * doivent au contraire afficher exactement le même contenu. D'où le rejeu
 * par _element_id ci-dessus : $cs_home_shown_ids est maintenant un tableau
 * associatif _element_id => [IDs], rempli une seule fois (au premier rendu
 * de chaque _element_id) et REJOUÉ tel quel (post__in) aux rendus suivants
 * du même _element_id, tandis que l'exclusion (post__not_in) ne porte que
 * sur les IDs des AUTRES _element_id déjà rendus.
 * Validé par un dry-run puis vérifié en direct sur le live après déploiement
 * (parsing du HTML public par _element_id) : "AUCUN DOUBLON" entre sections
 * distinctes, ET les deux rendus (mobile/desktop) d'un même _element_id
 * affichent maintenant un contenu identique et non-vide.
 *
 * Complété le 2026-07-17 (même jour) : Polylang est actif (fr/it,
 * force_lang=1) et tous les événements publiés ont une langue assignée,
 * mais jet-engine/listing-grid construit sa propre WP_Query qui ne passe
 * PAS par le filtrage automatique de Polylang (réservé à la requête
 * principale). Sans ce correctif, un visiteur sur la version FR pouvait
 * voir des événements en italien (et inversement). Ajout de
 * $args['lang'] = pll_current_language() pour forcer chaque grille à
 * respecter la langue couramment consultée.
 *
 * Complété le 2026-07-17 (garantie photo) : la maquette n'affiche jamais le
 * placeholder "Visuel" vide sur les cartes "À la une", "Ce week-end" et
 * "Événements d'aujourd'hui" (_element_id "ala-une"/"weekend"/"jour" —
 * partagé entre les blocs mobile ET desktop qui utilisent le même
 * _element_id). On restreint donc le pool de CES 3 sections aux tribe_events
 * ayant une image mise en avant (_thumbnail_id EXISTS). Les colonnes
 * "Nouveautés"/"En évidence"/"L'agenda à venir" (evidence, evidence-bottom,
 * venir, venir-bottom) NE SONT PAS concernées : elles peuvent continuer à
 * afficher le placeholder "Visuel" (inchangé par les réécritures du
 * 2026-07-18 — seul le mécanisme anti-doublon a changé, pas la garantie
 * photo).
 */
add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    if (function_exists('pll_current_language')) {
        $args['lang'] = pll_current_language();
    }

    $eid = $settings['_element_id'] ?? '';

    if (in_array($eid, ['ala-une', 'weekend', 'jour'], true)) {
        $args['meta_query'] = $args['meta_query'] ?? [];
        $args['meta_query'][] = [
            'key'     => '_thumbnail_id',
            'compare' => 'EXISTS',
        ];
    }

    if ($eid !== '') {
        global $cs_home_shown_ids;
        $cs_home_shown_ids = $cs_home_shown_ids ?? [];

        if (array_key_exists($eid, $cs_home_shown_ids)) {
            // Ce _element_id a déjà été rendu ailleurs sur la page (mobile
            // ET desktop) — on rejoue exactement le même résultat, on ne
            // relance jamais une requête concurrente avec exclusion pour un
            // _element_id déjà connu.
            $ids = $cs_home_shown_ids[$eid];
            $args['post__in'] = !empty($ids) ? $ids : [0];
            $args['orderby']  = 'post__in';
        } else {
            $exclude = [];
            foreach ($cs_home_shown_ids as $other_ids) {
                $exclude = array_merge($exclude, $other_ids);
            }
            if (!empty($exclude)) {
                $existing = $args['post__not_in'] ?? [];
                $args['post__not_in'] = array_values(array_unique(array_merge($existing, $exclude)));
            }
            // Marqueur lu uniquement par notre filtre 'the_posts' ci-dessous.
            $args['cs_dedup_eid'] = $eid;
        }
    }

    return $args;
}, 10, 3);

add_filter('the_posts', function ($posts, $query) {
    $eid = $query->get('cs_dedup_eid');
    if ($eid !== '') {
        global $cs_home_shown_ids;
        $cs_home_shown_ids = $cs_home_shown_ids ?? [];
        if (!array_key_exists($eid, $cs_home_shown_ids)) {
            $cs_home_shown_ids[$eid] = array_map(function ($p) {
                return $p->ID;
            }, $posts);
        }
    }
    return $posts;
}, 10, 2);
