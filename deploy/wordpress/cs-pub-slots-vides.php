<?php
/*
Plugin Name: Agenda Sabauda — Masquage des encarts publicitaires VIDES
Description: Demande de Franck 2026-07-20 ("supprimer les elements publicite") : les
  encarts "Publicite"/"Pubblicita" de la home affichaient de grands cadres vides quand
  Ad Inserter ne sert rien. Plutot que de SUPPRIMER les blocs du post_content (ils
  portent les shortcodes [adinserter block=N], emplacements de la future regie --
  chantier en cours dans une session parallele), ce filtre the_content (priorite 25,
  APRES l'execution des shortcodes en prio 11) retire du HTML rendu tout encart dont
  la zone interieure est restee vide. Des qu'une pub est reellement servie, la zone
  n'est plus vide et l'encart reapparait automatiquement -- zero maintenance.

  ⚠️ Recupere depuis wp-content/mu-plugins/ en production le 2026-08-04 : ce fichier
  existait deja en LIVE (cree le 2026-07-20), jamais commite ici auparavant. Meme
  derive non versionnee que cs-regie-serve.php (cf. docs/REGIE_MISE_EN_PLACE_SOCLE.md).

  Rollback : supprimer ce fichier (les cadres vides reapparaissent).
*/
if (!defined('ABSPATH')) { exit; }

add_filter('the_content', function ($content) {
    if (strpos($content, 'adsbygoogle') === false && stripos($content, 'publicit') === false) {
        return $content;
    }

    // Encart "inline" mobile (wrapper padding + boite bordee + label + zone vide).
    $pattern_a = '#<div style="padding:0 20px 4px">\s*<div style="border:1px solid \#E3DCCE;background:\#fff">\s*<div style="[^"]*">(?:Publicité|Pubblicità)</div>\s*<div style="[^"]*">\s*</div>\s*</div>\s*</div>#u';
    // Encart desktop "sous carrousel" / "sous tuiles", ordre EXACT margin-top d'abord.
    // Garde pour compat -- voir pattern_c : la home reelle ecrit border/background
    // AVANT margin (ou "margin:16px 0" au lieu de "margin-top:Npx"), donc pattern_b
    // ne matchait plus rien -- c'etait la cause des cadres vides encore visibles
    // (constat 2026-08-04, Franck : "tu n'as pas enleve les fausses pub").
    $pattern_b = '#<div style="margin-top:\d+px;border:1px solid \#E3DCCE;background:\#fff">\s*<div style="[^"]*">(?:Publicité|Pubblicità)</div>\s*<div style="[^"]*">\s*</div>\s*</div>#u';
    // Encart desktop "En evidence" / "agenda a venir" -- ORDRE LIBRE des proprietes
    // CSS et n'importe quelle valeur de margin. Ajoute 2026-08-04.
    $pattern_c = '#<div style="[^"]*border:1px solid \#E3DCCE;background:\#fff[^"]*">\s*<div style="[^"]*">(?:Publicité|Pubblicità)</div>\s*<div style="[^"]*">\s*</div>\s*</div>#u';

    $content = preg_replace($pattern_a, '', $content);
    $content = preg_replace($pattern_b, '', $content);
    $content = preg_replace($pattern_c, '', $content);

    return $content;
}, 25);
