<?php
/*
Plugin Name: Agenda Sabauda — URLs jolies pour le filtre territoire
Description: Demande Franck 2026-07-23 : l'URL de filtre territoire de la home
  (/?as_territoire=savoie) est jugee "un peu bizarre". Ce fichier ajoute des
  URLs propres qui redirigent en interne vers le mecanisme EXISTANT (inchange,
  cf. cs-home-territoire-filtre.php / cs-territoire-persistant.php) :

    /explore/<slug-fr>/          -> home FR (928) filtree sur ce territoire
    /it/scopri/<slug-it>/        -> home IT (1717) filtree sur ce territoire
    /choisir/<slug-fr>/          -> interstitiel de choix de langue (Piemont/VdA)

  Aucune des logiques de filtrage/cookie/traduction existantes n'est modifiee :
  ce fichier se contente d'injecter $_GET['as_territoire'] ou
  $_GET['choix_territoire'] tres tot (hook 'parse_request', avant TOUT le
  reste), pour que le code existant continue de fonctionner sans le savoir.
  Les anciennes URLs ?as_territoire=/?choix_territoire= continuent de marcher
  (rien n'est retire), donc aucun lien externe existant ne casse.

  Rollback : supprimer ce fichier (les regles orphelines sont juste ignorees).
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_jolies_urls_slugs')) {
    function cs_jolies_urls_slugs() {
        return array(
            'savoie'          => 'savoie',
            'piemont'         => 'piemont',
            'vallee-d-aoste'  => 'vallee-d-aoste',
            'comte-de-nice'   => 'comte-de-nice',
            'tous'            => 'tous',
            'savoia'          => 'savoia',
            'piemonte'        => 'piemonte',
            'valle-d-aosta'   => 'valle-d-aosta',
            'contea-di-nizza' => 'contea-di-nizza',
            'tutti'           => 'tutti',
        );
    }
}

add_action('init', function () {
    add_rewrite_rule('^explore/([^/]+)/?$', 'index.php?page_id=928&as_home_territoire=$matches[1]', 'top');
    add_rewrite_rule('^it/scopri/([^/]+)/?$', 'index.php?page_id=1717&as_home_territoire=$matches[1]', 'top');
    add_rewrite_rule('^choisir/([^/]+)/?$', 'index.php?page_id=928&as_home_choix=$matches[1]', 'top');

    // 2026-08-06 (Franck) : URLs racine dediees a la vue "tous les territoires",
    // plus courtes/memorables que /explore/tous/. Meme mecanisme (injection de
    // $_GET['as_home_territoire'] avant tout le reste), rien d'autre ne change.
    add_rewrite_rule('^espace-sabaudo/?$', 'index.php?page_id=928&as_home_territoire=tous', 'top');
    add_rewrite_rule('^it/spazio-sabaudo/?$', 'index.php?page_id=1717&as_home_territoire=tutti', 'top');

    if (!get_option('cs_jolies_urls_flushed')) {
        flush_rewrite_rules();
        update_option('cs_jolies_urls_flushed', 1, false);
    }
});

add_filter('query_vars', function ($vars) {
    $vars[] = 'as_home_territoire';
    $vars[] = 'as_home_choix';
    return $vars;
});

add_action('parse_request', function ($wp) {
    $slugs = cs_jolies_urls_slugs();

    if (!empty($wp->query_vars['as_home_territoire'])) {
        $slug = sanitize_title($wp->query_vars['as_home_territoire']);
        if (isset($slugs[$slug])) {
            $_GET['as_territoire'] = $slug;
        }
    }

    if (!empty($wp->query_vars['as_home_choix'])) {
        $slug = sanitize_title($wp->query_vars['as_home_choix']);
        if (isset($slugs[$slug])) {
            $_GET['choix_territoire'] = $slug;
        }
    }
});

// WordPress redirige canoniquement /explore/x/ et /it/scopri/x/ vers / (la home
// statique, page_on_front) car il ne connait pas nos query vars personnalisees.
// Le filtre 'redirect_canonical' ne suffit pas pour ce cas precis (front page) --
// on retire carrement l'action coeur sur 'wp', avant que 'template_redirect' ne
// l'execute, uniquement pour ces routes precises.
add_action('wp', function () {
    if (get_query_var('as_home_territoire') || get_query_var('as_home_choix')) {
        remove_action('template_redirect', 'redirect_canonical');
    }
}, 1);
