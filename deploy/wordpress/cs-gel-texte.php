<?php
/*
Plugin Name: Agenda Sabauda — Gel du texte retouché à la main + journal de fiche
Description: Empêche le pipeline (route cs/v1/event) d'écraser le TITRE, le CORPS,
  l'EXTRAIT et les métas Yoast d'un événement qui a été retravaillé à la main (Franck,
  Cowork, n'importe qui d'autre dans wp-admin). Tient à côté un JOURNAL par fiche —
  qui a écrit quoi, quand — visible dans l'éditeur et lisible par le back-office.
Author: Cultura Sabauda
Version: 1.0

  D'OÙ ÇA VIENT — Franck, 2026-09-21 : « si cowork a travaillé le seo, on ne doit pas
  pouvoir revenir dessus avec le cron ». Et le rapport de Cowork le même jour : « la
  réapparition de 9378 en rouge confirme que le risque d'écrasement par le cron reste
  actif et concerne potentiellement tous les articles retravaillés aujourd'hui ».

  L'ORDRE DE TRAVAIL, et il ne va QUE dans ce sens :
      création FR + IT  →  cron SEO (seo_batch)  →  reprise à la main / Cowork
  Une fois la troisième étape passée sur une fiche, les deux premières ne repassent plus
  sur son texte. Ce fichier est ce qui le garantit.

  POURQUOI ICI ET PAS DANS cs-publish.php — cs-publish.php vit dans Code Snippets, en
  base (CLAUDE.md, docs/DEPLOIEMENT_WORDPRESS.md) : le patcher demande une manipulation
  à la main, ligne à ligne, sur le code qui met le site en ligne. Ce fichier-ci est un
  mu-plugin ORDINAIRE, déposé par le canal Novamira, qui intercepte la requête AVANT
  cs-publish.php (rest_pre_dispatch) et la contrôle APRÈS (rest_post_dispatch). Il ne
  demande AUCUNE modification de cs-publish.php.

  COMMENT LA RETOUCHE EST DÉTECTÉE — par EMPREINTE, jamais par `post_modified`.
  post_modified bouge pour des raisons qui n'ont rien d'une retouche : cs-completude
  repasse une fiche incomplète en brouillon, 137-cs-completude-rouvreur la republie,
  cs-polylang aligne le slug d'une paire FR/IT. Trois faux gels par jour, et le pipeline
  se serait arrêté tout seul sur des fiches que personne n'avait touchées. L'empreinte
  (md5 du titre + corps + extrait + les trois métas Yoast) ne bouge, elle, que si l'un
  de ces six champs a VRAIMENT changé.

  CE QUI RESTE ÉCRIT PAR LE PIPELINE, MÊME GELÉ — tout le reste, et c'est voulu : dates,
  lieu, catégorie, territoire, langue, métas as_* (score home, à la une, déplacement),
  image à la une. Une fiche gelée continue de recevoir ses corrections de date et son
  classement ; seul son TEXTE lui appartient. Sans ça le gel serait un cul-de-sac au
  sens de CLAUDE.md règle 3.

  QUI ROUVRE (règle 3, docs/ETATS_TERMINAUX.md) — trois chemins, dont deux automatiques :
   1. la case « texte retravaillé à la main » de l'encadré Journal, dans l'éditeur ;
   2. POST cs/v1/degel {post_ids:[…]} — utilisé par scripts/gel_texte.py --degel ;
   3. `forcer_texte` dans le payload cs/v1/event : liste des champs que le pipeline
      écrit MALGRÉ le gel. L'annulation d'un événement s'en sert pour le seul titre
      (le préfixe « ANNULÉ — » doit passer coûte que coûte, docs/EVENEMENTS_ANNULES.md).
  Et le compte des fiches garées se lit d'un coup : GET cs/v1/gel.

  INSTALLATION : wp-content/mu-plugins/cs-gel-texte.php (canal Novamira, voir
  docs/DEPLOIEMENT_WORDPRESS.md § 3). Prérequis : cs-rest-auth.php pour les routes.
  Contrôle que la version EN LIGNE est bien celle-ci (règle 1 appliquée au code) :
      curl -s https://agendasabauda.eu/wp-json/cs/v1/gel/version
*/

