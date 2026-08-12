<?php
/*
Plugin Name: Agenda Sabauda — Endpoint de publication TEC (cs/v1/event)
Description: Expose une route REST maison « /wp-json/cs/v1/event » qui crée ou met à
  jour un ÉVÉNEMENT The Events Calendar (post_type tribe_events) à partir d'un JSON
  propre envoyé par le backoffice (scripts/publisher.py). Fait tout le travail TEC
  côté serveur : dates via tribe_create_event(), lieu (Venue), catégorie
  (tribe_events_cat), taxonomie maison « territoire », méta du contrat « as_* »,
  méta SEO Rank Math, image à la une (téléversée depuis l'URL), et AUTEUR selon le
  score (Cultura Sabauda ≥ 7 / Agenda Sabauda < 7). TOUJOURS en status=draft.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION (au choix) :
   A) Code Snippets : coller tout le code SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-publish.php.
  Prérequis : The Events Calendar actif ; authentification via cs-rest-auth.php
  (en-tête X-CS-Auth) OU Application Password classique.

  ROUTAGE AUTEUR (optionnel) : crée deux comptes « Cultura Sabauda » et
  « Agenda Sabauda » (rôle Auteur), puis renseigne leurs IDs :
     update_option('cs_author_id', 12);   // Cultura Sabauda
     update_option('as_author_id', 13);   // Agenda Sabauda
  À défaut, l'auteur reste le compte technique de l'API (rien ne casse).
*/

if (!defined('ABSPATH')) { exit; }

// UN FICHIER SUR LE DISQUE NE PROUVE RIEN SUR CE QUE WORDPRESS EXÉCUTE — c'est la règle 1
// appliquée au code plutôt qu'aux fiches. Le 2026-08-12, un correctif a été « déployé »
// sans jamais partir : push-wordpress.sh avait un fichier par défaut et personne ne
// pouvait le savoir depuis le VPS. D'où cette route, publique et en lecture seule, qui
// répond ce que la version EN LIGNE dit d'elle-même :
//     curl -s https://agendasabauda.eu/wp-json/cs/v1/version
// À incrémenter (la date suffit) quand ce fichier change de comportement.
define('CS_PUBLISH_VERSION', '2026-08-12 — fiche lieu retrouvée par titre ET ville');

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/version', array(
        'methods'             => 'GET',
        'callback'            => function () {
            return array('cs_publish' => CS_PUBLISH_VERSION);
        },
        'permission_callback' => '__return_true',
    ));
});

/**
 * Retrouve une fiche lieu (tribe_venue) par son TITRE EXACT + une condition sur sa ville.
 *
 * WordPress n'offre pas de recherche « titre + méta » toute faite : get_page_by_title()
 * ignore les métas, et WP_Query['title'] ne comparait pas le titre exact avant WP 5.7.
 * D'où ce petit intermédiaire, écrit une fois plutôt que recopié deux.
 */
function cs_trouver_venue($titre, $meta_query) {
    $q = new WP_Query(array(
        'post_type'              => 'tribe_venue',
        'post_status'            => 'any',
        'posts_per_page'         => 1,
        'title'                  => $titre,
        'meta_query'             => $meta_query,
        'no_found_rows'          => true,
        'ignore_sticky_posts'    => true,
        'update_post_term_cache' => false,
    ));
    return !empty($q->posts) ? $q->posts[0] : null;
}

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/event', array(
        'methods'             => 'POST',
        'callback'            => 'cs_publish_event',
        // cs-rest-auth.php authentifie l'utilisateur en amont (X-CS-Auth) ; ici on
        // vérifie seulement la capacité. Seuls les comptes pouvant éditer passent.
        'permission_callback' => function () {
            return current_user_can('edit_posts');
        },
    ));
});

/**
 * Résout un terme par slug PUIS par nom dans une taxonomie. Ne crée RIEN
 * (catégories et territoires sont pré-amorcés). Renvoie l'ID ou 0.
 */
