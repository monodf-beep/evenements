<?php
/*
Plugin Name: Cultura Sabauda — Scores Yoast calculés hors navigateur
Description: Deux routes REST (cs/v1/yoast-papers, cs/v1/yoast-scores) qui permettent au
  VPS de calculer les scores SEO et lisibilité de Yoast avec le moteur de Yoast lui-même
  (paquet npm `yoastseo`), puis de les écrire là où la colonne « Score SEO » les lit.
Author: Cultura Sabauda
Version: 1.2

  D'OÙ ÇA VIENT — Franck, 16/09/2026 : « pourquoi ça peut pas recalculer direct
  automatiquement Yoast ? » — puis « ok mais pour les articles, les pages, les events ».

  MESURÉ ce jour-là : 20 articles sur 24, 305 pages sur 306, 353 événements sur 364
  n'ont AUCUN score. Yoast calcule ses notes en JavaScript, dans le navigateur, quand on
  ouvre la fiche dans l'éditeur — jamais côté serveur, ni en gratuit ni en Premium. Tout
  ce que le pipeline publie par API reste donc « Non disponible » jusqu'à ce qu'un humain
  l'ouvre. Ce fichier ferme ce trou avec le MÊME moteur (le paquet `yoastseo` est le code
  de l'éditeur, publié en open source), exécuté sur le VPS par scripts/yoast_scores.py.

  CE QUE CHAQUE ROUTE FAIT, ET POURQUOI CÔTÉ WORDPRESS :
    GET  cs/v1/yoast-papers  — sert les fiches à noter avec EXACTEMENT ce que l'éditeur
         donnerait au moteur : la date au format de Yoast (« Sep 6, 2026 », lu dans
         description-data-provider.php), le titre SEO rendu par le gabarit quand il n'y a
         pas de titre personnalisé (wpseo_replace_vars), la locale Polylang du post.
         Deviner ces trois choses côté Python fabriquerait des écarts.
    POST cs/v1/yoast-scores  — écrit `_yoast_wpseo_linkdex` et `_yoast_wpseo_content_score`,
         PUIS reconstruit l'indexable : vérifié le 16/09, la colonne de la liste lit
         `wp_yoast_indexable.primary_focus_keyword_score`, pas la méta, et écrire la méta
         seule ne la rafraîchit pas (testé sur l'article 8228 : 0 avant, 0 après la méta,
         85 après reconstruction).

  RÉVERSIBLE : Yoast réécrit ces deux champs lui-même à la prochaine ouverture de la fiche
  dans l'éditeur. `cs_score_at` (= post_modified_gmt au moment du calcul) dit d'où vient
  la note et permet de ne recalculer que ce qui a changé.

  INSTALLATION : wp-content/mu-plugins/cs-yoast-scores.php (canal Novamira, voir
  docs/DEPLOIEMENT_WORDPRESS.md § 3). Prérequis : Yoast SEO actif, cs-rest-auth.php.
*/

if (!defined('ABSPATH')) { exit; }

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/yoast-papers', array(
        'methods'             => 'GET',
        'callback'            => 'cs_yoast_papers',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
    ));
    register_rest_route('cs/v1', '/yoast-scores', array(
        'methods'             => 'POST',
        'callback'            => 'cs_yoast_scores',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
    ));
});

function cs_yoast_types_autorises() {
    return array('post', 'page', 'tribe_events');
}

/**
 * Le titre SEO tel que l'éditeur l'analyse : le titre personnalisé, sinon le gabarit du
 * type rendu (« %%title%% %%sep%% %%sitename%% » → « Titre - Agenda Sabauda »).
 */
function cs_yoast_titre_seo($post) {
    $perso = trim((string) get_post_meta($post->ID, '_yoast_wpseo_title', true));
    if ($perso !== '') { return $perso; }
    $gabarit = '';
    if (class_exists('WPSEO_Options')) {
        $gabarit = (string) WPSEO_Options::get('title-' . $post->post_type, '');
    }
    if ($gabarit === '') { $gabarit = '%%title%% %%sep%% %%sitename%%'; }
    return function_exists('wpseo_replace_vars') ? trim(wpseo_replace_vars($gabarit, $post)) : $post->post_title;
}

