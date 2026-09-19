<?php
/*
Plugin Name: Agenda Sabauda — Sert /ads.txt (AdSense)
Description: Répond à https://agendasabauda.eu/ads.txt avec la ligne d'autorisation
  AdSense, sans avoir besoin de déposer un fichier par FTP. Google exige ce fichier
  pour diffuser les annonces (« ads.txt introuvable » = blocage). Ne dépend d'aucune
  donnée dynamique : une seule ligne d'éditeur, en texte brut.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION :
   A) Code Snippets : coller SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-ads-txt.php.

  Alternative (sans WordPress) : déposer par FTP un fichier « ads.txt » à la racine
  du site (www/ads.txt) contenant exactement la ligne CS_ADS_TXT_LINE ci-dessous.
*/

if (!defined('ABSPATH')) { exit; }

// La ligne d'autorisation AdSense (ID éditeur pub-4040905402577097).
if (!defined('CS_ADS_TXT_LINE')) {
    define('CS_ADS_TXT_LINE', 'google.com, pub-4040905402577097, DIRECT, f08c47fec0942fa0');
}

add_action('init', function () {
    $uri = isset($_SERVER['REQUEST_URI'])
        ? parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) : '';
    if (rtrim((string) $uri, '/') === '/ads.txt') {
        header('Content-Type: text/plain; charset=utf-8');
        header('X-Robots-Tag: noindex');
        echo CS_ADS_TXT_LINE . "\n";
        exit;
    }
}, 0);