if (!defined('ABSPATH')) { exit; }

define('CS_GEL_VERSION', '2026-09-21c — liste en SQL direct, pas WP_Query (v1.2)');
define('CS_GEL_JOURNAL_MAX', 40);       // entrées gardées par fiche (les plus récentes)
define('CS_GEL_META_EMPREINTE', 'as_bot_empreinte');
define('CS_GEL_META_GEL', 'as_gel_texte');       // horodatage du gel (vide = pas gelé)
define('CS_GEL_META_MOTIF', 'as_gel_motif');
define('CS_GEL_META_JOURNAL', 'as_journal');
define('CS_GEL_META_DETAIL', 'as_bot_longueurs');   // longueur de chaque champ au dernier passage
define('CS_GEL_TYPE', 'tribe_events');

/** Les six champs que le pipeline écrit et qu'une reprise à la main doit protéger. */
function cs_gel_surface($post_id) {
    $p = get_post($post_id);
    if (!$p) { return null; }
    return array(
        'title'   => (string) $p->post_title,
        'content' => (string) $p->post_content,
        'excerpt' => (string) $p->post_excerpt,
        'seo'     => (string) get_post_meta($post_id, '_yoast_wpseo_title', true),
        'seo_desc' => (string) get_post_meta($post_id, '_yoast_wpseo_metadesc', true),
        'seo_cle'  => (string) get_post_meta($post_id, '_yoast_wpseo_focuskw', true),
    );
}

/** Longueurs par champ, rangées à côté de l'empreinte : elles ne servent QU'à dire
 *  lesquels ont bougé le jour où un gel se déclenche. Une empreinte dit « ça a changé »,
 *  jamais « quoi » — et c'est « quoi » qu'on cherche à 17 h un dimanche. */
function cs_gel_longueurs($surface) {
    $out = array();
    if (is_array($surface)) {
        foreach ($surface as $k => $v) { $out[$k] = strlen((string) $v); }
    }
    return $out;
}

function cs_gel_empreinte($surface) {
    if (!is_array($surface)) { return ''; }
    return md5(implode("\x1f", array(
        $surface['title'], $surface['content'], $surface['excerpt'],
        $surface['seo'], $surface['seo_desc'], $surface['seo_cle'])));
}

/** Journal de la fiche : liste horodatée {at, qui, quoi}, la plus récente en dernier. */
function cs_gel_journal_lire($post_id) {
    $j = get_post_meta($post_id, CS_GEL_META_JOURNAL, true);
    if (is_array($j)) { return $j; }
    if (is_string($j) && $j !== '') {
        $d = json_decode($j, true);
        if (is_array($d)) { return $d; }
    }
    return array();
}

function cs_gel_journal_ajouter($post_id, $qui, $quoi) {
    $j = cs_gel_journal_lire($post_id);
    $j[] = array(
        'at'   => current_time('mysql'),
        'qui'  => substr(sanitize_text_field((string) $qui), 0, 40),
        'quoi' => substr(sanitize_text_field((string) $quoi), 0, 300),
    );
    if (count($j) > CS_GEL_JOURNAL_MAX) {
        $j = array_slice($j, -CS_GEL_JOURNAL_MAX);
    }
    // Tableau (et pas JSON) VOLONTAIREMENT : update_post_meta déballe les antislashs de
    // ce qu'on lui donne (wp_unslash), ce qui casserait un JSON dès le premier guillemet
    // échappé. Un tableau est sérialisé par WordPress lui-même, sans ce détour.
    update_post_meta($post_id, CS_GEL_META_JOURNAL, $j);
    return $j;
}

