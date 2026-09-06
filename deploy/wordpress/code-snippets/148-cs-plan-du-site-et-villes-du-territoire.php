/**
 * CS - Plan du site genere + liste des villes sur les hubs (2026-08-18)
 *
 * POURQUOI. Le plan du site etait 10 Ko de HTML ecrit a la main. Les 112 pages
 * creees le 2026-08-18 n'y figuraient pas, et n'auraient jamais pu y figurer
 * sans une reecriture manuelle a chaque ajout. Il est desormais calcule.
 *
 * Franck demandait comment retrouver ces pages autrement que par la recherche,
 * en evoquant un nuage de mots. Un nuage donne le meme poids a tout et efface
 * la hierarchie ; ces pages ont une structure nette, territoire puis ville puis
 * moment. D'ou deux surfaces :
 *
 *  - [cs_plan_du_site] : l'index complet, arborescent ;
 *  - [cs_villes_du_territoire] : une rangee de pastilles vers les villes du
 *    territoire, a poser sur un hub. C'est la forme la plus proche d'un nuage
 *    qui reste utile : compacte, scannable, contextuelle.
 *
 * Tout est lu depuis les pages reelles (meta cs_hub_ville), donc rien ne vieillit.
 *
 * PIEGE EVITE : ne pas ecrire \x{2019} dans une chaine PHP simple, cela ne vaut
 * que dans une expression reguliere et s'afficherait litteralement. Les vrais
 * caracteres sont ecrits en clair ci-dessous.
 */
if (!function_exists('cs_plan_zones')) {
function cs_plan_zones($lang) {
    $hubs = get_posts(array(
        'post_type' => 'page', 'post_status' => 'publish', 'posts_per_page' => -1,
        'lang' => $lang, 'meta_key' => 'cs_hub_ville', 'meta_value' => '1',
    ));
    $zones = array();
    foreach ($hubs as $p) {
        // Le filtre lang de get_posts ne mord pas hors contexte front : les hubs FR et
        // IT portent le meme titre, chaque zone sortait donc en double. Filtre explicite.
        if (function_exists('pll_get_post_language') && pll_get_post_language($p->ID) !== $lang) { continue; }
        $racine = $p->post_parent ? $p->post_parent : $p->ID;
        $quand = get_post_meta($p->ID, 'cs_hub_quand', true);
        if ($quand === '') { $quand = 'hub'; }
        $zones[$racine]['quand'][$quand] = $p->ID;
        if (!isset($zones[$racine]['nom'])) {
            $zones[$racine]['nom'] = get_the_title($racine);
            $zones[$racine]['terr'] = get_post_meta($racine, 'cs_hub_territoire', true);
            $zones[$racine]['type'] = get_post_meta($racine, 'cs_hub_type', true);
        }
    }
    return $zones;
}
}

if (!function_exists('cs_villes_du_territoire')) {
function cs_villes_du_territoire($atts) {
    $a = shortcode_atts(array('territoire' => '', 'titre' => ''), $atts, 'cs_villes_du_territoire');
    // pll_current_language() rend false hors contexte front : le ternaire retenait
    // false et plus aucune page ne correspondait. Repli explicite sur le francais.
    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    if (!$lang) { $lang = 'fr'; }
    $moi = (int) get_queried_object_id();
    $terr = $a['territoire'];
    if (!$terr) { $terr = get_post_meta($moi, 'cs_hub_territoire', true); }
    if (!$terr) { return ''; }

    $zones = cs_plan_zones($lang);
    $liens = array();
    foreach ($zones as $id => $z) {
        if ((int) $id === $moi) { continue; }
        if ($z['terr'] !== $terr) { continue; }
        if ($z['type'] === 'territoire' && mb_stripos($z['nom'], 'provinc') === false) { continue; }
        $liens[$z['nom']] = get_permalink($id);
    }
    if (!$liens) { return ''; }
    ksort($liens);

    $titre = $a['titre'];
    if ($titre === '') { $titre = ($lang === 'it') ? 'Città e zone' : 'Villes et zones'; }

    $out = '<div id="villes-et-zones" style="margin:26px 0 6px;border-top:2px solid #1D1D1B;padding-top:16px">';
    $out .= '<div style="font-family:sans-serif;font-weight:700;font-size:19px;color:#1D1D1B;margin-bottom:10px">' . esc_html($titre) . '</div>';
    $out .= '<div style="display:flex;flex-wrap:wrap;gap:8px">';
    foreach ($liens as $nom => $url) {
        $out .= '<a href="' . esc_url($url) . '" style="display:inline-block;padding:7px 13px;border:1px solid #C9BFAD;border-radius:999px;text-decoration:none;color:#18365E;font-family:sans-serif;font-size:13.5px;font-weight:700;background:#FBF7F0">' . esc_html($nom) . '</a>';
    }
    $out .= '</div></div>';
    return $out;
}
}
add_shortcode('cs_villes_du_territoire', 'cs_villes_du_territoire');

