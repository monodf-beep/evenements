<?php
/*
Plugin Name: Agenda Sabauda — Gabarit Hub "Musees" (type_de_lieu)
Description: Page archive de la taxonomie type_de_lieu (creee dans
  cs-taxonomie-type-de-lieu.php) : liste les evenements dont le LIEU porte ce type,
  avec les memes filtres reels Date/Ville/Territoire que les Hubs territoire/categorie
  (CS15). Resolution en 2 temps (les evenements ne portent pas directement le type de
  lieu, seul le lieu tribe_venue le porte) : lieux tagues -> _EventVenueID IN (...).
  Demande de Franck 2026-07-20 (tuile home "Musees").

  Rollback : supprimer ce fichier (l'archive retombe sur le template generique du
  theme, page vide -- meme constat historique que pour territoire/tribe_events_cat
  avant CS14/CS15).
*/
if (!defined('ABSPATH')) { exit; }

add_action('template_redirect', function () {
    if (is_admin() || !is_tax('type_de_lieu')) {
        return;
    }

    $term = get_queried_object();
    $title = $term ? $term->name : '';
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';

    $venue_ids = get_posts([
        'post_type' => 'tribe_venue', 'post_status' => 'publish', 'posts_per_page' => -1, 'fields' => 'ids',
        'tax_query' => [['taxonomy' => 'type_de_lieu', 'field' => 'term_id', 'terms' => $term->term_id]],
    ]);

    get_header();

    if (empty($venue_ids)) {
        $venue_ids = [0];
    }

    // Territoire actif (cookie/GET, cf. cs-territoire-persistant.php) : restreint la
    // page au territoire choisi par le visiteur (constat 2026-07-20 : les 4 territoires
    // apparaissaient malgre une selection).
    $base_args = [
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => -1,
        'meta_query' => [['key' => '_EventVenueID', 'value' => $venue_ids, 'compare' => 'IN']],
        'meta_key' => '_EventStartDate', 'orderby' => 'meta_value', 'order' => 'ASC',
        'lang' => $lang, 'fields' => 'ids',
    ];
    if (function_exists('cs_territoire_actif') && ($cs_canon = cs_territoire_actif())) {
        $cs_t = cs_terr_canon_data()[$cs_canon];
        $base_args['tax_query'] = [[
            'taxonomy' => 'territoire', 'field' => 'term_id',
            'terms' => $lang === 'it' ? $cs_t['it_term'] : $cs_t['fr_term'],
        ]];
    }
    $base_q = new WP_Query($base_args);
    $base_ids = $base_q->posts;

    $dates = [];
    $villes = [];
    $terrs = [];
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
        $tt = get_the_terms($eid, 'territoire');
        if ($tt && !is_wp_error($tt)) {
            foreach ($tt as $t) {
                $terrs[$t->term_id] = $t;
            }
        }
    }
    ksort($dates);
    $dates = array_keys($dates);
    ksort($villes);
    $villes = array_keys($villes);
    uasort($terrs, function ($a, $b) { return strcmp($a->name, $b->name); });
    $terrs = array_values($terrs);

    $sel_date = isset($_GET['jour']) ? sanitize_text_field(wp_unslash($_GET['jour'])) : '';
    $sel_ville = isset($_GET['ville']) ? sanitize_text_field(wp_unslash($_GET['ville'])) : '';
    $sel_terr = isset($_GET['filtre2']) ? sanitize_title(wp_unslash($_GET['filtre2'])) : '';

    $final_args = $base_args;
    $final_args['posts_per_page'] = 50;
    unset($final_args['fields']);

    if ($sel_date && preg_match('/^\d{4}-\d{2}-\d{2}$/', $sel_date)) {
        $final_args['meta_query'][] = ['key' => '_EventStartDate', 'value' => [$sel_date . ' 00:00:00', $sel_date . ' 23:59:59'], 'compare' => 'BETWEEN', 'type' => 'DATETIME'];
    }
    if ($sel_ville && in_array($sel_ville, $villes, true)) {
        $venue_ids_ville = get_posts([
            'post_type' => 'tribe_venue', 'post_status' => 'publish', 'posts_per_page' => -1, 'fields' => 'ids',
            'meta_query' => [['key' => '_VenueCity', 'value' => $sel_ville]],
        ]);
        $final_args['meta_query'][] = ['key' => '_EventVenueID', 'value' => $venue_ids_ville ?: [0], 'compare' => 'IN'];
    }
    $sel_terr_valid = false;
    foreach ($terrs as $t) {
        if ($t->slug === $sel_terr) { $sel_terr_valid = true; break; }
    }
    if ($sel_terr_valid) {
        $final_args['tax_query'] = [['taxonomy' => 'territoire', 'field' => 'slug', 'terms' => $sel_terr]];
    }

    $q = new WP_Query($final_args);

    $labels = $lang === 'it'
        ? ['date' => 'Data', 'ville' => 'Città', 'other' => 'Territorio', 'tous' => 'Tutte', 'appliquer' => 'Applica']
        : ['date' => 'Date', 'ville' => 'Ville', 'other' => 'Territoire', 'tous' => 'Tous', 'appliquer' => 'Appliquer'];
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none"><?php echo $lang === 'it' ? 'Home' : 'Accueil'; ?></a> / <span style="color:#1D1D1B"><?php echo esc_html($title); ?></span>
      </div>

      <div style="padding-top:12px">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($title); ?></h1>
        <p style="margin:0 0 18px;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48">
          <?php echo $lang === 'it'
              ? 'Tutti gli eventi nei musei dei quattro territori, aggiornati in continuo.'
              : 'Tous les événements dans les musées des quatre territoires, mis à jour en continu.'; ?>
        </p>
      </div>

      <form method="get" style="padding-bottom:16px">
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <input type="date" name="jour" value="<?php echo esc_attr($sel_date); ?>"<?php if ($dates): ?> min="<?php echo esc_attr($dates[0]); ?>" max="<?php echo esc_attr(end($dates)); ?>"<?php endif; ?> aria-label="<?php echo esc_attr($labels['date']); ?>" style="border:1px solid #1D1D1B;padding:6px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
          <?php if ($villes): ?>
          <select name="ville" style="border:1px solid #1D1D1B;padding:7px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
            <option value=""><?php echo esc_html($labels['ville']); ?></option>
            <?php foreach ($villes as $v): ?>
              <option value="<?php echo esc_attr($v); ?>" <?php selected($sel_ville, $v); ?>><?php echo esc_html($v); ?></option>
            <?php endforeach; ?>
          </select>
          <?php endif; ?>
          <?php if ($terrs): ?>
          <select name="filtre2" style="border:1px solid #1D1D1B;padding:7px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
            <option value=""><?php echo esc_html($labels['other']); ?></option>
            <?php foreach ($terrs as $t): ?>
              <option value="<?php echo esc_attr($t->slug); ?>" <?php selected($sel_terr, $t->slug); ?>><?php echo esc_html($t->name); ?></option>
            <?php endforeach; ?>
          </select>
          <?php endif; ?>
          <button type="submit" style="background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700"><?php echo esc_html($labels['appliquer']); ?></button>
        </div>
      </form>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62"><?php echo $lang === 'it' ? 'Nessun evento da mostrare per ora.' : "Aucun événement à afficher pour l'instant."; ?></p>
      <?php else: ?>
        <?php while ($q->have_posts()): $q->the_post(); echo cs_card_standard(get_the_ID()); endwhile; wp_reset_postdata(); ?>
      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
}, 8);