/**
 * Gelé ou pas — et si une retouche vient d'être découverte, on la MARQUE ici.
 *
 * Trois cas, dans cet ordre :
 *  - marqueur déjà posé (à la main, par une session Cowork, ou par une détection
 *    précédente) → gelé, on n'y revient pas ;
 *  - empreinte connue et DIFFÉRENTE de l'actuelle → quelqu'un a écrit depuis le dernier
 *    passage du pipeline : on gèle, on journalise, et c'est la seule fois où ce texte-ci
 *    échappe de justesse à l'écrasement ;
 *  - aucune empreinte (fiche jamais vue par ce fichier) → PAS de gel. On ne peut pas
 *    savoir, et geler tout le catalogue par précaution arrêterait le pipeline entier.
 *    C'est pour ce trou-là, et pour lui seul, qu'existe POST cs/v1/gel : les fiches
 *    retravaillées AVANT l'installation se marquent par leur liste d'ids.
 */
function cs_gel_etat($post_id) {
    $gel = (string) get_post_meta($post_id, CS_GEL_META_GEL, true);
    if ($gel !== '') {
        return array('gele' => true, 'depuis' => $gel,
                     'motif' => (string) get_post_meta($post_id, CS_GEL_META_MOTIF, true));
    }
    $connue = (string) get_post_meta($post_id, CS_GEL_META_EMPREINTE, true);
    if ($connue === '') {
        return array('gele' => false, 'depuis' => '', 'motif' => 'jamais vue');
    }
    $surface = cs_gel_surface($post_id);
    $actuelle = cs_gel_empreinte($surface);
    if ($actuelle !== '' && $actuelle !== $connue) {
        $quand = current_time('mysql');
        update_post_meta($post_id, CS_GEL_META_GEL, $quand);
        update_post_meta($post_id, CS_GEL_META_MOTIF, 'retouche détectée (empreinte)');
        // QUELS champs ont bougé, et pas seulement « ça a bougé ». Le 21/09, deux lignes
        // de journal sans cette précision ont coûté une heure de reconstitution : on
        // voyait un gel, sans pouvoir dire s'il venait d'une vraie retouche ou d'un
        // défaut de mesure. Les longueurs suffisent, le texte lui-même n'a rien à faire
        // dans un journal borné à 300 caractères.
        $anciennes = get_post_meta($post_id, CS_GEL_META_DETAIL, true);
        $bouges = array();
        if (is_array($anciennes)) {
            foreach ($surface as $champ => $valeur) {
                if (!isset($anciennes[$champ]) || $anciennes[$champ] !== strlen((string) $valeur)) {
                    $bouges[] = $champ;
                }
            }
        }
        cs_gel_journal_ajouter($post_id, 'gel',
            'Texte modifié hors pipeline depuis le dernier passage — gelé : le cron '
            . 'ne réécrira plus titre, corps, extrait ni métas Yoast.'
            . ($bouges ? ' Champs modifiés : ' . implode(', ', $bouges) . '.' : ''));
        return array('gele' => true, 'depuis' => $quand,
                     'motif' => 'retouche détectée (empreinte)');
    }
    return array('gele' => false, 'depuis' => '', 'motif' => '');
}

function cs_gel_poser($post_id, $qui, $motif) {
    update_post_meta($post_id, CS_GEL_META_GEL, current_time('mysql'));
    update_post_meta($post_id, CS_GEL_META_MOTIF, substr(sanitize_text_field((string) $motif), 0, 200));
    cs_gel_journal_ajouter($post_id, $qui, 'Gel posé : ' . $motif);
}

function cs_gel_lever($post_id, $qui, $motif) {
    delete_post_meta($post_id, CS_GEL_META_GEL);
    delete_post_meta($post_id, CS_GEL_META_MOTIF);
    // L'empreinte est remise à l'état ACTUEL : sans ça, la première lecture suivante
    // verrait un écart (le texte courant n'est pas celui du dernier passage du pipeline)
    // et regèlerait aussitôt la fiche. Un dégel qui ne dégèle pas serait pire que rien.
    $surface = cs_gel_surface($post_id);
    update_post_meta($post_id, CS_GEL_META_EMPREINTE, cs_gel_empreinte($surface));
    update_post_meta($post_id, CS_GEL_META_DETAIL, cs_gel_longueurs($surface));
    cs_gel_journal_ajouter($post_id, $qui,
        'Gel levé : le pipeline pourra réécrire le texte au prochain passage. ' . $motif);
}

