<?php
/*
Plugin Name: Agenda Sabauda — la liste d'un moment fort, en raccourci
Description: `[cs_moment_liste etiquette="…"]` pose, dans une page, la liste des fiches
  portant l'étiquette d'un événement-parapluie : les journées du patrimoine, Noël, un
  carnaval. C'est le corps de la page dédiée vers laquelle la strate de home renvoie.

  POURQUOI UN RACCOURCI ET PAS UNE PAGE-GABARIT. Le dépôt a déjà un gabarit de liste
  (`cs_render_agenda_list_page`, cs-agenda-list-shared.php), mais son routage vit dans
  un Code Snippet et il est bâti pour les fenêtres glissantes (aujourd'hui, ce week-end,
  cette semaine). Un moment fort n'est pas une fenêtre glissante : c'est une étiquette.
  Un raccourci se pose dans une page ordinaire, sans toucher au routage existant, et la
  page garde son texte éditorial au-dessus — ce qui est justement ce qui la rend
  indexable.

  CE QUI REND CETTE PAGE INDEXABLE, ET POURQUOI C'EST LE POINT. `cs-index-budget.php`
  sort de l'index les pages sans contenu propre. Une page qui ne serait QUE cette liste
  en ferait partie de fait : Google la lirait vide. Or elle est vide onze mois sur
  douze, puisque la liste ne montre que ce qui est à venir. C'est le texte au-dessus qui
  la fait exister hors saison, donc qui lui permet d'accumuler quoi que ce soit d'une
  édition à l'autre.

  D'OÙ LE COMPORTEMENT HORS SAISON : liste vide => une phrase qui dit que l'édition est
  passée et quand revient la suivante, jamais une page blanche ni un silence. Le texte
  de cette phrase se règle par attribut, parce qu'il est éditorial.

  GRAMMAIRE DES CARTES : celles du site, pas de nouvelles. Les classes `cs-card-*`
  portent déjà la vignette en 4/3, le sur-titre, le titre et la commune (relevé dans le
  HTML servi le 22/09). On les réutilise telles quelles ; seule la grille est à nous,
  et une grille n'est pas une grammaire de carte.

  Rollback : supprimer ce fichier. Le raccourci non interprété laisse son texte brut
  dans la page — donc retirer aussi la ligne `[cs_moment_liste …]` de la page.
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_moment_liste_fiches')) {
/**
 * Les fiches ENCORE DEVANT NOUS portant l'étiquette, dans la langue courante.
 *
 * La borne est `_EventEndDate >= aujourd'hui` et non `_EventStartDate` : une exposition
 * de mai à septembre compte tout l'été (règle 5 du CLAUDE.md). Pour un moment fort de
 * deux jours ça ne change rien ; pour Noël ou un festival d'été, si.
 */
function cs_moment_liste_fiches($etiquette, $lang, $max = 60) {
    $cle = 'cs_ml_' . md5($etiquette . '|' . $lang);
    $cache = get_transient($cle);
    if (is_array($cache)) { return $cache; }

    $q = new WP_Query(array(
        'post_type'           => 'tribe_events',
        'post_status'         => 'publish',
        'posts_per_page'      => $max,
        'ignore_sticky_posts' => true,
        'lang'                => $lang,
        'tax_query'           => array(array(
            'taxonomy' => 'post_tag', 'field' => 'slug', 'terms' => $etiquette,
        )),
        'meta_query'          => array('fin' => array(
            'key'     => '_EventEndDate',
            'value'   => current_time('Y-m-d') . ' 00:00:00',
            'compare' => '>=',
            'type'    => 'DATETIME',
        )),
        'orderby'             => array('fin' => 'ASC'),
    ));

    $out = array();
    foreach ($q->posts as $p) {
        $debut = get_post_meta($p->ID, '_EventStartDate', true);
        $out[] = array(
            'id'    => $p->ID,
            'titre' => get_the_title($p),
            'url'   => get_permalink($p),
            'image' => get_the_post_thumbnail_url($p, 'medium_large'),
            'jour'  => substr($debut, 0, 10),
            'lieu'  => get_post_meta($p->ID, 'as_lieu', true),
            'ville' => get_post_meta($p->ID, 'as_ville', true),
            'tarif' => get_post_meta($p->ID, 'as_gratuit', true) ? 'Gratuit' : '',
        );
    }
    wp_reset_postdata();
    set_transient($cle, $out, $out ? 15 * MINUTE_IN_SECONDS : 5 * MINUTE_IN_SECONDS);
    return $out;
}
}

