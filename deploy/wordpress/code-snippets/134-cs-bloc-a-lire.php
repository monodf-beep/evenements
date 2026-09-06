/**
 * CS - Bloc A lire (rendu PHP) -- REECRIT le 2026-09-06 (Franck) pour les regles
 * discutees en session ce jour-la, sur la maquette "Le moteur d'A lire" :
 *
 *   1. Territoire actif d'abord, jusqu'a 4 places (2 cartes + 2 lignes -- ou 3
 *      lignes selon combien passent en carte, cf. plus bas).
 *   2. Saison : `cs_guide_saison_debut`/`cs_guide_saison_fin` (Custom Fields,
 *      YYYY-MM-DD, facultatifs) -- un article HORS SAISON est EXCLU (regle 5 du
 *      depot : on ne travaille que sur ce qui est encore devant nous), pas
 *      seulement relegue. Vide des deux cotes = intemporel, toujours eligible.
 *      En saison AVANT intemporel, tri par fin la plus proche (derniere chance).
 *   3. Diversite de sujet (`cs_guide_cat_term`) : pas deux places du meme sujet
 *      si un autre sujet eligible peut remplir la place.
 *   4. Ex aequo : rotation quotidienne (hash jour+id), jamais figee sur la date
 *      de publication -- meme defaut que celui deja corrige sur "A la une".
 *   5. Repli si le territoire n'a pas 4 locaux eligibles : complete avec les
 *      autres territoires, MAIS jamais mélangé aux locaux -- sous le bandeau
 *      "Ailleurs dans l'espace sabaudo", comme "Ca vaut le deplacement" le fait
 *      deja. Franck, le 06/09, sur l'ancien rendu : "je ne sais pas si on
 *      mélange des territoires" -- le bandeau est la reponse.
 *   6. Voisin : une place SUPPLEMENTAIRE (pas comptee dans les 4 locaux),
 *      reservee a un territoire limitrophe (carte de proximite ci-dessous),
 *      meme quand le territoire actif a largement de quoi remplir ses 4 places.
 *      Distincte du repli : le repli comble un manque, le voisin est une
 *      promesse editoriale ("l'espace sabaudo"), toujours tentee.
 *
 * Verifie en direct sur les 6 guides reels le 06/09 (voir conversation) : avec
 * un corpus aussi petit, "voisin" est souvent absorbe par le repli (rien ne
 * reste pour lui) -- pas un bug, juste la consequence honnete d'un stock qui
 * va grossir (Franck : "les contenus arriveront").
 *
 * PAS DE FILTRE PAR SUJET SEUL (page categorie) POUR L'INSTANT : croiser sujet
 * + territoire viderait la section avec 6 guides au total. A revoir si le
 * stock grossit beaucoup (voir conversation du 06/09).
 *
 * DEBOGAGE : `?cs_a_lire_debug=1` sur la home, reserve aux comptes qui peuvent
 * editer (`current_user_can('edit_posts')`) -- montre les 5 places et LEUR
 * MOTIF (regle 6 du depot : jamais deviner pourquoi une section montre ce
 * qu'elle montre).
 */
if (!function_exists('cs_a_lire_proximite')) {
function cs_a_lire_proximite() {
    return array(
        'savoie' => array('piemont', 'vda'),
        'piemont' => array('vda', 'savoie', 'nice'),
        'vda' => array('savoie', 'piemont'),
        'nice' => array('piemont'),
    );
}
}

if (!function_exists('cs_a_lire_hash')) {
function cs_a_lire_hash($jour, $id) {
    return (($jour * 2654435761) + $id) % 2147483647;
}
}

if (!function_exists('cs_a_lire_classify')) {
function cs_a_lire_classify($debut, $fin, $today) {
    if ($debut === '' || $fin === '') { return 'intemporel'; }
    if ($today >= $debut && $today <= $fin) { return 'saison'; }
    return 'hors-saison';
}
}

if (!function_exists('cs_a_lire_sort')) {
function cs_a_lire_sort($pool, $jour) {
    usort($pool, function ($a, $b) use ($jour) {
        if ($a['etat'] !== $b['etat']) { return $a['etat'] === 'saison' ? -1 : 1; }
        if ($a['etat'] === 'saison' && $a['fin'] !== $b['fin']) { return strcmp($a['fin'], $b['fin']); }
        $ha = cs_a_lire_hash($jour, $a['id']); $hb = cs_a_lire_hash($jour, $b['id']);
        return $ha <=> $hb;
    });
    return $pool;
}
}

if (!function_exists('cs_a_lire_diverse')) {
function cs_a_lire_diverse($sorted, $n, $used_sujets = array()) {
    $used = array_flip($used_sujets);
    $picked = array(); $rest = array();
    foreach ($sorted as $a) {
        if (count($picked) >= $n) { break; }
        if (!isset($used[$a['sujet']])) { $picked[] = $a; $used[$a['sujet']] = true; } else { $rest[] = $a; }
    }
    foreach ($rest as $a) { if (count($picked) >= $n) { break; } $picked[] = $a; }
    return $picked;
}
}

