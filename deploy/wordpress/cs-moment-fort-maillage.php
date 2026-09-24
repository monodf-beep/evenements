<?php
/*
Plugin Name: Agenda Sabauda — maillage du moment fort (fiches, guides, pages territoire)
Description: Pendant la fenêtre d'un moment fort, relie ses fiches à leur guide, liste les fiches dans le guide, et pose la strate sur les pages territoire concernées.
Author: Cultura Sabauda
Version: 1.2

  D'OÙ ÇA VIENT — 24/09/2026 au soir. Franck : « il faut une vraie stratégie pour faire
  connaître la journée européenne du patrimoine en Piémont et Vallée d'Aoste ». Mesuré
  ce soir-là, avant d'écrire une ligne :
    - les quatre guides (Journées du patrimoine en Piémont, Plaisirs de Culture en Vallée
      d'Aoste, FR et IT) ne contenaient chacun que DEUX liens — la source officielle et la
      page du territoire — et AUCUN vers les fiches qu'ils décrivent ;
    - aucune des 131 fiches à venir du moment ne renvoyait vers son guide : un lecteur
      arrivé de Google sur Serralunga ne voyait jamais les trente autres ouvertures ;
    - la strate « moment fort » n'existait que sur l'accueil ; les pages Piémont et Vallée
      d'Aoste — celles des habitants — n'en disaient rien.

  CE QUE FAIT CE FICHIER, en trois points, TOUS À L'AFFICHAGE :
    1. en bas de chaque fiche du moment, un encadré vers le guide de son territoire ;
    2. dans chaque guide, la liste des fiches encore devant nous, jour par jour, avec leurs
       liens — calculée à chaque affichage, donc toujours à jour ;
    3. la strate du moment en tête des quatre pages territoire concernées.
  Rien n'est écrit en base ni dans le texte des fiches : le GEL (cs-gel-texte.php) n'est
  pas concerné, et aucune retouche humaine n'est écrasée.

  AUCUN SECOND CALCUL. Tout vient de cs-moment-fort.php : la fenêtre
  (`cs_moment_fort_actif`), les volets, leurs étiquettes et leurs guides
  (`cs_moments_forts`), les fiches (`cs_mf_evenements`), la strate (`cs_mf_html`).
  Deux détecteurs pour la même chose, un seul juste (journal du 08/09) : si la
  configuration du moment change, ces trois points suivent.

  EXTINCTION : automatique, avec la fenêtre du moment (`affiche_au`). Règle 3 : personne
  n'a à penser à le retirer. Rollback immédiat : supprimer ce fichier.
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_mfm_actif')) {
function cs_mfm_actif() {
    return function_exists('cs_moment_fort_actif') && function_exists('cs_mf_evenements')
        ? cs_moment_fort_actif() : null;
}
}

if (!function_exists('cs_mfm_lang')) {
function cs_mfm_lang($post_id = 0) {
    if ($post_id && function_exists('pll_get_post_language')) {
        $l = pll_get_post_language($post_id);
        if ($l) { return $l; }
    }
    return function_exists('pll_current_language') ? (pll_current_language() ?: 'fr') : 'fr';
}
}

if (!function_exists('cs_mfm_volet_de_fiche')) {
/** Le volet auquel appartient une fiche : son territoire ET l'étiquette du moment. */
function cs_mfm_volet_de_fiche($moment, $post_id, $lang) {
    $etiq = isset($moment['etiquette'][$lang]) ? array_filter((array) $moment['etiquette'][$lang]) : array();
    if ($etiq && !has_term($etiq, 'post_tag', $post_id)) { return null; }
    foreach ($moment['volets'] as $v) {
        $t = isset($v['terr'][$lang]) ? $v['terr'][$lang] : '';
        if ($t && has_term($t, 'territoire', $post_id)) { return $v; }
    }
    return null;
}
}

if (!function_exists('cs_mfm_volet_de_guide')) {
/** Le volet dont la page courante est le guide, en comparant les chemins. */
function cs_mfm_volet_de_guide($moment, $post_id, $lang) {
    $ici = untrailingslashit(wp_make_link_relative(get_permalink($post_id)));
    foreach ($moment['volets'] as $v) {
        $page = isset($v['page'][$lang]) ? $v['page'][$lang] : '';
        if ($page && untrailingslashit(wp_make_link_relative($page)) === $ici) { return $v; }
    }
    return null;
}
}

