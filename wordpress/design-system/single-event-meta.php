<?php
/**
 * Fiche événement — gabarit COMPLET custom (plus un simple habillage du
 * template natif TEC). Source réelle : "Agenda Sabaudo - Fiche Evenement.dc.html"
 * (projet "Brief design agenda Sabaudo", lue le 2026-07-13) — très différente
 * de ce que TEC affiche par défaut (fil d'Ariane, héro 4:3 + crédit photo,
 * badges, bloc pratique encadré avec CTA "Réserver · site officiel", 3 rails
 * dans CET ordre précis : Au même endroit → Même catégorie → Près d'ici,
 * mêmes dates — brief §6.4). Même méthode que les Hubs (template_redirect,
 * pas de Theme Builder). Le header/footer de marque site-wide s'applique
 * automatiquement (get_header()/get_footer() déclenchent wp_body_open/wp_footer).
 *
 * Dépend de cs-cards.php (cs_pill_class, cs_event_venue_line, cs_event_date_short,
 * cs_card_rail) — doit être actif.
 *
 * "Mode minimal d'abord" (brief §6.4) : pas d'article riche pour l'instant
 * (aucun événement du site n'a de contenu score ≥7) — le corps affiche la
 * description courte native TEC (post_content), suffisant pour ce mode.
 */

if (!function_exists('cs_event_badges')) {
    function cs_event_badges($event_id) {
        $badges = [];
        $statut = get_post_meta($event_id, 'as_statut', true);
        $statut_labels = ['complet' => 'Complet', 'annule' => 'Annulé', 'reporte' => 'Reporté'];
        if (isset($statut_labels[$statut])) {
            // Écrase tout (brief §8.3).
            return [['label' => $statut_labels[$statut], 'accent' => $statut === 'annule']];
        }
        $end = get_post_meta($event_id, '_EventEndDate', true);
        $end_ts = $end ? strtotime($end) : null;
        if ($end_ts) {
            $days_left = ceil(($end_ts - current_time('timestamp')) / DAY_IN_SECONDS);
            if ($days_left >= 0 && $days_left <= 2) {
                $badges[] = ['label' => $days_left <= 0 ? 'Dernier jour' : 'Plus que ' . $days_left . ' jour' . ($days_left > 1 ? 's' : ''), 'accent' => true];
            } elseif ($days_left > 2) {
                $start = get_post_meta($event_id, '_EventStartDate', true);
                $start_ts = $start ? strtotime($start) : null;
                if ($start_ts && current_time('timestamp') >= $start_ts) {
                    $badges[] = ['label' => 'En cours', 'accent' => false];
                }
            }
        }
        $cost = get_post_meta($event_id, '_EventCost', true);
        if ($cost === '' || $cost === '0' || strtolower((string) $cost) === 'gratuit') {
            $badges[] = ['label' => 'Gratuit', 'accent' => false];
        }
        return $badges;
    }
}

