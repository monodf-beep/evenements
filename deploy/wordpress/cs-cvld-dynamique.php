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
/* PLANCHER DE LA SECTION (2026-09-08, Franck devant la home : « est-ce que Pinocchio ça
   fait déplacer ? non »). La fiche affichée pour la Vallée d'Aoste valait 6/12. Le plancher
   décidé le 04/08 est à 10/12 (utils/deplacement.py, DEPLACEMENT_MIN — c'est lui qui laisse
   as_deplacement_now VIDE sous le plancher), mais il ne vivait qu'en Python : ce mu-plugin
   triait sans plancher et « garantissait » une carte par territoire, même médiocre. Le bonus
   temporel posé le matin même a aggravé le cas : une fiche proche et faible passait devant.
   Deux exigences, donc : la note INTRINSÈQUE >= plancher (on ne montre pas une sortie
   quelconque parce qu'elle est bientôt), ET la note TEMPS-AJUSTÉE >= plancher (la Foire de
   Saint-Ours à 12 mais dans cinq mois vaut 6 aujourd'hui : « trop loin dans le temps »,
   Franck, même jour). Un territoire sans fiche qui tienne les deux laisse sa case au second
   passage — une carte d'un autre territoire plutôt qu'une carte médiocre, comme l'écrit
   scripts/audit_deplacement.py depuis le 04/08. Même valeur que DEPLACEMENT_MIN : à changer
   ENSEMBLE. */
if (!defined('CS_CVLD_PLANCHER')) { define('CS_CVLD_PLANCHER', 10); }

if (!function_exists('cs_cvld_note_temps')) {
function cs_cvld_note_temps($id, $dep) {
    /* 2026-09-08 (Franck : « au lieu de couper il faut trouver la solution », transpose ici
       apres l'audit du figement). MEME bareme que cs_une_note() (snippet 140, section
       "A la une"), SANS son seuil as_deplacement>=8 : applique tel quel, ce seuil aurait
       laisse 2 candidates en Vallee d'Aoste et 1 a Nice au 08/10 -- pas le probleme mesure
       ici (le vivier suffit, 5 a 18 fiches par territoire). Sans ce bonus, le tri ne
       departageait QUE sur la note figee : la Foire de Saint-Ours (dep=12, fin 31/01/2027)
       devancait sa concurrente de 3 points et tenait la case ~21 semaines d'affilee, mesure
       par scripts/audit_deplacement.py. */
    $today = strtotime(current_time('Y-m-d'));
    $d1 = strtotime(substr((string) get_post_meta($id, '_EventStartDate', true), 0, 10));
    $d2 = strtotime(substr((string) get_post_meta($id, '_EventEndDate', true), 0, 10));
    $j1 = $d1 ? (int) floor(($d1 - $today) / 86400) : 999;
    $j2 = $d2 ? (int) floor(($d2 - $today) / 86400) : 999;
    $debut = 0;
    if ($j1 >= 0) {
        if ($j1 <= 3)       { $debut = 5; }
        elseif ($j1 <= 7)   { $debut = 4; }
        elseif ($j1 <= 14)  { $debut = 3; }
        elseif ($j1 <= 30)  { $debut = 1; }
        elseif ($j1 <= 60)  { $debut = 0; }
        elseif ($j1 <= 120) { $debut = -3; }
        else                { $debut = -6; }
    }
    $fin = ($j1 < 0 && $j2 >= 0 && $j2 <= 10) ? 3 : 0;
    return $dep + $debut + $fin;
}
}

if (!function_exists('cs_cvld_pick_one')) {
function cs_cvld_pick_one($term_id, $lang, $exclude, $strict = true) {
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
        $dep_brut = ($dep === '' ? -1 : (int) $dep);
        if ($dep_brut < CS_CVLD_PLANCHER) { continue; }   // plancher intrinsèque
        $classes[] = array(
            'id'  => (int) $pid,
            'dep' => $dep_brut,
            /* Note temps-ajustee : departage entre deux fiches sur leur PROXIMITE, pas
               seulement leur note figee -- cf. cs_cvld_note_temps ci-dessus. */
            'dep_temps' => ($dep_brut < 0) ? $dep_brut : cs_cvld_note_temps($pid, $dep_brut),
            'sco' => ($sco === '' ? -1 : (int) $sco),
        );
    }
    if (empty($classes)) { return 0; }
    usort($classes, function ($a, $b) {
        if ($a['dep_temps'] !== $b['dep_temps']) { return $b['dep_temps'] - $a['dep_temps']; }
        return $b['sco'] - $a['sco'];
    });
    /* Premier passage ($strict) : trop loin dans le temps = pas de carte. Second passage
       (repli) : le plancher de NOTE reste, l'échéance peut être lointaine — 2026-09-08,
       Franck sur le hub Piémont : « on a que 2 au lieu de 3 ». Les trois autres territoires
       n'avaient que deux fiches proches au-dessus du plancher ; la Foire de Saint-Ours (12,
       en janvier) vaut mieux qu'un trou, et jamais une fiche à 6. */
    if ($strict && $classes[0]['dep_temps'] < CS_CVLD_PLANCHER) { return 0; }
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
            $pid = cs_cvld_pick_one($tid, $lang, $used, false);
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
    // 2026-09-08 (Franck : « pourquoi j'ai pas explore-sabauda à la place de
    // ?as_territoire=tous »). Les URLs jolies existent depuis le 06/08
    // (cs-territoire-urls-jolies.php) ; ce bouton était resté sur l'ancienne forme.
    $url   = $is_it ? "https://agendasabauda.eu/it/spazio-sabaudo/" : "https://agendasabauda.eu/espace-sabaudo/";
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
