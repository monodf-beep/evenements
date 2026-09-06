<?php
/*
Plugin Name: Agenda Sabauda -- Redirections "Ce week-end en X" (legacy) vers les hubs
Description: 2026-07-24 (Franck). Les 8 pages "Ce week-end en X"/"Cosa fare X questo
  weekend" (IDs 1840-1847) sont un ancien systeme, vides (0 contenu), superseed par le
  nouveau systeme de hubs territoire (2857-2888). On les garde (slugs renommes selon la
  convention canonique du document REGLES-HOMEPAGES.md) mais on redirige 301 vers leur
  equivalent reel dans le nouveau systeme, pour ne perdre ni SEO ni liens externes/
  favoris eventuels vers les anciennes URLs.

  Rollback : supprimer ce fichier (les 8 pages redeviendraient vides et visibles).
*/
if (!defined('ABSPATH')) { exit; }

add_action('template_redirect', function () {
    $map = array(
        1840 => 2867, // Ce week-end en Savoie -> Que faire en Savoie ce week-end ?
        1841 => 2868, // Cosa fare in Savoia questo weekend? -> idem IT
        1842 => 2873, // Ce week-end en Piemont -> Que faire dans le Piemont ce week-end ?
        1843 => 2874,
        1844 => 2879, // Ce week-end en Vallee d'Aoste -> ...
        1845 => 2880,
        1846 => 2885, // Ce week-end dans le Comte de Nice -> ...
        1847 => 2886,
    );
    $current = get_queried_object_id();
    if (!isset($map[$current]) || !is_page($current)) {
        return;
    }
    $target = get_permalink($map[$current]);
    if ($target) {
        wp_redirect($target, 301);
        exit;
    }
}, 5);