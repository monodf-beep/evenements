<?php
/**
 * Hub territoire / Hub catégorie — rendu complet en PHP (pas de Theme Builder).
 * Source réelle : "Agenda Sabaudo - Hub Categorie.dc.html" (lue le 2026-07-13) —
 * remplace la carte .ag-row (mauvaise grammaire, cf. cs-cards.php) par la vraie
 * carte "standard" (image 3:2 + date + titre + lieu·ville + pilule territoire
 * colorée), avec fil d'Ariane, intro éditoriale, filtres (cosmétiques v1,
 * non fonctionnels — nécessiteraient JetEngine Query Builder ou AJAX),
 * pagination, newsletter légère. Dépend de cs-cards.php.
 *
 * Intro éditoriale PLACEHOLDER (brief §6.3 : 100-150 mots catégorie, 150-250
 * territoire, texte pérenne indexable) — textes réels à récupérer auprès de
 * Franck ("nos textes FR/IT sont écrits" selon le brief plus ancien).
 */
add_action('template_redirect', function () {
    if (is_admin() || (!is_tax('territoire') && !is_tax('tribe_events_cat'))) {
        return;
    }

    $term = get_queried_object();
    $title = $term ? $term->name : '';
    $is_territoire = is_tax('territoire');

    get_header();

    $q = new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 20,
        'tax_query' => [[
            'taxonomy' => $term->taxonomy,
            'field' => 'term_id',
            'terms' => $term->term_id,
        ]],
        'meta_key' => '_EventStartDate',
        'orderby' => 'meta_value',
        'order' => 'ASC',
    ]);
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none">Accueil</a> / <span style="color:#1D1D1B"><?php echo esc_html($title); ?></span>
      </div>

      <div style="padding-top:12px">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($title); ?></h1>
        <p style="margin:0 0 18px;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48">
          <?php echo $is_territoire
              ? 'Retrouvez tous les événements de ce territoire, mis à jour en continu.'
              : 'La programmation de cette catégorie sur les quatre territoires, mise à jour en continu.'; ?>
        </p>
      </div>

      <div style="padding-bottom:16px;display:flex;gap:8px;overflow-x:auto">
        <div style="flex-shrink:0;display:flex;align-items:center;gap:6px;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Date <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg></div>
        <div style="flex-shrink:0;display:flex;align-items:center;gap:6px;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Ville <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg></div>
        <?php if ($is_territoire): ?>
        <div style="flex-shrink:0;display:flex;align-items:center;gap:6px;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Catégorie <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg></div>
        <?php else: ?>
        <div style="flex-shrink:0;display:flex;align-items:center;gap:6px;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Territoire <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg></div>
        <?php endif; ?>
      </div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62">Aucun événement à afficher pour l'instant.</p>
      <?php else: ?>
        <?php while ($q->have_posts()): $q->the_post(); echo cs_card_standard(get_the_ID()); endwhile; wp_reset_postdata(); ?>
        <div style="padding:8px 0 24px;display:flex;justify-content:center;gap:8px">
          <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:#1D1D1B;color:#F7F1E8;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">1</div>
        </div>
      <?php endif; ?>

      <div style="margin:0 0 24px;background:#FBF7F0;padding:16px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B;margin-bottom:10px">Recevez l'agenda <?php echo esc_html(mb_strtolower($title)); ?> chaque semaine</div>
        <form style="display:flex;border-bottom:1px solid #1D1D1B;padding-bottom:8px">
          <input type="email" placeholder="Votre adresse e-mail" style="flex:1;border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
          <button type="submit" style="border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;color:#DC5D45;cursor:pointer">S'inscrire</button>
        </form>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