if (!function_exists('cs_mfm_cible')) {
/**
 * L'id de la page demandée si le contenu en cours de filtrage est bien le sien, sinon 0.
 *
 * PAS `in_the_loop()` NI `is_main_query()`. Première version déployée le 24/09 au soir :
 * rien ne s'affichait nulle part, ni encadré, ni programme, ni strate — et la logique,
 * rejouée côté serveur, était juste (volets et guides reconnus, filtres enregistrés). Ce
 * thème et The Events Calendar rendent le contenu HORS de la boucle principale : ces deux
 * conditions y sont toujours fausses. La strate de l'accueil, qui ne les emploie pas,
 * s'affichait. On compare donc l'objet demandé et le post courant, et chaque ajout n'est
 * posé qu'une fois par page (`$deja`) — un extrait ou un widget qui repasserait par
 * the_content ne le recevra pas une seconde fois.
 */
function cs_mfm_cible($cle) {
    static $deja = array();
    // APRÈS wp_head seulement : Yoast et les métadonnées de partage passent le contenu dans
    // the_content pendant l'en-tête ; sans cette garde, ce premier passage consommerait
    // l'unique pose autorisée et le corps de la page ne recevrait rien.
    if (is_admin() || is_feed() || !is_singular() || !did_action('wp_head')) { return 0; }
    $id = (int) get_queried_object_id();
    $courant = (int) get_the_ID();
    if (!$id || ($courant && $courant !== $id) || isset($deja[$cle . $id])) { return 0; }
    $deja[$cle . $id] = true;
    return $id;
}
}

if (!function_exists('cs_mfm_style')) {
function cs_mfm_style() {
    static $fait = false;
    if ($fait) { return ''; }
    $fait = true;
    return '<style id="cs-mfm">'
        . '.cs-mfm{margin:32px 0 8px;padding:18px 22px;background:#18365E;color:#F7F1E8;border-radius:4px}'
        . '.cs-mfm__k{font-size:.78em;letter-spacing:.08em;text-transform:uppercase;color:#F0916F;margin:0 0 4px}'
        . '.cs-mfm__t{font-weight:700;margin:0 0 6px;font-size:1.05em}'
        . '.cs-mfm p{margin:0 0 10px;color:#D6CEC0}'
        . '.cs-mfm a{color:#F7F1E8;font-weight:700;text-decoration:underline;text-underline-offset:3px}'
        . '.cs-mfm-prog{margin:36px 0 12px}'
        . '.cs-mfm-prog h3{margin:22px 0 8px}'
        . '.cs-mfm-prog ul{margin:0 0 8px 1.1em;padding:0}'
        . '.cs-mfm-prog li{margin:0 0 6px}'
        . '.cs-mfm-prog .cs-mfm-ou{color:#6F6B62;font-size:.92em}'
        . '</style>';
}
}

/* 1. En bas de chaque fiche du moment : l'encadré vers son guide.
 *
 * PAS PAR the_content. La fiche est rendue par le snippet 56 (« Gabarit Fiche Événement »)
 * avec `wpautop(get_the_content())` : le filtre the_content n'y passe jamais. Mesuré le
 * 24/09 — guides et pages territoire recevaient leurs ajouts, les fiches rien. Le snippet 56
 * a reçu à cette occasion UN point d'accroche générique, juste après le corps :
 * `do_action('cs_fiche_apres_corps', $event_id)`. C'est lui qu'on utilise. */
add_action('cs_fiche_apres_corps', function ($event_id) {
    echo cs_mfm_encadre_fiche((int) $event_id);
});