function cs_resolve_term($value, $taxonomy) {
    $value = trim((string) $value);
    if ($value === '') { return 0; }
    $t = get_term_by('slug', sanitize_title($value), $taxonomy);
    if (!$t) { $t = get_term_by('name', $value, $taxonomy); }
    return $t ? (int) $t->term_id : 0;
}

/**
 * Callback principal : crée/met à jour l'événement TEC. Renvoie {id,url,updated}.
 */
function cs_publish_event(WP_REST_Request $req) {
    if (!function_exists('tribe_create_event')) {
        return new WP_Error('tec_absent', 'The Events Calendar inactif.', array('status' => 500));
    }

    $b = $req->get_json_params();
    if (!is_array($b)) {
        return new WP_Error('bad_json', 'Corps JSON invalide.', array('status' => 400));
    }

    $title = trim((string) ($b['title'] ?? ''));
    if ($title === '') {
        return new WP_Error('no_title', 'Titre manquant.', array('status' => 400));
    }

    // --- Arguments TEC (dates gérées proprement par tribe_create_event) --------
    // Statut : AUTO-PUBLICATION (décision Franck 2026-07-20). Le backoffice a déjà sa
    // porte de qualité (évaluation + complétude) → on met EN LIGNE directement au lieu
    // de laisser des dizaines de brouillons invisibles. Surchargeable par le payload
    // ('status' = 'draft'|'pending'|'publish') si on veut repasser en relecture manuelle.
    $pub_status = (isset($b['status']) && in_array($b['status'], array('draft', 'pending', 'publish'), true))
        ? $b['status'] : 'publish';
    $args = array(
        'post_title'   => $title,
        'post_content' => (string) ($b['content'] ?? ''),
        'post_excerpt' => (string) ($b['excerpt'] ?? ''),
        'post_status'  => $pub_status,
    );
    // Slug explicite (paires FR/IT) : la fiche traduite reprend le slug de l'originale —
    // Polylang autorise un slug identique entre langues (le préfixe /fr//it/ suffit à les
    // distinguer), et une URL commune permet de retrouver la paire d'un coup d'œil.
    // Seulement à la CRÉATION : on ne modifie jamais le slug d'une fiche déjà publiée.
    if (!empty($b['slug']) && empty($b['wp_post_id'])) {
        $args['post_name'] = sanitize_title((string) $b['slug']);
    }
    // Dates : NORMALISER en 'Y-m-d H:i:s'. tribe_create_event retombe silencieusement
    // sur AUJOURD'HUI si on lui passe une date « seule » (ex. « 2025-07-22 ») ou un
    // format qu'il ne reconnaît pas. On force donc un datetime complet.
    $start_ts = !empty($b['start_date']) ? strtotime((string) $b['start_date']) : false;
    if ($start_ts) {
        $end_ts = !empty($b['end_date']) ? strtotime((string) $b['end_date']) : $start_ts;
        if (!$end_ts || $end_ts < $start_ts) { $end_ts = $start_ts; }
        // Heure de DÉBUT réelle (« HH:MM », extraite déterministe côté Python) : sans
        // ça, le Schema.org Event affichait 00:00-23:59 même quand l'heure exacte (ex.
        // « 21h30 ») était visible dans l'article — divergence donnée structurée / page
        // visible, signalée par l'audit SEO du 2026-07-29. Pas d'heure connue → repli
        // JOURNÉE ENTIÈRE (comportement historique, inchangé).
        $start_time = (!empty($b['start_time']) && preg_match('/^([01]\d|2[0-3]):[0-5]\d$/', (string) $b['start_time']))
            ? (string) $b['start_time'] : '';
        if ($start_time !== '') {
            $args['EventStartDate'] = date('Y-m-d', $start_ts) . ' ' . $start_time . ':00';
            // Pas d'heure de fin fiable non plus (on ne l'extrait pas) : même heure que
            // le début plutôt que d'inventer une durée — TEC affiche alors un point de
            // départ précis sans revendiquer une fin qu'on ne connaît pas.
            $args['EventEndDate'] = date('Y-m-d', $end_ts) . ' ' . $start_time . ':00';
            $args['EventAllDay']  = 'no';
        } else {
            $args['EventStartDate'] = date('Y-m-d', $start_ts) . ' 00:00:00';
            $args['EventEndDate']   = date('Y-m-d', $end_ts)   . ' 23:59:59';
            $args['EventAllDay']    = 'yes';
        }
    }
    // Site officiel de l'événement (champ natif TEC « EventURL »).
    if (!empty($b['website'])) { $args['EventURL'] = esc_url_raw((string) $b['website']); }
    // Prix natif TEC.
    if (isset($b['cost']) && $b['cost'] !== '') { $args['EventCost'] = sanitize_text_field((string) $b['cost']); }
    // Afficher la carte (une clé Google Maps est configurée dans TEC).
    $args['EventShowMap']     = true;
    $args['EventShowMapLink'] = true;

    // --- Auteur selon le score (routage éditorial) ----------------------------
    $score   = isset($b['score']) ? (float) $b['score'] : null;
    $cs_auth = (int) get_option('cs_author_id', 0);
    $as_auth = (int) get_option('as_author_id', 0);
    if ($score !== null) {
        $wanted = ($score >= 7) ? $cs_auth : $as_auth;
        if ($wanted > 0) { $args['post_author'] = $wanted; }
    }

    // --- Lieu (Venue) : réutilise s'il existe, sinon crée ----------------------
    $venue_id = 0;
    $venue_city_fixed = '';
    $venue = $b['venue'] ?? null;
    if (is_string($venue) && trim($venue) !== '') { $venue = array('Venue' => trim($venue)); }
    if (is_array($venue) && !empty($venue['Venue'])) {
        // ON CHERCHE PAR TITRE **ET PAR VILLE**. Chercher par le seul titre fusionnait
        // toutes les « Salle des Fêtes » de la région sur une même fiche lieu, avec une
        // seule ville : l'une des communes affichait celle de l'autre. Constaté le
        // 2026-08-12 sur deux fiches EN LIGNE — « Salle des Fêtes » à Margencel (926) et
        // à Draillant (925). Chaque village a la sienne ; ce sont deux lieux, pas un.
        //
        // Repli sur le titre seul quand nous n'avons PAS de ville : sans ce repli on
        // créerait une fiche lieu de plus à chaque publication sans ville, ce qui
        // remplacerait une fusion abusive par une prolifération — l'inverse, pas mieux.
        $existing = null;
        $ville_cherchee = isset($venue['City']) ? trim((string) $venue['City']) : '';
        if ($ville_cherchee !== '') {
            // 1) MÊME NOM, MÊME VILLE — c'est le même lieu, sans discussion.
            $existing = cs_trouver_venue($venue['Venue'], array(array(
                'key' => '_VenueCity', 'value' => $ville_cherchee, 'compare' => '=',
            )));
            // 2) sinon MÊME NOM, VILLE ABSENTE — les fiches lieu créées avant ce
            //    correctif n'ont souvent pas de ville. On les ADOPTE et le bloc ci-dessous
            //    les remplit, plutôt que d'en créer un double à côté. Sans cette étape, le
            //    premier `publisher_as --update` après déploiement aurait dupliqué chaque
            //    lieu du site : on aurait remplacé une fusion abusive par une
            //    prolifération, ce qui n'est pas un progrès.
            if (!$existing) {
                $existing = cs_trouver_venue($venue['Venue'], array(
                    'relation' => 'OR',
                    array('key' => '_VenueCity', 'value' => '', 'compare' => '='),
                    array('key' => '_VenueCity', 'compare' => 'NOT EXISTS'),
                ));
            }
            // 3) et RIEN D'AUTRE. Un lieu du même nom dans une AUTRE ville est un autre
            //    lieu : on en crée un nouveau. C'est tout l'objet du correctif — sans ce
            //    refus de se rabattre sur le titre seul, la salle des fêtes de Draillant
            //    continuerait de pointer sur celle de Margencel.
        } else {
            // Pas de ville de notre côté : on ne peut que retomber sur le titre. Créer une
            // fiche lieu de plus à chaque publication sans ville serait pire que la fusion.
            $existing = get_page_by_title($venue['Venue'], OBJECT, 'tribe_venue');
        }
        if ($existing) {
            $venue_id = (int) $existing->ID;
            // UNE FICHE LIEU CRÉÉE FAUSSE LE RESTAIT POUR TOUJOURS. On réutilisait le
            // post existant sans jamais regarder sa ville : chaque nouvel événement au
            // même endroit héritait de l'erreur, et rien dans la chaîne ne pouvait la
            // défaire. C'est un état terminal sans rouvreur (règle 3), et il a produit un
            // cas réel — fiche lieu 208, `_VenueCity = Aosta` pour le Forte di Bard, qui
            // est à Bard, cinquante kilomètres plus bas ; trois événements l'affichaient.
            //
            // DEUX CAS SEULEMENT, et la distinction est tout le sujet :
            //   • la ville du lieu est VIDE → on la remplit, on n'écrase rien ;
            //   • elle est renseignée et DIFFÈRE → on ne touche que si l'appelant nous
            //     dit tenir un fait qui fait autorité (`CityAuthoritative`, posé par
            //     publisher_as quand la ville vient du registre : note de savoir ou
            //     arbitrage consigné). Sans cette condition, deux événements en désaccord
            //     se réécriraient l'un l'autre à chaque publication — le dernier poussé
            //     gagnerait, ce qui n'est pas une règle, c'est un tirage au sort.
            $city = isset($venue['City']) ? trim((string) $venue['City']) : '';
            if ($city !== '') {
                $actuelle = trim((string) get_post_meta($venue_id, '_VenueCity', true));
                $autorite = !empty($venue['CityAuthoritative']);
                if ($actuelle === '' || ($autorite && strcasecmp($actuelle, $city) !== 0)) {
                    update_post_meta($venue_id, '_VenueCity', sanitize_text_field($city));
                    // Rendu dans la réponse : sans ça la correction serait muette, et on
                    // la découvrirait des semaines plus tard (règle 6).
                    $venue_city_fixed = ($actuelle === '' ? '(vide)' : $actuelle) . ' → ' . $city;
                }
            }
        } elseif (function_exists('tribe_create_venue')) {
            $venue_id = (int) tribe_create_venue(array(
                'Venue'   => $venue['Venue'],
                'Address' => $venue['Address'] ?? '',
                'City'    => $venue['City']    ?? '',
                'Country' => $venue['Country'] ?? '',
                'Zip'     => $venue['Zip']     ?? '',
            ));
        }
        if ($venue_id > 0) { $args['EventVenueID'] = $venue_id; }
    }

    // --- Organisateur (Organizer) : réutilise s'il existe, sinon crée ----------
    $org_id = 0;
    $org = isset($b['organizer']) ? trim((string) $b['organizer']) : '';
    if ($org !== '') {
        $existing_org = get_page_by_title($org, OBJECT, 'tribe_organizer');
        if ($existing_org) {
            $org_id = (int) $existing_org->ID;
        } elseif (function_exists('tribe_create_organizer')) {
            $org_id = (int) tribe_create_organizer(array('Organizer' => $org));
        }
        if ($org_id > 0) { $args['EventOrganizerID'] = $org_id; }
    }

    // --- Création ou mise à jour ----------------------------------------------
    $existing_id = isset($b['wp_post_id']) ? (int) $b['wp_post_id'] : 0;
    $updated = false;
    if ($existing_id > 0 && get_post_type($existing_id) === 'tribe_events') {
        // NE PAS dépublier au re-push : on retire post_status pour préserver le statut
        // existant (publié ou brouillon). Le forçage draft ne vaut QUE pour la création.
        unset($args['post_status']);
        tribe_update_event($existing_id, $args);
        $post_id = $existing_id;
        $updated = true;
    } elseif (!empty($b['force_create'])) {
        // FORCE_CREATE : on saute le dédoublonnage et on crée toujours une nouvelle
        // fiche. Indispensable pour les TRADUCTIONS : leur titre (nom propre : festival,
        // artiste) est souvent IDENTIQUE à l'original ; sans ça, le dédoublonnage ci-
        // dessous retrouverait l'original (même titre + date) et l'ÉCRASERAIT au lieu de
        // créer la version dans l'autre langue.
        $post_id = (int) tribe_create_event($args);
    } else {
        // IDEMPOTENCE : avant de créer, chercher un événement identique déjà en base
        // (même titre + même date de début). Évite les DOUBLONS quand wp_post_id est
        // absent ou périmé (ex. site reconstruit → ancien id mort). Sans ce repli,
        // un re-push recréait un second post au lieu de retrouver le premier.
        $dupe_args = array(
            'post_type'        => 'tribe_events',
            'post_status'      => array('publish', 'pending', 'draft', 'future', 'private'),
            'title'            => $title,
            'posts_per_page'   => 1,
            'fields'           => 'ids',
            'no_found_rows'    => true,
            'suppress_filters' => false,
        );
        if (!empty($args['EventStartDate'])) {
            $dupe_args['meta_query'] = array(array(
                'key'   => '_EventStartDate',
                'value' => $args['EventStartDate'],
            ));
        }
        $dupe = get_posts($dupe_args);
        if (!empty($dupe)) {
            // Retrouvé : on met à jour au lieu de dupliquer. On préserve le statut
            // existant (comme la branche update ci-dessus).
            unset($args['post_status']);
            $post_id = (int) $dupe[0];
            tribe_update_event($post_id, $args);
            $updated = true;
        } else {
            $post_id = (int) tribe_create_event($args);
        }
    }
    if (!$post_id) {
        return new WP_Error('tec_fail', 'Création TEC échouée.', array('status' => 500));
    }

    // Lien du lieu FORCÉ (tribe_update_event ne relie pas toujours le Venue sur la
    // mise à jour) : on écrit directement la méta que TEC lit pour lier le lieu.
    if ($venue_id > 0) { update_post_meta($post_id, '_EventVenueID', $venue_id); }
    if ($org_id > 0)   { update_post_meta($post_id, '_EventOrganizerID', $org_id); }

    // --- Catégorie (tribe_events_cat) + territoire (taxo maison) ---------------
    $cat_id = cs_resolve_term($b['category'] ?? '', 'tribe_events_cat');
    if ($cat_id) { wp_set_object_terms($post_id, array($cat_id), 'tribe_events_cat', false); }
    $terr_id = cs_resolve_term($b['territoire'] ?? '', 'territoire');
    if ($terr_id) { wp_set_object_terms($post_id, array($terr_id), 'territoire', false); }

    // --- Étiquettes (post_tag) : TOUJOURS remplacées par la liste fournie -------
    // Liste vide = on nettoie les tags existants. Contrôle total côté publisher
    // (aucun tag auto libre ; vocabulaire contrôlé plus tard).
    if (isset($b['tags']) && is_array($b['tags'])) {
        $tags = array_filter(array_map('sanitize_text_field', $b['tags']));
        wp_set_object_terms($post_id, $tags, 'post_tag', false);
    }

    // --- Méta du contrat « as_* » (voir docs/CONTRAT_META_AS.md) ---------------
    $meta = isset($b['meta']) && is_array($b['meta']) ? $b['meta'] : array();
    $allowed = array('as_score', 'as_home_score', 'as_home_override', 'as_home_order', 'as_gratuit', 'as_tarif', 'as_horaire',
        'as_billetterie_url', 'as_source_officielle_url', 'as_verifie_le', 'as_image_credit',
        // Statut RÉEL de rédaction (enrich_status local : 'enriched' ou vide/None) — sert de
        // filtre d'ÉLIGIBILITÉ pour l'allocateur home (cs_home_build_allocation), en amont du
        // tri par as_home_score : un événement jamais rédigé n'a pas à apparaître en « À la
        // une »/« En évidence » même si la section est en manque de contenu ce jour-là.
        'as_enrich_status',
        // Lieu + ville EN PLAT (en plus du Venue TEC) : binding JetEngine trivial
        // pour la carte-événement (pas de relation vers le CPT Venue à gérer).
        'as_lieu', 'as_ville',
        // URL de l'image ORIGINALE (non recadrée) : la vignette mise en avant est en
        // 4:3 pour la grille ; la FICHE affiche l'affiche entière via ce méta.
        'as_image_original',
        // Détail du panel de personas lecteurs (scripts.enrich.reader_panel) + statut
        // affiche/placement — cf. docs/CONTRAT_META_AS.md, section Extensions post-gel.
        'as_panel_mean', 'as_panel_vmean', 'as_panel_votes', 'as_panel_verdict',
        'as_panel_revision', 'as_affiches', 'as_placement',
        // Score « ça vaut le déplacement » (0-8, vide si non mesuré) : TRI de la section
        // home du même nom. Dérivé des critères d'importance de l'évaluateur
        // (utils/deplacement.py). ⚠️ Ne PAS trier cette section sur as_panel_vmean, qui
        // mesure la richesse de l'ARTICLE et non l'ampleur de l'événement.
        'as_deplacement');
    foreach ($allowed as $k) {
        if (array_key_exists($k, $meta)) {
            update_post_meta($post_id, $k, sanitize_text_field((string) $meta[$k]));
        }
    }

    // --- SEO Yoast (clés natives) ---------------------------------------------
    $seo = isset($b['seo']) && is_array($b['seo']) ? $b['seo'] : array();
    if (!empty($seo['title']))         { update_post_meta($post_id, '_yoast_wpseo_title', sanitize_text_field($seo['title'])); }
    if (!empty($seo['description']))   { update_post_meta($post_id, '_yoast_wpseo_metadesc', sanitize_text_field($seo['description'])); }
    if (!empty($seo['focus_keyword'])) { update_post_meta($post_id, '_yoast_wpseo_focuskw', sanitize_text_field($seo['focus_keyword'])); }

    // --- Image à la une -------------------------------------------------------
    // PRIORITÉ au média déjà téléversé côté Python (fiable). Repli : sideload depuis
    // l'URL (moins fiable côté serveur — hotlink/UA/firewall — mais mieux que rien).
    $fm = isset($b['featured_media_id']) ? (int) $b['featured_media_id'] : 0;
    if ($fm > 0) {
        set_post_thumbnail($post_id, $fm);
    } elseif (!empty($b['image_url']) && !has_post_thumbnail($post_id)) {
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $att_id = media_sideload_image((string) $b['image_url'], $post_id,
            $b['image_alt'] ?? $title, 'id');
        if (!is_wp_error($att_id) && $att_id) {
            set_post_thumbnail($post_id, $att_id);
            if (!empty($b['image_alt'])) {
                update_post_meta($att_id, '_wp_attachment_image_alt', sanitize_text_field($b['image_alt']));
            }
            if (!empty($b['meta']['as_image_credit'])) {
                wp_update_post(array('ID' => $att_id,
                    'post_excerpt' => sanitize_text_field($b['meta']['as_image_credit'])));
            }
        }
    }

    return new WP_REST_Response(array(
        'id'      => $post_id,
        'url'     => get_permalink($post_id),
        'updated' => $updated,
        'start'   => isset($args['EventStartDate']) ? $args['EventStartDate'] : '(aucune date)',
        'venue'   => $venue_id ?: 0,
        'venue_city_fixed' => $venue_city_fixed,
    ), 200);
}
