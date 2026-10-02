<?php
/*
Plugin Name: Agenda Sabauda — Éditeur parent dans le schema Organization
Description: Déclare Cultura Sabauda comme organisation mère d'Agenda Sabauda dans le
  nœud Organization que Yoast émet sur toutes les pages.
Author: Cultura Sabauda
Version: 1.0

  POURQUOI (2026-09-28) : Franck ne sortait pas en tête sur la recherche « agenda
  sabauda ». Google la lisait comme « l'agenda de la Galleria Sabauda » (Musei Reali,
  Turin), et rien sur le site ne disait qu'Agenda Sabauda est un éditeur : Yoast avait
  « Organisation » coché, mais le nom et le logo étaient vides, donc aucun nœud
  Organization n'était émis. Ces deux champs sont remplis ce jour-là dans les réglages
  Yoast, avec le profil Instagram en sameAs. Yoast n'a pas de champ pour l'organisation
  mère : ce filtre l'ajoute. Arbitrage de Franck, même jour : éditeur parent = Cultura
  Sabauda (cf. docs/REGLES_SEO_GEO_AEO_AGENDA_SABAUDO.md § 4).

  Un fichier séparé plutôt qu'une retouche du snippet « Assainissement schema Event »
  (Code Snippets n°63) : la version en ligne de celui-ci diffère de
  deploy/wordpress/cs-schema-fix.php (7 341 octets contre ~4 000), donc la patcher
  depuis le dépôt aurait été une régression.

  Retrait : supprimer wp-content/mu-plugins/cs-schema-editeur-parent.php. Rien en base.
*/

if (!defined('ABSPATH')) { exit; }

add_filter('wpseo_schema_organization', function ($data) {
    if (!is_array($data) || !empty($data['parentOrganization'])) { return $data; }
    $data['parentOrganization'] = array(
        '@type' => 'Organization',
        'name'  => 'Cultura Sabauda',
        'url'   => 'https://culturasabauda.eu/',
    );
    return $data;
});
