<?php
/**
 * "Aujourd'hui" (929) — rendu complet en PHP, sur le modèle EXACT de
 * liste-evenements-template.php (930/932). Filtre les événements dont la
 * plage [_EventStartDate, _EventEndDate] COUVRE la date du jour — même
 * logique de chevauchement que le filtre "Ce week-end" (snippet #22,
 * liste-evenements-template.php) et que le rail mobile "jour" (snippet #45,
 * rail-jour-date-filter.php) : _EventStartDate <= aujourd'hui 23:59:59 ET
 * _EventEndDate >= aujourd'hui 00:00:00, pas juste _EventStartDate == jour,
 * pour qu'un événement commencé hier soir et qui se termine ce soir apparaisse
 * bien. Dépend de cs-cards.php (cs_card_compact, cs_render_day_groups) —
 * déjà chargé globalement (snippet #21).
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(929)) {
        return;
    }

    get_header();

    // --- Plage du jour en cours ---
    $today = current_time('Y-m-d');
    $range_start = $today . ' 00:00:00';
    $range_end = $today . ' 23:59:59';

    $meta_query = [
        'relation' => 'AND',
        'start_clause' => [
            'key' => '_EventStartDate',
            'compare' => 'EXISTS',
            'type' => 'DATETIME',
        ],
        [
            'key' => '_EventStartDate',
            'value' => $range_end,
            'compare' => '<=',
            'type' => 'DATETIME',
        ],
        [
            'key' => '_EventEndDate',
            'value' => $range_start,
            'compare' => '>=',
            'type' => 'DATETIME',
        ],
    ];

    $q = new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 50,
        'meta_query' => $meta_query,
        'orderby' => ['start_clause' => 'ASC'],
    ]);
    $count = $q->found_posts;
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:16px 0 0">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Aujourd'hui</h1>
        <p style="margin:0 0 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#4A4A48"><?php echo esc_html(ucfirst(date_i18n('l j F', strtotime($today)))); ?> dans les 4 territoires</p>
      </div>

      <div style="padding-bottom:12px">
        <div style="display:flex;align-items:center;justify-content:space-between;border:1px solid #1D1D1B;padding:10px 14px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B">Filtres</div>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
      </div>

      <div style="padding-bottom:10px;font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62"><?php echo (int) $count; ?> événement<?php echo $count > 1 ? 's' : ''; ?></div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62">Aucun événement à afficher aujourd'hui.</p>
      <?php else: ?>
        <?php echo cs_render_day_groups($q, 'cs_card_compact'); ?>
        <div style="padding:8px 0 24px;display:flex;justify-content:center;gap:8px">
          <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:#1D1D1B;color:#F7F1E8;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">1</div>
        </div>
      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
