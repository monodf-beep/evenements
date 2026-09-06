<?php
/*
Plugin Name: Agenda Sabauda — Pas de bandeau Chrome pour un visiteur FR/IT
Description: Le site est bilingue NATIVEMENT (Polylang, sélecteur de langue,
  hreflang FR<->IT) : proposer en plus la traduction automatique de Chrome entre
  ces deux langues est redondant, pas une aide. Supprime UNIQUEMENT ce cas — un
  visiteur dont le navigateur est réglé en anglais, allemand, etc. continue de
  voir le bandeau Chrome normalement, aucune langue n'est bloquée pour lui.

  POURQUOI EN JAVASCRIPT ET PAS EN PHP (Accept-Language + notranslate côté
  serveur, l'approche naturelle) : une balise choisie d'après l'en-tête
  Accept-Language DU PREMIER VISITEUR serait figée par n'importe quelle couche
  de cache HTTP placée devant le site, puis servie à tous les suivants quelle
  que soit LEUR langue. Le JS, lui, lit navigator.language dans le NAVIGATEUR,
  après réception de la page : chaque visiteur reçoit sa propre décision,
  jamais celle d'un autre, quel que soit l'état du cache.

  ⚠ÉTAT MESURÉ LE 2026-08-06, à relire avant de conclure quoi que ce soit : la
  home est servie en `Cache-Control: no-cache, must-revalidate, max-age=0` et
  AUCUN mu-plugin ne touche au cache. Le risque ci-dessus n'est donc pas actif
  aujourd'hui ; il le redeviendrait au premier réglage de cache, sans que
  personne ne fasse le lien. La version précédente de ce commentaire invoquait
  un fichier `cs-cache-control-home.php` QUI N'EXISTE PAS dans mu-plugins/ —
  une justification invisible ne se vérifie jamais et finit par être crue.

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