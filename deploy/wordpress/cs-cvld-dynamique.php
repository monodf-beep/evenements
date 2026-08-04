<?php
/**
 * "Ca vaut le deplacement" -- selection par QUOTA DE TERRITOIRE.
 *
 * 2026-08-02 (Franck). Avant : la section tirait les 2 evenements les mieux notes
 * parmi DEUX territoires figes en dur (query builder 22 = Piemont+Vallee d Aoste,
 * 23 = Savoia+Contea di Nizza), logique "autre versant" de la frontiere. Turin
 * produisant beaucoup plus d evenements bien notes, le classement par score seul
 * renvoyait en pratique DEUX FOIS LE PIEMONT : la section promettait les autres
 * territoires et n en montrait qu un.
 *
 * Maintenant : un evenement GARANTI par territoire, et les territoires eligibles
 * sont tous ceux qui ne sont pas celui affiche (filtre actif ou page territoire).
 * Sans filtre, les quatre sont eligibles et la rangee montre les quatre.
 * Avec un filtre, il en reste trois et la 4e case devient l appel a action.
 *
 * Repli obligatoire : un territoire peut n avoir aucun evenement eligible (la
 * Vallee d Aoste produit peu). Sans second passage, la rangee se retrouverait avec
 * un trou. On complete alors avec les meilleurs scores restants.
 */