if (!function_exists('cs_mfm_encadre_fiche')) {
function cs_mfm_encadre_fiche($id) {
    $content = '';
    $moment = cs_mfm_actif();
    if (!$moment || !$id) { return $content; }
    $lang = cs_mfm_lang($id);
    $v = cs_mfm_volet_de_fiche($moment, $id, $lang);
    if (!$v || empty($v['page'][$lang]) || empty($v['lien'][$lang])) { return $content; }
    if (function_exists('cs_mf_page_existe') && !cs_mf_page_existe($v['page'][$lang])) { return $content; }
    // Textes REPRIS de la configuration du moment (déjà relus pour la strate de l'accueil) :
    // aucun texte éditorial nouveau n'est introduit ici.
    $k = isset($moment['chez_soi']['kicker'][$lang]) ? $moment['chez_soi']['kicker'][$lang] : '';
    $bloc = '<aside class="cs-mfm" data-moment="' . esc_attr($moment['slug']) . '">'
          . ($k ? '<p class="cs-mfm__k">' . esc_html($k) . '</p>' : '')
          . '<p class="cs-mfm__t">' . esc_html($v['titre'][$lang]) . ' · ' . esc_html($v['quand'][$lang]) . '</p>'
          . (!empty($v['phrase'][$lang]) ? '<p>' . esc_html($v['phrase'][$lang]) . '</p>' : '')
          . '<a href="' . esc_url($v['page'][$lang]) . '">' . esc_html($v['lien'][$lang]) . ' →</a>'
          . '</aside>';
    return $content . cs_mfm_style() . $bloc;
}
}

/* 2. Dans chaque guide : la liste des fiches encore devant nous, jour par jour. */
add_filter('the_content', function ($content) {
    if (!is_singular(array('post', 'page'))) { return $content; }
    $moment = cs_mfm_actif();
    if (!$moment) { return $content; }
    $id = (int) get_queried_object_id();
    $v = $id ? cs_mfm_volet_de_guide($moment, $id, cs_mfm_lang($id)) : null;
    if (!$v || !cs_mfm_cible('guide')) { return $content; }
    $lang = cs_mfm_lang($id);
    if (!$v) { return $content; }
    $data = cs_mf_evenements($moment, $v, $lang);
    $aujourdhui = current_time('Y-m-d');
    $par_jour = array();
    foreach ($data['lignes'] as $l) {
        // Règle 5 : seulement ce qui est encore devant nous. On lit la date de FIN de la
        // fiche, pas le jour de début : une exposition commencée lundi court encore.
        $pid = url_to_postid($l['url']);
        $fin = $pid ? substr((string) get_post_meta($pid, '_EventEndDate', true), 0, 10) : $l['jour'];
        if ($fin && $fin < $aujourdhui) { continue; }
        $jour = max($l['jour'], $aujourdhui);
        $par_jour[$jour][] = $l;
    }
    if (!$par_jour) { return $content; }
    ksort($par_jour);
    $titre = ($lang === 'it') ? 'Il programma, giorno per giorno' : 'Le programme, jour par jour';
    $h = '<section class="cs-mfm-prog" data-moment="' . esc_attr($moment['slug']) . '">'
       . '<h2>' . esc_html($titre) . '</h2>';
    foreach ($par_jour as $jour => $lignes) {
        $h .= '<h3>' . esc_html(ucfirst(date_i18n('l j F', strtotime($jour)))) . '</h3><ul>';
        foreach ($lignes as $l) {
            $h .= '<li><a href="' . esc_url($l['url']) . '">' . esc_html(wp_strip_all_tags($l['titre'])) . '</a>'
                . ($l['ou'] ? ' <span class="cs-mfm-ou">— ' . esc_html($l['ou']) . '</span>' : '') . '</li>';
        }
        $h .= '</ul>';
    }
    $h .= '</section>';
    return $content . cs_mfm_style() . $h;
}, 28);

/* 3. En tête des pages territoire du moment : la strate de l'accueil, en mode programme. */
add_filter('the_content', function ($content) {
    if (!is_page()) { return $content; }
    // Pages hub des territoires (cf. snippet 15, carte de redirection des termes).
    $hubs = array(2859 => 'piemont', 2860 => 'piemont', 2861 => 'vda', 2862 => 'vda');
    $id = (int) get_queried_object_id();
    if (!isset($hubs[$id]) || !cs_mfm_cible('hub')) { return $content; }
    $moment = cs_mfm_actif();
    if (!$moment || !function_exists('cs_mf_html') || !function_exists('cs_mf_css')) { return $content; }
    $strate = cs_mf_html($moment, cs_mfm_lang($id), $hubs[$id]);
    if (strpos($strate, '<section') !== 0) { return $strate . $content; }   // commentaire de diagnostic
    return cs_mf_css($moment) . $strate . $content;
}, 23);