// ── Interception de cs/v1/event ────────────────────────────────────────────────
// Mémoire d'un appel à l'autre (pre_dispatch → post_dispatch), INDEXÉE PAR L'OBJET
// REQUÊTE et pas par un simple drapeau « une passe est en cours ».
//
// MESURÉ le 2026-09-21, et c'est la première version de ce fichier qui s'y est fait
// prendre : `rest_post_dispatch` se déclenche pour TOUTE requête REST servie, y compris
// une requête qui n'a rien à voir. Avec un drapeau global, la passe ouverte sur
// /cs/v1/event a été refermée par la réponse d'une requête /mcp/novamira-oauth — le
// journal de la fiche a reçu « Création par le pipeline » au nom d'un appel qui ne la
// concernait pas, et la contre-épreuve n'a jamais tourné sur la bonne réponse.
// La clé d'objet rend l'appariement exact : ce qui a été ouvert par une requête ne peut
// être refermé que par ELLE.
//
// ⚠️ Et une chose qu'il faut savoir avant de tester ce fichier : `rest_do_request()`
// (l'appel REST INTERNE) n'applique PAS `rest_post_dispatch` — seul le service HTTP le
// fait, dans WP_REST_Server::serve_request(). Un test écrit avec rest_do_request seul
// ne passe donc jamais dans la moitié « après » et donne l'illusion que le gel ne tient
// pas. Pour reproduire fidèlement le chemin de production :
//     $rep = rest_do_request($req);
//     $rep = apply_filters('rest_post_dispatch', rest_ensure_response($rep),
//                          rest_get_server(), $req);
function &cs_gel_memos() {
    static $memos = array();
    return $memos;
}

add_filter('rest_pre_dispatch', 'cs_gel_avant_dispatch', 10, 3);
function cs_gel_avant_dispatch($result, $server, $request) {
    if (!is_object($request) || $request->get_route() !== '/cs/v1/event') { return $result; }
    // MÊME PORTE QUE LA ROUTE QU'ON INTERCEPTE. `rest_pre_dispatch` se déclenche AVANT
    // le permission_callback de cs-publish.php : sans ce contrôle, une requête anonyme
    // — qui sera refusée trois lignes plus loin — aurait quand même fait écrire des
    // métas et une ligne de journal sur une fiche publique.
    if (!current_user_can('edit_posts')) { return $result; }
    $memos = &cs_gel_memos();
    $cle = spl_object_id($request);
    $memos[$cle] = array('post_id' => 0, 'gele' => false, 'surface' => null,
                         'neutralises' => array(), 'forces' => array());

    $b = $request->get_json_params();
    if (!is_array($b)) { return $result; }
    $pid = isset($b['wp_post_id']) ? (int) $b['wp_post_id'] : 0;
    if ($pid <= 0 || get_post_type($pid) !== CS_GEL_TYPE) { return $result; }

    $memos[$cle]['post_id'] = $pid;
    $memos[$cle]['surface'] = cs_gel_surface($pid);
    $etat = cs_gel_etat($pid);
    $memos[$cle]['gele'] = $etat['gele'];
    if (!$etat['gele']) { return $result; }

    // `forcer_texte` : liste des champs que le pipeline écrit MALGRÉ le gel.
    // true ⇒ tous (repli pour un appel qui assume de tout reprendre).
    $forces = isset($b['forcer_texte']) ? $b['forcer_texte'] : array();
    if ($forces === true)      { $forces = array('title', 'content', 'excerpt', 'seo'); }
    elseif (!is_array($forces)) { $forces = array(); }
    $forces = array_map('strval', $forces);
    $memos[$cle]['forces'] = $forces;

    // On ne SUPPRIME pas les clés : cs-publish.php refuse un titre vide (erreur
    // no_title) et son bloc SEO ne teste que `!empty`. On les remplace par ce qui est
    // DÉJÀ en ligne — l'écriture devient un non-événement, et tout le reste du payload
    // (dates, lieu, taxonomies, métas as_*, image) continue son chemin intact.
    $s = $memos[$cle]['surface'];
    $neutralises = array();
    if (!in_array('title', $forces, true) && isset($b['title'])) {
        $b['title'] = $s['title']; $neutralises[] = 'title';
    }
    if (!in_array('content', $forces, true) && isset($b['content'])) {
        $b['content'] = $s['content']; $neutralises[] = 'content';
    }
    if (!in_array('excerpt', $forces, true) && isset($b['excerpt'])) {
        $b['excerpt'] = $s['excerpt']; $neutralises[] = 'excerpt';
    }
    if (!in_array('seo', $forces, true) && isset($b['seo'])) {
        unset($b['seo']); $neutralises[] = 'seo';
    }
    unset($b['slug']);   // jamais de renommage d'adresse sur une fiche reprise à la main
    $memos[$cle]['neutralises'] = $neutralises;

    $request->set_body(wp_json_encode($b));
    return $result;
}

