<?php
/*
Plugin Name: CS — budget d'exploration : les pages sans contenu propre hors index
Description: Sort de l'index Google et du sitemap les pages générées qui n'ont pas de
  contenu à elles : fiches LIEU sans aucun événement à venir, fiches ORGANISATEUR, et
  les vues « période » des hubs (ce week-end / aujourd'hui / cette semaine), qui sont
  des filtres de leur page parente. Rien n'est retiré du site : ces pages restent
  visibles, navigables et suivies (noindex, FOLLOW).
Author: Cultura Sabauda
Version: 1.0

  D'OÙ ÇA VIENT — 2026-09-09, Search Console de Franck : 223 pages dans l'index,
  589 hors index, dont 524 « Explorée, actuellement non indexée ». Mesuré le même jour
  sur le sitemap réel :

      /lieu/…            307 URLs   ~560 mots chacune, et ZÉRO événement affiché :
                                    tout le texte est le menu et le pied de page
      pages « période »  137 URLs   /que-faire-a-turin/ce-week-end/ et ses variantes
      /organisateur/…     75 URLs
      fiches événement   189 URLs   le vrai contenu — 22 % du sitemap
      -------------------------------------------------------------------
      total déclaré      858 URLs

  498 pages sans contenu propre, 524 refusées par Google : l'écart est mince. Le dégât
  ne s'arrête pas à ces pages — un site qui déclare trois fois plus de pages vides que
  de vraies dépense son budget d'exploration à les relire, et Google en tire une
  conclusion sur TOUT le domaine. C'est la cause la plus probable des fiches qui
  attendent longtemps avant d'être indexées.

  CE QUI EST VOLONTAIREMENT ÉPARGNÉ
  - les hubs (`cs_hub_quand` vide) : /que-faire-a-turin/, /it/cosa-fare-in-piemonte/…
    Ils portent la même intention de recherche que leurs vues période, avec un contenu
    stable — c'est eux qui doivent capter « que faire à Turin ».
  - les fiches événement, les articles, les pages institutionnelles.

  POURQUOI LES LIEUX SE ROUVRENT TOUT SEULS (règle 3, CLAUDE.md). Le critère n'est pas
  « lieu = hors index » mais « lieu SANS événement à venir ». Le jour où le gabarit
  listera les événements du lieu (chantier d'enrichissement des 30-50 lieux qui
  comptent), ces pages auront du contenu ET des événements : elles repasseront dans
  l'index sans que personne n'ait à toucher ce fichier. Aucun état à rouvrir à la main.

  INSTALLATION : wp-content/mu-plugins/cs-index-budget.php (must-use, actif seul).
  ROLLBACK : supprimer le fichier — tout revient comme avant, rien n'est écrit en base.

  CONTRÔLE APRÈS DÉPÔT
    curl -s https://agendasabauda.eu/lieu/forte-di-bard/ | grep -o 'data-cs="cs-index-budget"'
    curl -s https://agendasabauda.eu/tribe_venue-sitemap.xml | grep -c '<loc>'   # doit chuter
    curl -s https://agendasabauda.eu/que-faire-a-turin/ | grep -c 'cs-index-budget'  # doit rendre 0
*/

if (!defined('ABSPATH')) { exit; }

// Nombre d'événements à venir en dessous duquel une page LIEU n'a rien à faire dans
// l'index. 1 = il suffit d'un seul événement pour que la page ait une raison d'exister.
if (!defined('CS_IB_MIN_EVENTS_LIEU')) { define('CS_IB_MIN_EVENTS_LIEU', 1); }

if (!function_exists('cs_ib_evenements_a_venir')) {
/**
 * Combien d'événements PUBLIÉS et non terminés pointent vers ce lieu (ou organisateur).
 * La date de FIN décide (règle 5 : une exposition de mai à septembre compte tout l'été).
 */
function cs_ib_evenements_a_venir($post_id, $meta_cle) {
    global $wpdb;
    $post_id = (int) $post_id;
    if ($post_id <= 0) { return 0; }
    $cle = 'cs_ib_n_' . md5($meta_cle . ':' . $post_id);
    $n = get_transient($cle);
    if ($n === false) {
        $n = (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$wpdb->posts} p
             JOIN {$wpdb->postmeta} lien ON lien.post_id = p.ID AND lien.meta_key = %s
                  AND lien.meta_value = %d
             JOIN {$wpdb->postmeta} fin ON fin.post_id = p.ID AND fin.meta_key = '_EventEndDate'
             WHERE p.post_type = 'tribe_events' AND p.post_status = 'publish'
               AND fin.meta_value >= %s",
            $meta_cle, $post_id, current_time('Y-m-d H:i:s')));
        set_transient($cle, $n, HOUR_IN_SECONDS);
    }
    return (int) $n;
}
}

