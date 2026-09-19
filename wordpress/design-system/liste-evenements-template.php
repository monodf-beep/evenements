<?php
/**
 * "Ce week-end" (930) / "Tout l'agenda" (932) — rendu complet en PHP.
 * Source réelle : "Agenda Sabaudo - Liste Evenements.dc.html" (lue le
 * 2026-07-13) — carte "compacte/liste" (vignette 88px + texte), compteur
 * "N événements", barre de filtres (bouton, cosmétique v1), pagination.
 * Remplace le Listing Grid JetEngine (carte-evenement-blocks/.ag-row, mauvaise
 * grammaire) poussé par apply-liste-pages.mjs. Dépend de cs-cards.php.
 *
 * Filtre par date ("le week-end en cours") PAS câblé — nécessiterait
 * JetEngine Query Builder ou une meta_query dédiée sur une plage de dates ;
 * les deux pages affichent pour l'instant la même liste complète, triée
 * par date.
 */
add_action('template_redirect', function () {
    if (is_admin() || !(is_page(930) || is_page(932))) {
        return;
    }
    $is_weekend = is_page(930);

    get_header();

    $q = new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 20,
        'meta_key' => '_EventStartDate',
        'orderby' => 'meta_value',
        'order' => 'ASC',
    ]);
    $count = $q->found_posts;
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:16px 0 0">
        <h1 style="margin:0 0 6px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo $is_weekend ? "Ce week-end" : "Tout l'agenda"; ?></h1>
        <?php if ($is_weekend): ?>
        <p style="margin:0 0 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#4A4A48">Le prochain week-end dans les 4 territoires</p>
        <?php endif; ?>
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
        <?php while ($q->have_posts()): $q->the_post(); echo cs_card_compact(get_the_ID()); endwhile; wp_reset_postdata(); ?>
        <div style="padding:8px 0 24px;display:flex;justify-content:center;gap:8px">
          <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:#1D1D1B;color:#F7F1E8;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">1</div>
        </div>
      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
