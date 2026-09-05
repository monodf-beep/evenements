<?php
/*
Plugin Name: Agenda Sabauda — Cache-Control page d'accueil
Description: Le cache HTTP OVH devant agendasabauda.eu ignore les paramètres d'URL
  (`?nocache=1` sans effet, vérifié empiriquement le 2026-07-18) mais respecte les
  en-têtes Cache-Control envoyés par l'origine. Plafonne la fraîcheur de la home à
  5 minutes après toute modification d'un bloc Ad Inserter (ex. socle régie pub),
  sans désactiver le cache entièrement (perf préservée sur la page la plus visitée).

  Historique : un premier essai en no-store/no-cache permanent a confirmé le
  diagnostic (le cache OVH a bien laissé passer une version fraîche), mais a été
  remplacé par ce max-age=300 pour ne pas perdre le bénéfice du cache en continu.

INSTALLATION : déposer dans wp-content/mu-plugins/. Rollback : supprimer.
*/
if (!defined('ABSPATH')) { exit; }

add_action('send_headers', function () {
    if (is_front_page()) {
        header('Cache-Control: public, max-age=300, s-maxage=300');
        header_remove('Pragma');
        header('X-AI-Cache-Test: max-age-300-applied');
    }
});
