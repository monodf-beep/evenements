/**
 * "Le Fil" (page 994, brouillon — pas encore publiée, cf. STATUS.md) —
 * listing des articles éditoriaux (native `post` WP), fidèle à
 * "Agenda Sabaudo - Le Fil.dc.html" (lue le 2026-07-13) : H1, liste
 * image+titre+chapô+chevron, pagination. Réutilise le post type `post`
 * natif (pas de CPT dédié — plus simple, taxonomie catégorie déjà native).
 *
 * 2026-09-06 (Franck) : « /category/curiosites/ ne correspond pas au template des
 * pages ». Les archives de CATÉGORIE d'articles (/category/<slug>/ et /it/category/…)
 * tombaient sur l'archive par défaut de GeneratePress (colonne latérale, gabarit du
 * thème) — le seul endroit du site rendu hors gabarit maison. Elles passent désormais
 * par ce même rendu, filtré sur la catégorie, avec son nom en titre et un rappel
 * « Nos articles » qui ramène à la liste complète.
 */
add_action('template_redirect', function () {
    if (is_admin()) { return; }
    $cat = (!is_page(994) && !is_page(3186) && is_category()) ? get_queried_object() : null;
    if (!$cat && !is_page(994) && !is_page(3186)) {
        return;
    }

    $is_it = function_exists('pll_current_language') && pll_current_language() === 'it';
    $LB = $is_it ? array(
      'Nos articles' => 'I nostri articoli',
      "Aucun article publié pour l'instant." => 'Nessun articolo pubblicato al momento.',
    ) : array();
    $tr = function($s) use ($LB){ return isset($LB[$s]) ? $LB[$s] : $s; };

    $paged = max(1, get_query_var('paged') ?: (int) ($_GET['paged'] ?? 1));
    $args = [
        'post_type' => 'post',
        'post_status' => 'publish',
        'posts_per_page' => 10,
        'paged' => $paged,
    ];
    if ($cat) { $args['cat'] = (int) $cat->term_id; }
    $q = new WP_Query($args);

    $titre = $cat ? $cat->name : $tr("Nos articles");
    $retour = get_permalink($is_it ? 3186 : 994);

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:16px 0 8px">
        <?php if ($cat): ?>
        <a href="<?php echo esc_url($retour); ?>" style="display:inline-block;margin-bottom:6px;text-decoration:none;font-family:'Saira Condensed',sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;color:#6F6B62"><?php echo esc_html($tr("Nos articles")); ?> <span style="color:#DC5D45">&rsaquo;</span></a>
        <?php endif; ?>
        <h1 style="margin:0;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($titre); ?></h1>
      </div>

      <?php if (!$q->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62;padding:16px 0"><?php echo esc_html($tr("Aucun article publié pour l'instant.")); ?></p>
      <?php else: ?>
        <?php while ($q->have_posts()): $q->the_post(); ?>
        <a href="<?php the_permalink(); ?>" style="display:flex;gap:12px;text-decoration:none;border-top:1px solid #E3DCCE;padding:16px 0">
          <div style="width:104px;flex-shrink:0;align-self:flex-start;aspect-ratio:4/3;overflow:hidden;background:#FBF7F0;border-radius:3px"><?php echo get_the_post_thumbnail(get_the_ID(), 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
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
