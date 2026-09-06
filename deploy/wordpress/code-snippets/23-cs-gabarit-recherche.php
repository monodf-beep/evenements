/**
 * Page de recherche, rendu complet en PHP (template_redirect).
 * 2026-07-23 : recherche contextuelle en 2 niveaux (ville connue -> primaire+alentours ;
 * sinon categorie -> primaire+autres resultats ; sinon plein texte simple).
 * Traduit desormais integralement en IT (etait FR-only malgre is_search() bilingue).
 */

if (!function_exists('cs_search_norm')) {
    function cs_search_norm($s) {
        $s = mb_strtolower(trim((string) $s), 'UTF-8');
        $map = array('à'=>'a','â'=>'a','ä'=>'a','é'=>'e','è'=>'e','ê'=>'e','ë'=>'e','î'=>'i','ï'=>'i','ô'=>'o','ö'=>'o','ù'=>'u','û'=>'u','ü'=>'u','ç'=>'c','ñ'=>'n');
        return strtr($s, $map);
    }
}

if (!function_exists('cs_search_city_map')) {
    function cs_search_city_map() {
        $cached = get_transient('cs_search_city_map_v1');
        if ($cached !== false) {
            return $cached;
        }
        global $wpdb;
        $rows = $wpdb->get_results("
            SELECT vm.meta_value AS city, tt.term_id AS term_id, COUNT(*) AS cnt
            FROM {$wpdb->postmeta} evm
            JOIN {$wpdb->postmeta} vm ON vm.post_id = evm.meta_value AND vm.meta_key = '_VenueCity'
            JOIN {$wpdb->term_relationships} tr ON tr.object_id = evm.post_id
            JOIN {$wpdb->term_taxonomy} tt ON tt.term_taxonomy_id = tr.term_taxonomy_id AND tt.taxonomy = 'territoire'
            JOIN {$wpdb->posts} p ON p.ID = evm.post_id AND p.post_status = 'publish' AND p.post_type = 'tribe_events'
            WHERE evm.meta_key = '_EventVenueID' AND vm.meta_value != ''
            GROUP BY vm.meta_value, tt.term_id
        ");
        $fr_terms = array(3, 6, 8, 10);
        $it_terms = array(318, 321, 324, 327);
        $agg = array();
        foreach ($rows as $r) {
            $key = cs_search_norm($r->city);
            if ($key === '') continue;
            if (!isset($agg[$key])) $agg[$key] = array('fr' => array(), 'it' => array(), 'label' => $r->city);
            if (in_array((int) $r->term_id, $fr_terms, true)) $agg[$key]['fr'][$r->term_id] = (isset($agg[$key]['fr'][$r->term_id]) ? $agg[$key]['fr'][$r->term_id] : 0) + (int) $r->cnt;
            if (in_array((int) $r->term_id, $it_terms, true)) $agg[$key]['it'][$r->term_id] = (isset($agg[$key]['it'][$r->term_id]) ? $agg[$key]['it'][$r->term_id] : 0) + (int) $r->cnt;
        }
        $map = array();
        foreach ($agg as $key => $d) {
            arsort($d['fr']);
            arsort($d['it']);
            $fr_keys = array_keys($d['fr']);
            $it_keys = array_keys($d['it']);
            $map[$key] = array(
                'label' => $d['label'],
                'fr_term' => $fr_keys ? (int) $fr_keys[0] : 0,
                'it_term' => $it_keys ? (int) $it_keys[0] : 0,
            );
        }
        set_transient('cs_search_city_map_v1', $map, 12 * HOUR_IN_SECONDS);
        return $map;
    }
}

if (!function_exists('cs_search_match_city')) {
    function cs_search_match_city($norm_query, $city_map) {
        if ($norm_query === '') return null;
        $best = null;
        $best_score = 0;
        foreach ($city_map as $key => $info) {
            $score = 0;
            if ($norm_query === $key) {
                $score = 1000 + strlen($key);
            } elseif (strlen($key) >= 4 && strpos($norm_query, $key) !== false) {
                $score = 500 + strlen($key);
            } elseif (strlen($norm_query) >= 4 && strpos($key, $norm_query) === 0) {
                $score = 200 + strlen($norm_query);
            }
            if ($score > $best_score) {
                $best_score = $score;
                $best = $info;
                $best['key'] = $key;
            }
        }
        return $best;
    }
}

/**
 * 2026-08-03 : correctif de routage de la page Rechercher.
 *
 * Symptome : /rechercher/?s=terme renvoyait une 404, alors que /?s=terme
 * fonctionnait. Le pied de page menait donc a une page qui affichait en clair
 * "Page a construire : recherche sur l agenda."
 *
 * Cause : WordPress posait pagename sur cette URL, donc is_search restait faux.
 * La requete principale cherchait le terme dans la seule page 1771, dont le
 * contenu fait 51 caracteres, ne trouvait aucun post, et handle_404 basculait
 * la reponse en 404.
 *
 * Correctif : on convertit la requete principale en veritable recherche des que
 * l URL vise la page Rechercher ou sa traduction. Le gabarit ci-dessous se joue
 * alors normalement, et handle_404 exempte explicitement is_search, donc le 404
 * disparait meme quand la recherche ne renvoie aucun resultat.
 *
 * Effet secondaire voulu : /rechercher/ sans terme rend desormais le formulaire
 * de recherche au lieu du contenu de la page 1771.
 */
if (!function_exists('cs_search_pages_cibles')) {
    function cs_search_pages_cibles() {
        $ids = array(1771);
        if (function_exists('pll_get_post_translations')) {
            $trad = pll_get_post_translations(1771);
            if (is_array($trad) && !empty($trad)) {
                $ids = array_map('intval', array_values($trad));
            }
        }
        return $ids;
    }
}

if (!function_exists('cs_search_url_visee')) {
    function cs_search_url_visee($q) {
        $cibles = cs_search_pages_cibles();

        $page_id = (int) $q->get('page_id');
        if ($page_id && in_array($page_id, $cibles, true)) {
            return true;
        }

        $pagename = (string) $q->get('pagename');
        if ($pagename !== '') {
            $p = get_page_by_path($pagename);
            if ($p && in_array((int) $p->ID, $cibles, true)) {
                return true;
            }
        }

        return false;
    }
}

add_action('parse_query', function ($q) {
    if (is_admin() || !is_a($q, 'WP_Query') || !$q->is_main_query()) {
        return;
    }
    if (!cs_search_url_visee($q)) {
        return;
    }

    $terme = isset($_GET['s']) ? trim((string) wp_unslash($_GET['s'])) : '';

    $q->set('pagename', '');
    $q->set('page_id', 0);
    $q->set('s', $terme);

    // Sans terme, la requete principale ne sert a rien : le gabarit fait ses
    // propres WP_Query. On la reduit au minimum plutot que de ramener tout le
    // catalogue pour rien.
    if ($terme === '') {
        $q->set('posts_per_page', 1);
    }

    $q->is_page     = false;
    $q->is_singular = false;
    $q->is_home     = false;
    $q->is_search   = true;
    $q->is_404      = false;
}, 5);

// Sans ce garde-fou, WordPress renvoie /rechercher/?s=terme vers /?s=terme,
// puisque la requete n est plus une page. On veut garder l URL de marque.
add_filter('redirect_canonical', function ($redirect, $requested) {
    if (!is_search()) {
        return $redirect;
    }
    if (preg_match('#/(rechercher|cerca)/#', (string) $requested)) {
        return false;
    }
    return $redirect;
}, 10, 2);


add_action('template_redirect', function () {
    if (is_admin() || !is_search()) {
        return;
    }

    $lang = function_exists('pll_current_language') ? (pll_current_language() ?: 'fr') : 'fr';
    $is_it = $lang === 'it';

    $LB = $is_it ? array(
        'placeholder' => 'Cerca un evento, una città...',
        'categorie' => 'Categoria',
        'ville' => 'Città',
        'raccourcis' => 'Scorciatoie',
        'pages_guides' => 'Pagine e guide',
        'tag_ville' => 'Città',
        'tag_territoire' => 'Territorio',
        'gratuit' => 'Gratis',
        'ou' => 'Dove',
        'quand' => 'Quando',
        'peu_importe' => 'Non importa',
        'plus_filtres' => 'Altri filtri',
        'cat_existe' => 'Esiste una categoria',
        'filtrer_dessus' => 'Filtra',
        'aucun_filtre' => 'Nessun filtro attivo',
        'n_filtres' => '%d filtri attivi',
        'n_resultats' => '%d risultati',
        'tout_effacer' => 'Cancella tutto',
        'effacer' => 'Cancella',
        'tag_guide' => 'Guida',
        'tag_article' => 'Articolo',
        'tag_page' => 'Pagina',
        'aucun_resultat' => 'Nessun risultato: prova una città o una categoria',
        'ce_weekend' => 'Questo weekend',
        'tout_agenda' => "Tutto l'agenda",
        'a_ville' => 'A %s',
        'alentours' => 'Nei dintorni di %s',
        'evenements_pour' => 'Eventi per «%s»',
        'autres_resultats' => 'Altri risultati per «%s»',
    ) : array(
        'placeholder' => 'Rechercher un événement, une ville...',
        'categorie' => 'Catégorie',
        'ville' => 'Ville',
        'raccourcis' => 'Raccourcis',
        'pages_guides' => 'Pages & guides',
        'tag_ville' => 'Ville',
        'tag_territoire' => 'Territoire',
        'gratuit' => 'Gratuit',
        'ou' => 'Où',
        'quand' => 'Quand',
        'peu_importe' => 'Peu importe',
        'plus_filtres' => 'Plus de filtres',
        'cat_existe' => 'Il existe une catégorie',
        'filtrer_dessus' => 'Filtrer dessus',
        'aucun_filtre' => 'Aucun filtre actif',
        'n_filtres' => '%d filtres actifs',
        'n_resultats' => '%d résultats',
        'tout_effacer' => 'Tout effacer',
        'effacer' => 'Effacer',
        'tag_guide' => 'Guide',
        'tag_article' => 'Article',
        'tag_page' => 'Page',
        'aucun_resultat' => 'Aucun résultat : essayez une ville ou une catégorie',
        'ce_weekend' => 'Ce week-end',
        'tout_agenda' => "Tout l'agenda",
        'a_ville' => 'À %s',
        'alentours' => 'Aux alentours de %s',
        'evenements_pour' => 'Événements pour «%s»',
        'autres_resultats' => 'Autres résultats pour «%s»',
    );

    $query = get_search_query();
    $norm_query = cs_search_norm($query);

    // 2026-08-03 : filtre gratuite. Une seule information de prix sur ce site,
    // la gratuite, jamais de tarif ni de fourchette. Cf. la decision prise apres
    // le releve de Guida Torino, qui traite Eventi Gratis comme une categorie.
    $only_free = !empty($_GET['gratuit']);
    $f_ou    = isset($_GET['ou']) ? sanitize_text_field(wp_unslash($_GET['ou'])) : '';
    $f_quand = isset($_GET['quand']) ? sanitize_text_field(wp_unslash($_GET['quand'])) : '';
    $f_cat   = isset($_GET['cat']) ? sanitize_text_field(wp_unslash($_GET['cat'])) : '';
    $cat_suggestion = null;

    // URL de la page de recherche de marque, pour ne pas renvoyer le formulaire
    // vers /?s= et perdre /rechercher/ ou /it/cerca/.
    $action_url = home_url('/');
    if (function_exists('cs_search_pages_cibles')) {
        foreach (cs_search_pages_cibles() as $cible_id) {
            if (!function_exists('pll_get_post_language') || pll_get_post_language($cible_id) === $lang) {
                $lien = get_permalink($cible_id);
                if ($lien && !is_wp_error($lien)) { $action_url = $lien; }
                break;
            }
        }
    }

    get_header();

    $loc = null;
    $cat_term = null;
    $primary_q = null;
    $secondary_q = null;
    $primary_ids = array();

    if ($query !== '') {
        $loc = cs_search_match_city($norm_query, cs_search_city_map());
    }

    if ($loc) {
        $venue_q = new WP_Query(array(
            'post_type' => 'tribe_events',
            'post_status' => 'publish',
            'posts_per_page' => 60,
            'lang' => $lang,
            // 2026-09-06 (Franck) : jamais de passe dans les resultats ("Nice" remontait jusqu'a mai).
            'meta_query' => array(array('key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME')),
            'meta_key' => '_EventStartDate',
            'orderby' => 'meta_value',
            'order' => 'ASC',
        ));
        $kept = array();
        if ($venue_q->have_posts()) {
            foreach ($venue_q->posts as $ppost) {
                $vid = get_post_meta($ppost->ID, '_EventVenueID', true);
                $vcity = $vid ? get_post_meta($vid, '_VenueCity', true) : '';
                if ($vcity !== '' && cs_search_norm($vcity) === $loc['key']) {
                    $kept[] = $ppost;
                    $primary_ids[] = $ppost->ID;
                }
            }
        }
        $primary_q = $venue_q;
        $primary_q->posts = $kept;
        $primary_q->post_count = count($kept);

        $terr_term = $is_it ? $loc['it_term'] : $loc['fr_term'];
        if ($terr_term) {
            $secondary_q = new WP_Query(array(
                'post_type' => 'tribe_events',
                'post_status' => 'publish',
                'posts_per_page' => 12,
                'lang' => $lang,
                // 2026-09-06 (Franck) : jamais de passe dans les resultats ("Nice" remontait jusqu'a mai).
                'meta_query' => array(array('key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME')),
                'post__not_in' => $primary_ids ?: array(0),
                'tax_query' => array(array('taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $terr_term)),
                'meta_key' => '_EventStartDate',
                'orderby' => 'meta_value',
                'order' => 'ASC',
            ));
        }
    } elseif ($query !== '') {
        $cats = get_terms(array('taxonomy' => 'tribe_events_cat', 'hide_empty' => false, 'lang' => $lang));
        if (!is_wp_error($cats)) {
            foreach ($cats as $c) {
                if (cs_search_norm($c->name) === $norm_query || stripos($c->name, $query) !== false) {
                    $cat_term = $c;
                    break;
                }
            }
        }
        $cat_suggestion = $cat_term;
        $cat_term = null; // 2026-08-03 : plus d application silencieuse, cf. bloc filtres
        if ($cat_term) {
            $primary_q = new WP_Query(array(
                'post_type' => 'tribe_events',
                'post_status' => 'publish',
                'posts_per_page' => 30,
                'lang' => $lang,
                // 2026-09-06 (Franck) : jamais de passe dans les resultats ("Nice" remontait jusqu'a mai).
                'meta_query' => array(array('key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME')),
                'tax_query' => array(array('taxonomy' => 'tribe_events_cat', 'field' => 'term_id', 'terms' => $cat_term->term_id)),
                'meta_key' => '_EventStartDate',
                'orderby' => 'meta_value',
                'order' => 'ASC',
            ));
            if ($primary_q->have_posts()) {
                foreach ($primary_q->posts as $ppost) $primary_ids[] = $ppost->ID;
            }
        }
        $secondary_q = new WP_Query(array(
            'post_type' => 'tribe_events',
            'post_status' => 'publish',
            'posts_per_page' => 20,
            'lang' => $lang,
            's' => $query,
            // 2026-09-06 (Franck) : jamais de passe dans les resultats ("Nice" remontait jusqu'a mai).
            'meta_query' => array(array('key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME')),
            'post__not_in' => $primary_ids ?: array(0),
        ));
    }

    $pages_q = null;
    if ($query !== '') {
        $pages_q = new WP_Query(array(
            'post_type' => array('page', 'post'),
            'post_status' => 'publish',
            's' => $query,
            'posts_per_page' => 10,
            'lang' => $lang,
            'meta_query' => array(
                'relation' => 'OR',
                array('key' => 'cs_hub_quand', 'compare' => 'NOT EXISTS'),
            ),
        ));
    }

    $terr_data = function_exists('cs_terr_canon_data') ? cs_terr_canon_data() : array();
    $shortcut_hub_ids = array('savoie' => 2857, 'piemont' => 2859, 'vda' => 2861, 'nice' => 2863);
    $shortcuts = array(
        array('label' => $is_it ? 'Questo weekend' : 'Ce week-end', 'url' => get_permalink($is_it ? 1789 : 930)),
    );
    foreach ($shortcut_hub_ids as $canon => $hub_fr_id) {
        $hub_id = $is_it ? pll_get_post($hub_fr_id, 'it') : $hub_fr_id;
        $label = isset($terr_data[$canon]) ? ($is_it ? $terr_data[$canon]['it_name'] : $terr_data[$canon]['fr_name']) : '';
        $url = $hub_id ? get_permalink($hub_id) : '';
        if ($label && $url) {
            $shortcuts[] = array('label' => $label, 'url' => $url);
        }
    }
    $music_term_id = $is_it ? (function_exists('pll_get_term') ? pll_get_term(13, 'it') : 0) : 13;
    if ($music_term_id) {
        $music_link = get_term_link((int) $music_term_id, 'tribe_events_cat');
        if (!is_wp_error($music_link)) {
            $shortcuts[] = array('label' => $is_it ? 'Concerti e musica' : 'Concerts & Musique', 'url' => $music_link);
        }
    }
    ?>
    <div style='max-width:700px;margin:0 auto;padding:0 20px'>

      <div style='padding:16px 0 10px'>
        <form role='search' method='get' action='<?php echo esc_url($action_url); ?>' style='display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #E3DCCE;border-radius:10px;padding:11px 14px'>
          <svg width='17' height='17' viewBox='0 0 24 24' fill='none' stroke='#1D1D1B' stroke-width='1.8' style='flex-shrink:0'><circle cx='10.5' cy='10.5' r='6.5'></circle><line x1='20' y1='20' x2='15.3' y2='15.3'></line></svg>
          <input type='search' name='s' value='<?php echo esc_attr($query); ?>' placeholder='<?php echo esc_attr($LB['placeholder']); ?>' style="flex:1;border:0;background:transparent;outline:0;font-family:'Nunito Sans',sans-serif;font-size:15px;color:#1D1D1B">
          <?php if ($only_free): ?><input type='hidden' name='gratuit' value='1'><?php endif; ?>
          <?php if ($query !== ''): ?>
          <a href='<?php echo esc_url($action_url); ?>' aria-label='<?php echo esc_attr($LB['effacer']); ?>' style='flex-shrink:0;line-height:0;text-decoration:none'>
            <svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='#8FA4BF' stroke-width='2'><line x1='5' y1='5' x2='19' y2='19'></line><line x1='19' y1='5' x2='5' y2='19'></line></svg>
          </a>
          <?php endif; ?>
        </form>
      </div>

      <?php
// ---------------------------------------------------------------------------
// 2026-08-03 : filtres de recherche.
//
// Trois filtres en surface (Ou, Quand, Gratuit) et le reste replie derriere
// "Plus de filtres". Decision Franck : la categorie a beaucoup de valeurs, en
// pilules elle noyait les trois filtres principaux, en panneau deplie elle
// devient lisible avec ses compteurs.
//
// La categorie n est PLUS appliquee automatiquement depuis le terme cherche.
// Taper "festival" convertissait silencieusement la recherche en filtre de
// categorie, ce qui masquait les evenements parlant de festival sans y etre
// ranges, sans que le lecteur puisse le savoir. Elle est desormais proposee.
//
// Tous les filtres s appliquent APRES construction des requetes, comme le
// filtre par ville deja en place. Une seule ecriture, aucun risque de
// desynchroniser les requetes entre elles.
//
// Les compteurs sont calcules sur le jeu de resultats AVANT filtrage : ils
// disent "combien parmi ces resultats", pas "combien sur tout le site".
// ---------------------------------------------------------------------------

// Jeu de base, avant application des filtres.
$base_posts = array();
foreach (array('primary_q', 'secondary_q') as $var_q) {
    if (!empty($$var_q) && !empty($$var_q->posts)) {
        $base_posts = array_merge($base_posts, $$var_q->posts);
    }
}

$today_ymd = current_time('Y-m-d');
$ts_today  = strtotime($today_ymd);
$dow       = (int) date('N', $ts_today);
$sam       = date('Y-m-d', strtotime('+' . (6 - $dow) . ' day', $ts_today));
$dim       = date('Y-m-d', strtotime('+' . (7 - $dow) . ' day', $ts_today));
if ($dow >= 6) { $sam = ($dow === 6) ? $today_ymd : date('Y-m-d', strtotime('-1 day', $ts_today)); $dim = date('Y-m-d', strtotime('+' . (7 - $dow) . ' day', $ts_today)); }
$fin_semaine = date('Y-m-d', strtotime('+7 day', $ts_today));
$fin_mois    = date('Y-m-t', $ts_today);

$cs_chevauche = function ($id, $d1, $d2) {
    $deb = substr((string) get_post_meta($id, '_EventStartDate', true), 0, 10);
    $fin = substr((string) get_post_meta($id, '_EventEndDate', true), 0, 10);
    if ($deb === '' || $fin === '') { return false; }
    return ($deb <= $d2 && $fin >= $d1);
};

// Facettes.
$fac_ou = array();
$fac_cat = array();
$fac_quand = array('aujourdhui' => 0, 'weekend' => 0, 'semaine' => 0, 'mois' => 0);
$fac_gratuit = 0;

foreach ($base_posts as $bp) {
    $vid = get_post_meta($bp->ID, '_EventVenueID', true);
    $vcity = $vid ? trim((string) get_post_meta($vid, '_VenueCity', true)) : '';
    if ($vcity !== '') {
        $k = cs_search_norm($vcity);
        if (!isset($fac_ou[$k])) { $fac_ou[$k] = array('label' => $vcity, 'n' => 0, 'terr' => ''); }
        $fac_ou[$k]['n']++;
        if ($fac_ou[$k]['terr'] === '') {
            $tt = wp_get_post_terms($bp->ID, 'territoire', array('fields' => 'names'));
            if (!is_wp_error($tt) && !empty($tt)) { $fac_ou[$k]['terr'] = $tt[0]; }
        }
    }
    $cts = wp_get_post_terms($bp->ID, 'tribe_events_cat');
    if (!is_wp_error($cts)) {
        foreach ($cts as $ct) {
            if (!isset($fac_cat[$ct->slug])) { $fac_cat[$ct->slug] = array('label' => $ct->name, 'n' => 0); }
            $fac_cat[$ct->slug]['n']++;
        }
    }
    if ((int) get_post_meta($bp->ID, 'as_gratuit', true) === 1) { $fac_gratuit++; }
    if ($cs_chevauche($bp->ID, $today_ymd, $today_ymd)) { $fac_quand['aujourdhui']++; }
    if ($cs_chevauche($bp->ID, $sam, $dim)) { $fac_quand['weekend']++; }
    if ($cs_chevauche($bp->ID, $today_ymd, $fin_semaine)) { $fac_quand['semaine']++; }
    if ($cs_chevauche($bp->ID, $today_ymd, $fin_mois)) { $fac_quand['mois']++; }
}

uasort($fac_ou, function ($a, $b) { return $b['n'] - $a['n']; });
uasort($fac_cat, function ($a, $b) { return $b['n'] - $a['n']; });

// Regroupement des villes par territoire, pour que le menu enseigne la
// geographie en meme temps qu il filtre.
$ou_par_terr = array();
foreach ($fac_ou as $k => $info) {
    $t = $info['terr'] !== '' ? $info['terr'] : '—';
    if (!isset($ou_par_terr[$t])) { $ou_par_terr[$t] = array(); }
    $ou_par_terr[$t][$k] = $info;
}

// Application des filtres.
$actifs = 0;
if ($f_ou !== '' || $f_quand !== '' || $f_cat !== '' || $only_free) {
    foreach (array('primary_q', 'secondary_q') as $var_q) {
        if (!isset($$var_q) || !$$var_q || empty($$var_q->posts)) { continue; }
        $gardes = array();
        foreach ($$var_q->posts as $pp) {
            if ($only_free && (int) get_post_meta($pp->ID, 'as_gratuit', true) !== 1) { continue; }
            if ($f_ou !== '') {
                $vid = get_post_meta($pp->ID, '_EventVenueID', true);
                $vcity = $vid ? trim((string) get_post_meta($vid, '_VenueCity', true)) : '';
                if ($vcity === '' || cs_search_norm($vcity) !== $f_ou) { continue; }
            }
            if ($f_cat !== '' && !has_term($f_cat, 'tribe_events_cat', $pp->ID)) { continue; }
            if ($f_quand !== '') {
                $ok = false;
                if ($f_quand === 'aujourdhui') { $ok = $cs_chevauche($pp->ID, $today_ymd, $today_ymd); }
                elseif ($f_quand === 'weekend') { $ok = $cs_chevauche($pp->ID, $sam, $dim); }
                elseif ($f_quand === 'semaine') { $ok = $cs_chevauche($pp->ID, $today_ymd, $fin_semaine); }
                elseif ($f_quand === 'mois') { $ok = $cs_chevauche($pp->ID, $today_ymd, $fin_mois); }
                if (!$ok) { continue; }
            }
            $gardes[] = $pp;
        }
        $$var_q->posts = $gardes;
        $$var_q->post_count = count($gardes);
    }
}
foreach (array($f_ou, $f_quand, $f_cat) as $vf) { if ($vf !== '') { $actifs++; } }
if ($only_free) { $actifs++; }

// Construction des URL de filtre : on repart toujours de l etat courant et on
// ne change que la cle demandee. null retire la cle.
$url_f = function ($args) use ($action_url, $query, $f_ou, $f_quand, $f_cat, $only_free) {
    $base = array();
    if ($query !== '') { $base['s'] = $query; }
    if ($f_ou !== '') { $base['ou'] = $f_ou; }
    if ($f_quand !== '') { $base['quand'] = $f_quand; }
    if ($f_cat !== '') { $base['cat'] = $f_cat; }
    if ($only_free) { $base['gratuit'] = 1; }
    foreach ($args as $k => $v) {
        if ($v === null) { unset($base[$k]); } else { $base[$k] = $v; }
    }
    return add_query_arg($base, $action_url);
};

$ic = '#E85D3A';
$pill = "display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:6px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;text-decoration:none;white-space:nowrap;color:#1D1D1B";
$pill_off = $pill . ";background:#fff;border:1px solid #E3DCCE";
$pill_on  = $pill . ";background:#F2EDE3;border:1px solid #D8CFBC;font-weight:800";
$menu = "position:absolute;top:34px;left:0;min-width:210px;max-height:290px;overflow-y:auto;background:#fff;border:1px solid #E3DCCE;border-radius:10px;padding:7px;z-index:20";
$opt  = "display:flex;justify-content:space-between;gap:10px;padding:6px 9px;border-radius:6px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B;text-decoration:none";
$grp  = "font-family:'Nunito Sans',sans-serif;font-size:9.5px;font-weight:800;letter-spacing:0.12em;text-transform:uppercase;color:#8FA4BF;padding:7px 9px 4px";

$quand_lbl = $is_it
    ? array('aujourdhui' => 'Oggi', 'weekend' => 'Questo weekend', 'semaine' => 'Questa settimana', 'mois' => 'Questo mese')
    : array('aujourdhui' => "Aujourd'hui", 'weekend' => 'Ce week-end', 'semaine' => 'Cette semaine', 'mois' => 'Ce mois-ci');
?>

<?php if ($cat_suggestion && $f_cat === ''): ?>
<div style='display:flex;align-items:center;gap:8px;background:#fff;border:1px dashed #E3DCCE;border-radius:9px;padding:8px 12px;margin-bottom:12px'>
  <svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='<?php echo esc_attr($ic); ?>' stroke-width='1.9' style='flex-shrink:0'><path d='M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z'></path></svg>
  <span style="flex:1;font-family:'Nunito Sans',sans-serif;font-size:12.5px;color:#6B6B67"><?php echo esc_html($LB['cat_existe']); ?> <strong style='color:#1D1D1B'><?php echo esc_html($cat_suggestion->name); ?></strong></span>
  <a href='<?php echo esc_url($url_f(array('cat' => $cat_suggestion->slug))); ?>' style="font-family:'Nunito Sans',sans-serif;font-size:11.5px;font-weight:800;color:<?php echo esc_attr($ic); ?>;text-decoration:none;white-space:nowrap"><?php echo esc_html($LB['filtrer_dessus']); ?></a>
</div>
<?php endif; ?>

<div style='display:flex;gap:7px;flex-wrap:wrap;align-items:flex-start;margin-bottom:6px'>

  <details style='position:relative'>
    <summary style='list-style:none;cursor:pointer;<?php echo esc_attr($f_ou !== '' ? $pill_on : $pill_off); ?>'>
      <svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='<?php echo esc_attr($ic); ?>' stroke-width='1.9'><path d='M12 21s7-6.3 7-11a7 7 0 1 0-14 0c0 4.7 7 11 7 11z'></path><circle cx='12' cy='10' r='2.6'></circle></svg>
      <?php echo esc_html($f_ou !== '' && isset($fac_ou[$f_ou]) ? $fac_ou[$f_ou]['label'] : $LB['ou']); ?>
      <svg width='11' height='11' viewBox='0 0 24 24' fill='none' stroke='#8FA4BF' stroke-width='2.6'><polyline points='6 9 12 15 18 9'></polyline></svg>
    </summary>
    <div style='<?php echo esc_attr($menu); ?>'>
      <?php if ($f_ou !== ''): ?><a href='<?php echo esc_url($url_f(array('ou' => null))); ?>' style='<?php echo esc_attr($opt); ?>;font-weight:700'><?php echo esc_html($LB['peu_importe']); ?></a><?php endif; ?>
      <?php foreach ($ou_par_terr as $terr_nom => $villes): ?>
        <div style='<?php echo esc_attr($grp); ?>'><?php echo esc_html($terr_nom); ?></div>
        <?php foreach ($villes as $vk => $vi): ?>
        <a href='<?php echo esc_url($url_f(array('ou' => $vk))); ?>' style='<?php echo esc_attr($opt); ?><?php echo $f_ou === $vk ? ';background:#F6F1E7;font-weight:700' : ''; ?>'><span><?php echo esc_html($vi['label']); ?></span><span style='color:#8FA4BF'><?php echo (int) $vi['n']; ?></span></a>
        <?php endforeach; ?>
      <?php endforeach; ?>
      <?php if (empty($ou_par_terr)): ?><div style='<?php echo esc_attr($grp); ?>'>—</div><?php endif; ?>
    </div>
  </details>

  <details style='position:relative'>
    <summary style='list-style:none;cursor:pointer;<?php echo esc_attr($f_quand !== '' ? $pill_on : $pill_off); ?>'>
      <svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='<?php echo esc_attr($ic); ?>' stroke-width='1.9'><rect x='3' y='5' width='18' height='16' rx='2'></rect><line x1='3' y1='10' x2='21' y2='10'></line><line x1='8' y1='3' x2='8' y2='7'></line><line x1='16' y1='3' x2='16' y2='7'></line></svg>
      <?php echo esc_html($f_quand !== '' && isset($quand_lbl[$f_quand]) ? $quand_lbl[$f_quand] : $LB['quand']); ?>
      <svg width='11' height='11' viewBox='0 0 24 24' fill='none' stroke='#8FA4BF' stroke-width='2.6'><polyline points='6 9 12 15 18 9'></polyline></svg>
    </summary>
    <div style='<?php echo esc_attr($menu); ?>'>
      <a href='<?php echo esc_url($url_f(array('quand' => null))); ?>' style='<?php echo esc_attr($opt); ?><?php echo $f_quand === '' ? ';background:#F6F1E7;font-weight:700' : ''; ?>'><?php echo esc_html($LB['peu_importe']); ?></a>
      <?php foreach ($quand_lbl as $qk => $qv): ?>
      <a href='<?php echo esc_url($url_f(array('quand' => $qk))); ?>' style='<?php echo esc_attr($opt); ?><?php echo $f_quand === $qk ? ';background:#F6F1E7;font-weight:700' : ''; ?>'><span><?php echo esc_html($qv); ?></span><span style='color:#8FA4BF'><?php echo (int) $fac_quand[$qk]; ?></span></a>
      <?php endforeach; ?>
    </div>
  </details>

  <a href='<?php echo esc_url($url_f(array('gratuit' => $only_free ? null : 1))); ?>' style='<?php echo esc_attr($only_free ? $pill_on : $pill_off); ?>'>
    <svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='<?php echo esc_attr($ic); ?>' stroke-width='1.9'><path d='M3 9V7a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v2a3 3 0 0 0 0 6v2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-2a3 3 0 0 0 0-6z'></path></svg>
    <?php echo esc_html($LB['gratuit']); ?><?php if ($fac_gratuit && !$only_free): ?> <span style='color:#8FA4BF;font-weight:400'><?php echo (int) $fac_gratuit; ?></span><?php endif; ?>
  </a>

  <details style='position:relative'<?php echo $f_cat !== '' ? ' open' : ''; ?>>
    <summary style='list-style:none;cursor:pointer;<?php echo esc_attr($f_cat !== '' ? $pill_on : $pill . ';background:transparent;border:1px dashed #E3DCCE;color:#6B6B67'); ?>'>
      <svg width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4'><line x1='12' y1='5' x2='12' y2='19'></line><line x1='5' y1='12' x2='19' y2='12'></line></svg>
      <?php echo esc_html($LB['plus_filtres']); ?>
    </summary>
    <div style='position:absolute;top:34px;left:0;width:330px;background:#fff;border:1px solid #E3DCCE;border-radius:10px;padding:13px;z-index:20'>
      <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#8FA4BF;margin-bottom:9px"><?php echo esc_html($LB['categorie']); ?></div>
      <div style='display:flex;gap:6px;flex-wrap:wrap'>
        <?php if ($f_cat !== ''): ?>
        <a href='<?php echo esc_url($url_f(array('cat' => null))); ?>' style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;background:#F2EDE3;border:1px solid #D8CFBC;border-radius:7px;padding:6px 11px;text-decoration:none"><?php echo esc_html($LB['peu_importe']); ?></a>
        <?php endif; ?>
        <?php foreach ($fac_cat as $ck => $ci): ?>
        <a href='<?php echo esc_url($url_f(array('cat' => $ck))); ?>' style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;background:<?php echo $f_cat === $ck ? '#F2EDE3' : '#F6F1E7'; ?>;border-radius:7px;padding:6px 11px;text-decoration:none"><?php echo esc_html($ci['label']); ?> <span style='color:#8FA4BF;font-weight:400'><?php echo (int) $ci['n']; ?></span></a>
        <?php endforeach; ?>
        <?php if (empty($fac_cat)): ?><span style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;color:#8FA4BF">—</span><?php endif; ?>
      </div>
    </div>
  </details>

</div>

<div style="font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#8FA4BF;margin-bottom:16px">
  <?php
  $n_res = 0;
  foreach (array('primary_q', 'secondary_q') as $var_q) { if (!empty($$var_q)) { $n_res += (int) $$var_q->post_count; } }
  echo esc_html(($actifs === 0 ? $LB['aucun_filtre'] : sprintf($LB['n_filtres'], $actifs)) . ' · ' . sprintf($LB['n_resultats'], $n_res));
  if ($actifs > 0) { echo " <a href='" . esc_url($url_f(array('ou' => null, 'quand' => null, 'cat' => null, 'gratuit' => null))) . "' style='color:" . esc_attr($ic) . ";font-weight:700;text-decoration:none'>" . esc_html($LB['tout_effacer']) . "</a>"; }
  ?>
</div>

<?php

            // 2026-08-03 : les ponctuels AVANT les longue duree.
            // Les trois requetes ci-dessus trient par _EventStartDate ASC, si bien
            // qu une exposition ouverte depuis mars remontait avant un festival qui
            // commence demain. Or on rate un evenement d un jour, jamais une expo
            // ouverte jusqu au 15 octobre. On reordonne donc apres construction,
            // comme le filtre gratuite plus haut, plutot que dans chaque WP_Query.
            // Les deja commences ne sont pas ecartes, seulement repousses, et tries
            // entre eux par date de FIN croissante : ce qui ferme le plus tot passe
            // devant, c est la seule urgence qui leur reste.
            $cs_tri_ponctuels = function ($q) {
                if (!$q || empty($q->posts)) { return; }
                $aujourdhui = current_time('Y-m-d');
                $rangs = array();
                foreach ($q->posts as $i => $pp) {
                    $d = substr((string) get_post_meta($pp->ID, '_EventStartDate', true), 0, 10);
                    $f = substr((string) get_post_meta($pp->ID, '_EventEndDate', true), 0, 10);
                    $commence = ($d !== '' && $d < $aujourdhui) ? 1 : 0;
                    $rangs[] = array('i' => $i, 'p' => $pp, 'c' => $commence, 'cle' => $commence ? $f : $d);
                }
                usort($rangs, function ($a, $b) {
                    if ($a['c'] !== $b['c']) { return $a['c'] - $b['c']; }
                    $s = strcmp($a['cle'], $b['cle']);
                    return $s !== 0 ? $s : ($a['i'] - $b['i']);
                });
                $q->posts = array_column($rangs, 'p');
                $q->post_count = count($q->posts);
            };
            $cs_tri_ponctuels($primary_q);
            $cs_tri_ponctuels($secondary_q);

            $has_primary = $primary_q && $primary_q->have_posts();
      $has_secondary = $secondary_q && $secondary_q->have_posts();
      $has_pages = $pages_q && $pages_q->have_posts();
      ?>

      <?php if ($query === ''): ?>

        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:12px"><?php echo esc_html($LB['raccourcis']); ?></div>
        <div style='display:flex;flex-direction:column;gap:8px;margin-bottom:22px'>
          <?php foreach ($shortcuts as $s): if (empty($s['url']) || is_wp_error($s['url'])) continue; ?>
          <a href='<?php echo esc_url($s['url']); ?>' style='display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;padding:12px 14px'>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B"><?php echo esc_html($s['label']); ?></div>
            <svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='#1D1D1B' stroke-width='1.8'><line x1='5' y1='12' x2='19' y2='12'></line><polyline points='13 6 19 12 13 18'></polyline></svg>
          </a>
          <?php endforeach; ?>
        </div>

      <?php elseif ($has_primary || $has_secondary || $has_pages): ?>

        <?php if ($has_pages): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:12px"><?php echo esc_html($LB['pages_guides']); ?></div>
        <div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px'>
          <?php while ($pages_q->have_posts()): $pages_q->the_post();
            $pid = get_the_ID();
            // 2026-08-03 : tous les hubs portent cs_hub_ville, y compris les territoires,
            // les secteurs et les provinces. Le libelle Ville etait donc faux pour
            // Savoie, Piemont, Comte de Nice, Chablais, Monferrato et les provinces.
            // On lit desormais cs_hub_type, pose explicitement sur chaque hub.
            $hub_type = get_post_meta($pid, 'cs_hub_type', true);
            if ($hub_type === 'territoire') { $tag = $LB['tag_territoire']; }
            elseif ($hub_type === 'ville' || get_post_meta($pid, 'cs_hub_ville', true)) { $tag = $LB['tag_ville']; }
            elseif (get_post_meta($pid, 'cs_guide_territoire', true)) { $tag = $LB['tag_guide']; }
            else { $tag = (get_post_type($pid) === 'post') ? $LB['tag_article'] : $LB['tag_page']; }
          ?>
          <a href='<?php echo esc_url(get_permalink($pid)); ?>' style="display:inline-flex;align-items:baseline;gap:7px;text-decoration:none;background:#fff;border:1px solid #E3DCCE;border-radius:10px;padding:8px 13px">
            <span style="font-family:'Nunito Sans',sans-serif;font-size:9.5px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;color:#8A6D3B"><?php echo esc_html($tag); ?></span>
            <span style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;font-weight:700;color:#1D1D1B"><?php echo esc_html(get_the_title($pid)); ?></span>
          </a>
          <?php endwhile; wp_reset_postdata(); ?>
        </div>
        <?php endif; ?>

        <?php if ($has_primary):
          $primary_header = $loc ? sprintf($LB['a_ville'], $loc['label']) : ($cat_term ? $cat_term->name : sprintf($LB['evenements_pour'], $query));
        ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:4px"><?php echo esc_html($primary_header); ?></div>
        <?php foreach ($primary_q->posts as $ppost): echo cs_card_compact($ppost->ID); endforeach; ?>
        <?php endif; ?>

        <?php if ($has_secondary):
          $secondary_header = $loc ? sprintf($LB['alentours'], $loc['label']) : sprintf($LB['autres_resultats'], $query);
        ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin:18px 0 4px"><?php echo esc_html($secondary_header); ?></div>
        <?php while ($secondary_q->have_posts()): $secondary_q->the_post(); echo cs_card_compact(get_the_ID()); endwhile; wp_reset_postdata(); ?>
        <?php endif; ?>

      <?php else: ?>

        <div style='padding:32px 0 24px;text-align:center'>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;color:#4A4A48;margin-bottom:14px"><?php echo esc_html($LB['aucun_resultat']); ?></div>
          <div style='display:flex;gap:8px;justify-content:center;flex-wrap:wrap'>
            <a href='<?php echo esc_url(get_permalink($is_it ? 1789 : 930)); ?>' style="text-decoration:none;border:1px solid #1D1D1B;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B"><?php echo esc_html($LB['ce_weekend']); ?></a>
            <a href='<?php echo esc_url(get_permalink($is_it ? 1790 : 932)); ?>' style="text-decoration:none;border:1px solid #1D1D1B;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B"><?php echo esc_html($LB['tout_agenda']); ?></a>
          </div>
        </div>

      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