if (!function_exists('cs_cvld_pick_one')) {
function cs_cvld_pick_one($term_id, $lang, $exclude) {
    $q = new WP_Query(array(
        'post_type' => 'tribe_events', 'post_status' => 'publish',
        'fields' => 'ids', 'lang' => $lang, 'no_found_rows' => true,
        'post__not_in' => !empty($exclude) ? $exclude : array(0),
        'tax_query' => array(array('taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $term_id)),
        'meta_query' => array(
            'relation' => 'AND',
            array('key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME'),
            array('relation' => 'OR',
                array('key' => 'as_home_override', 'compare' => 'NOT EXISTS'),
                array('key' => 'as_home_override', 'value' => 'excluded', 'compare' => '!=')),
        ),
        'posts_per_page' => 60,
    ));
    /* 2026-08-03 (Franck : « au diapason n a pas une note haute »).
       TROIS defauts cumules, mesures avant correction :
       1. Le tri ne s appliquait PAS. La requete demandait meta_value_num sur
          as_score, elle renvoyait 4, 4, 5, 6, 2, 2, 7, 3 -- soit l ordre des
          identifiants. The Events Calendar reordonne les requetes tribe_events
          et annule l orderby. La fonction prenait donc la premiere ligne venue.
          Meme cause que la section 7 prochains jours, corrigee le meme jour :
          on ne se bat plus contre l ordre SQL, on trie en PHP.
       2. Le tri portait sur as_score, la qualite editoriale generale, alors que
          la section a un champ dedie : as_deplacement, 0 a 8.
       3. Aucun garde-fou sur le contenu : la fiche 6400, zero mot, porte un
          as_deplacement de 8 et serait passee en vitrine. */
    if (empty($q->posts)) { return 0; }
    $classes = array();
    foreach ($q->posts as $pid) {
        if (get_post_meta($pid, '_yoast_wpseo_meta-robots-noindex', true) === '1') { continue; }
        $mots = str_word_count(wp_strip_all_tags((string) get_post_field('post_content', $pid)));
        if ($mots < 150) { continue; }
        $dep = get_post_meta($pid, 'as_deplacement', true);
        $sco = get_post_meta($pid, 'as_score', true);
        $classes[] = array(
            'id'  => (int) $pid,
            'dep' => ($dep === '' ? -1 : (int) $dep),
            'sco' => ($sco === '' ? -1 : (int) $sco),
        );
    }
    if (empty($classes)) { return 0; }
    usort($classes, function ($a, $b) {
        if ($a['dep'] !== $b['dep']) { return $b['dep'] - $a['dep']; }
        return $b['sco'] - $a['sco'];
    });
    return $classes[0]['id'];
}
}

if (!function_exists('cs_cvld_get_cards')) {
function cs_cvld_get_cards($lang) {
    if (!function_exists('cs_terr_canon_data')) { return array(); }
    $TERR  = cs_terr_canon_data();
    $actif = function_exists('cs_territoire_actif') ? cs_territoire_actif() : null;
    $is_it = ($lang === 'it');

    $keys = array_keys($TERR);
    if ($actif && isset($TERR[$actif])) {
        $keys = array_values(array_diff($keys, array($actif)));
    }
    $limit = count($keys) >= 4 ? 4 : 3;

    $picked = array(); $used = array();
    // 1er passage : un evenement garanti par territoire eligible.
    foreach ($keys as $k) {
        $tid = $is_it ? (int) $TERR[$k]['it_term'] : (int) $TERR[$k]['fr_term'];
        if (!$tid) { continue; }
        $pid = cs_cvld_pick_one($tid, $lang, $used);
        if ($pid) { $picked[] = $pid; $used[] = $pid; }
    }
    // 2e passage : repli si un territoire n a rien donne, pour ne jamais laisser
    // la rangee incomplete.
    if (count($picked) < $limit) {
        foreach ($keys as $k) {
            if (count($picked) >= $limit) { break; }
            $tid = $is_it ? (int) $TERR[$k]['it_term'] : (int) $TERR[$k]['fr_term'];
            if (!$tid) { continue; }
            $pid = cs_cvld_pick_one($tid, $lang, $used);
            if ($pid) { $picked[] = $pid; $used[] = $pid; }
        }
    }

    $cards = array();
    foreach (array_slice($picked, 0, $limit) as $pid) {
        $terms = get_the_terms($pid, 'territoire');
        $start = get_post_meta($pid, '_EventStartDate', true);
        $cards[] = array(
            'title' => esc_html(get_the_title($pid)),
            'link'  => esc_url(get_permalink($pid)),
            'thumb' => esc_url(get_the_post_thumbnail_url($pid, 'medium_large')),
            'terr'  => ($terms && !is_wp_error($terms)) ? esc_html($terms[0]->name) : '',
            'pill'  => ($terms && !is_wp_error($terms)) ? cs_pill_class($terms[0]->name) : '',
            'date'  => $start ? esc_html(date_i18n('j M', strtotime($start))) : '',
            'lieu'  => esc_html(get_post_meta($pid, '_cs_commune', true)),
        );
    }
    return $cards;
}
}

/* Les polices viennent des classes CSS (cs-cvld-*, snippet 12) : pas de
   font-family en ligne, ce qui evite d embarquer des apostrophes dans du HTML
   genere en PHP -- source classique de casse a la moindre reecriture. */
if (!function_exists('cs_cvld_meta_line')) {
function cs_cvld_meta_line($c) {
    $bits = array();
    if ($c['terr']) { $bits[] = "<span class=\"as-pill " . $c['pill'] . "\">" . $c['terr'] . "</span>"; }
    if ($c['date']) { $bits[] = "<span>" . $c['date'] . "</span>"; }
    if (empty($bits)) { return ""; }
    return "<div class=\"cs-cvld-meta\">" . implode("<span class=\"cs-cvld-sep\">&middot;</span>", $bits) . "</div>";
}
}

if (!function_exists('cs_cvld_card')) {
function cs_cvld_card($c, $mode) {
    $cls = ($mode === "m") ? "cs-cvld-card cs-cvld-card--row" : "cs-cvld-card";
    return "<a class=\"" . $cls . "\" href=\"" . $c['link'] . "\">"
        . "<span class=\"cs-cvld-thumb\"><img src=\"" . $c['thumb'] . "\" alt=\"\"></span>"
        . "<span class=\"cs-cvld-body\">" . cs_cvld_meta_line($c)
        . "<span class=\"cs-cvld-title\">" . $c['title'] . "</span>"
        . "<span class=\"cs-cvld-lieu\">" . $c['lieu'] . "</span></span></a>";
}
}

if (!function_exists('cs_cvld_cta_cell')) {
function cs_cvld_cta_cell($lang) {
    // Reprend le bouton noir existant du site (fond #1D1D1B, bord inferieur en
    // dents de scie via clip-path). Il ne flotte plus SOUS la section : il occupe
    // la 4e case, ce qui remplit la rangee quand un filtre territoire ne laisse
    // que trois territoires eligibles.
    $is_it = ($lang === "it");
    $url   = $is_it ? "https://agendasabauda.eu/it/?as_territoire=tutti" : "https://agendasabauda.eu/?as_territoire=tous";
    $kick  = $is_it ? "E altrove" : "Et ailleurs";
    $lab   = $is_it ? "Vedi negli altri territori" : "Voir dans les autres territoires";
    return "<a class=\"cs-cvld-card cs-cvld-cta\" href=\"" . $url . "\">"
        . "<span class=\"cs-cvld-cta-kick\">" . $kick . "</span>"
        . "<span class=\"cs-cvld-cta-lab\">" . $lab . "</span>"
        . "<span class=\"cs-cvld-cta-arrow\">&rarr;</span></a>";
}
}

add_filter('the_content', function ($content) {
    if (strpos($content, "CVLD_MOBILE_START") === false && strpos($content, "CVLD_DESKTOP_START") === false) {
        return $content;
    }
    $lang  = function_exists("pll_current_language") ? pll_current_language() : "fr";
    $cards = cs_cvld_get_cards($lang);
    if (count($cards) < 2) { return $content; }

    $mobile = "";
    foreach ($cards as $c) { $mobile .= cs_cvld_card($c, "m"); }

    $desktop = "<div class=\"cs-cvld-grid\">";
    foreach ($cards as $c) { $desktop .= cs_cvld_card($c, "d"); }
    if (count($cards) < 4) { $desktop .= cs_cvld_cta_cell($lang); }
    $desktop .= "</div>";

    $swap = function ($content, $start, $end, $html) {
        $s = strpos($content, $start);
        $e = strpos($content, $end);
        if ($s === false || $e === false || $e <= $s) { return $content; }
        return substr($content, 0, $s + strlen($start)) . "\n" . $html . substr($content, $e);
    };
    $content = $swap($content, "<!-- CVLD_MOBILE_START -->", "<!-- CVLD_MOBILE_END -->", $mobile);
    $content = $swap($content, "<!-- CVLD_DESKTOP_START -->", "<!-- CVLD_DESKTOP_END -->", $desktop);
    return $content;
}, 9);
