<?php
/*
Plugin Name: Agenda Sabauda - Redirections 301 (slugs territoire)
Description: Redirige les anciennes URL de territoire vers les nouveaux slugs (savoie,
  savoia, comte-de-nice, contea-di-nizza). Demande Franck 2026-07-22. Rollback: supprimer.
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
    );
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