if (!function_exists('cs_a_lire_corpus')) {
function cs_a_lire_corpus($lang) {
    $canon = function_exists('cs_terr_canon_data') ? cs_terr_canon_data() : array();
    $term_to_canon = array();
    foreach ($canon as $k => $v) {
        $term_to_canon[(int) $v['fr_term']] = $k;
        $term_to_canon[(int) $v['it_term']] = $k;
    }
    $w = new WP_Query(array('post_type' => 'post', 'post_status' => 'publish', 'posts_per_page' => 80,
        'lang' => $lang, 'orderby' => 'date', 'order' => 'DESC', 'fields' => 'ids'));
    $today = current_time('Y-m-d');
    $out = array();
    foreach ($w->posts as $id) {
        $tt = wp_get_post_terms($id, 'territoire', array('fields' => 'all'));
        $tc = null; $slug = ''; $nom = '';
        foreach ((array) $tt as $t) {
            if (isset($term_to_canon[(int) $t->term_id])) { $tc = $term_to_canon[(int) $t->term_id]; $slug = $t->slug; $nom = $t->name; break; }
        }
        // Sans territoire reconnu, l'article ne participe pas -- garde-fou : mieux vaut
        // l'absence que de le classer au hasard (meme principe que le score d'interet
        // de "A la une" : None != 0).
        if (!$tc) { continue; }
        $debut = (string) get_post_meta($id, 'cs_guide_saison_debut', true);
        $fin = (string) get_post_meta($id, 'cs_guide_saison_fin', true);
        $etat = cs_a_lire_classify($debut, $fin, $today);
        if ($etat === 'hors-saison') { continue; }
        $sujet = (int) get_post_meta($id, 'cs_guide_cat_term', true);
        $out[] = array('id' => $id, 'territoire' => $tc, 'slug' => $slug, 'nom' => $nom,
            'sujet' => $sujet ?: ('none-' . $id), 'etat' => $etat, 'fin' => $fin);
    }
    return $out;
}
}

if (!function_exists('cs_a_lire_choisir')) {
function cs_a_lire_choisir($lang, $canon_actif) {
    $jour = (int) wp_date('z');
    $data = cs_a_lire_corpus($lang);
    if (empty($data)) { return array('local' => array(), 'ailleurs' => array()); }

    if (!$canon_actif) {
        // Vue "les 4 territoires" : rotation entre les quatre, rien n'est "chez soi".
        $terrs = array('savoie', 'piemont', 'vda', 'nice');
        usort($terrs, function ($a, $b) use ($jour) { return cs_a_lire_hash($jour, crc32($a)) <=> cs_a_lire_hash($jour, crc32($b)); });
        $par_terr = array();
        foreach ($terrs as $t) { $par_terr[$t] = cs_a_lire_sort(array_values(array_filter($data, function ($a) use ($t) { return $a['territoire'] === $t; })), $jour); }
        $picked = array(); $i = 0;
        while (count($picked) < 5 && $i < 40) {
            $t = $terrs[$i % count($terrs)];
            foreach ($par_terr[$t] as $a) {
                if (!in_array($a, $picked, true)) { $picked[] = $a; break; }
            }
            $i++;
        }
        foreach ($picked as $i => $a) { $picked[$i]['_motif'] = $a['etat']; }
        return array('local' => $picked, 'ailleurs' => array());
    }

    $local_pool = cs_a_lire_sort(array_values(array_filter($data, function ($a) use ($canon_actif) { return $a['territoire'] === $canon_actif; })), $jour);
    $local = cs_a_lire_diverse($local_pool, 4);
    $used_sujets = array_map(function ($a) { return $a['sujet']; }, $local);
    $restant = 4 - count($local);

    $autre_pool = cs_a_lire_sort(array_values(array_filter($data, function ($a) use ($canon_actif) { return $a['territoire'] !== $canon_actif; })), $jour);
    $repli = array();
    if ($restant > 0) {
        $dispo = array_values(array_filter($autre_pool, function ($a) use ($local) { return !in_array($a, $local, true); }));
        $repli = cs_a_lire_diverse($dispo, $restant, $used_sujets);
        foreach ($repli as $i => $a) { $repli[$i]['_motif'] = 'repli'; }
    }

    $voisins = cs_a_lire_proximite()[$canon_actif];
    $repli_ids = array_map(function ($a) { return $a['id']; }, $repli);
    $voisin_pool = cs_a_lire_sort(array_values(array_filter($data, function ($a) use ($voisins, $repli_ids) {
        return in_array($a['territoire'], $voisins, true) && !in_array($a['id'], $repli_ids, true);
    })), $jour);
    $ailleurs = $repli;
    if (!empty($voisin_pool)) { $v = $voisin_pool[0]; $v['_motif'] = 'voisin'; $ailleurs[] = $v; }

    foreach ($local as $i => $a) { $local[$i]['_motif'] = $a['etat']; }
    return array('local' => $local, 'ailleurs' => $ailleurs);
}
}