add_filter('rest_post_dispatch', 'cs_gel_apres_dispatch', 10, 3);
function cs_gel_apres_dispatch($response, $server, $request) {
    // Seule la requête qui a ouvert la passe peut la refermer (cf. le commentaire de
    // cs_gel_memos) : ce filtre-ci reçoit AUSSI les réponses de routes étrangères.
    if (!is_object($request)) { return $response; }
    $memos = &cs_gel_memos();
    $cle = spl_object_id($request);
    if (!isset($memos[$cle])) { return $response; }
    $memo = $memos[$cle];
    unset($memos[$cle]);
    if (!is_object($response) || $response->get_status() >= 300) { return $response; }

    $data = $response->get_data();
    $pid = $memo['post_id'];
    if (!$pid && is_array($data) && !empty($data['id'])) { $pid = (int) $data['id']; }
    if ($pid <= 0 || get_post_type($pid) !== CS_GEL_TYPE) { return $response; }

    $apres = cs_gel_surface($pid);
    $restaures = array();
    if ($memo['gele']) {
        // CONTRE-ÉPREUVE. Le remplacement du corps de requête ci-dessus suppose que
        // WP_REST_Request relit son JSON après set_body() — c'est le cas, mais un
        // garde-fou qui n'a jamais été mis à l'épreuve ne prouve rien (docs/ERREURS
        // _2026-09-14). On REGARDE donc ce qui est en base après coup, et si le texte a
        // bougé quand même, on le remet. Le gel tient alors même si l'interception rate.
        $avant = $memo['surface'];
        $a_bouge = array();
        foreach (array('title', 'content', 'excerpt') as $champ) {
            if (!in_array($champ, $memo['forces'], true) && $apres[$champ] !== $avant[$champ]) {
                $a_bouge[] = $champ;
            }
        }
        $restaures = $a_bouge;
        if ($a_bouge) {
            wp_update_post(array(
                'ID'           => $pid,
                'post_title'   => wp_slash($avant['title']),
                'post_content' => wp_slash($avant['content']),
                'post_excerpt' => wp_slash($avant['excerpt']),
            ));
            cs_gel_journal_ajouter($pid, 'gel',
                '⚠️ Le pipeline a écrit malgré le gel (' . implode(', ', $a_bouge)
                . ') — texte RESTAURÉ. Si ça se répète, c\'est l\'interception qu\'il faut reprendre.');
        }
        if (!in_array('seo', $memo['forces'], true)) {
            foreach (array('seo' => '_yoast_wpseo_title', 'seo_desc' => '_yoast_wpseo_metadesc',
                           'seo_cle' => '_yoast_wpseo_focuskw') as $k => $meta) {
                if ($apres[$k] !== $avant[$k]) { update_post_meta($pid, $meta, $avant[$k]); }
            }
        }
        $quoi = 'Passage du pipeline — texte GELÉ, seules les données structurées (dates, '
              . 'lieu, catégorie, métas as_*, image) ont été mises à jour.';
        if ($memo['forces']) {
            $quoi .= ' Forcé malgré le gel : ' . implode(', ', $memo['forces']) . '.';
        }
        cs_gel_journal_ajouter($pid, 'pipeline', $quoi);
        // L'empreinte de référence reste celle du texte RETOUCHÉ : c'est lui la version
        // à protéger, pas ce que le pipeline vient de proposer.
        $final = cs_gel_surface($pid);
        update_post_meta($pid, CS_GEL_META_EMPREINTE, cs_gel_empreinte($final));
        update_post_meta($pid, CS_GEL_META_DETAIL, cs_gel_longueurs($final));
    } else {
        update_post_meta($pid, CS_GEL_META_EMPREINTE, cs_gel_empreinte($apres));
        update_post_meta($pid, CS_GEL_META_DETAIL, cs_gel_longueurs($apres));
        cs_gel_journal_ajouter($pid, 'pipeline',
            (empty($data['updated']) ? 'Création' : 'Mise à jour')
            . ' par le pipeline (titre, corps, extrait, métas Yoast et données structurées).');
    }

    // Ce que Python doit apprendre (scripts/publish_batch_as.py le range en base) :
    // la fiche est gelée, et ces champs-là n'ont PAS été écrits.
    if (is_array($data)) {
        $etat = cs_gel_etat($pid);
        $data['gel'] = array(
            'gele'   => (bool) $etat['gele'],
            'depuis' => $etat['depuis'],
            'motif'  => $etat['motif'],
            'champs' => $memo['neutralises'],
            'forces' => $memo['forces'],
            // Champs que cs-publish a écrits malgré l'interception et qu'on a dû
            // remettre : non vide = l'interception n'a pas tenu, à regarder.
            'restaures' => $restaures,
        );
        $response->set_data($data);
    }
    return $response;
}