function cs_yoast_paper($post) {
    global $wpdb;
    $id = (int) $post->ID;
    // LA LOCALE DU SITE, PAS CELLE DE L'ARTICLE — vérifié le 16/09 sur le panneau collé
    // par Franck : l'éditeur juge un texte italien avec les règles françaises (« 65 % de
    // phrases de plus de 20 mots », seuil français ; « aucun mot de transition », il
    // cherche les français). Servir la locale Polylang donnait 90 de lisibilité là où
    // l'éditeur dit 60. On sert ce que l'éditeur fait, pas ce qu'il devrait faire.
    $locale      = get_locale();
    $post_locale = function_exists('pll_get_post_language') ? (string) pll_get_post_language($id, 'locale') : '';
    // L'IMAGE MISE EN AVANT compte dans l'analyse (« Images : bon travail » sur un corps
    // sans balise img) : l'éditeur l'ajoute au texte, on sert son HTML pour faire pareil.
    $thumb        = get_post_thumbnail_id($id);
    $featured     = $thumb ? get_the_post_thumbnail($id, 'full') : '';
    // « Expression clé utilisée précédemment » : combien d'AUTRES contenus publiés
    // portent la même clé (greffon previouslyUsedKeywords, barème 0 → 9, 1 → 6, 2+ → 1).
    $kw = (string) get_post_meta($id, '_yoast_wpseo_focuskw', true);
    $kw_ailleurs = 0;
    if ($kw !== '') {
        $kw_ailleurs = (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID = m.post_id
              WHERE m.meta_key = '_yoast_wpseo_focuskw' AND m.meta_value = %s AND m.post_id <> %d
                AND p.post_status = 'publish'", $kw, $id));
    }
    $date = '';
    try { $date = YoastSEO()->helpers->date->format_translated($post->post_date, 'M j, Y'); }
    catch (\Throwable $e) { $date = date_i18n('M j, Y', strtotime($post->post_date)); }
    return array(
        'id'            => $id,
        'type'          => $post->post_type,
        'locale'        => $locale,
        'post_locale'   => $post_locale,
        'featured_html' => $featured,
        'kw_utilisee_ailleurs' => $kw_ailleurs,
        'keyword'       => $kw,
        'title'         => cs_yoast_titre_seo($post),
        'description'   => (string) get_post_meta($id, '_yoast_wpseo_metadesc', true),
        'slug'          => $post->post_name,
        'permalink'     => get_permalink($id),
        'date'          => $date,
        'post_title'    => $post->post_title,
        'content'       => $post->post_content,
        'modified'      => $post->post_modified_gmt,
        'linkdex'       => (string) get_post_meta($id, '_yoast_wpseo_linkdex', true),
        'content_score' => (string) get_post_meta($id, '_yoast_wpseo_content_score', true),
        'cs_score_at'   => (string) get_post_meta($id, 'cs_score_at', true),
    );
}

/**
 * GET — ?types=post,page,tribe_events&limit=200&ids=1,2&tout=1
 * Par défaut : les fiches publiées dont la note est ABSENTE ou plus vieille que la
 * dernière modification (cs_score_at < post_modified_gmt). `tout=1` ignore ce filtre.
 */
function cs_yoast_papers(WP_REST_Request $req) {
    global $wpdb;
    $types = array_values(array_intersect(
        array_filter(array_map('trim', explode(',', (string) $req->get_param('types')))),
        cs_yoast_types_autorises()));
    if (!$types) { $types = cs_yoast_types_autorises(); }
    $limit = max(1, min(500, (int) ($req->get_param('limit') ?: 200)));
    $ids   = array_filter(array_map('intval', explode(',', (string) $req->get_param('ids'))));
    $tout  = (string) $req->get_param('tout') === '1';

    $ph = implode(',', array_fill(0, count($types), '%s'));
    if ($ids) {
        $sql = $wpdb->prepare(
            "SELECT p.ID FROM {$wpdb->posts} p WHERE p.ID IN (" . implode(',', $ids) . ")
               AND p.post_type IN ($ph) AND p.post_status = 'publish'", $types);
    } else {
        $filtre = $tout ? '' :
            "AND (m.meta_value IS NULL OR m.meta_value = '' OR m.meta_value < p.post_modified_gmt)";
        $sql = $wpdb->prepare(
            "SELECT p.ID FROM {$wpdb->posts} p
               LEFT JOIN {$wpdb->postmeta} m ON m.post_id = p.ID AND m.meta_key = 'cs_score_at'
              WHERE p.post_type IN ($ph) AND p.post_status = 'publish' $filtre
              ORDER BY p.post_modified_gmt DESC LIMIT %d", array_merge($types, array($limit)));
    }
    $papers = array();
    foreach ($wpdb->get_col($sql) as $pid) {
        $p = get_post((int) $pid);
        if ($p) { $papers[] = cs_yoast_paper($p); }
    }
    // Le dénominateur, toujours : un « 0 à noter » doit dire combien sont publiées.
    $publiees = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ($ph) AND post_status = 'publish'", $types));
    return array('papers' => $papers, 'publiees' => $publiees, 'types' => $types);
}

function cs_yoast_reconstruire_indexable($id, $type) {
    try {
        $repo = YoastSEO()->classes->get(\Yoast\WP\SEO\Repositories\Indexable_Repository::class);
        $ix   = $repo->find_by_id_and_type($id, 'post');
        $b    = YoastSEO()->classes->get(\Yoast\WP\SEO\Builders\Indexable_Builder::class);
        $b->build_for_id_and_type($id, 'post', $ix);
        return true;
    } catch (\Throwable $e) {
        return $e->getMessage();
    }
}

/**
 * POST — {"scores":[{"id":8236,"seo":84,"readability":90}, …]}
 * `seo` peut être null : fiche SANS expression clé (196 événements sur 364 le 17/09, le
 * SEO se pose après publication). On écrit alors la lisibilité seule et on laisse la
 * colonne SEO à « Aucune expression clé », comme l'éditeur. Sans ça, le moteur rendait
 * -637 et cette route refusait 107 fiches sur 300 — qui se seraient représentées chaque
 * jour, refusées à l'identique (règle 3 de CLAUDE.md).
 */
function cs_yoast_scores(WP_REST_Request $req) {
    global $wpdb;
    $b = $req->get_json_params();
    if (!is_array($b) || empty($b['scores']) || !is_array($b['scores'])) {
        return new WP_Error('bad_json', 'Corps attendu : {"scores":[{id,seo,readability}]}', array('status' => 400));
    }
    $ecrits = 0; $erreurs = array();
    foreach ($b['scores'] as $s) {
        $id  = (int) ($s['id'] ?? 0);
        $sans_cle = !isset($s['seo']) || $s['seo'] === null || $s['seo'] === '';
        $seo = $sans_cle ? null : (int) $s['seo'];
        $lis = (int) ($s['readability'] ?? -1);
        $p   = $id ? get_post($id) : null;
        if (!$p || !in_array($p->post_type, cs_yoast_types_autorises(), true) || $p->post_status !== 'publish') {
            $erreurs[] = "$id : absent, non publié ou type non couvert"; continue;
        }
        if (($seo !== null && ($seo < 0 || $seo > 100)) || $lis < 0 || $lis > 100) {
            $erreurs[] = "$id : notes hors de 0-100 (" . ($seo ?? 'null') . " / $lis)"; continue;
        }
        if ($seo !== null) { update_post_meta($id, '_yoast_wpseo_linkdex', (string) $seo); }
        update_post_meta($id, '_yoast_wpseo_content_score', (string) $lis);
        update_post_meta($id, 'cs_score_at', $p->post_modified_gmt);
        update_post_meta($id, 'cs_score_par', 'node-yoastseo');
        $r = cs_yoast_reconstruire_indexable($id, $p->post_type);
        if ($r !== true) { $erreurs[] = "$id : indexable non reconstruit ($r)"; continue; }
        $ecrits++;
    }
    // RECOMPTE en base après écriture (règle 6) : ce que la colonne va afficher.
    // « sans_score » = aucune note de lisibilité (jamais passée ici ni dans l'éditeur) ;
    // « sans_cle » = pas d'expression clé, donc pas de note SEO possible. Deux périmètres,
    // deux compteurs — compter les sans-clé dans les sans-note les aurait fait passer
    // pour un travail en retard alors que c'est seo_batch qui les attend.
    $recompte = array();
    foreach (cs_yoast_types_autorises() as $t) {
        $recompte[$t] = array(
            'publiees'   => (int) $wpdb->get_var($wpdb->prepare(
                "SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type=%s AND post_status='publish'", $t)),
            'sans_score' => (int) $wpdb->get_var($wpdb->prepare(
                "SELECT COUNT(*) FROM {$wpdb->posts} p
                  WHERE p.post_type=%s AND p.post_status='publish'
                    AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} m WHERE m.post_id=p.ID
                                    AND m.meta_key='_yoast_wpseo_content_score' AND m.meta_value<>'')", $t)),
            'sans_cle'   => (int) $wpdb->get_var($wpdb->prepare(
                "SELECT COUNT(*) FROM {$wpdb->posts} p
                  WHERE p.post_type=%s AND p.post_status='publish'
                    AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} m WHERE m.post_id=p.ID
                                    AND m.meta_key='_yoast_wpseo_focuskw' AND m.meta_value<>'')", $t)),
        );
    }
    return array('ecrits' => $ecrits, 'erreurs' => $erreurs, 'recompte' => $recompte);
}
