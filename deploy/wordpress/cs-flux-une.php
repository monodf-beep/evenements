<?php
/**
 * Plugin Name: CS - Flux RSS : les fiches de la une rejoignent les articles
 * Description: Ajoute au flux principal (/feed/, /it/feed/) les fiches « À la une » du jour, avec leur date d'entrée dans la une.
 *
 * POURQUOI (24/09/2026). Franck a vu sur guidatorino.com un encadré « seguiteci su Google
 * Discover ». Suivre un site sur Discover passe par le flux RSS qu'il déclare. Mesuré ce
 * jour-là : notre /feed/ ne contenait que les ARTICLES (10 en tout, 2 depuis le 06/09) et
 * aucune fiche d'événement — un abonné n'aurait presque rien reçu. Toutes les fiches, ce
 * serait l'excès inverse (des dizaines par semaine). Arbitrage proposé et accepté : les
 * articles, plus les fiches que la page d'accueil met « À la une ».
 *
 * CE QUI EST SÉLECTIONNÉ. Les ids de la section 'ala-une' de l'allocateur de la home
 * (Code Snippets n° 44, `cs_home_build_allocation`) — le MÊME calcul que la page, pas une
 * seconde règle (journal du 08/09 : deux détecteurs pour la même chose, un seul juste).
 * Dans un flux, sans cookie de territoire, c'est la une des quatre territoires, dans la
 * langue du flux (Polylang : /feed/ FR, /it/feed/ IT). 40 fiches FR avaient
 * as_une_now > 0 ce jour-là : les prendre toutes aurait noyé l'abonné.
 *
 * LA DATE. The Events Calendar remplace la date de publication d'un événement dans un flux
 * par la DATE DE L'ÉVÉNEMENT (`Tribe__Events__Templates::event_date_to_pubDate`, relevé
 * sur le site le 24/09) : une fiche du 26/09 se disait « publiée le 26/09 », dans le
 * futur. Et sa vraie date de création peut dater de juillet : elle tomberait en bas du
 * flux, invisible comme nouveauté. On date donc chaque fiche du jour où elle est ENTRÉE
 * dans la une (méta `as_flux_une_depuis`, posée à la première apparition, jamais
 * réécrite). C'est une date vraie : celle où elle est devenue une recommandation.
 *
 * NE REQUÊTE PAS LES ÉVÉNEMENTS PAR LA REQUÊTE PRINCIPALE. The Events Calendar réécrit
 * toute requête qui porte sur tribe_events (tri par date d'événement, tables maison). On
 * laisse donc la requête du flux telle quelle (les articles) et on AJOUTE les fiches
 * ensuite, par `the_posts`, avant de retrier par date.
 *
 * ACTIVATION. Inerte tant que l'option `cs_flux_une_actif` ne vaut pas 1. Aperçu sans
 * rien activer : /feed/?cs_flux_une=1. Retour arrière : remettre l'option à 0 (le flux
 * redevient celui d'avant, les métas `as_flux_une_depuis` restent sans effet).
 */
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_flux_une_motif')) {
/**
 * '' si la requête est le flux principal à compléter, sinon la raison du refus. Une
 * RAISON plutôt qu'un booléen : en aperçu, elle part dans l'en-tête X-CS-Flux-Une — le
 * 24/09, deux versions successives ont rendu un flux inchangé sans dire pourquoi, et la
 * seconde hypothèse (la langue Polylang vue comme une archive) n'était qu'une partie de
 * la réponse. Un refus silencieux ressemble exactement à « rien à ajouter ».
 */
function cs_flux_une_motif($q) {
    if (!($q instanceof WP_Query)) { return 'pas une requete'; }
    if (!$q->is_main_query()) { return 'pas la requete principale'; }
    if (!$q->is_feed() || $q->is_comment_feed()) { return 'pas un flux d articles'; }
    // PAS `is_archive()` : Polylang ajoute la langue (taxonomie 'language') à la requête
    // du flux, qui passe alors pour une archive de taxonomie. On nomme donc les archives
    // à écarter, et pour les taxonomies on ignore celle de la langue.
    if ($q->is_search() || $q->is_singular() || $q->is_category() || $q->is_tag()
        || $q->is_author() || $q->is_date() || $q->is_post_type_archive()) {
        return 'flux d une archive, d une recherche ou d un contenu';
    }
    // Un type de contenu fixé par un autre code est admis s'il ne s'agit que des articles.
    $pt = array_values(array_filter((array) $q->get('post_type')));
    if ($pt && $pt !== array('post')) { return 'type de contenu ' . implode(',', $pt); }
    if ($q->is_tax()) {
        foreach ((array) $q->tax_query->queries as $t) {
            if (is_array($t) && isset($t['taxonomy']) && $t['taxonomy'] !== 'language') {
                return 'flux de taxonomie ' . $t['taxonomy'];
            }
        }
    }
    $actif  = (string) get_option('cs_flux_une_actif', '0') === '1';
    $apercu = isset($_GET['cs_flux_une']) && $_GET['cs_flux_une'] === '1';
    return ($actif || $apercu) ? '' : 'inactif';
}
}

