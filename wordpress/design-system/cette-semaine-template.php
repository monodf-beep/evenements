<?php
/**
 * "Cette semaine" (931) — rendu complet en PHP, sur le modèle EXACT de
 * liste-evenements-template.php ("Ce week-end" / "Tout l'agenda").
 * Filtre par date câblé : semaine en cours, lundi → dimanche, via meta_query
 * de CHEVAUCHEMENT sur _EventStartDate/_EventEndDate — pas juste
 * _EventStartDate dans la plage, pour qu'un événement commencé avant lundi et
 * qui finit dans la semaine (ou l'inverse) apparaisse bien. Dépend de
 * cs-cards.php (cs_card_compact, cs_render_day_groups), déjà chargé
 * globalement (snippet #21).
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(931)) {
        return;
    }

    get_header();

    // --- Semaine en cours (lundi → dimanche) ---
    $today = current_time('Y-m-d');
    $dow = (int) date('N', strtotime($today)); // 1=lundi ... 7=dimanche
    $monday = date('Y-m-d', strtotime($today . ' -' . ($dow - 1) . ' days'));
    $sunday = date('Y-m-d', strtotime($monday . ' +6 days'));
    $range_start = $monday . ' 00:00:00';
    $range_end = $sunday . ' 23:59:59';

    // Chevauchement de plage : l'événement doit commencer avant/à la fin de
    // la semaine ET finir après/au début de la semaine.
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
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Cette semaine</h1>
        <p style="margin:0 0 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#4A4A48">Du <?php echo esc_html(date_i18n('d/m', strtotime($monday))); ?> au <?php echo esc_html(date_i18n('d/m', strtotime($sunday))); ?> dans les 4 territoires</p>
      </div>

      <div style="padding-bottom:12px">
        <div style="display:flex;align-items:center;justify-content:space-between;border:1px solid #1D1D1B;padding:10px 14px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B">Filtres</div>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
        </div>
      </div>

      <div style="padding-bottom:10px;font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62"><?php echo (int) $count; ?> événement<?php echo $count > 1 ? 's' : ''; ?></div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62">Aucun événement à afficher pour l'instant.</p>
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
