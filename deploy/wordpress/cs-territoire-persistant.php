<?php
/*
Plugin Name: Agenda Sabauda — Territoire persistant site-wide (cookie + bandeau global)
Description: Chantier "territoire partout" demande par Franck le 2026-07-20 :
  1) PERSISTANCE — tout clic ?as_territoire=<slug> pose un cookie 'as_territoire'
     (cle canonique savoie|piemont|vda|nice, 30 jours) ; ?as_territoire=tous / tutti
     l'efface. Le choix survit donc a la navigation, plus seulement a l'URL courante.
  2) FILTRE HOME VIA COOKIE — les requetes home (14-21) sont filtrees par le cookie
     quand aucun ?as_territoire n'est dans l'URL (le cas GET reste gere par
     cs-home-territoire-filtre.php / cs-home-territoire-choix-langue.php, ce fichier
     ne double jamais leur tax_query).
  3) LIBELLE HOME VIA COOKIE — meme logique de non-recouvrement pour "Vous regardez X".
  4) BANDEAU GLOBAL — wp_body_open prio 6 (juste apres le header de marque, prio 5,
     cf. snippet 19 site-header-footer.php, VOLONTAIREMENT NON MODIFIE — convention
     du site : nouveau comportement = nouveau fichier) : sur toutes les pages sauf les
     home (qui ont leur propre bandeau bake dans leur contenu), affiche "Vous regardez
     X | Changer : ..." + "Tous les territoires", ou "Choisir votre territoire :" si
     aucun choix actif. Piémont/Vallee d'Aoste passent par l'interstitiel de choix de
     langue (?choix_territoire=, cf. cs-home-territoire-choix-langue.php).

  Le filtrage des pages LISTES (Ce week-end, Tout l'agenda...) selon ce territoire vit
  dans cs-agenda-list-shared.php (cs_render_agenda_list_page) — il utilise
  cs_territoire_actif() defini ici.

  Rollback : supprimer ce fichier (le cookie residuel devient inerte).
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_terr_canon_data')) {
function cs_terr_canon_data() {
    return [
        'savoie'  => ['fr_slug' => 'savoie',  'it_slug' => 'savoia',   'fr_term' => 3,  'it_term' => 318, 'fr_name' => 'Savoie',          'it_name' => 'Savoia'],
        'piemont' => ['fr_slug' => 'piemont',              'it_slug' => 'piemonte',             'fr_term' => 6,  'it_term' => 321, 'fr_name' => 'Piémont',         'it_name' => 'Piemonte'],
        'vda'     => ['fr_slug' => 'vallee-d-aoste',       'it_slug' => 'valle-d-aosta',        'fr_term' => 8,  'it_term' => 324, 'fr_name' => "Vallée d'Aoste",  'it_name' => "Valle d'Aosta"],
        'nice'    => ['fr_slug' => 'comte-de-nice', 'it_slug' => 'contea-di-nizza', 'fr_term' => 10, 'it_term' => 327, 'fr_name' => 'Comté de Nice',   'it_name' => 'Contea di Nizza'],
    ];
}
}

if (!function_exists('cs_terr_slug_to_canon')) {
function cs_terr_slug_to_canon($slug) {
    foreach (cs_terr_canon_data() as $key => $t) {
        if ($slug === $t['fr_slug'] || $slug === $t['it_slug']) {
            return $key;
        }
    }
    return null;
}
}

if (!function_exists('cs_territoire_actif')) {
// Cle canonique ('savoie'|'piemont'|'vda'|'nice') du territoire actif : GET prioritaire,
// cookie en repli. Null si rien de valide.
function cs_territoire_actif() {
    if (!empty($_GET['as_territoire'])) {
        $canon = cs_terr_slug_to_canon(sanitize_title(wp_unslash($_GET['as_territoire'])));
        if ($canon) {
            return $canon;
        }
    }
    if (!empty($_COOKIE['as_territoire'])) {
        $key = sanitize_key(wp_unslash($_COOKIE['as_territoire']));
        if (isset(cs_terr_canon_data()[$key])) {
            return $key;
        }
    }
    return null;
}
}

// Persistance : tout clic sur un territoire (?as_territoire=<slug>) pose le cookie 30 jours ;
// ?as_territoire=tous l'efface (retour a la vue 4 territoires).
//
// 2026-08-02 (Franck) : la pose du cookie est extraite dans une fonction et rejouee
// sur 'parse_request'. RAISON : les jolies URLs (/explore/<slug>/, /choisir/<slug>/,
// /it/scopri/<slug>/, cf. cs-territoire-urls-jolies.php) n'injectent $_GET['as_territoire']
// qu'au moment de 'parse_request' -- soit APRES le hook 'init' ci-dessous. Le
// parametre arrivait donc toujours trop tard et AUCUN des liens de la barre
// territoire ne posait le cookie : on atterrissait bien sur la page du territoire,
// mais le site n'en gardait aucune memoire, et la navigation suivante (Ce week-end,
// Aujourd'hui...) repartait sur les 4 territoires. Bug signale le 2026-08-02.
if (!function_exists('cs_territoire_pose_cookie')) {
function cs_territoire_pose_cookie() {
    if (headers_sent()) { return; }
    // /choisir/<slug>/ (interstitiel de langue Piemont/VdA) vaut aussi choix de territoire.
    $raw = '';
    if (!empty($_GET['as_territoire']))      { $raw = sanitize_title(wp_unslash($_GET['as_territoire'])); }
    elseif (!empty($_GET['choix_territoire'])) { $raw = sanitize_title(wp_unslash($_GET['choix_territoire'])); }
    if ($raw === '') { return; }
    if ($raw === 'tous' || $raw === 'tutti') {
        setcookie('as_territoire', '', time() - 3600, '/');
        unset($_COOKIE['as_territoire']);
        return;
    }
    $canon = cs_terr_slug_to_canon($raw);
    if ($canon) {
        setcookie('as_territoire', $canon, time() + 30 * DAY_IN_SECONDS, '/');
        $_COOKIE['as_territoire'] = $canon;
    }
}
}
add_action('parse_request', 'cs_territoire_pose_cookie', 20);
add_action('init', function () {
    if (empty($_GET['as_territoire'])) {
        return;
    }
    $raw = sanitize_title(wp_unslash($_GET['as_territoire']));
    if ($raw === 'tous' || $raw === 'tutti') {
        setcookie('as_territoire', '', time() - 3600, '/');
        unset($_COOKIE['as_territoire']);
        return;
    }
    $canon = cs_terr_slug_to_canon($raw);
    if ($canon) {
        setcookie('as_territoire', $canon, time() + 30 * DAY_IN_SECONDS, '/');
        $_COOKIE['as_territoire'] = $canon;
    }
}, 5);

// Filtre des requetes home (14-21) via COOKIE quand aucun ?as_territoire n'est present
// (le cas GET est deja gere par cs-home-territoire-filtre.php / -choix-langue.php).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [14, 15, 16, 17, 18, 19, 20, 21], true)) {
        return $args;
    }
    if (!empty($_GET['as_territoire'])) {
        return $args;
    }
    $canon = cs_territoire_actif();
    if (!$canon) {
        return $args;
    }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $t = cs_terr_canon_data()[$canon];
    $term_id = $lang === 'it' ? $t['it_term'] : $t['fr_term'];

    $args['tax_query'] = $args['tax_query'] ?? [];
    $args['tax_query'][] = ['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $term_id];
    return $args;
}, 10, 2);

// Libelle "Vous regardez X" de la home via COOKIE (le cas GET est deja gere par
// cs-home-territoire-choix-langue.php).
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (!is_page($home_ids) || !empty($_GET['as_territoire'])) {
        return $content;
    }
    $canon = cs_territoire_actif();
    if (!$canon) {
        return $content;
    }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $t = cs_terr_canon_data()[$canon];
    $new_name = $lang === 'it' ? $t['it_name'] : $t['fr_name'];
    $default_name = $lang === 'it' ? 'i 4 territori' : 'les 4 territoires';
    if ($new_name === $default_name) {
        return $content;
    }
    return str_replace(
        '<strong style="color:#DC5D45">' . esc_html($default_name) . '</strong>',
        '<strong style="color:#DC5D45">' . esc_html($new_name) . '</strong>',
        $content
    );
}, 21);

// Bandeau territoire SITE-WIDE : injecte sous le header de marque (wp_body_open prio 6,
// juste apres le header prio 5 de site-header-footer.php) sur TOUTES les pages SAUF les
// home (928/1717). MEME UX/UI que le bandeau de la home (demande Franck 2026-07-20) :
// "Vous regardez X" + label souligne rouge "Changer de territoire" ouvrant un dropdown
// (checkbox hack CSS, reutilise les classes .as-terr-toggle/.as-terr-dropdown de
// components.css — selecteurs par classe, donc partages sans modification du CSS).
add_action('wp_body_open', function () {
    // 2026-07-22 (Franck) : re-exclusion des home (928 FR / 1717 IT). Le bandeau
    // wp_body_open s'affiche AVANT tout le contenu (donc au-dessus du masthead), alors
    // que la home a deja sa propre barre bakee dans le contenu, correctement placee
    // juste sous la ligne FR|IT|menu. Le doublon du dessus etait le seul visible (celui
    // dans le contenu n'etait pas reellement masque malgre le commentaire d'origine).
    if (in_array(get_queried_object_id(), array(928, 1717), true)) { return; }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $is_it = $lang === 'it';
    $TERR = cs_terr_canon_data();
    $actif = cs_territoire_actif();
    // Contexte (option A, Franck 2026-07-21) : sur une page LIEU (hub ville, meta
    // cs_hub_territoire) ou une fiche evenement, la barre reflete le territoire de la
    // PAGE, pas le cookie -> plus de contradiction titre/barre.
    if (is_page() && ($cs_pm = get_post_meta(get_queried_object_id(), 'cs_hub_territoire', true)) && isset($TERR[$cs_pm])) {
        $actif = $cs_pm;
    } elseif (is_singular('tribe_events')) {
        $cs_tt = wp_get_post_terms(get_queried_object_id(), 'territoire', array('fields' => 'ids'));
        if ($cs_tt && !is_wp_error($cs_tt)) {
            foreach ($TERR as $cs_k => $cs_t) {
                if (in_array((int) $cs_t['fr_term'], $cs_tt, true) || in_array((int) $cs_t['it_term'], $cs_tt, true)) { $actif = $cs_k; break; }
            }
        }
    }

    $link_for = function ($key) use ($TERR, $is_it) {
        $t = $TERR[$key];
        if ($is_it) {
            return 'https://agendasabauda.eu/it/scopri/' . $t['it_slug'] . '/';
        }
        if ($key === 'piemont' || $key === 'vda') {
            return 'https://agendasabauda.eu/choisir/' . $t['fr_slug'] . '/';
        }
        return 'https://agendasabauda.eu/explore/' . $t['fr_slug'] . '/';
    };
    // 2026-09-08 (Franck) : URL jolie (cs-territoire-urls-jolies.php, 06/08) plutôt que ?as_territoire=tous.
    $reset_url = ($is_it ? 'https://agendasabauda.eu/it/spazio-sabaudo/' : 'https://agendasabauda.eu/espace-sabaudo/');

    // Sans territoire choisi, on INVITE explicitement plutot que de decrire un etat
    // ("Vous regardez les 4 territoires" n'appelle aucune action).
    // 2026-08-02 (Franck) : l'invitation passe du texte de GAUCHE (etat) au LIEN de
    // DROITE (action). L'ancienne formule longue ("Choisissez votre territoire, ou
    // restez sur les 4 territoires") passait sur 2 lignes sous 400px : la barre
    // faisait 58px de haut sur mobile contre 40px pour la barre equivalente des
    // home -- deux hauteurs de header differentes selon la page. Le libelle d'etat
    // est desormais le meme partout, et c'est le libelle du lien qui porte l'appel
    // a l'action ("Choisir" tant que rien n'est selectionne, "Changer" ensuite).
    $watching = $is_it ? 'Stai guardando' : 'Vous regardez';
    $change = $actif
        ? ($is_it ? 'Cambia territorio' : 'Changer de territoire')
        : ($is_it ? 'Scegli un territorio' : 'Choisir un territoire');
    $all_label = $is_it ? 'Tutti i territori' : 'Tous les territoires';
    $neutral = $is_it ? 'i 4 territori' : 'les 4 territoires';
    $active_name = $actif ? ($is_it ? $TERR[$actif]['it_name'] : $TERR[$actif]['fr_name']) : $neutral;
    ?>
    <div class="as-terr-bar" style="background:#FBF7F0">
      <div style="max-width:900px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;padding:10px 20px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;color:#1D1D1B"><?php echo esc_html($watching); ?> <strong style="color:#DC5D45"><?php echo esc_html($active_name); ?></strong></div>
        <div class="as-terr-bar__links" style="display:none;align-items:center;gap:16px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62"><?php echo $is_it ? 'Cambia:' : 'Changer :'; ?></div>
          <?php foreach ($TERR as $k2 => $t2): ?>
          <a href="<?php echo esc_url($link_for($k2)); ?>" class="as-terr-link" style="text-decoration:none;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:<?php echo ($k2 === $actif) ? '800' : '600'; ?>;color:<?php echo ($k2 === $actif) ? '#DC5D45' : '#6F6B62'; ?>"><?php echo esc_html($is_it ? $t2['it_name'] : $t2['fr_name']); ?></a>
          <?php endforeach; ?>
          <?php if ($actif): ?>
          <a href="<?php echo esc_url($reset_url); ?>" class="as-terr-link" style="text-decoration:none;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:600;color:#6F6B62"><?php echo esc_html($all_label); ?></a>
          <?php endif; ?>
        </div>
        <label for="as-terr-toggle-global" class="as-terr-bar__toggle" style="cursor:pointer;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:800;color:#DC5D45;text-decoration:underline"><?php echo esc_html($change); ?></label>
      </div>
      <input type="checkbox" id="as-terr-toggle-global" class="as-terr-toggle">
      <div class="as-terr-dropdown" style="max-width:900px;margin:0 auto;left:0;right:0">
        <?php foreach ($TERR as $key => $tt): $is_active = ($key === $actif); ?>
        <a href="<?php echo esc_url($link_for($key)); ?>" style="display:block;text-decoration:none;padding:12px 20px;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:<?php echo $is_active ? '800' : '400'; ?>;color:#1D1D1B;border-top:1px solid #E3DCCE"><?php echo esc_html($is_it ? $tt['it_name'] : $tt['fr_name']); ?></a>
        <?php endforeach; ?>
        <?php if ($actif): ?>
        <a href="<?php echo esc_url($reset_url); ?>" style="display:block;text-decoration:none;padding:12px 20px;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:400;color:#6F6B62;border-top:1px solid #E3DCCE"><?php echo esc_html($all_label); ?></a>
        <?php endif; ?>
      </div>
    </div>
    <?php
}, 6);


// Filtre territoire des listings home SANS custom query (elements 'weekend', 'venir',
// 'venir-bottom' -- desktop "Ce week-end", "L'agenda a venir" x2). Les autres sections
// passent par les requetes Query Builder 14-21, deja couvertes plus haut. Meme hook
// (jet-engine/listing/grid/posts-query-args) et meme convention par _element_id que
// les snippets 44/45/54. Couvre GET et cookie via cs_territoire_actif().
add_filter('jet-engine/listing/grid/posts-query-args', function ($args, $render, $settings) {
    $eid = $settings['_element_id'] ?? '';
    if (!in_array($eid, ['weekend', 'venir', 'venir-bottom'], true)) {
        return $args;
    }
    $canon = cs_territoire_actif();
    if (!$canon) {
        return $args;
    }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $t = cs_terr_canon_data()[$canon];
    $term_id = $lang === 'it' ? $t['it_term'] : $t['fr_term'];

    $args['tax_query'] = $args['tax_query'] ?? [];
    $args['tax_query'][] = ['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $term_id];
    return $args;
}, 25, 3);

// Regeneration DYNAMIQUE des listes de territoires des bandeaux de la home (desktop
// "Changer :"/"Cambia:" + dropdown mobile). Signale par Franck le 2026-07-20 : la liste
// statique excluait toujours Savoie/Savoia (suppose actif a l'ecriture) -- avec Piemonte
// actif, on voyait "Cambia: Piemonte, Valle d'Aosta, Nizza" (l'actif en double, Savoia
// absente). Regle : la rangee desktop liste les territoires AUTRES que l'actif (ou les 4
// si aucun), le dropdown mobile liste les 4 (actif en gras) + "Tous les territoires" si
// un choix est actif.
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (!is_page($home_ids)) {
        return $content;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $is_it = $lang === 'it';
    $TERR = cs_terr_canon_data();
    $actif = cs_territoire_actif();
    // Contexte (option A, Franck 2026-07-21) : sur une page LIEU (hub ville, meta
    // cs_hub_territoire) ou une fiche evenement, la barre reflete le territoire de la
    // PAGE, pas le cookie -> plus de contradiction titre/barre.
    if (is_page() && ($cs_pm = get_post_meta(get_queried_object_id(), 'cs_hub_territoire', true)) && isset($TERR[$cs_pm])) {
        $actif = $cs_pm;
    } elseif (is_singular('tribe_events')) {
        $cs_tt = wp_get_post_terms(get_queried_object_id(), 'territoire', array('fields' => 'ids'));
        if ($cs_tt && !is_wp_error($cs_tt)) {
            foreach ($TERR as $cs_k => $cs_t) {
                if (in_array((int) $cs_t['fr_term'], $cs_tt, true) || in_array((int) $cs_t['it_term'], $cs_tt, true)) { $actif = $cs_k; break; }
            }
        }
    }

    $link_for = function ($key) use ($TERR, $is_it) {
        $t = $TERR[$key];
        if ($is_it) {
            return 'https://agendasabauda.eu/it/scopri/' . $t['it_slug'] . '/';
        }
        if ($key === 'piemont' || $key === 'vda') {
            return 'https://agendasabauda.eu/choisir/' . $t['fr_slug'] . '/';
        }
        return 'https://agendasabauda.eu/explore/' . $t['fr_slug'] . '/';
    };
    $name_for = function ($key) use ($TERR, $is_it) {
        return $is_it ? $TERR[$key]['it_name'] : $TERR[$key]['fr_name'];
    };
    // 2026-09-08 (Franck) : URL jolie (cs-territoire-urls-jolies.php, 06/08) plutôt que ?as_territoire=tous.
    $reset_url = $is_it ? 'https://agendasabauda.eu/it/spazio-sabaudo/' : 'https://agendasabauda.eu/espace-sabaudo/';
    $all_label = $is_it ? 'Tutti i territori' : 'Tous les territoires';

    // --- Rangee desktop "Changer :" / "Cambia:" ---
    $change_word = $is_it ? 'Cambia:' : 'Changer :';
    $desktop_links = '';
    foreach ($TERR as $key => $t) {
        if ($key === $actif) {
            continue;
        }
        $desktop_links .= '  <a href="' . esc_url($link_for($key)) . '" class="as-terr-link" style="text-decoration:none;font-family:\'Nunito Sans\',sans-serif;font-size:12px;font-weight:600;color:#6F6B62">' . esc_html($name_for($key)) . '</a>' . "\n";
    }
    if ($actif) {
        $desktop_links .= '  <a href="' . esc_url($reset_url) . '" class="as-terr-link" style="text-decoration:underline;font-family:\'Nunito Sans\',sans-serif;font-size:12px;font-weight:600;color:#6F6B62">' . esc_html($all_label) . '</a>' . "\n";
    }

    $content = preg_replace(
        '#(<div style="font-family:\'Nunito Sans\',sans-serif;font-size:12px;color:\#6F6B62">' . preg_quote($change_word, '#') . '</div>)\s*(?:<a [^>]*class="as-terr-link"[^>]*>[^<]+</a>\s*)+(</div>)#u',
        '$1' . "\n" . str_replace(['\\', '$'], ['\\\\', '\\$'], $desktop_links) . '$2',
        $content,
        1
    );

    // --- Dropdown mobile ---
    $dropdown_links = '';
    foreach ($TERR as $key => $t) {
        $weight = ($key === $actif) ? '800' : '400';
        $dropdown_links .= '    <a href="' . esc_url($link_for($key)) . '" style="display:block;text-decoration:none;padding:12px 20px;font-family:\'Nunito Sans\',sans-serif;font-size:13px;font-weight:' . $weight . ';color:#1D1D1B;border-top:1px solid #E3DCCE">' . esc_html($name_for($key)) . '</a>' . "\n";
    }
    if ($actif) {
        $dropdown_links .= '    <a href="' . esc_url($reset_url) . '" style="display:block;text-decoration:none;padding:12px 20px;font-family:\'Nunito Sans\',sans-serif;font-size:13px;font-weight:400;color:#6F6B62;border-top:1px solid #E3DCCE">' . esc_html($all_label) . '</a>' . "\n";
    }

    $content = preg_replace(
        '#(<div class="as-terr-dropdown">).*?(</div>)#su',
        '$1' . "\n" . str_replace(['\\', '$'], ['\\\\', '\\$'], $dropdown_links) . '  $2',
        $content,
        1
    );

    return $content;
}, 23);

// CARROUSEL "Selections" adapte au territoire actif (demande Franck 2026-07-20 :
// "le carrousel doit etre adapte a la localisation"). Query Builder ID 4
// (selections-home). Regles :
//  - selections d'un territoire precis (sel_territoire != 'tous') : visibles seulement
//    si leur territoire correspond au territoire actif ;
//  - selections generiques (sel_territoire = 'tous') : toujours visibles (leur PAGE
//    de destination se filtre elle-meme sur le territoire actif, cf. gabarit CS58) ;
//  - exception : les selections "Ca vaut le deplacement" (1729 FR) / "Vale il viaggio"
//    (1736 IT) sont masquees quand un territoire est actif -- "on ne va pas mettre
//    'ca vaut le detour' quand on y est deja".
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || 4 !== (int) $query->id) {
        return $args;
    }
    $canon = cs_territoire_actif();
    if (!$canon) {
        return $args;
    }
    $fr_slug = cs_terr_canon_data()[$canon]['fr_slug'];

    $args['meta_query'] = $args['meta_query'] ?? [];
    $args['meta_query'][] = [
        'key'     => 'sel_territoire',
        'value'   => ['tous', $fr_slug],
        'compare' => 'IN',
    ];

    $exclusions = [1729, 1736]; // Ca vaut le deplacement / Vale il viaggio
    $args['post__not_in'] = array_merge($args['post__not_in'] ?? [], $exclusions);

    return $args;
}, 15, 2);


// Section home "Ca vaut le deplacement" : le versant montre devient l'OPPOSE du
// territoire ACTIF (et plus seulement l'oppose de la langue). Queries 22 (home FR) et
// 23 (home IT). Sans territoire actif : comportement d'origine inchange (versant
// oppose de la langue).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    $qid = (int) ($query->id ?? 0);
    if (!in_array($qid, [22, 23], true)) {
        return $args;
    }
    $canon = cs_territoire_actif();
    if (!$canon) {
        return $args;
    }
    $side = in_array($canon, ['piemont', 'vda'], true) ? 'it' : 'fr';
    // Termes du versant OPPOSE, dans la langue des events de la query (22=FR, 23=IT).
    if ($qid === 22) {
        $terms = $side === 'it' ? [3, 10] : [6, 8];   // FR terms : Savoie+Nice / Piemont+VdA
    } else {
        $terms = $side === 'it' ? [318, 327] : [321, 324]; // IT terms : Savoia+Nizza / Piemonte+VdA
    }
    $args['tax_query'] = [[
        'taxonomy' => 'territoire',
        'field'    => 'term_id',
        'terms'    => $terms,
    ]];
    return $args;
}, 15, 2);