if (!function_exists('cs_flux_une_concerne')) {
function cs_flux_une_concerne($q) { return cs_flux_une_motif($q) === ''; }
}

if (!function_exists('cs_flux_une_ids')) {
function cs_flux_une_ids() {
    if (!function_exists('cs_home_build_allocation')) { return array(); }
    $plan = cs_home_build_allocation();
    $ids = isset($plan['ala-une']) ? array_map('intval', (array) $plan['ala-une']) : array();
    return array_values(array_filter($ids));
}
}

add_filter('the_posts', function ($posts, $q) {
    $apercu = isset($_GET['cs_flux_une']) && $_GET['cs_flux_une'] === '1';
    $motif = cs_flux_une_motif($q);
    if ($apercu && $q instanceof WP_Query && $q->is_main_query() && !headers_sent()) {
        header('X-CS-Flux-Une: ' . ($motif === '' ? 'actif' : 'ecarte: ' . $motif));
    }
    if ($motif !== '') { return $posts; }
    $ids = cs_flux_une_ids();
    if ($apercu && !headers_sent()) { header('X-CS-Flux-Une-Ids: ' . implode(',', $ids), false); }
    if (!$ids) { return $posts; }

    $deja = wp_list_pluck($posts, 'ID');
    $fiches = array();
    foreach ($ids as $id) {
        if (in_array($id, $deja, true)) { continue; }
        $p = get_post($id);
        if (!$p || $p->post_status !== 'publish' || $p->post_type !== 'tribe_events') { continue; }
        $depuis = (string) get_post_meta($id, 'as_flux_une_depuis', true);
        // En APERÇU, rien n'est écrit : la date d'entrée posée un jour d'essai serait
        // fausse le jour de l'activation. On date alors « maintenant », en mémoire.
        if ($depuis === '' && (string) get_option('cs_flux_une_actif', '0') === '1') {
            add_post_meta($id, 'as_flux_une_depuis', current_time('mysql', true), true);
        }
        $fiches[] = $p;
    }
    if (!$fiches) { return $posts; }

    $cle = function ($p) {
        if ($p->post_type === 'tribe_events') {
            $d = (string) get_post_meta($p->ID, 'as_flux_une_depuis', true);
            return $d !== '' ? $d : current_time('mysql', true);
        }
        return $p->post_date_gmt;
    };
    $tous = array_merge($posts, $fiches);
    usort($tous, function ($a, $b) use ($cle) { return strcmp($cle($b), $cle($a)); });
    $q->post_count = count($tous);
    return $tous;
}, 20, 2);

// La date affichée dans <pubDate> : `get_post_time` est ce que lit mysql2date/get_post_time
// dans le gabarit RSS2. On passe APRÈS The Events Calendar (priorité 10) pour rendre à la
// fiche sa date d'entrée dans la une au lieu de la date de l'événement.
add_filter('get_post_time', function ($time, $format, $gmt) {
    if (!is_feed() || !cs_flux_une_concerne($GLOBALS['wp_query'] ?? null)) { return $time; }
    $p = get_post();
    if (!$p || $p->post_type !== 'tribe_events') { return $time; }
    if (!in_array((int) $p->ID, cs_flux_une_ids(), true)) { return $time; }
    $d = (string) get_post_meta($p->ID, 'as_flux_une_depuis', true);
    $ts = $d !== '' ? strtotime($d . ' UTC') : time();   // aperçu : pas encore de date posée
    if ($format === 'U' || $format === 'G') { return $ts; }
    return $gmt ? gmdate($format, $ts) : wp_date($format, $ts);
}, 20, 3);
