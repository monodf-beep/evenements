<?php
/*
Plugin Name: Agenda Sabauda — Pas de bandeau Chrome pour un visiteur FR/IT
Description: Le site est bilingue NATIVEMENT (Polylang, sélecteur de langue,
  hreflang FR<->IT) : proposer en plus la traduction automatique de Chrome entre
  ces deux langues est redondant, pas une aide. Supprime UNIQUEMENT ce cas — un
  visiteur dont le navigateur est réglé en anglais, allemand, etc. continue de
  voir le bandeau Chrome normalement, aucune langue n'est bloquée pour lui.

  POURQUOI EN JAVASCRIPT ET PAS EN PHP (Accept-Language + notranslate côté
  serveur, l'approche naturelle) : le raisonnement tient sur le principe, pas sur
  un fait constaté aujourd'hui — CORRIGÉ le 2026-08-06 après vérification en
  production (Novamira) : « cs-cache-control-home.php » n'existe PAS sur le site
  réel (seul un fichier de test « ai-cache-control-test.php » traînait dans le
  bac à sable Novamira), aucun mu-plugin ne touche au cache, et l'accueil répond
  aujourd'hui `Cache-Control: no-cache, must-revalidate, max-age=0` — donc AUCUN
  cache actif ne menace une balise posée côté PHP en ce moment précis.
  Le choix du JavaScript reste néanmoins le bon : si un cache est réglé un jour
  (l'hébergement OVH le permet), une balise choisie selon l'Accept-Language DU
  PREMIER VISITEUR figerait la page pour tous les suivants, quelle que soit LEUR
  langue — un risque qui redeviendrait actif sans que personne ne fasse le lien
  avec ce fichier. navigator.language, lu dans le NAVIGATEUR après réception de
  la page, ne dépend d'aucun réglage de cache, présent ou futur : chaque visiteur
  reçoit sa propre décision, jamais celle d'un autre.

  `google: notranslate` (et non `translate="no"` sur <html>, équivalent mais
  moins largement supporté par les navigateurs non-Chrome) est la balise que
  Google Translate / le moteur de traduction intégré à Chrome respecte pour ne
  PAS proposer de traduire la page.

INSTALLATION : déposer dans wp-content/mu-plugins/. Rollback : supprimer le fichier.
*/

if (!defined('ABSPATH')) { exit; }

add_action('wp_head', function () {
    ?>
<script>
(function () {
  var lang = ((navigator.language || navigator.userLanguage || '') + '').slice(0, 2).toLowerCase();
  if (lang === 'fr' || lang === 'it') {
    var m = document.createElement('meta');
    m.name = 'google';
    m.content = 'notranslate';
    document.head.appendChild(m);
  }
})();
</script>
    <?php
}, 1); // priorité 1 : tôt dans <head>, avant que Chrome n'ait fini d'analyser la page.