// ── Routes REST ────────────────────────────────────────────────────────────────
add_action('rest_api_init', function () {
    $peut = function () { return current_user_can('edit_posts'); };
    register_rest_route('cs/v1', '/gel/version', array(
        'methods'             => 'GET',
        'callback'            => function () { return array('cs_gel' => CS_GEL_VERSION); },
        'permission_callback' => '__return_true',
    ));
    register_rest_route('cs/v1', '/gel', array(
        array('methods' => 'GET',  'callback' => 'cs_gel_route_liste', 'permission_callback' => $peut),
        array('methods' => 'POST', 'callback' => 'cs_gel_route_poser', 'permission_callback' => $peut),
    ));
    register_rest_route('cs/v1', '/degel', array(
        'methods'             => 'POST',
        'callback'            => 'cs_gel_route_lever',
        'permission_callback' => $peut,
    ));
    register_rest_route('cs/v1', '/journal', array(
        array('methods' => 'GET',  'callback' => 'cs_gel_route_journal_lire', 'permission_callback' => $peut),
        array('methods' => 'POST', 'callback' => 'cs_gel_route_journal_ecrire', 'permission_callback' => $peut),
    ));
});

/**
 * GET cs/v1/gel — la file des fiches garées, avec son périmètre (CLAUDE.md règle 6).
 *
 * ⚠️ SQL DIRECT, ET SURTOUT PAS WP_Query. Mesuré le 21/09, une heure après la pose des
 * 49 premiers gels : la version WP_Query de cette route en rendait **23 sur 51**. Cause :
 * The Events Calendar filtre ses propres collections et en retire les événements PASSÉS
 * (CLAUDE.md règle 2, écrite pour exactement ça). Or le premier lot gelé était justement
 * fait d'événements passés récurrents.
 *
 * Ce n'était pas un compteur inexact, c'était un compteur DANGEREUX : `scripts/gel_texte.py
 * --sync` compare cette liste à la base locale et EFFACE le marqueur de ce qui n'y figure
 * pas. Un `--sync --apply` aurait donc dégelé 28 fiches en silence, en croyant recopier
 * fidèlement l'état du site. Une liste qui ment sur son périmètre finit toujours par faire
 * agir quelqu'un — ici, elle-même.
 *
 * `!= ''` et pas EXISTS : cs_gel_etat() traite la chaîne vide comme « pas de gel », et
 * deux détecteurs pour la même chose finissent toujours par diverger.
 */