if (!function_exists('cs_a_lire_couleur')) {
function cs_a_lire_couleur($slug) {
    $coul = array('savoie' => '#1a5fa8', 'savoia' => '#1a5fa8', 'piemont' => '#b3261e', 'piemonte' => '#b3261e',
        'vallee-d-aoste' => '#1e7d34', 'valle-d-aosta' => '#1e7d34', 'comte-de-nice' => '#b25e00', 'contea-di-nizza' => '#b25e00');
    return isset($coul[$slug]) ? $coul[$slug] : '#6F6B62';
}
}

if (!function_exists('cs_a_lire_carte')) {
function cs_a_lire_carte($a, $avec_nom = true) {
    $co = cs_a_lire_couleur($a['slug']);
    $img = get_the_post_thumbnail_url($a['id'], 'medium_large');
    $h = '<a href="' . esc_url(get_permalink($a['id'])) . '" style="display:block;text-decoration:none;color:#1D1D1B;margin-bottom:16px">';
    if ($img) {
        $h .= '<div style="aspect-ratio:3/2;border-radius:3px;overflow:hidden;margin-bottom:8px"><img src="' . esc_url($img) . '" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover"></div>';
    } else {
        $h .= '<div style="aspect-ratio:3/2;border-radius:3px;margin-bottom:8px;background:#FBF7F0;display:flex;align-items:center;justify-content:center;font-family:Saira Condensed,sans-serif;font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:12px;color:' . $co . '">' . esc_html($a['nom']) . '</div>';
    }
    if ($avec_nom) {
        $h .= '<div style="font-size:11.5px;font-weight:800;margin-bottom:2px;color:' . $co . '">' . esc_html($a['nom']) . '</div>';
    }
    $h .= '<h3 style="font-family:Saira Condensed,sans-serif;font-size:17px;line-height:1.22;margin:0;font-weight:600">' . esc_html(get_the_title($a['id'])) . '</h3></a>';
    return $h;
}
}

if (!function_exists('cs_a_lire_ligne')) {
function cs_a_lire_ligne($a, $avec_nom = true) {
    $co = cs_a_lire_couleur($a['slug']);
    $nom = $avec_nom ? '<div style="font-size:11.5px;font-weight:800;margin-bottom:1px;color:' . $co . '">' . esc_html($a['nom']) . '</div>' : '';
    return '<li style="border-bottom:1px solid #E3DCCE"><a href="' . esc_url(get_permalink($a['id'])) . '" style="display:block;text-decoration:none;color:#1D1D1B;padding:9px 0">' . $nom . '<b style="font-family:Saira Condensed,sans-serif;font-weight:600;font-size:14.5px;line-height:1.25;display:block">' . esc_html(get_the_title($a['id'])) . '</b></a></li>';
}
}

if (!function_exists('cs_a_lire_bandeau')) {
function cs_a_lire_bandeau($texte, $couleur, $premier) {
    // Meme dessin que le bandeau « Ailleurs dans l'espace sabaudo » : un trait, un
    // intitule en capitales espacees. Ici la couleur est celle du territoire.
    $marge = $premier ? '0' : '18px';
    return '<div style="margin-top:' . $marge . ';padding-top:10px;border-top:2px solid #1D1D1B">'
        . '<div style="font-family:Saira Condensed,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:' . $couleur . ';font-weight:700;margin-bottom:9px">' . esc_html($texte) . '</div>';
}
}

if (!function_exists('cs_a_lire_html_tous')) {
function cs_a_lire_html_tous($local) {
    // 2026-09-06 (Franck) : « il faut que ce soit comme sur Savoie, mais adapte aux
    // territoires selectionnes ». Sur la vue « les 4 territoires », rien n'est
    // « ailleurs » : on rend donc UN bandeau PAR territoire, dans l'ordre de la rotation
    // du jour, chaque article sous le sien -- et plus d'etiquette de territoire sur
    // les cartes, le bandeau la porte deja. Cartes : le premier article des deux
    // premiers groupes (2 cartes + 3 lignes, comme partout ailleurs).
    $groupes = array();
    foreach ($local as $a) { $groupes[$a['territoire']][] = $a; }
    $h = '';
    $g = 0;
    foreach ($groupes as $terr => $articles) {
        $co = cs_a_lire_couleur($articles[0]['slug']);
        $h .= cs_a_lire_bandeau($articles[0]['nom'], $co, $g === 0);
        $lignes = array();
        foreach ($articles as $i => $a) {
            if ($i === 0 && $g < 2) { $h .= cs_a_lire_carte($a, false); } else { $lignes[] = $a; }
        }
        if ($lignes) {
            $h .= '<ul style="list-style:none;margin:0;padding:0;border-top:1px solid #E3DCCE">';
            foreach ($lignes as $a) { $h .= cs_a_lire_ligne($a, false); }
            $h .= '</ul>';
        }
        $h .= '</div>';
        $g++;
    }
    return $h;
}
}

