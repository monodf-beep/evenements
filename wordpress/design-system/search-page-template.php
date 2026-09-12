<?php
/**
 * Page de recherche — rendu complet en PHP (template_redirect), remplace le
 * gabarit search.php générique de GeneratePress. Source réelle : "Agenda
 * Sabaudo - Recherche.dc.html" (lue le 2026-07-13) — champ de recherche,
 * filtres rapides (cosmétiques v1), état "Raccourcis" (avant saisie), état
 * résultats (carte compacte), état vide. Dépend de cs-cards.php.
 *
 * Complète (ne remplace pas) search-events.php : ce fichier élargit encore
 * la query PRINCIPALE de recherche (pre_get_posts) — un vestige inoffensif
 * ici puisqu'on interroge nous-mêmes une WP_Query dédiée, mais utile si un
 * jour ce gabarit custom est retiré et qu'on retombe sur le thème par défaut.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_search()) {
        return;
    }

    $query = get_search_query();

    get_header();

    $results = null;
    if ($query !== '') {
        $results = new WP_Query([
            'post_type' => 'tribe_events',
            'post_status' => 'publish',
            's' => $query,
            'posts_per_page' => 20,
        ]);
    }

    $shortcuts = [
        ['label' => 'Ce week-end', 'url' => home_url('/ce-week-end/')],
        ['label' => 'Savoie', 'url' => get_term_link(3, 'territoire')],
        ['label' => 'Piémont', 'url' => get_term_link(6, 'territoire')],
        ["label" => "Vallée d'Aoste", 'url' => get_term_link(8, 'territoire')],
        ['label' => 'Nice', 'url' => get_term_link(10, 'territoire')],
        ['label' => 'Concerts & Musique', 'url' => get_term_link(13, 'tribe_events_cat')],
    ];
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:16px 0 12px">
        <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="display:flex;align-items:center;gap:10px;border:1.5px solid #1D1D1B;padding:12px 14px">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.8" style="flex-shrink:0"><circle cx="10.5" cy="10.5" r="6.5"></circle><line x1="20" y1="20" x2="15.3" y2="15.3"></line></svg>
          <input type="search" name="s" value="<?php echo esc_attr($query); ?>" placeholder="Rechercher un événement, une ville…" style="flex:1;border:0;background:transparent;outline:0;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#1D1D1B">
        </form>
      </div>

      <div style="padding-bottom:16px;display:flex;gap:8px;overflow-x:auto">
        <div style="flex-shrink:0;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Catégorie</div>
        <div style="flex-shrink:0;border:1px solid #1D1D1B;padding:7px 12px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Ville</div>
      </div>

      <?php if ($query === ''): ?>

        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:12px">Raccourcis</div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:22px">
          <?php foreach ($shortcuts as $s): if (is_wp_error($s['url']) || !$s['url']) continue; ?>
          <a href="<?php echo esc_url($s['url']); ?>" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;padding:12px 14px">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B"><?php echo esc_html($s['label']); ?></div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.8"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="13 6 19 12 13 18"></polyline></svg>
          </a>
          <?php endforeach; ?>
        </div>

      <?php elseif ($results && $results->have_posts()): ?>

        <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:4px">Résultats pour «<?php echo esc_html($query); ?>»</div>
        <?php while ($results->have_posts()): $results->the_post(); echo cs_card_compact(get_the_ID()); endwhile; wp_reset_postdata(); ?>

      <?php else: ?>

        <div style="padding:32px 0 24px;text-align:center">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;color:#4A4A48;margin-bottom:14px">Aucun résultat : essayez une ville ou une catégorie</div>
          <div style="display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <a href="<?php echo esc_url(home_url('/ce-week-end/')); ?>" style="text-decoration:none;border:1px solid #1D1D1B;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Ce week-end</a>
            <a href="<?php echo esc_url(home_url('/tout-l-agenda/')); ?>" style="text-decoration:none;border:1px solid #1D1D1B;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">Tout l'agenda</a>
          </div>
        </div>

      <?php endif; ?>

    </div>
    <?php
    get_footer();
    exit;
});