add_action('template_redirect', function () {
    if (is_admin() || !is_singular('tribe_events')) {
        return;
    }
    global $post;
    $event_id = $post->ID;

    get_header();

    $cats = get_the_terms($event_id, 'tribe_events_cat');
    $cat_name = ($cats && !is_wp_error($cats)) ? $cats[0]->name : '';
    $venue_id = get_post_meta($event_id, '_EventVenueID', true);
    $venue_line = cs_event_venue_line($event_id);
    $pill = cs_event_territory_pill($event_id);
    $badges = cs_event_badges($event_id);

    // Bloc pratique
    $start_raw = get_post_meta($event_id, '_EventStartDate', true);
    $end_raw = get_post_meta($event_id, '_EventEndDate', true);
    $start_ts = $start_raw ? strtotime($start_raw) : null;
    $end_ts = $end_raw ? strtotime($end_raw) : null;
    $dates_html = '';
    if ($start_ts) {
        $same_day = $end_ts && date('Y-m-d', $start_ts) === date('Y-m-d', $end_ts);
        $dates_html = $same_day || !$end_ts
            ? date_i18n('l j F', $start_ts)
            : date_i18n('l j', $start_ts) . ' – ' . date_i18n('l j F', $end_ts);
        $dates_html = ucfirst($dates_html);
    }
    $horaires_html = '';
    if ($start_ts && date('H:i', $start_ts) !== '00:00') {
        $horaires_html = date('H\hi', $start_ts);
        if ($end_ts && date('H:i', $end_ts) !== '00:00') {
            $horaires_html .= ' – ' . date('H\hi', $end_ts);
        }
    }
    $cost = get_post_meta($event_id, '_EventCost', true);
    $prix_html = ($cost === '' || $cost === '0') ? 'Gratuit' : esc_html($cost);
    $reserve_url = get_post_meta($event_id, '_EventURL', true) ?: ($venue_id ? get_post_meta($venue_id, '_VenueURL', true) : '');
    $venue_title = $venue_id ? get_the_title($venue_id) : '';
    $venue_city = $venue_id ? get_post_meta($venue_id, '_VenueCity', true) : '';

    // Rails liés (brief §6.4 : ordre fixe)
    $rail_lieu = $venue_id ? cs_render_event_rail_v2('Au même endroit', new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
        'post__not_in' => [$event_id], 'meta_key' => '_EventVenueID', 'meta_value' => $venue_id,
    ]), $event_id) : '';
    $rail_cat = ($cats && !is_wp_error($cats)) ? cs_render_event_rail_v2('Même catégorie', new WP_Query([
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
        'post__not_in' => [$event_id],
        'tax_query' => [['taxonomy' => 'tribe_events_cat', 'field' => 'term_id', 'terms' => $cats[0]->term_id]],
    ]), $event_id) : '';
    $rail_dates = '';
    if ($start_ts) {
        $window_start = date('Y-m-d', $start_ts);
        $window_end = date('Y-m-d', $start_ts + 3 * DAY_IN_SECONDS);
        $rail_dates = cs_render_event_rail_v2("Près d'ici, mêmes dates", new WP_Query([
            'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 4,
            'post__not_in' => [$event_id],
            'meta_query' => [[
                'key' => '_EventStartDate', 'value' => [$window_start . ' 00:00:00', $window_end . ' 23:59:59'],
                'compare' => 'BETWEEN', 'type' => 'DATETIME',
            ]],
        ]), $event_id);
    }
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none">Accueil</a>
        <?php if ($cat_name): ?> / <span style="color:#1D1D1B"><?php echo esc_html($cat_name); ?></span><?php endif; ?>
        / <span style="color:#1D1D1B"><?php the_title(); ?></span>
      </div>

      <?php if (has_post_thumbnail($event_id)): $thumb_id = get_post_thumbnail_id($event_id); $caption = wp_get_attachment_caption($thumb_id); ?>
      <div style="position:relative;margin-top:14px">
        <div style="aspect-ratio:4/3;overflow:hidden;background:#1D1D1B"><?php echo get_the_post_thumbnail($event_id, 'large', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
        <?php if ($caption): ?><div style="position:absolute;left:12px;bottom:8px;font-family:'Nunito Sans',sans-serif;font-size:10px;color:#F7F1E8;background:rgba(29,29,27,0.55);padding:3px 8px">Photo · <?php echo esc_html($caption); ?></div><?php endif; ?>
      </div>
      <?php endif; ?>

      <?php if ($badges): ?>
      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:14px">
        <?php foreach ($badges as $b): ?>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;<?php echo $b['accent'] ? 'color:#F7F1E8;background:#DC5D45' : 'color:#1D1D1B;border:1px solid #C9C4B8'; ?>;padding:4px 10px;text-transform:uppercase;letter-spacing:0.05em"><?php echo esc_html($b['label']); ?></div>
        <?php endforeach; ?>
      </div>
      <?php endif; ?>

      <div style="padding-top:14px">
        <?php if ($cat_name): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#DC5D45;text-transform:uppercase;margin-bottom:8px"><?php echo esc_html($cat_name); ?></div><?php endif; ?>
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:34px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php the_title(); ?></h1>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:20px">
          <?php if ($venue_line): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:13px;color:#4A4A48"><?php echo $venue_line; ?></div><?php endif; ?>
          <?php echo $pill; ?>
        </div>
      </div>

      <div style="border:1.5px solid #1D1D1B;padding:16px;margin-bottom:20px">
        <?php if ($dates_html): ?>
        <div style="display:flex;justify-content:space-between;padding-bottom:10px;border-bottom:1px solid #E3DCCE;margin-bottom:10px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;color:#6F6B62;text-transform:uppercase;letter-spacing:0.05em">Dates</div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B;text-align:right"><?php echo esc_html($dates_html); ?></div>
        </div>
        <?php endif; ?>
        <?php if ($horaires_html): ?>
        <div style="display:flex;justify-content:space-between;padding-bottom:10px;border-bottom:1px solid #E3DCCE;margin-bottom:10px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;color:#6F6B62;text-transform:uppercase;letter-spacing:0.05em">Horaires</div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B"><?php echo esc_html($horaires_html); ?></div>
        </div>
        <?php endif; ?>
        <div style="display:flex;justify-content:space-between;padding-bottom:10px;border-bottom:1px solid #E3DCCE;margin-bottom:10px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;color:#6F6B62;text-transform:uppercase;letter-spacing:0.05em">Prix</div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B"><?php echo $prix_html; ?></div>
        </div>
        <?php if ($venue_title): ?>
        <div style="padding-bottom:12px;border-bottom:1px solid #E3DCCE;margin-bottom:12px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;color:#6F6B62;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Lieu</div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B;margin-bottom:8px"><?php echo esc_html($venue_title . ($venue_city ? ', ' . $venue_city : '')); ?></div>
          <div style="aspect-ratio:16/9;background:#FBF7F0;border:1px solid #E3DCCE;display:flex;align-items:center;justify-content:center">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6F6B62" stroke-width="1.5"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"></path><circle cx="12" cy="9.5" r="2.3"></circle></svg>
          </div>
        </div>
        <?php endif; ?>
        <?php if ($reserve_url): ?>
        <a href="<?php echo esc_url($reserve_url); ?>" target="_blank" rel="noopener" style="display:block;text-align:center;background:#1D1D1B;color:#F7F1E8;text-decoration:none;padding:13px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;letter-spacing:0.02em">Réserver · site officiel</a>
        <?php endif; ?>
      </div>

      <div style="padding-bottom:8px;font-family:'Nunito Sans',sans-serif;font-size:14px;line-height:1.6;color:#1D1D1B"><?php echo wp_kses_post(wpautop(get_the_content(null, false, $event_id))); ?></div>
      <div style="padding-bottom:24px;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62">Vérifié le <?php echo esc_html(get_the_modified_date('j/m', $event_id)); ?></div>

      <?php echo $rail_lieu . $rail_cat . $rail_dates; ?>

    </div>
    <?php
    get_footer();
    exit;
}, 5);

if (!function_exists('cs_render_event_rail_v2')) {
    function cs_render_event_rail_v2($title, WP_Query $q, $current_id) {
        if (!$q->have_posts()) {
            return '';
        }
        $items = '';
        while ($q->have_posts()) {
            $q->the_post();
            if (get_the_ID() === $current_id) {
                continue;
            }
            $items .= cs_card_rail(get_the_ID());
        }
        wp_reset_postdata();
        if (!$items) {
            return '';
        }
        return '<div style="padding:16px 0 4px">'
            . '<div style="display:flex;align-items:center;gap:8px;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:12px">'
            . '<div style="font-family:\'Nunito Sans\',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase">' . esc_html($title) . '</div></div>'
            . '<div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:4px">' . $items . '</div></div>';
    }
}