function cs_gel_route_liste(WP_REST_Request $req) {
    global $wpdb;
    $lignes = $wpdb->get_results($wpdb->prepare(
        "SELECT p.ID, p.post_status, m.meta_value AS depuis
           FROM {$wpdb->postmeta} m
           JOIN {$wpdb->posts} p ON p.ID = m.post_id
          WHERE m.meta_key = %s AND m.meta_value <> ''
            AND p.post_type = %s
            AND p.post_status NOT IN ('trash', 'auto-draft')
          ORDER BY m.meta_value DESC",
        CS_GEL_META_GEL, CS_GEL_TYPE), ARRAY_A);
    $out = array();
    foreach ($lignes as $l) {
        $id = (int) $l['ID'];
        $out[] = array(
            'id'     => $id,
            'titre'  => get_the_title($id),
            'statut' => $l['post_status'],
            'depuis' => (string) $l['depuis'],
            'motif'  => (string) get_post_meta($id, CS_GEL_META_MOTIF, true),
            'url'    => get_permalink($id),
        );
    }
    return array('total' => count($out),
                 'perimetre' => 'tribe_events hors corbeille, PASSÉS COMPRIS (SQL direct)',
                 'fiches' => $out);
}

function cs_gel_ids_du_corps(WP_REST_Request $req) {
    $b = $req->get_json_params();
    $ids = (is_array($b) && isset($b['post_ids']) && is_array($b['post_ids'])) ? $b['post_ids'] : array();
    $out = array();
    foreach ($ids as $i) {
        $i = (int) $i;
        if ($i > 0 && get_post_type($i) === CS_GEL_TYPE) { $out[] = $i; }
    }
    return array($out, $b);
}

/** POST cs/v1/gel {post_ids, qui, motif} — marquage à la main (reprise de l'existant). */
function cs_gel_route_poser(WP_REST_Request $req) {
    list($ids, $b) = cs_gel_ids_du_corps($req);
    $qui   = isset($b['qui']) ? (string) $b['qui'] : 'main';
    $motif = isset($b['motif']) ? (string) $b['motif'] : 'marqué à la main';
    foreach ($ids as $id) { cs_gel_poser($id, $qui, $motif); }
    return array('geles' => $ids, 'total' => count($ids));
}

/** POST cs/v1/degel {post_ids, qui} — rend la main au pipeline (le rouvreur, règle 3). */
function cs_gel_route_lever(WP_REST_Request $req) {
    list($ids, $b) = cs_gel_ids_du_corps($req);
    $qui   = isset($b['qui']) ? (string) $b['qui'] : 'main';
    $motif = isset($b['motif']) ? (string) $b['motif'] : '';
    foreach ($ids as $id) { cs_gel_lever($id, $qui, $motif); }
    return array('degeles' => $ids, 'total' => count($ids));
}

function cs_gel_route_journal_lire(WP_REST_Request $req) {
    $pid = (int) $req->get_param('post_id');
    if ($pid <= 0 || !get_post($pid)) {
        return new WP_Error('bad_post', 'post_id inconnu.', array('status' => 404));
    }
    $etat = cs_gel_etat($pid);
    return array('post_id' => $pid, 'gel' => $etat, 'journal' => cs_gel_journal_lire($pid));
}

/**
 * POST cs/v1/journal {post_id, qui, quoi, gel} — c'est par là qu'une session Cowork
 * DIT ce qu'elle a fait, fiche par fiche. `gel: true` pose le gel dans la foulée (à
 * n'utiliser que si la retouche n'est pas détectable autrement — une modification du
 * texte se voit toute seule à l'empreinte).
 */
function cs_gel_route_journal_ecrire(WP_REST_Request $req) {
    $b = $req->get_json_params();
    if (!is_array($b)) { return new WP_Error('bad_json', 'Corps JSON invalide.', array('status' => 400)); }
    $pid = isset($b['post_id']) ? (int) $b['post_id'] : 0;
    if ($pid <= 0 || !get_post($pid)) {
        return new WP_Error('bad_post', 'post_id inconnu.', array('status' => 404));
    }
    $qui  = isset($b['qui']) ? (string) $b['qui'] : 'cowork';
    $quoi = isset($b['quoi']) ? (string) $b['quoi'] : '';
    if (trim($quoi) === '') {
        return new WP_Error('vide', 'Rien à journaliser (champ « quoi » vide).', array('status' => 400));
    }
    $j = cs_gel_journal_ajouter($pid, $qui, $quoi);
    if (!empty($b['gel'])) { cs_gel_poser($pid, $qui, 'demandé par ' . $qui); }
    return array('post_id' => $pid, 'entrees' => count($j), 'gel' => cs_gel_etat($pid));
}