if (!function_exists('cs_a_lire_debug_html')) {
function cs_a_lire_debug_html($lang, $canon_actif, $choix) {
    if (!current_user_can('edit_posts')) { return ''; }
    $motifs = array('saison' => 'en saison', 'intemporel' => 'intemporel', 'repli' => 'repli — territoire pauvre', 'voisin' => 'voisin de proximité (place réservée)');
    $h = '<div style="max-width:700px;margin:20px auto;padding:14px 16px;background:#FBF7F0;border:1px dashed #C9BFAD;font-family:monospace;font-size:12px;color:#1D1D1B">';
    $h .= '<b>Débogage « À lire »</b> — territoire actif : ' . esc_html($canon_actif ?: 'aucun (les 4)') . ' — langue : ' . esc_html($lang) . '<br><br>';
    $place = 1;
    foreach (array_merge($choix['local'], $choix['ailleurs']) as $a) {
        $motif = isset($motifs[$a['_motif']]) ? $motifs[$a['_motif']] : $a['_motif'];
        $h .= $place++ . '. [' . esc_html($a['nom']) . '] ' . esc_html(get_the_title($a['id'])) . ' — <i>' . esc_html($motif) . '</i><br>';
    }
    if (empty($choix['local']) && empty($choix['ailleurs'])) { $h .= '(rien à afficher — aucun article éligible)'; }
    $h .= '</div>';
    return $h;
}
}

if (!function_exists('cs_a_lire_html')) {
function cs_a_lire_html() {
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $canon_actif = '';
    if (function_exists('cs_territoire_actif')) {
        $k = cs_territoire_actif();
        if ($k) { $canon_actif = $k; }
    }
    $choix = cs_a_lire_choisir($lang, $canon_actif);
    if (empty($choix['local']) && empty($choix['ailleurs'])) { return ''; }

    $h = '';
    if ($canon_actif === '') {
        // Vue « tous les territoires » : un bandeau par territoire, même gabarit
        // que « Ailleurs dans l'espace sabaudo » (demande de Franck, 06/09).
        $h .= cs_a_lire_html_tous($choix['local']);
    } else {
        $local = $choix['local'];
        $nbc = count($local) < 4 ? min(2, count($local)) : 2;
        $cartes = array_slice($local, 0, $nbc);
        $lignes = array_slice($local, $nbc);
        foreach ($cartes as $a) { $h .= cs_a_lire_carte($a); }
        if (count($lignes)) {
            $h .= '<ul style="list-style:none;margin:2px 0 0;padding:0;border-top:1px solid #E3DCCE">';
            foreach ($lignes as $a) { $h .= cs_a_lire_ligne($a); }
            $h .= '</ul>';
        }
    }

    if (!empty($choix['ailleurs'])) {
        $kick = $lang === 'it' ? 'Altrove nello spazio sabaudo' : "Ailleurs dans l'espace sabaudo";
        $h .= '<div style="margin-top:20px;padding-top:12px;border-top:2px solid #1D1D1B">';
        $h .= '<div style="font-family:Saira Condensed,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#6F6B62;font-weight:700;margin-bottom:9px">' . esc_html($kick) . '</div>';
        $h .= '<ul style="list-style:none;margin:0;padding:0;border-top:1px solid #E3DCCE">';
        foreach ($choix['ailleurs'] as $a) { $h .= cs_a_lire_ligne($a); }
        $h .= '</ul></div>';
    }

    $fil = get_permalink($lang === 'it' ? 3186 : 994);
    $lib = $lang === 'it' ? 'Tutti gli articoli' : 'Tous les articles';
    $h .= '<a href="' . esc_url($fil) . '" style="display:inline-flex;align-items:center;gap:6px;margin-top:12px;text-decoration:none;font-size:12.5px;font-weight:800;color:#1D1D1B">' . esc_html($lib) . ' <span style="color:#DC5D45">&rarr;</span></a>';

    if (isset($_GET['cs_a_lire_debug'])) { $h .= cs_a_lire_debug_html($lang, $canon_actif, $choix); }

    return $h;
}
}

add_filter('the_content', function ($t) {
    if (strpos($t, 'CS_A_LIRE') === false) { return $t; }
    return str_replace('<!-- CS_A_LIRE -->', cs_a_lire_html(), $t);
}, 5);
