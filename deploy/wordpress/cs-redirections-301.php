<?php
/*
Plugin Name: Agenda Sabauda - Redirections 301 (slugs territoire + selections)
Description: Redirige les anciennes URL de territoire vers les nouveaux slugs (savoie,
  savoia, comte-de-nice, contea-di-nizza). Demande Franck 2026-07-22. Rollback: supprimer.
  2026-09-12 : ajoute les coquilles du type « Selections » vers leur vraie page.
*/
if (!defined('ABSPATH')) { exit; }

add_action('template_redirect', function () {
    $uri = isset($_SERVER['REQUEST_URI']) ? $_SERVER['REQUEST_URI'] : '';
    $path = parse_url($uri, PHP_URL_PATH);
    if (!$path) { return; }
    $path = '/' . trim($path, '/') . '/';
    $map = array(
        '/territoire/savoie-haute-savoie/'     => '/territoire/savoie/',
        '/it/territoire/savoia-alta-savoia/'   => '/it/territoire/savoia/',
        '/territoire/nice-alpes-maritimes/'    => '/territoire/comte-de-nice/',
        '/it/territoire/nizza-alpi-marittime/' => '/it/territoire/contea-di-nizza/',

        // LES COQUILLES DU TYPE « SELECTIONS » (2026-09-12, Franck : « /selections/
        // ce-week-end/ devrait laisser la place a /ce-week-end/ »). Le carousel de la
        // home lie cinq cartes vers ce type de contenu ; or MESURE faite ce jour-la :
        // les onze posts « selection » ont un contenu VIDE, et la page rendue liste 8
        // evenements generiques — les MEMES sur les trois pages testees — quand la vraie
        // page en liste 47. Les deux URL portent le meme titre, aucune n'est en noindex,
        // et chacune se declare canonique d'elle-meme : doublon pour le lecteur comme
        // pour Google.
        //
        // Seules les paires VERIFIEES sont ici : une coquille dont la page canonique
        // existe, repond 200, et porte le meme sujet. Les sept autres « selections »
        // (Les nouveautes, Ca vaut le deplacement, Quelle sagre ce mois, Novita, Vale il
        // viaggio, Cuneo., Quale sagra questo mese) n'ont AUCUNE page equivalente : les
        // rediriger au jugé enverrait le lecteur ailleurs que là où la carte promet de
        // l'emmener. Elles attendent l'arbitrage de Franck — creer la page, ou retirer
        // la carte du carousel.
        '/selections/ce-week-end/'                    => '/ce-week-end/',
        '/it/selections/questo-weekend/'              => '/it/questo-weekend/',
        '/selections/que-faire-a-annecy-ce-week-end/' => '/que-faire-a-annecy/ce-week-end/',
        '/it/selections/torino/'                      => '/it/cosa-fare-a-torino/',
    );
    // GARDE-FOU : jamais de redirection vers soi-meme (boucle infinie, site injoignable).
    // Le cout d'une erreur ici est le meme que celui du mu-plugin casse d'aout : tout le
    // site, y compris la porte qui permettrait de le reparer.
    if (isset($map[$path]) && $map[$path] === $path) { return; }
    if (!isset($map[$path])) { return; }
    $base   = home_url('/');
    $scheme = parse_url($base, PHP_URL_SCHEME);
    $host   = parse_url($base, PHP_URL_HOST);
    if (!$scheme) { $scheme = is_ssl() ? 'https' : 'http'; }
    $qs   = parse_url($uri, PHP_URL_QUERY);
    $dest = $scheme . '://' . $host . $map[$path] . ($qs ? '?' . $qs : '');
    wp_redirect($dest, 301);
    exit;
}, 0);