if (!function_exists('cs_plan_du_site')) {
function cs_plan_du_site($atts) {
    // pll_current_language() rend false hors contexte front : le ternaire retenait
    // false et plus aucune page ne correspondait. Repli explicite sur le francais.
    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    if (!$lang) { $lang = 'fr'; }
    $it = ($lang === 'it');
    $zones = cs_plan_zones($lang);

    $ordre = $it
        ? array('aujourdhui' => 'Oggi', 'weekend' => 'Questo weekend', 'semaine' => 'Questa settimana')
        : array('aujourdhui' => 'Aujourd’hui', 'weekend' => 'Ce week-end', 'semaine' => 'Cette semaine');

    $terrs = array();
    foreach ($zones as $id => $z) { $terrs[$z['terr']][$id] = $z; }

    $noms_terr = $it
        ? array('savoie' => 'Savoia', 'piemont' => 'Piemonte', 'vda' => 'Valle d’Aosta', 'nice' => 'Contea di Nizza')
        : array('savoie' => 'Savoie', 'piemont' => 'Piémont', 'vda' => 'Vallée d’Aoste', 'nice' => 'Comté de Nice');

    $st_h2 = 'font-family:sans-serif;font-weight:600;font-size:20px;color:#1D1D1B;margin:26px 0 10px;border-top:2px solid #1D1D1B;padding-top:16px';
    $st_li = 'border-top:1px solid #E3DCCE;padding:9px 0;font-family:sans-serif;font-size:14px';
    $st_a  = 'text-decoration:none;color:#18365E;font-weight:700';
    $st_s  = 'text-decoration:none;color:#6F6B62;font-weight:400';

    $out = '<p style="font-family:sans-serif;font-size:14px;line-height:1.6;color:#4A4A48">'
         . ($it ? 'Tutte le pagine dell’agenda, per territorio, città e momento.' : 'Toutes les pages de l’agenda, par territoire, ville et moment.')
         . '</p>';

    foreach ($noms_terr as $code => $libelle) {
        if (empty($terrs[$code])) { continue; }
        $out .= '<h2 style="' . $st_h2 . '">' . esc_html($libelle) . '</h2><ul style="margin:0;padding:0;list-style:none">';
        $liste = $terrs[$code];
        uasort($liste, function ($a, $b) { return strcmp($a['nom'], $b['nom']); });
        foreach ($liste as $id => $z) {
            $out .= '<li style="' . $st_li . '">';
            $out .= '<a href="' . esc_url(get_permalink($id)) . '" style="' . $st_a . '">' . esc_html($z['nom']) . '</a>';
            $suite = array();
            foreach ($ordre as $k => $lib) {
                if (!empty($z['quand'][$k])) {
                    $suite[] = '<a href="' . esc_url(get_permalink($z['quand'][$k])) . '" style="' . $st_s . '">' . esc_html($lib) . '</a>';
                }
            }
            if ($suite) { $out .= ' <span style="color:#C9BFAD">|</span> ' . implode(' <span style="color:#C9BFAD">·</span> ', $suite); }
            $out .= '</li>';
        }
        $out .= '</ul>';
    }

    return $out;
}
}
add_shortcode('cs_plan_du_site', 'cs_plan_du_site');
