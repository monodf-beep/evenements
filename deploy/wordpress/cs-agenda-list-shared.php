<?php
/*
Plugin Name: Agenda Sabauda — Composants partages Liste Agenda (Date/Ville/Categorie)
Description: Fonctions partagees pour les pages "liste d'evenements" du site (Aujourd'hui,
  Cette semaine, Ce week-end, Tout l'agenda, Ce week-end x territoire) — consolidation
  demandee par Franck le 2026-07-20 : ces pages dupliquaient chacune la meme logique de
  fenetre de dates + carte + "barre Filtres" purement decorative (jamais fonctionnelle).
  Regroupe ici : calcul de fenetre de dates (cs_agenda_date_range), libelles FR/IT
  (cs_agenda_labels), titres/sous-titres par type de page (cs_agenda_titles), la VRAIE
  barre de filtres Date/Ville/Categorie en GET, sans JS, formulaire natif (cs_agenda_filter_bar),
  et le rendu de page complet (cs_render_agenda_list_page) qui assemble tout.

  Fichier FONCTIONS SEULEMENT — ne route aucune page lui-meme (pas de template_redirect ici).
  Le routage (quelle page -> quelle config) vit dans le Code Snippet "Gabarit Liste Agenda
  (routage)" qui appelle cs_render_agenda_list_page().

  Reversible : supprimer ce fichier ET desactiver le snippet de routage pour revenir aux
  anciens gabarits (22/46/47/59), qui restent installes et desactives (pas supprimes) pour
  rollback rapide.
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_agenda_date_range')) {
function cs_agenda_date_range($window, $offset = 0) {
    // $offset : nombre de SEMAINES a decaler (2026-08-02, Franck : "aller de
    // week-end en week-end sans ouvrir les filtres"). Jamais negatif : un agenda
    // dont les evenements sont passes n a pas d interet, et un bouton "precedent"
    // toujours actif invite a s y perdre. Le retour n existe que pour revenir.
    $offset = max(0, (int) $offset);
    $today = current_time('Y-m-d');
    if ($offset > 0) { $today = date('Y-m-d', strtotime($today . ' +' . ($offset * 7) . ' days')); }
    $dow = (int) date('N', strtotime($today));
    switch ($window) {
        case 'today':
            $start_d = $today;
            $end_d = $today;
            break;
        case 'week':
            $start_d = date('Y-m-d', strtotime($today . ' -' . ($dow - 1) . ' days'));
            $end_d = date('Y-m-d', strtotime($start_d . ' +6 days'));
            break;
        case 'weekend':
            if ($dow >= 5) {
                $start_d = date('Y-m-d', strtotime($today . ' -' . ($dow - 5) . ' days'));
            } else {
                $start_d = date('Y-m-d', strtotime($today . ' +' . (5 - $dow) . ' days'));
            }
            $end_d = date('Y-m-d', strtotime($start_d . ' +2 days'));
            break;
        case 'all':
        default:
            $start_d = $today;
            $end_d = null;
            break;
    }
    return [$start_d . ' 00:00:00', $end_d ? $end_d . ' 23:59:59' : null];
}
}

if (!function_exists('cs_agenda_labels')) {
function cs_agenda_labels($lang) {
    if ($lang === 'it') {
        return [
            'date' => 'Data', 'ville' => 'Città', 'categorie' => 'Categoria',
            'tous' => 'Tutte', 'appliquer' => 'Applica',
            'evenement' => 'evento', 'evenements' => 'eventi',
            'aucun' => 'Nessun evento da mostrare per ora.',
            'filtres' => 'Filtri',
        ];
    }
    return [
        'date' => 'Date', 'ville' => 'Ville', 'categorie' => 'Catégorie',
        'tous' => 'Tous', 'appliquer' => 'Appliquer',
        'evenement' => 'événement', 'evenements' => 'événements',
        'aucun' => "Aucun événement à afficher pour l'instant.",
        'filtres' => 'Filtres',
    ];
}
}

if (!function_exists('cs_agenda_titles')) {
function cs_agenda_titles($kind, $lang, $start_ts, $end_ts, $terr_name = '') {
    $is_it = $lang === 'it';
    switch ($kind) {
        case 'today':
            $h1 = $is_it ? 'Oggi' : "Aujourd'hui";
            $sub = ucfirst(date_i18n('l j F', $start_ts)) . ($is_it ? ' nei 4 territori' : ' dans les 4 territoires');
            break;
        case 'week':
            $h1 = $is_it ? 'Questa settimana' : 'Cette semaine';
            $sub = ($is_it ? 'Dal ' : 'Du ') . date_i18n('d/m', $start_ts) . ($is_it ? ' al ' : ' au ') . date_i18n('d/m', $end_ts) . ($is_it ? ' nei 4 territori' : ' dans les 4 territoires');
            break;
        case 'weekend':
            $h1 = $is_it ? 'Cosa fare questo weekend' : 'Ce week-end';
            $sub = ($is_it ? 'Dal ' : 'Du ') . date_i18n('d/m', $start_ts) . ($is_it ? ' al ' : ' au ') . date_i18n('d/m', $end_ts) . ($is_it ? ' nei 4 territori' : ' dans les 4 territoires');
            break;
        case 'weekend_territoire':
            $h1 = ($is_it ? 'Questo weekend a ' : 'Ce week-end en ') . $terr_name;
            $sub = ($is_it ? 'Dal ' : 'Du ') . date_i18n('d/m', $start_ts) . ($is_it ? ' al ' : ' au ') . date_i18n('d/m', $end_ts) . ' · ' . $terr_name;
            break;
        case 'all':
        default:
            $h1 = $is_it ? 'Eventi' : "Tout l'agenda";
            $sub = '';
            break;
    }
    return [$h1, $sub];
}
}

if (!function_exists('cs_agenda_filter_bar')) {
function cs_agenda_filter_bar($labels, $dates, $villes, $categories, $sel_date, $sel_ville, $sel_cat, $lang) {
    ob_start();
    ?>
    <form method="get" style="padding-bottom:12px">
      <details style="border:0">
        <!-- 2026-08-02 (Franck) : la navigation de semaine en semaine prime sur les
             filtres. Ceux-ci passent donc en retrait : plus de cadre noir plein, un
             simple filet et un libelle gris. Ils restent accessibles, ils cessent
             juste de capter l attention avant le contenu. -->
        <summary style="display:inline-flex;align-items:center;gap:6px;padding:8px 0;cursor:pointer;list-style:none;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#6F6B62">
          <span><?php echo esc_html($labels['filtres']); ?></span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6F6B62" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </summary>
        <div style="padding:4px 0 14px;display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end">
          <div>
            <label style="display:block;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;margin-bottom:4px"><?php echo esc_html($labels['date']); ?></label>
            <input type="date" name="jour" value="<?php echo esc_attr($sel_date); ?>"<?php if ($dates): ?> min="<?php echo esc_attr($dates[0]); ?>" max="<?php echo esc_attr(end($dates)); ?>"<?php endif; ?> style="border:1px solid #1D1D1B;padding:7px 10px;font-family:'Nunito Sans',sans-serif;font-size:13px;background:#fff">
          </div>
          <?php if ($villes): ?>
          <div>
            <label style="display:block;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;margin-bottom:4px"><?php echo esc_html($labels['ville']); ?></label>
            <select name="ville" style="border:1px solid #1D1D1B;padding:8px 10px;font-family:'Nunito Sans',sans-serif;font-size:13px;background:#fff">
              <option value=""><?php echo esc_html($labels['tous']); ?></option>
              <?php foreach ($villes as $v): ?>
                <option value="<?php echo esc_attr($v); ?>" <?php selected($sel_ville, $v); ?>><?php echo esc_html($v); ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <?php endif; ?>
          <?php if ($categories): ?>
          <div>
            <label style="display:block;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;margin-bottom:4px"><?php echo esc_html($labels['categorie']); ?></label>
            <select name="categorie" style="border:1px solid #1D1D1B;padding:8px 10px;font-family:'Nunito Sans',sans-serif;font-size:13px;background:#fff">
              <option value=""><?php echo esc_html($labels['tous']); ?></option>
              <?php foreach ($categories as $c): ?>
                <option value="<?php echo esc_attr($c->slug); ?>" <?php selected($sel_cat, $c->slug); ?>><?php echo esc_html($c->name); ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <?php endif; ?>
          <button type="submit" style="background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:9px 16px;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700"><?php echo esc_html($labels['appliquer']); ?></button>
        </div>
      </details>
    </form>
    <?php
    return ob_get_clean();
}
}

if (!function_exists('cs_render_agenda_list_page')) {
function cs_render_agenda_list_page($config) {
    get_header();

    $lang = $config['lang'];
    $labels = cs_agenda_labels($lang);

    // Territoire persistant (cookie/GET, cf. cs-territoire-persistant.php) : applique
    // le territoire actif aux pages listes sans territoire explicite, et le repercute
    // dans le sous-titre ("Ce week-end ou ?", demande Franck 2026-07-20). Les options
    // de filtre (dates/villes/categories) se recalculent automatiquement dans ce scope.
    if (empty($config['territoire_term_id']) && function_exists('cs_territoire_actif')) {
        $cs_canon = cs_territoire_actif();
        if ($cs_canon) {
            $cs_t = cs_terr_canon_data()[$cs_canon];
            $config['territoire_term_id'] = $lang === 'it' ? $cs_t['it_term'] : $cs_t['fr_term'];
            $config['cs_terr_suffix_name'] = $lang === 'it' ? $cs_t['it_name'] : $cs_t['fr_name'];
        }
    }
    // Decalage de semaine (?wk=N), uniquement sur les fenetres glissantes.
    $cs_wk = 0;
    if (in_array($config['window'], array('weekend', 'week'), true) && isset($_GET['wk'])) {
        $cs_wk = max(0, min(26, (int) $_GET['wk']));
    }
    list($range_start, $range_end) = cs_agenda_date_range($config['window'], $cs_wk);
    // 2026-08-02 (Franck) : la borne basse ne descend JAMAIS avant aujourd hui.
    // Les fenetres calendaires commencent dans le passe des qu on est en milieu de
    // periode : un dimanche, "Cette semaine" partait du lundi precedent et
    // "Ce week-end" du vendredi. Comme le filtre retenait les evenements dont la fin
    // est posterieure a cette borne, on proposait des sorties DEJA TERMINEES --
    // mesure : 21 fiches sur 73 pour la semaine, 11 sur 63 pour le week-end.
    // Le libelle de la periode, lui, reste celui de la fenetre reelle : on ne ment
    // pas sur les dates affichees, on cesse juste de proposer ce qui est passe.
    $cs_floor = current_time('Y-m-d') . ' 00:00:00';
    $cs_filtre_debut = ($range_start < $cs_floor) ? $cs_floor : $range_start;
    $start_ts = strtotime($range_start);
    $end_ts = $range_end ? strtotime($range_end) : $start_ts;

    $meta_query = [
        'relation' => 'AND',
        'start_clause' => ['key' => '_EventStartDate', 'compare' => 'EXISTS', 'type' => 'DATETIME'],
    ];
    if ($range_end) {
        $meta_query[] = ['key' => '_EventStartDate', 'value' => $range_end, 'compare' => '<=', 'type' => 'DATETIME'];
        $meta_query[] = ['key' => '_EventEndDate', 'value' => $cs_filtre_debut, 'compare' => '>=', 'type' => 'DATETIME'];
    } else {
        $meta_query[] = ['key' => '_EventEndDate', 'value' => $cs_filtre_debut, 'compare' => '>=', 'type' => 'DATETIME'];
    }

    $tax_query = [];
    if (!empty($config['territoire_term_id'])) {
        $tax_query[] = ['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => (int) $config['territoire_term_id']];
    }

    $base_args = [
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => -1,
        'meta_query' => $meta_query, 'lang' => $lang, 'fields' => 'ids',
    ];
    if ($tax_query) {
        $base_args['tax_query'] = $tax_query;
    }
    $base_q = new WP_Query($base_args);
    $base_ids = $base_q->posts;

    $dates = [];
    $villes = [];
    $cats = [];
    foreach ($base_ids as $eid) {
        $s = get_post_meta($eid, '_EventStartDate', true);
        if ($s) {
            $dates[date('Y-m-d', strtotime($s))] = true;
        }
        $venue_id = get_post_meta($eid, '_EventVenueID', true);
        if ($venue_id) {
            $city = get_post_meta($venue_id, '_VenueCity', true);
            if ($city) {
                $villes[$city] = true;
            }
        }
        $terms = get_the_terms($eid, 'tribe_events_cat');
        if ($terms && !is_wp_error($terms)) {
            foreach ($terms as $t) {
                $cats[$t->term_id] = $t;
            }
        }
    }
    ksort($dates);
    $dates = array_keys($dates);
    ksort($villes);
    $villes = array_keys($villes);
    uasort($cats, function ($a, $b) { return strcmp($a->name, $b->name); });
    $cats = array_values($cats);

    $sel_date = isset($_GET['jour']) ? sanitize_text_field(wp_unslash($_GET['jour'])) : '';
    $sel_ville = isset($_GET['ville']) ? sanitize_text_field(wp_unslash($_GET['ville'])) : '';
    $sel_cat = isset($_GET['categorie']) ? sanitize_title(wp_unslash($_GET['categorie'])) : '';

    $final_meta_query = $meta_query;
    if ($sel_date && preg_match('/^\d{4}-\d{2}-\d{2}$/', $sel_date)) {
        $final_meta_query[] = ['key' => '_EventStartDate', 'value' => [$sel_date . ' 00:00:00', $sel_date . ' 23:59:59'], 'compare' => 'BETWEEN', 'type' => 'DATETIME'];
    }
    if ($sel_ville && in_array($sel_ville, $villes, true)) {
        $venue_ids = get_posts([
            'post_type' => 'tribe_venue', 'post_status' => 'publish', 'posts_per_page' => -1, 'fields' => 'ids',
            'meta_query' => [['key' => '_VenueCity', 'value' => $sel_ville]],
        ]);
        $final_meta_query[] = ['key' => '_EventVenueID', 'value' => $venue_ids ?: [0], 'compare' => 'IN'];
    }
    $final_tax_query = $tax_query;
    $sel_cat_valid = false;
    if ($sel_cat) {
        foreach ($cats as $c) {
            if ($c->slug === $sel_cat) { $sel_cat_valid = true; break; }
        }
    }
    if ($sel_cat_valid) {
        $final_tax_query[] = ['taxonomy' => 'tribe_events_cat', 'field' => 'slug', 'terms' => $sel_cat];
    }

    $final_args = [
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 50,
        'meta_query' => $final_meta_query, 'orderby' => ['start_clause' => 'ASC'], 'lang' => $lang,
    ];
    if ($final_tax_query) {
        $final_args['tax_query'] = $final_tax_query;
    }
    // 2026-08-02 (Franck) : ordre "ce qui commence d abord, ce qui court deja ensuite".
    // Le tri par date de debut croissante remontait les evenements longue duree (expos
    // demarrees en fevrier) AVANT ceux du jour. Sur "Ce week-end", les 3 evenements qui
    // commencaient reellement ce week-end tombaient meme en page 2 derriere 60 fiches
    // deja en cours : la page ne repondait pas a sa propre question.
    // Comme ailleurs sur ce site, The Events Calendar impose son ORDER BY et ignore
    // toute consigne de tri sur une meta -> on classe en PHP puis on fige avec post__in.
    // Il faut trier AVANT la pagination, sinon le reclassement ne joue que sur la page
    // deja decoupee (erreur commise dans une 1re version).
    $cs_pre = $final_args;
    $cs_pre['fields'] = 'ids';
    $cs_pre['posts_per_page'] = -1;
    $cs_pre['no_found_rows'] = true;
    unset($cs_pre['orderby'], $cs_pre['paged']);
    $cs_ids = get_posts($cs_pre);
    if ($cs_ids) {
        // Meme reference que le regroupement : le debut de la fenetre consultee,
        // pas la date du jour (sinon, sur un week-end futur, un evenement demarre
        // entre-temps serait classe "ponctuel" alors qu il aura deja commence).
        $cs_today = substr($cs_filtre_debut, 0, 10);
        $cs_rank = array();
        foreach ($cs_ids as $cs_id) {
            $cs_d = substr((string) get_post_meta($cs_id, '_EventStartDate', true), 0, 10);
            $cs_rank[] = array('id' => $cs_id, 'ongoing' => ($cs_d !== '' && $cs_d < $cs_today) ? 1 : 0, 'd' => $cs_d);
        }
        usort($cs_rank, function ($a, $b) {
            if ($a['ongoing'] !== $b['ongoing']) { return $a['ongoing'] <=> $b['ongoing']; }
            return strcmp($a['d'], $b['d']);
        });
        // post__in NE SUFFIT PAS : TEC ecrase aussi ce tri-la. On force l ORDER BY
        // au niveau SQL, en dernier (priorite 999), le temps de cette seule requete.
        $cs_order_ids = wp_list_pluck($cs_rank, 'id');
        $final_args['post__in'] = $cs_order_ids;
        $final_args['cs_force_order'] = 1;
        $cs_cb = function ($orderby, $wq) use ($cs_order_ids) {
            if (empty($wq->query_vars['cs_force_order'])) { return $orderby; }
            global $wpdb;
            $list = implode(',', array_map('intval', $cs_order_ids));
            return $list !== '' ? 'FIELD(' . $wpdb->posts . '.ID, ' . $list . ')' : $orderby;
        };
        add_filter('posts_orderby', $cs_cb, 999, 2);
    }
    $q = new WP_Query($final_args);
    if (!empty($cs_cb)) { remove_filter('posts_orderby', $cs_cb, 999); }
    $count = $q->found_posts;

    list($h1, $subtitle) = cs_agenda_titles($config['kind'], $lang, $start_ts, $end_ts, $config['territoire_name'] ?? '');
    // 2026-08-02 (Franck) : des qu on quitte la fenetre courante, "Ce week-end" devient
    // faux et desoriente -- le titre doit dire DE QUEL week-end il s agit.
    if ($cs_wk > 0) {
        // Mois repete une seule fois quand les deux dates tombent dans le meme mois :
        // "du 7 au 9 aout" et non "du 7 aout au 9 aout".
        $cs_meme_mois = (date('n', $start_ts) === date('n', $end_ts));
        $cs_span = $cs_meme_mois ? date_i18n('j', $start_ts) : date_i18n('j F', $start_ts);
        $cs_d2 = date_i18n('j F', $end_ts);
        if ($config['window'] === 'weekend') {
            $h1 = ($lang === 'it') ? ('Weekend dal ' . $cs_span . ' al ' . $cs_d2) : ('Week-end du ' . $cs_span . ' au ' . $cs_d2);
        } else {
            $h1 = ($lang === 'it') ? ('Settimana dal ' . $cs_span . ' al ' . $cs_d2) : ('Semaine du ' . $cs_span . ' au ' . $cs_d2);
        }
    }
    if ($cs_wk > 0) {
        // Le titre porte deja la periode : le sous-titre ne garde que le territoire.
        $cs_terr_txt = $config['cs_terr_suffix_name'] ?? '';
        if ($cs_terr_txt === '') { $cs_terr_txt = ($lang === 'it') ? 'nei 4 territori' : 'dans les 4 territoires'; }
        $subtitle = $cs_terr_txt;
    }
    if (!empty($config['cs_terr_suffix_name'])) {
        $cs_suffix = '· ' . $config['cs_terr_suffix_name'];
        if (strpos($subtitle, 'dans les 4 territoires') !== false) {
            $subtitle = str_replace('dans les 4 territoires', $cs_suffix, $subtitle);
        } elseif (strpos($subtitle, 'nei 4 territori') !== false) {
            $subtitle = str_replace('nei 4 territori', $cs_suffix, $subtitle);
        } else {
            $subtitle = trim($subtitle . ' ' . $cs_suffix);
        }
    }
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none"><?php echo $lang === 'it' ? 'Home' : 'Accueil'; ?></a> / <span style="color:#1D1D1B"><?php echo esc_html($h1); ?></span>
      </div>

      <div style="padding-top:12px">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($h1); ?></h1>
        <?php if ($subtitle): ?>
        <p style="margin:0 0 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#4A4A48"><?php echo esc_html($subtitle); ?></p>
        <?php endif; ?>
      </div>

      <?php
      // Navigation de semaine en semaine, sans passer par les filtres.
      if (in_array($config['window'], array('weekend', 'week'), true)):
        $cs_base = strtok($_SERVER['REQUEST_URI'], '?');
        $cs_keep = $_GET; unset($cs_keep['wk']);
        $cs_url = function ($n) use ($cs_base, $cs_keep) {
            $q = $cs_keep; if ($n > 0) { $q['wk'] = $n; }
            return esc_url($cs_base . ($q ? '?' . http_build_query($q) : ''));
        };
        $cs_is_wk = ($config['window'] === 'weekend');
        $cs_prev = $lang === 'it' ? ($cs_is_wk ? 'Weekend precedente' : 'Settimana precedente') : ($cs_is_wk ? 'Week-end pr' . chr(0xC3) . chr(0xA9) . 'c' . chr(0xC3) . chr(0xA9) . 'dent' : 'Semaine pr' . chr(0xC3) . chr(0xA9) . 'c' . chr(0xC3) . chr(0xA9) . 'dente');
        $cs_next = $lang === 'it' ? ($cs_is_wk ? 'Weekend successivo' : 'Settimana successiva') : ($cs_is_wk ? 'Week-end suivant' : 'Semaine suivante');
        ?>
        <div style="display:flex;align-items:center;gap:14px;margin:0 0 14px;font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:800">
          <?php if ($cs_wk > 0): ?>
            <a href="<?php echo $cs_url($cs_wk - 1); ?>" style="text-decoration:none;color:#1D1D1B"><span style="color:#DC5D45">&larr;</span> <?php echo esc_html($cs_prev); ?></a>
          <?php endif; ?>
          <a href="<?php echo $cs_url($cs_wk + 1); ?>" style="text-decoration:none;color:#1D1D1B;margin-left:auto"><?php echo esc_html($cs_next); ?> <span style="color:#DC5D45">&rarr;</span></a>
        </div>
      <?php endif; ?>

      <?php echo cs_agenda_filter_bar($labels, $dates, $villes, $cats, $sel_date, $sel_ville, $sel_cat, $lang); ?>

      <div style="padding-bottom:10px;font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62"><?php echo (int) $count; ?> <?php echo $count > 1 ? esc_html($labels['evenements']) : esc_html($labels['evenement']); ?></div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62"><?php echo esc_html($labels['aucun']); ?></p>
      <?php else: ?>
        <?php echo cs_render_day_groups($q, 'cs_card_compact', $cs_filtre_debut); ?>
        <div style="padding:8px 0 24px;display:flex;justify-content:center;gap:8px">
          <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:#1D1D1B;color:#F7F1E8;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">1</div>
        </div>
      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
}
}