<?php
/**
 * "Le Fil" (page 994, brouillon — pas encore publiée, cf. STATUS.md) —
 * listing des articles éditoriaux (native `post` WP), fidèle à
 * "Agenda Sabaudo - Le Fil.dc.html" (lue le 2026-07-13) : H1, liste
 * image+titre+chapô+chevron, pagination. Réutilise le post type `post`
 * natif (pas de CPT dédié — plus simple, taxonomie catégorie déjà native).
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_page(994)) {
        return;
    }

    $paged = max(1, get_query_var('paged') ?: (int) ($_GET['paged'] ?? 1));
    $q = new WP_Query([
        'post_type' => 'post',
        'post_status' => 'publish',
        'posts_per_page' => 10,
        'paged' => $paged,
    ]);

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:16px 0 8px">
        <h1 style="margin:0;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em">Le fil</h1>
      </div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62;padding:16px 0">Aucun article publié pour l'instant.</p>
      <?php else: ?>
        <?php while ($q->have_posts()): $q->the_post(); ?>
        <a href="<?php the_permalink(); ?>" style="display:flex;gap:12px;text-decoration:none;border-top:1px solid #E3DCCE;padding:16px 0">
          <div style="width:104px;flex-shrink:0;aspect-ratio:4/3;overflow:hidden;background:#FBF7F0;border-radius:3px"><?php echo get_the_post_thumbnail(get_the_ID(), 'thumbnail', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
          <div style="flex:1;min-width:0">
            <h2 style="margin:0 0 5px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:17px;line-height:1.2;color:#1D1D1B"><?php the_title(); ?></h2>
            <p style="margin:0;font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.5;color:#4A4A48"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 16)); ?> <span style="color:#DC5D45;font-weight:700">»</span></p>
          </div>
        </a>
        <?php endwhile; ?>

        <div style="padding:16px 0 24px;display:flex;justify-content:center;gap:8px">
          <?php
          $links = paginate_links([
              'total' => $q->max_num_pages,
              'current' => $paged,
              'type' => 'array',
              'prev_next' => false,
          ]);
          if ($links) {
              foreach ($links as $link) {
                  $is_current = strpos($link, 'current') !== false;
                  $style = 'width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-family:\'Nunito Sans\',sans-serif;font-size:13px;font-weight:700;text-decoration:none;' . ($is_current ? 'background:#1D1D1B;color:#F7F1E8' : 'border:1px solid #E3DCCE;color:#1D1D1B');
                  echo str_replace('<a ', '<a style="' . $style . '" ', $link);
              }
          }
          ?>
        </div>
      <?php endif; ?>

    </div>
    <?php
    wp_reset_postdata();
    get_footer();
    exit;
});
