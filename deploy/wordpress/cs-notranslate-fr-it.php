<?php
/*
Plugin Name: Agenda Sabauda — Pas de bandeau Chrome pour un visiteur FR/IT
Description: Le site est bilingue NATIVEMENT (Polylang, sélecteur de langue,
  hreflang FR<->IT) : proposer en plus la traduction automatique de Chrome entre
  ces deux langues est redondant, pas une aide. Supprime UNIQUEMENT ce cas — un
  visiteur dont le navigateur est réglé en anglais, allemand, etc. continue de
  voir le bandeau Chrome normalement, aucune langue n'est bloquée pour lui.

  POURQUOI EN JAVASCRIPT ET PAS EN PHP (Accept-Language + notranslate côté
  serveur, l'approche naturelle) : un cache HTTP tourne devant tout le site
  (cs-cache-control-home.php le documente pour la home, mais le cache OVH est
  une couche générale) — une balise choisie selon l'en-tête Accept-Language DU
  PREMIER VISITEUR figerait cette même page pour tous les suivants, quelle que
  soit LEUR langue. lit navigator.language dans le NAVIGATEUR, après réception
  de la page (donc quel que soit l'état du cache) : chaque visiteur reçoit sa
  propre décision, jamais celle d'un autre.

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