if (!function_exists('cs_moment_liste_jour')) {
/** « Samedi 26 septembre » / « Sabato 26 settembre ». Tables en dur, comme ailleurs. */
function cs_moment_liste_jour($iso, $lang) {
    if (strlen($iso) !== 10) { return ''; }
    $ts = strtotime($iso);
    if (!$ts) { return ''; }
    $jfr = array('Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi');
    $jit = array('Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato');
    $mfr = array(1 => 'janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
                 'août', 'septembre', 'octobre', 'novembre', 'décembre');
    $mit = array(1 => 'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
                 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre');
    $j = $lang === 'it' ? $jit : $jfr;
    $m = $lang === 'it' ? $mit : $mfr;
    return $j[(int) date('w', $ts)] . ' ' . (int) date('j', $ts) . ' ' . $m[(int) date('n', $ts)];
}
}

if (!function_exists('cs_moment_liste_carte')) {
/** Une carte, dans la grammaire DU SITE (classes cs-card-*), pas une nouvelle. */
function cs_moment_liste_carte($f) {
    $ou = trim(($f['ville'] ? $f['ville'] : '') . ($f['ville'] && $f['lieu'] ? ' · ' : '') . $f['lieu']);
    $h  = '<article class="cs-ml__carte ala-une-full-card">';
    $h .= '<a class="cs-ml__lien" href="' . esc_url($f['url']) . '">';
    $h .= '<span class="cs-ml__img cs-card-thumb">';
    // Pas d'image : la case reste vide plutôt qu'un visuel inadapté (charte §9).
    $h .= $f['image'] ? '<img src="' . esc_url($f['image']) . '" alt="" loading="lazy">' : '';
    $h .= '</span>';
    if ($f['tarif']) {
        $h .= '<span class="cs-ml__meta cs-card-meta"><span class="cs-card-date">' . esc_html($f['tarif']) . '</span></span>';
    }
    $h .= '<span class="cs-ml__titre cs-card-title">' . esc_html($f['titre']) . '</span>';
    if ($ou) { $h .= '<span class="cs-ml__ou cs-card-commune">' . esc_html($ou) . '</span>'; }
    return $h . '</a></article>';
}
}

if (!function_exists('cs_moment_liste_css')) {
function cs_moment_liste_css() {
    return '<style id="cs-moment-liste">
.cs-ml{margin:26px 0 8px;font-family:\'Nunito Sans\',sans-serif}
.cs-ml *{box-sizing:border-box}
.cs-ml__jour{margin:26px 0 12px;padding-bottom:7px;border-bottom:1.5px solid #1D1D1B;
 font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:21px;letter-spacing:.01em}
.cs-ml__jour:first-child{margin-top:6px}
.cs-ml__grille{display:grid;grid-template-columns:1fr 1fr;gap:18px 14px}
.cs-ml__lien{display:block;text-decoration:none;color:#1D1D1B}
.cs-ml__img{display:block;overflow:hidden;background:#F1EADF;border-radius:3px;margin-bottom:8px}
.cs-ml__img img{width:100%;height:100%;object-fit:cover;display:block}
.cs-ml__meta{display:block;margin-bottom:2px}
.cs-ml__titre{display:block;font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-size:16px}
.cs-ml__lien:hover .cs-ml__titre{text-decoration:underline;text-underline-offset:3px}
.cs-ml__ou{display:block}
.cs-ml__total{margin:20px 0 0;font-size:12.5px;color:#6F6B62}
.cs-ml__vide{margin:18px 0;padding:16px 18px;border:1.5px solid #1D1D1B;border-radius:4px;background:#FBF7F0;
 transform:rotate(-.4deg);font-size:14px;line-height:1.55}
@media(min-width:900px){
 .cs-ml__grille{grid-template-columns:repeat(3,1fr);gap:26px 20px}
 .cs-ml__jour{font-size:25px;margin-top:34px}
 .cs-ml__titre{font-size:17.5px}
}
</style>';
}
}

/**
 * `[cs_moment_liste etiquette="…" vide="…" total="%d rendez-vous"]`
 *
 * `etiquette` : le SLUG du terme post_tag, dans la langue de la page. Il est posé par le
 * pipeline (config/moments_forts.json), jamais à la main.
 * `vide`      : la phrase à afficher hors saison. Éditoriale, donc réglable ici.
 * `total`     : le libellé du compte, avec %d. Vide = pas de compte affiché.
 */
add_shortcode('cs_moment_liste', function ($atts) {
    $a = shortcode_atts(array(
        'etiquette' => '',
        'vide'      => '',
        'total'     => '',
    ), $atts, 'cs_moment_liste');

    if (!$a['etiquette']) {
        return '<!-- cs-moment-liste : pas d\'étiquette déclarée -->';
    }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $fiches = cs_moment_liste_fiches($a['etiquette'], $lang);

    if (!$fiches) {
        // Le zéro dit d'où il vient, et la page reste lisible : elle est vide onze mois
        // sur douze, et c'est justement dans ces mois-là que Google la relit.
        $mot = $a['vide'] ? '<p class="cs-ml__vide">' . esc_html($a['vide']) . '</p>' : '';
        return cs_moment_liste_css() . '<div class="cs-ml">' . $mot
             . '<!-- cs-moment-liste : aucune fiche à venir pour « ' . esc_html($a['etiquette'])
             . ' » [' . esc_html($lang) . '] -->' . '</div>';
    }

    $h = cs_moment_liste_css() . '<div class="cs-ml">';
    $jour_courant = null;
    $ouvert = false;
    foreach ($fiches as $f) {
        if ($f['jour'] !== $jour_courant) {
            if ($ouvert) { $h .= '</div>'; }
            $jour_courant = $f['jour'];
            $h .= '<h2 class="cs-ml__jour">' . esc_html(cs_moment_liste_jour($f['jour'], $lang)) . '</h2>';
            $h .= '<div class="cs-ml__grille">';
            $ouvert = true;
        }
        $h .= cs_moment_liste_carte($f);
    }
    if ($ouvert) { $h .= '</div>'; }

    // Le compteur dit ce qu'il compte : les fiches DE L'AGENDA encore à venir, ce qui
    // n'est pas le nombre de rendez-vous du programme officiel. Deux compteurs qui
    // portent le même nom se contrediront un jour (règle 6).
    if ($a['total']) {
        $h .= '<p class="cs-ml__total">' . esc_html(sprintf($a['total'], count($fiches))) . '</p>';
    }
    return $h . '</div>';
});
