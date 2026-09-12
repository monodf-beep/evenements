<?php
/*
Plugin Name: CS — fiches terminées hors index et hors sitemap
Description: Une fiche événement dont la date de FIN est révolue reste publiée et
  accessible par son adresse (The Events Calendar la retire seulement de ses listes),
  mais elle sort de l'index Google (noindex, follow) et du sitemap Yoast. Rien n'est
  retiré du site, rien n'est écrit en base : tout se lit sur _EventEndDate au rendu,
  donc une date corrigée vers l'avenir rouvre la fiche toute seule.
Author: Cultura Sabauda
Version: 1.0

  D'OÙ ÇA VIENT — 2026-09-08, audit SEO. Le sitemap portait 186 URLs d'événements ;
  sur 156 mesurées, 90 étaient terminées, 64 à venir. La chaîne hebdomadaire ne
  pouvait pas les toucher : cleanup_as_dupes --past refuse par construction un post
  publié, et cleanup_as_trash --passes n'est branché nulle part. « La Farandole »
  (12-16 août) a encore reçu 51 impressions après sa fin, pour zéro clic : Google
  montrait une page dont plus personne ne voulait.

  POURQUOI NOINDEX ET PAS LA CORBEILLE : la corbeille rend 404, perd les liens
  entrants, et fait du bruit dans la Search Console ; ici la page vit, ses liens
  sortants restent suivis, et le dispositif se défait en supprimant ce fichier.

  INSTALLATION : wp-content/mu-plugins/cs-passe-noindex.php (must-use, actif seul).
  Même dispositif que cs-completude.php § 4, y compris la balise écrite à la main
  dans wp_head : constaté le 2026-08-08, Yoast n'émet AUCUNE balise robots sur ce
  site, les filtres wpseo_robots* n'ont donc rien à intercepter.

  CONTRÔLE : GET /evenement/<slug-terminé>/ doit contenir
  <meta name="robots" content="noindex, follow" data-cs="cs-passe-noindex">,
  et /tribe_events-sitemap.xml ne doit plus lister cette adresse.
*/

if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_passe_est_terminee')) {
/**
 * Vrai si l'événement est TERMINÉ : sa date de fin (heure locale du site) est
 * strictement antérieure à maintenant. Sans date de fin, on ne conclut rien
 * (règle 5 : une donnée manquante n'est pas un événement passé).
 */
function cs_passe_est_terminee($id) {
    $fin = (string) get_post_meta($id, '_EventEndDate', true);
    if ($fin === '') { return false; }
    return $fin < current_time('Y-m-d H:i:s');
}
}

if (!function_exists('cs_passe_singulier_terminee')) {
function cs_passe_singulier_terminee() {
    if (is_admin() || !is_singular('tribe_events')) { return false; }
    return cs_passe_est_terminee(get_queried_object_id());
}
}

add_filter('wpseo_robots_array', function ($robots) {
    if (!cs_passe_singulier_terminee()) { return $robots; }
    $robots['index'] = 'noindex';
    return $robots;
}, 20);

add_filter('wpseo_robots', function ($chaine) {
    if (!cs_passe_singulier_terminee()) { return $chaine; }
    return 'noindex, follow';
}, 20);

add_filter('wp_robots', function ($robots) {
    if (!cs_passe_singulier_terminee()) { return $robots; }
    $robots['noindex'] = true;
    $robots['follow']  = true;
    unset($robots['index']);
    return $robots;
}, 20);

add_action('wp_head', function () {
    if (!cs_passe_singulier_terminee()) { return; }
    echo '<meta name="robots" content="noindex, follow" data-cs="cs-passe-noindex">' . "\n";
}, 1);

// Sitemap : la liste des terminés est calculée une fois par heure, pas à chaque
// requête. Une heure de retard sur une fin d'événement ne change rien pour Google.
add_filter('wpseo_exclude_from_sitemap_by_post_ids', function ($ids) {
    $termines = get_transient('cs_passe_noindex_ids');
    if ($termines === false) {
        global $wpdb;
        $termines = $wpdb->get_col($wpdb->prepare(
            "SELECT p.ID FROM {$wpdb->posts} p
             JOIN {$wpdb->postmeta} m ON m.post_id = p.ID AND m.meta_key = '_EventEndDate'
             WHERE p.post_type = 'tribe_events' AND p.post_status = 'publish'
               AND m.meta_value <> '' AND m.meta_value < %s",
            current_time('Y-m-d H:i:s')
        ));
        $termines = array_map('intval', (array) $termines);
        set_transient('cs_passe_noindex_ids', $termines, HOUR_IN_SECONDS);
    }
    return array_values(array_unique(array_merge((array) $ids, $termines)));
});
