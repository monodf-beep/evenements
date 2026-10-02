<?php
/**
 * Fiche lieu (venue TEC, `tribe_venue`) — rendu complet en PHP
 * (template_redirect), fidèle à "Agenda Sabaudo - Page Lieu.dc.html" (lue le
 * 2026-07-13) : fil d'Ariane, H1, liste "Événements à venir" (date + titre),
 * mini-carte placeholder + adresse, footer de marque.
 *
 * ⚠️ PRÊT MAIS PAS ENCORE ATTEIGNABLE : les permaliens `/lieu/{slug}/`
 * pointent actuellement vers la page d'accueil au lieu du singulier
 * `tribe_venue` (bug de rewrite rules documenté dans STATUS.md, bloqué —
 * pas de solution côté template). Ce fichier s'activera automatiquement dès
 * que ce bug sera résolu (WP-CLI/SSH ou investigation de Franck) : rien à
 * changer ici, `is_singular('tribe_venue')` deviendra vrai une fois le
 * routage réparé.
 */
add_action('template_redirect', function () {
    if (is_admin() || !is_singular('tribe_venue')) {
        return;
    }

    $venue_id = get_the_ID();
    $title = get_the_title($venue_id);
    $terms = get_the_terms($venue_id, 'territoire');
    $territoire = ($terms && !is_wp_error($terms)) ? $terms[0] : null;

    $address = get_post_meta($venue_id, '_VenueAddress', true);
    $zip = get_post_meta($venue_id, '_VenueZip', true);
    $city = get_post_meta($venue_id, '_VenueCity', true);

    $events = new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 10,
        'orderby' => 'start_date',
        'order' => 'ASC',
        'meta_query' => [
            'relation' => 'AND',
            'start_date' => ['key' => '_EventStartDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME'],
            ['key' => '_EventVenueID', 'value' => $venue_id],
        ],
    ]);

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none">Accueil</a>
        <?php if ($territoire && !is_wp_error(get_term_link($territoire))): ?>
          / <a href="<?php echo esc_url(get_term_link($territoire)); ?>" style="color:#6F6B62;text-decoration:none"><?php echo esc_html($territoire->name); ?></a>
        <?php elseif ($city): ?>
          / <span><?php echo esc_html($city); ?></span>
        <?php endif; ?>
        / <span style="color:#1D1D1B"><?php echo esc_html($title); ?></span>
      </div>

      <div style="padding:12px 0 20px">
        <h1 style="margin:0;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($title); ?></h1>
      </div>

      <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:4px">Événements à venir</div>
      <?php if (!$events->have_posts()): ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62;padding:14px 0">Aucun événement à venir dans ce lieu pour l'instant.</p>
      <?php else: ?>
        <?php while ($events->have_posts()): $events->the_post(); $eid = get_the_ID(); ?>
        <a href="<?php echo esc_url(get_permalink($eid)); ?>" style="display:flex;align-items:baseline;gap:10px;text-decoration:none;border-bottom:1px solid #E3DCCE;padding:14px 0">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:800;color:#DC5D45;flex-shrink:0"><?php echo esc_html(cs_event_date_short($eid)); ?></div>
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:15.5px;color:#1D1D1B;line-height:1.25"><?php echo esc_html(get_the_title($eid)); ?></div>
        </a>
        <?php endwhile; wp_reset_postdata(); ?>
      <?php endif; ?>

      <div style="padding:20px 0 24px">
        <div style="aspect-ratio:16/9;background:#FBF7F0;border:1px solid #E3DCCE;display:flex;align-items:center;justify-content:center;margin-bottom:10px">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6F6B62" stroke-width="1.5"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"></path><circle cx="12" cy="9.5" r="2.3"></circle></svg>
        </div>
        <?php if ($address || $city): ?>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B;line-height:1.6">
          <?php echo esc_html($address); ?><?php if ($address && ($zip || $city)) echo '<br>'; ?>
          <?php echo esc_html(trim($zip . ' ' . $city)); ?>
        </div>
        <?php endif; ?>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
