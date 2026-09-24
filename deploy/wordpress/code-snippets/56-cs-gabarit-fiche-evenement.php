add_action('template_redirect', function () {
    if (is_admin() || !is_singular('tribe_events')) {
        return;
    }

    $event_id = get_the_ID();
    $L_it = function_exists('pll_get_post_language') && pll_get_post_language($event_id) === 'it';
    $LB = $L_it ? array('Accueil'=>'Home','Dans cette fiche'=>'In questa scheda','Quand'=>'Quando','Ou &amp; prix'=>'Dove &amp; prezzo','Carte'=>'Mappa','Ou'=>'Dove','Prix'=>'Prezzo','Gratuit'=>'Gratuito','Billetterie'=>'Biglietteria','Source officielle'=>'Fonte ufficiale','Ouvrir dans Maps'=>'Apri in Maps','Carte : '=>'Mappa : ','Recevez les dernieres actualites'=>'Ricevi le ultime notizie',"S'inscrire a la newsletter"=>'Iscriviti alla newsletter','Au meme endroit'=>'Nello stesso luogo','Meme categorie'=>'Stessa categoria','Pres d\'ici, memes dates'=>'Nello stesso periodo','Suivez-nous sur Instagram'=>'Seguici su Instagram','Suivez-nous sur Facebook'=>'Seguici su Facebook','Rechercher...'=>'Cerca...','Chercher'=>'Cerca') : array();
    $tr = function($s) use ($LB){ return isset($LB[$s]) ? $LB[$s] : $s; };
    $cats = get_the_terms($event_id, 'tribe_events_cat');
    $primary_cat = ($cats && !is_wp_error($cats)) ? $cats[0] : null;

    $venue_id = get_post_meta($event_id, '_EventVenueID', true);
    $venue_name = $venue_id ? get_the_title($venue_id) : '';
    $venue_city = $venue_id ? get_post_meta($venue_id, '_VenueCity', true) : '';
    if ($venue_city) {
        $venue_city = ($L_it ?? false)
            ? str_ireplace(array('Turin', 'Aoste'), array('Torino', 'Aosta'), $venue_city)
            : str_ireplace(array('Torino', 'Aosta'), array('Turin', 'Aoste'), $venue_city);
    }
    $venue_address = $venue_id ? get_post_meta($venue_id, '_VenueAddress', true) : '';
    $venue_full = trim($venue_name . ($venue_city ? ', ' . $venue_city : ''));
    $map_query = trim($venue_full . ($venue_address ? ', ' . $venue_address : ''));

    $start = get_post_meta($event_id, '_EventStartDate', true);
    $end = get_post_meta($event_id, '_EventEndDate', true);
    $horaire = get_post_meta($event_id, 'as_horaire', true);
    $gratuit = get_post_meta($event_id, 'as_gratuit', true);
    $tarif = get_post_meta($event_id, 'as_tarif', true);
    $billetterie = get_post_meta($event_id, 'as_billetterie_url', true);
    $source = get_post_meta($event_id, 'as_source_officielle_url', true);
    $verifie_le = get_post_meta($event_id, 'as_verifie_le', true);
    $image_credit = get_post_meta($event_id, 'as_image_credit', true);

    $has_quand = (bool) $start;
    $has_ou = (bool) $venue_full;
    $has_prix = ($gratuit === '1') || $tarif;

    // Rails contextuels (remplace l'ancien bloc "En vedette" generique, trop
    // gros visuellement et sans rapport avec ce que l'utilisateur regarde --
    // cf. retour Franck 2026-07-20). Deux rails horizontaux compacts (cartes
    // 150px, meme convention que .as-day-rail deja utilise sur la home) :
    // "Au meme endroit" (meme lieu, evenements a venir) et "Meme categorie"
    // (evenements a venir de la meme categorie, en excluant ceux deja
    // montres dans "Au meme endroit" pour ne pas les repeter). Source :
    // "Agenda Sabaudo - Fiche Evenement.dc.html" (maquette non utilisee
    // jusqu'ici), memes 2 rails.
    $lang_current = function_exists('pll_get_post_language') ? pll_get_post_language($event_id) : '';
    $now = current_time('Y-m-d H:i:s');

    $same_venue = $venue_id ? new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 6,
        'post__not_in' => [$event_id],
        'meta_query' => [
            ['key' => '_EventVenueID', 'value' => $venue_id],
            ['key' => '_EventStartDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'],
        ],
        'meta_key' => '_EventStartDate',
        'orderby' => 'meta_value',
        'order' => 'ASC',
        'lang' => $lang_current,
    ]) : null;
    $same_venue_ids = $same_venue ? wp_list_pluck($same_venue->posts, 'ID') : [];

    $same_cat = $primary_cat ? new WP_Query([
        'post_type' => 'tribe_events',
        'post_status' => 'publish',
        'posts_per_page' => 6,
        'post__not_in' => array_merge([$event_id], $same_venue_ids),
        'tax_query' => [['taxonomy' => 'tribe_events_cat', 'field' => 'term_id', 'terms' => $primary_cat->term_id]],
        'meta_query' => [
            ['key' => '_EventStartDate', 'value' => $now, 'compare' => '>=', 'type' => 'DATETIME'],
        ],
        'meta_key' => '_EventStartDate',
        'orderby' => 'meta_value',
        'order' => 'ASC',
        'lang' => $lang_current,
    ]) : null;
    $same_cat_ids = $same_cat ? wp_list_pluck($same_cat->posts, 'ID') : [];

    // 3e rail (prevu par le brief, jamais construit avant le 2026-07-24) : evenements
    // dont la date de DEBUT tombe dans les 3 jours suivant celle de l'evenement courant
    // -- "pres d'ici" au sens temporel (meme moment), pas geographique (pas de donnee
    // de distance disponible). Exclut ce qui est deja montre dans les 2 rails precedents.
    $same_dates = null;
    if ($start) {
        $start_ts_rail = strtotime($start);
        if ($start_ts_rail) {
            $window_start = date('Y-m-d', $start_ts_rail);
            $window_end = date('Y-m-d', $start_ts_rail + 3 * DAY_IN_SECONDS);
            $same_dates = new WP_Query([
                'post_type' => 'tribe_events',
                'post_status' => 'publish',
                'posts_per_page' => 6,
                'post__not_in' => array_merge([$event_id], $same_venue_ids, $same_cat_ids),
                'meta_query' => [
                    ['key' => '_EventStartDate', 'value' => [$window_start . ' 00:00:00', $window_end . ' 23:59:59'], 'compare' => 'BETWEEN', 'type' => 'DATETIME'],
                ],
                'meta_key' => '_EventStartDate',
                'orderby' => 'meta_value',
                'order' => 'ASC',
                'lang' => $lang_current,
            ]);
        }
    }

    $render_rail = function ($query, $title) {
        if (!$query || !$query->have_posts()) {
            return;
        }
        ?>
        <div style="padding:16px 0 4px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;letter-spacing:0.18em;color:#1D1D1B;text-transform:uppercase;border-top:1px solid #1D1D1B;padding-top:10px;margin-bottom:12px"><?php echo esc_html($title); ?></div>
          <div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:4px">
            <?php while ($query->have_posts()): $query->the_post();
              $rail_id = get_the_ID();
              $rail_start = get_post_meta($rail_id, '_EventStartDate', true);
              $rail_venue_id = get_post_meta($rail_id, '_EventVenueID', true);
              $rail_venue = $rail_venue_id ? get_the_title($rail_venue_id) : '';
              $rail_city = $rail_venue_id ? get_post_meta($rail_venue_id, '_VenueCity', true) : '';
              $rail_terr = get_the_terms($rail_id, 'territoire');
              $rail_terr_name = ($rail_terr && !is_wp_error($rail_terr)) ? $rail_terr[0]->name : '';
            ?>
            <a href="<?php the_permalink(); ?>" style="flex-shrink:0;width:150px;text-decoration:none">
              <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px;margin-bottom:6px"><?php echo get_the_post_thumbnail($rail_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
              <?php if ($rail_start): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:9.5px;font-weight:800;color:#1D1D1B;margin-bottom:2px"><?php echo esc_html(date_i18n('d/m', strtotime($rail_start))); ?></div><?php endif; ?>
              <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:13.5px;line-height:1.2;color:#1D1D1B;margin-bottom:3px"><?php the_title(); ?></div>
              <?php if ($rail_venue || $rail_city): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:10.5px;color:#6F6B62;margin-bottom:4px"><?php echo esc_html(trim($rail_venue . ($rail_city ? ' · ' . $rail_city : ''))); ?></div><?php endif; ?>
              <?php if ($rail_terr_name): ?><div style="display:inline-block;font-family:'Nunito Sans',sans-serif;font-size:9px;font-weight:800;color:#1D1D1B;border:1px solid #C9C4B8;padding:2px 7px"><?php echo esc_html($rail_terr_name); ?></div><?php endif; ?>
            </a>
            <?php endwhile; wp_reset_postdata(); ?>
          </div>
        </div>
        <?php
    };

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;line-height:1.6">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none"><?php echo $tr("Accueil"); ?></a>
        <?php if ($primary_cat): ?> &gt; <a href="<?php echo esc_url(get_term_link($primary_cat)); ?>" style="color:#6F6B62;text-decoration:none"><?php echo esc_html($primary_cat->name); ?></a><?php endif; ?>
        <?php if ($venue_city): ?> &gt; <span style="color:#1D1D1B"><?php echo esc_html($venue_city); ?></span><?php endif; ?>
      </div>

      <div style="padding:10px 0 0">
        <h1 style="margin:0;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:23px;line-height:1.22;color:#1D1D1B"><?php the_title(); ?></h1>
        <?php
        // Badge d'etat, calcule uniquement a partir des dates (aucune saisie manuelle
        // requise, aucun risque d'etre faux) -- "Complet"/"Annule"/"Reporte" ecartes
        // (demande explicite Franck 2026-07-24 : ces etats dependraient d'une meta
        // as_statut jamais fiable sur un site alimente en grande partie par import
        // automatique). Uniquement "Dernier jour" et "En cours", purement calcules.
        $cs_badge = '';
        if ($start) {
            $cs_start_ts = strtotime($start);
            $cs_end_ts = $end ? strtotime($end) : $cs_start_ts;
            $cs_now_ts = current_time('timestamp');
            if ($cs_now_ts >= $cs_start_ts && $cs_now_ts <= $cs_end_ts) {
                $cs_days_left = (int) floor(($cs_end_ts - $cs_now_ts) / DAY_IN_SECONDS);
                if ($cs_days_left <= 0) {
                    $cs_badge = $L_it ? 'Ultimo giorno' : 'Dernier jour';
                } else {
                    $cs_badge = $L_it ? 'In corso' : 'En cours';
                }
            }
        }
        if ($cs_badge): ?>
        <div style="display:inline-block;margin-top:8px;font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.05em;text-transform:uppercase;color:#F7F1E8;background:#DC5D45;padding:4px 10px"><?php echo esc_html($cs_badge); ?></div>
        <?php endif; ?>
      </div>

      <?php if ($has_quand || $has_ou): ?>
      <div style="padding:14px 0 0">
        <div style="border-top:1px solid #E3DCCE;border-bottom:1px solid #E3DCCE;padding:11px 0;display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px">
          <div style="font-family:'Nunito Sans',sans-serif;font-size:9px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:#6F6B62"><?php echo $tr("Dans cette fiche"); ?></div>
          <?php if ($has_quand): ?><a href="#as-quand" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none"><?php echo $tr("Quand"); ?></a><?php endif; ?>
          <?php if ($has_ou): ?><a href="#as-ou" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none"><?php echo $tr("Ou &amp; prix"); ?></a><?php endif; ?>
          <?php if ($has_ou): ?><a href="#as-carte" style="font-family:'Nunito Sans',sans-serif;font-size:12.5px;font-weight:700;color:#1D1D1B;text-decoration:none"><?php echo $tr("Carte"); ?></a><?php endif; ?>
        </div>
      </div>
      <?php endif; ?>

      <?php if (has_post_thumbnail($event_id)): ?>
      <div style="padding:16px 0 0">
        <div style="aspect-ratio:3/2;overflow:hidden;background:#1D1D1B"><?php echo get_the_post_thumbnail($event_id, 'large', ['style' => 'width:100%;height:100%;object-fit:cover']); ?></div>
        <?php if ($image_credit): ?>
        <div style="padding:6px 0 0;font-family:'Nunito Sans',sans-serif;font-size:10.5px;color:#6F6B62"><?php echo esc_html($image_credit); ?></div>
        <?php endif; ?>
      </div>
      <?php else: ?>
      <div style="padding:16px 0 0"><div style="aspect-ratio:3/2;overflow:hidden"><?php echo function_exists('cs_fallback_visual') ? cs_fallback_visual($event_id) : ''; ?></div></div>
      <?php endif; ?>

      <div style="padding:18px 0 0;font-family:'Nunito Sans',sans-serif;font-size:14.5px;line-height:1.65;color:#1D1D1B">
        <?php echo wpautop(wptexturize(get_the_content(null, false, $event_id))); ?>
      </div>
      <?php /* Point d'accroche generique sous le corps de la fiche (24/09/2026) : les ajouts d'affichage s'y branchent sans retoucher ce gabarit. Premier usage : cs-moment-fort-maillage.php. */ do_action('cs_fiche_apres_corps', $event_id); ?>

      <?php if ($has_quand || $has_ou): ?>
      <div id="as-quand" style="padding:20px 0 0;scroll-margin-top:16px">
        <div style="background:#F7F1E8;border-radius:12px;padding:18px 20px">

          <?php if ($has_quand): ?>
          <div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:14px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#DC5D45" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:2px" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;font-weight:700;color:#1D1D1B;line-height:1.5">
              <?php
              $as_today = current_time('Y-m-d');
              $as_s_day = substr($start, 0, 10);
              $as_e_day = $end ? substr($end, 0, 10) : $as_s_day;
              $as_in_progress = ($as_s_day < $as_today && $as_e_day >= $as_today);
              ?>
              <?php if ($as_in_progress): ?>
                <?php echo $L_it ? "Fino al " : "Jusqu'au "; ?><?php echo esc_html(date_i18n('d/m/Y', strtotime($end))); ?>
              <?php else: ?>
                <?php echo $L_it ? "Data : " : "Date : "; ?><?php echo esc_html(date_i18n('d/m/Y', strtotime($start))); ?><?php if ($end && $as_e_day !== $as_s_day): ?> - <?php echo esc_html(date_i18n('d/m/Y', strtotime($end))); ?><?php endif; ?>
              <?php endif; ?>
              <?php if ($horaire): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:400;color:#6F6B62;margin-top:2px">Horaire : <?php echo esc_html($horaire); ?></div><?php endif; ?>
            </div>
          </div>
          <?php endif; ?>

          <?php if ($has_ou): ?>
          <div id="as-ou" style="display:flex;gap:10px;align-items:flex-start;margin-bottom:14px;scroll-margin-top:16px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#DC5D45" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:2px" aria-hidden="true"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.5">
              <div style="font-weight:700;color:#1D1D1B"><?php echo esc_html($venue_name ?: $venue_full); ?></div>
              <?php if ($venue_city && $venue_name): ?><div style="font-size:12px;color:#6F6B62"><?php echo esc_html($venue_city); ?></div><?php endif; ?>
              <?php if ($venue_address): ?><div style="font-size:12px;color:#6F6B62"><?php echo esc_html($venue_address); ?></div><?php endif; ?>
            </div>
          </div>
          <?php endif; ?>

          <?php if ($has_prix): ?>
          <div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:14px">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#DC5D45" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:2px" aria-hidden="true"><path d="M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v1a2 2 0 0 0 0 4v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1a2 2 0 0 0 0-4V9z"/></svg>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:13.5px;font-weight:700;color:#1D1D1B"><?php echo $gratuit === '1' ? $tr("Gratuit") : esc_html($tarif); ?></div>
          </div>
          <?php endif; ?>

          <?php if ($primary_cat || $billetterie || $source): ?>
          <div style="border-top:1px solid #E3DCCE;margin:0 0 14px"></div>
          <div style="display:flex;align-items:center;justify-content:space-between;gap:10px 14px;flex-wrap:wrap">
            <?php if ($primary_cat): ?>
            <a href="<?php echo esc_url(get_term_link($primary_cat)); ?>" style="background:#18365E;color:#fff;font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:700;padding:5px 12px;border-radius:100px;text-decoration:none;white-space:nowrap"><?php echo esc_html($primary_cat->name); ?></a>
            <?php endif; ?>
            <div style="display:flex;gap:14px;flex-wrap:wrap">
              <?php if ($billetterie): ?><a href="<?php echo esc_url($billetterie); ?>" target="_blank" rel="noopener" style="font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#DC5D45;text-decoration:none;white-space:nowrap"><?php echo $tr("Billetterie"); ?> &#8599;</a><?php endif; ?>
              <?php if ($source): ?><a href="<?php echo esc_url($source); ?>" target="_blank" rel="noopener" style="font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#DC5D45;text-decoration:none;white-space:nowrap"><?php echo $tr("Source officielle"); ?> &#8599;</a><?php endif; ?>
            </div>
          </div>
          <?php endif; ?>

        </div>

        <?php if ($verifie_le): ?>
        <div style="margin-top:8px;font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62;display:flex;align-items:center;gap:5px">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#639922" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>
          <?php echo $L_it ? 'Verificato il ' : 'Vérifié le '; ?><?php echo esc_html(date_i18n('d/m', strtotime($verifie_le))); ?>
        </div>
        <?php endif; ?>
      </div>
      <?php endif; ?>

      <?php
      /* 2026-08-03 (Franck) : encadre agenda remonte dans la fiche.
         Mesure avant correction : il etait a 3016 px sur une page de 3962, soit
         76 pour cent de la hauteur, et surtout APRES quatre sorties -- la carte,
         Meme categorie, Pres d ici, Instagram et le champ de recherche. La page
         proposait de partir ailleurs avant de proposer d enregistrer la date
         qu on est en train de lire.
         Place ici, juste apres le bloc pratique, au moment precis ou le lecteur
         vient d apprendre quand et ou. Volontairement PAS au-dessus de la date :
         l intention d y aller ne peut pas naitre avant de savoir quand. */
      ?>
      <?php echo function_exists('cs_atc_render') ? cs_atc_render($event_id) : ''; ?>

      <?php if ($has_ou): ?>
      <div id="as-carte" style="padding:20px 0 0;scroll-margin-top:16px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:800;letter-spacing:0.1em;color:#1D1D1B;text-transform:uppercase;margin-bottom:8px"><?php echo $tr("Carte"); ?></div>
        <div style="aspect-ratio:16/11;background:#FBF7F0;border:1px solid #E3DCCE;border-radius:12px;position:relative;overflow:hidden">
          <?php $cs_map_url = 'https://maps.google.com/maps?q=' . rawurlencode($map_query) . '&output=embed'; ?>
          <div class="cmplz-placeholder-parent" style="width:100%;height:100%">
            <iframe data-cmplz-target="src" data-src-cmplz="<?php echo esc_url($cs_map_url); ?>" src="about:blank" class="cmplz-iframe cmplz-iframe-styles cmplz-no-video" data-service="google-maps" data-category="marketing" width="100%" height="100%" style="border:0;display:block" referrerpolicy="no-referrer-when-downgrade" title="<?php echo esc_attr($tr("Carte : ") . $map_query); ?>"></iframe>
          </div>
          <a href="<?php echo esc_url('https://www.google.com/maps/search/?api=1&query=' . rawurlencode($map_query)); ?>" target="_blank" rel="noopener" style="position:absolute;top:10px;left:10px;background:#F7F1E8;border:1px solid #1D1D1B;text-decoration:none;padding:5px 10px;font-family:'Nunito Sans',sans-serif;font-size:11px;font-weight:700;color:#1D1D1B"><?php echo $tr("Ouvrir dans Maps"); ?> &#8599;</a>
        </div>
      </div>
      <?php endif; ?>

      

      <?php $render_rail($same_venue, $tr('Au meme endroit')); ?>
      <?php $render_rail($same_cat, $tr('Meme categorie')); ?>
      <?php $render_rail($same_dates, $tr("Pres d'ici, memes dates")); ?>

      <?php
      $cs_inst_canon = function_exists('cs_instagram_canon_for_event') ? cs_instagram_canon_for_event($event_id) : null;
      $cs_inst_acc = function_exists('cs_instagram_account') ? cs_instagram_account($cs_inst_canon, $L_it ? 'it' : 'fr') : null;
      $cs_inst_label = $cs_inst_acc ? ($L_it ? 'Segui Agenda Sabauda ' . $cs_inst_acc['label'] . ' su Instagram' : 'Suivre Agenda Sabauda ' . $cs_inst_acc['label'] . ' sur Instagram') : '';
      ?>
      <div style="padding:24px 0 0;display:flex;flex-direction:column;gap:12px">
        <?php if ($cs_inst_acc): ?>
        <a href="<?php echo esc_url($cs_inst_acc['url']); ?>" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;border:1px solid #1D1D1B;padding:16px 18px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:16px;color:#1D1D1B"><?php echo esc_html($cs_inst_label); ?></div>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="4"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="1"></circle></svg>
        </a>
        <?php endif; ?>
        <?php // Aucun compte Facebook a ce jour ; reactiver en renseignant $cs_fb_acc le jour ou un compte existera. ?>
        <?php $cs_fb_acc = null; if ($cs_fb_acc): ?>
        <a href="<?php echo esc_url($cs_fb_acc['url']); ?>" target="_blank" rel="noopener" style="display:flex;align-items:center;justify-content:space-between;text-decoration:none;background:#FBF7F0;border:1px solid #1D1D1B;padding:16px 18px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:16px;color:#1D1D1B"><?php echo esc_html($tr('Suivez-nous sur Facebook')); ?></div>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.5"><path d="M15 4h-2a4 4 0 0 0-4 4v3H7v3h2v7h3v-7h2.5l.5-3H12V8a1 1 0 0 1 1-1h2z"></path></svg>
        </a>
        <?php endif; ?>
      </div>

      <form role="search" method="get" action="<?php echo esc_url(home_url('/')); ?>" style="padding:20px 0 0;display:flex;gap:8px">
        <input type="search" name="s" placeholder="<?php echo esc_attr($tr('Rechercher...')); ?>" style="flex:1;border:1px solid #1D1D1B;padding:11px 14px;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B;background:transparent">
        <button type="submit" style="background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:11px 18px;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700"><?php echo esc_html($tr('Chercher')); ?></button>
      </form>

      

      <div style="padding:20px 0 0">
        <div style="background:#DC5D45;padding:18px 20px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:17px;color:#F7F1E8;margin-bottom:10px"><?php echo $tr("Recevez les dernieres actualites"); ?><?php echo $venue_city ? ($L_it ? ' di ' : ' de ') . esc_html($venue_city) : ($L_it ? ' dell\'agenda' : ' de l\'agenda'); ?></div>
          <a href="<?php echo esc_url(home_url('/newsletter/')); ?>" style="display:block;text-align:center;background:#F7F1E8;color:#1D1D1B;text-decoration:none;padding:11px 0;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800"><?php echo $tr("S'inscrire a la newsletter"); ?></a>
        </div>
      </div>

      <div style="padding:20px 0 0">
        
      </div>

      <div style="padding:24px 0 24px"></div>

    </div>
    <?php
    get_footer();
    exit;
}, 1);