// ── L'encadré dans l'éditeur ───────────────────────────────────────────────────
add_action('add_meta_boxes', function () {
    foreach (array(CS_GEL_TYPE, 'post', 'page') as $type) {
        add_meta_box('cs_gel_journal', 'Journal Agenda Sabauda', 'cs_gel_metabox',
                     $type, 'side', 'high');
    }
});

function cs_gel_metabox($post) {
    $est_event = ($post->post_type === CS_GEL_TYPE);
    $etat = $est_event ? cs_gel_etat($post->ID)
                       : array('gele' => false, 'depuis' => '', 'motif' => '');
    wp_nonce_field('cs_gel_box', 'cs_gel_nonce');
    if ($est_event) {
        echo '<p><label><input type="checkbox" name="cs_gel_actif" value="1" '
           . checked($etat['gele'], true, false) . '> <strong>Texte retravaillé à la main</strong></label><br>';
        echo '<span class="description">Coché, le cron ne réécrit plus le titre, le corps, '
           . 'l\'extrait ni les métas Yoast de cette fiche. Il continue de mettre à jour '
           . 'les dates, le lieu, la catégorie et l\'image.</span></p>';
        if ($etat['gele']) {
            echo '<p><em>Gelé depuis le ' . esc_html($etat['depuis'])
               . ' (' . esc_html($etat['motif']) . ').</em></p>';
        }
    }
    $j = array_reverse(cs_gel_journal_lire($post->ID));
    if (!$j) {
        echo '<p><em>Aucun passage enregistré pour l\'instant.</em></p>';
        return;
    }
    echo '<ul style="margin:0;max-height:22em;overflow:auto">';
    foreach (array_slice($j, 0, 20) as $e) {
        echo '<li style="margin-bottom:.6em;border-bottom:1px solid #eee;padding-bottom:.4em">'
           . '<strong>' . esc_html(isset($e['qui']) ? $e['qui'] : '?') . '</strong> · '
           . '<span style="color:#666">' . esc_html(isset($e['at']) ? $e['at'] : '') . '</span><br>'
           . esc_html(isset($e['quoi']) ? $e['quoi'] : '') . '</li>';
    }
    echo '</ul>';
}

add_action('save_post', 'cs_gel_sauver_metabox', 10, 2);
function cs_gel_sauver_metabox($post_id, $post) {
    if (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE) { return; }
    if (wp_is_post_revision($post_id) || wp_is_post_autosave($post_id)) { return; }
    if ($post->post_type !== CS_GEL_TYPE) { return; }
    $nonce = isset($_POST['cs_gel_nonce']) ? sanitize_text_field(wp_unslash($_POST['cs_gel_nonce'])) : '';
    if (!$nonce || !wp_verify_nonce($nonce, 'cs_gel_box')) { return; }
    if (!current_user_can('edit_post', $post_id)) { return; }

    $veut = !empty($_POST['cs_gel_actif']);
    $a    = (string) get_post_meta($post_id, CS_GEL_META_GEL, true) !== '';
    if ($veut && !$a) {
        cs_gel_poser($post_id, wp_get_current_user()->user_login, 'case cochée dans l\'éditeur');
    } elseif (!$veut && $a) {
        cs_gel_lever($post_id, wp_get_current_user()->user_login, 'case décochée dans l\'éditeur');
    } elseif (!$veut) {
        // Ni gelée ni demandée gelée : la fiche vient d'être enregistrée à la main, donc
        // son texte n'est plus celui du pipeline. On NE gèle pas (l'opérateur n'a rien
        // demandé) mais on garde la trace — c'est la prochaine lecture d'empreinte qui
        // tranchera, et le journal dira qui est passé.
        cs_gel_journal_ajouter($post_id, wp_get_current_user()->user_login,
                               'Enregistrement depuis l\'éditeur WordPress.');
    }
}