if (!function_exists('cs_ib_est_vue_periode')) {
/**
 * Vrai si la page est une VUE « période » d'un hub, jamais le hub lui-même.
 *
 * DEUX CRITÈRES, et c'est délibéré. Le méta `cs_hub_quand` est le marqueur maison
 * (snippet 148 : vide ou 'hub' = la page hub) — propre, et il suit si une période est
 * ajoutée un jour. Mais il n'est PAS exposé en REST, donc impossible à vérifier depuis
 * l'extérieur avant de livrer ; s'il manquait sur une partie des pages, ce fichier
 * n'aurait rien désindexé du tout, en silence.
 *
 * D'où la ceinture, elle VÉRIFIÉE le 2026-09-09 sur douze pages réelles du site :
 * une vue période est TOUJOURS enfant de son hub (parent ≠ 0) et porte un slug de
 * période, alors que les hubs sont à la racine (`/que-faire-a-turin/` → parent 0,
 * `/que-faire-a-menton/ce-week-end/` → parent 8016). Le slug seul ne suffirait pas :
 * `/ce-week-end/` À LA RACINE est une vraie page d'agenda, elle doit rester indexée —
 * d'où l'exigence du parent.
 */
function cs_ib_est_vue_periode($id) {
    $quand = (string) get_post_meta($id, 'cs_hub_quand', true);
    if ($quand !== '' && $quand !== 'hub') { return true; }
    $parent = (int) wp_get_post_parent_id($id);
    if ($parent <= 0) { return false; }   // hub ou page racine : on n'y touche pas
    $slug = get_post_field('post_name', $id);
    return in_array($slug, array(
        'ce-week-end', 'aujourdhui', 'cette-semaine',
        'questo-weekend', 'oggi', 'questa-settimana',
    ), true);
}
}

if (!function_exists('cs_ib_hors_index')) {
/**
 * Vrai si la page courante (ou $id) n'a pas de contenu propre à faire indexer.
 * Trois familles, dans l'ordre du moins au plus coûteux à évaluer.
 */
function cs_ib_hors_index($id = 0) {
    if (is_admin()) { return false; }
    $id = $id ? (int) $id : (int) get_queried_object_id();
    if ($id <= 0) { return false; }
    $type = get_post_type($id);

    // 1. Organisateur : jamais de contenu propre.
    if ($type === 'tribe_organizer') { return true; }

    // 2. Lieu : hors index tant qu'aucun événement à venir n'y renvoie.
    if ($type === 'tribe_venue') {
        return cs_ib_evenements_a_venir($id, '_EventVenueID') < CS_IB_MIN_EVENTS_LIEU;
    }

    // 3. Vue « période » d'un hub : /que-faire-a-turin/ce-week-end/ et ses variantes.
    if ($type === 'page') { return cs_ib_est_vue_periode($id); }
    return false;
}
}

if (!function_exists('cs_ib_singulier_hors_index')) {
function cs_ib_singulier_hors_index() {
    if (is_admin() || !is_singular(array('tribe_venue', 'tribe_organizer', 'page'))) {
        return false;
    }
    return cs_ib_hors_index();
}
}

// ── Balise robots ───────────────────────────────────────────────────────────────────
// « follow » : les liens de ces pages continuent d'être suivis, donc les fiches qu'elles
// listent restent découvrables. On retire de l'INDEX, pas du maillage.
add_filter('wpseo_robots_array', function ($robots) {
    if (!cs_ib_singulier_hors_index()) { return $robots; }
    $robots['index'] = 'noindex';
    return $robots;
}, 20);

add_filter('wpseo_robots', function ($chaine) {
    if (!cs_ib_singulier_hors_index()) { return $chaine; }
    return 'noindex, follow';
}, 20);

add_filter('wp_robots', function ($robots) {
    if (!cs_ib_singulier_hors_index()) { return $robots; }
    $robots['noindex'] = true;
    $robots['follow']  = true;
    unset($robots['index']);
    return $robots;
}, 20);

// Émission directe : constaté le 2026-08-08 (cs-completude.php), Yoast n'émet AUCUNE
// balise robots sur ce site — les filtres ci-dessus n'ont donc rien à intercepter.
add_action('wp_head', function () {
    if (!cs_ib_singulier_hors_index()) { return; }
    echo '<meta name="robots" content="noindex, follow" data-cs="cs-index-budget">' . "\n";
}, 1);

// ── Sitemap ─────────────────────────────────────────────────────────────────────────
// Les organisateurs sortent en bloc : aucun n'a de contenu propre, inutile de compter.
add_filter('wpseo_sitemap_exclude_post_type', function ($exclu, $post_type) {
    return ($post_type === 'tribe_organizer') ? true : $exclu;
}, 10, 2);

// Lieux sans événement à venir + vues « période » : liste calculée une fois par heure.
// Une heure de retard sur un sitemap ne change rien pour Google, et la requête ne pèse
// donc pas sur chaque génération.
add_filter('wpseo_exclude_from_sitemap_by_post_ids', function ($ids) {
    $hors = get_transient('cs_ib_sitemap_ids');
    if ($hors === false) {
        global $wpdb;
        $hors = array();

        // Vues « période » : mêmes deux critères que cs_ib_est_vue_periode (le méta
        // maison, et à défaut « enfant d'un hub + slug de période »). On passe par la
        // fonction pour qu'il n'existe qu'UNE définition de « vue période » — deux
        // formulations divergent tôt ou tard, et c'est le sitemap qui mentirait.
        $pages = $wpdb->get_col(
            "SELECT ID FROM {$wpdb->posts}
             WHERE post_type = 'page' AND post_status = 'publish' AND post_parent > 0");
        foreach ((array) $pages as $pid) {
            if (cs_ib_est_vue_periode((int) $pid)) { $hors[] = (int) $pid; }
        }

        // Lieux : ceux qu'AUCUN événement à venir ne réclame.
        $lieux = $wpdb->get_col(
            "SELECT ID FROM {$wpdb->posts}
             WHERE post_type = 'tribe_venue' AND post_status = 'publish'");
        foreach ((array) $lieux as $lid) {
            if (cs_ib_evenements_a_venir($lid, '_EventVenueID') < CS_IB_MIN_EVENTS_LIEU) {
                $hors[] = (int) $lid;
            }
        }
        set_transient('cs_ib_sitemap_ids', $hors, HOUR_IN_SECONDS);
    }
    return array_values(array_unique(array_merge((array) $ids, (array) $hors)));
});
