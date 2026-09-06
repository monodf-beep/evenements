add_action('template_redirect', function () {
    if (is_admin() || (!is_tax('territoire') && !is_tax('tribe_events_cat'))) {
        return;
    }

    $term = get_queried_object();
    $title = $term ? $term->name : '';
    $is_territoire = is_tax('territoire');
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';

    /* 2026-07-23 (Franck) : les 4 territoires migrent vers le gabarit hub (meme moteur
       que les villes, cs_hub_ville_render en mode territoire, snippet 61) -- 301 vers
       la nouvelle page au lieu de rendre l'ancien gabarit ici (filtres casses, cf.
       diagnostic session). Ne concerne QUE la taxonomie territoire ; tribe_events_cat
       continue de passer par ce fichier normalement, inchange.
       Rollback : supprimer ce bloc, l'ancien gabarit territoire se re-affiche direct. */
    if ($is_territoire && $term) {
        $cs_terr_hub_redirect_map = array(
            3 => 2857, 318 => 2858,
            6 => 2859, 321 => 2860,
            8 => 2861, 324 => 2862,
            10 => 2863, 327 => 2864,
        );
        if (isset($cs_terr_hub_redirect_map[$term->term_id])) {
            $cs_redir_target = get_permalink($cs_terr_hub_redirect_map[$term->term_id]);
            if ($cs_redir_target) {
                wp_safe_redirect($cs_redir_target, 301);
                exit;
            }
        }
    }

    get_header();

    // Langue : ces Hubs interrogeaient toutes langues confondues (constat 2026-07-20),
    // d'ou des fiches italiennes sur une page francaise. On scope a la langue courante.
    $base_tax = [['taxonomy' => $term->taxonomy, 'field' => 'term_id', 'terms' => $term->term_id]];

    // Territoire actif (cookie/GET) : sur une page CATEGORIE, on restreint au territoire
    // choisi par le visiteur. Inutile sur une page TERRITOIRE (le terme EST le territoire).
    $cs_active_terr_term = 0;
    if (!$is_territoire && function_exists('cs_territoire_actif') && ($cs_canon = cs_territoire_actif())) {
        $cs_t = cs_terr_canon_data()[$cs_canon];
        $cs_active_terr_term = (int) ($lang === 'it' ? $cs_t['it_term'] : $cs_t['fr_term']);
        $base_tax[] = [
            'taxonomy' => 'territoire', 'field' => 'term_id',
            'terms' => $cs_active_terr_term,
        ];
    }

    // 2026-09-06 (Franck) : ne jamais lister le passe. Sans ce plancher, "Tous" affichait
    // 141 fiches terminees sur 263 publiees (Sport : 10 passees sur 13). Meme critere que
    // le hub ville (snippet 61) : la date de FIN decide, une expo en cours reste visible.
    $cs_now = current_time('Y-m-d H:i:s');
    $base_args = [
        'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => -1,
        'tax_query' => $base_tax,
        'lang' => $lang,
        'meta_query' => [['key' => '_EventEndDate', 'value' => $cs_now, 'compare' => '>=', 'type' => 'DATETIME']],
        'meta_key' => '_EventStartDate', 'orderby' => 'meta_value', 'order' => 'ASC', 'fields' => 'ids',
    ];
    $base_q = new WP_Query($base_args);
    $base_ids = $base_q->posts;

    $dates = [];
    $villes = [];
    $others = [];
    $other_taxonomy = $is_territoire ? 'tribe_events_cat' : 'territoire';
    foreach ($base_ids as $eid) {
        $s = get_post_meta($eid, '_EventStartDate', true);
        if ($s) {
            $dates[date('Y-m-d', strtotime($s))] = true;
        }
        $venue_id = get_post_meta($eid, '_EventVenueID', true);
        if ($venue_id) {
            $city = get_post_meta($venue_id, '_VenueCity', true);
            if ($city) {
                $villes[$city] = true;
            }
        }
        $terms = get_the_terms($eid, $other_taxonomy);
        if ($terms && !is_wp_error($terms)) {
            foreach ($terms as $t) {
                $others[$t->term_id] = $t;
            }
        }
    }
    ksort($dates);
    $dates = array_keys($dates);
    ksort($villes);
    $villes = array_keys($villes);
    uasort($others, function ($a, $b) { return strcmp($a->name, $b->name); });
    $others = array_values($others);

    $sel_date = isset($_GET['jour']) ? sanitize_text_field(wp_unslash($_GET['jour'])) : '';
    $sel_quand = isset($_GET['quand']) ? sanitize_key(wp_unslash($_GET['quand'])) : '';
    $win = function_exists('cs_hub_window') ? cs_hub_window($sel_quand) : null;
    $sel_ville = isset($_GET['ville']) ? sanitize_text_field(wp_unslash($_GET['ville'])) : '';
    $sel_other = isset($_GET['filtre2']) ? sanitize_title(wp_unslash($_GET['filtre2'])) : '';

    $final_args = $base_args;
    $final_args['posts_per_page'] = 50;
    unset($final_args['fields']);

    // Les filtres s'AJOUTENT au plancher ci-dessus (avant, ils le remplacaient).
    $cs_date_ok = false;
    if ($sel_date && preg_match('/^\d{4}-\d{2}-\d{2}$/', $sel_date)) {
        $cs_date_ok = true;
        $final_args['meta_query'][] = ['key' => '_EventStartDate', 'value' => [$sel_date . ' 00:00:00', $sel_date . ' 23:59:59'], 'compare' => 'BETWEEN', 'type' => 'DATETIME'];
    }
    if (!$cs_date_ok && $win) {
        $final_args['meta_query'][] = ['key' => '_EventStartDate', 'value' => $win[1], 'compare' => '<=', 'type' => 'DATETIME'];
        $final_args['meta_query'][] = ['key' => '_EventEndDate', 'value' => $win[0], 'compare' => '>=', 'type' => 'DATETIME'];
    }
    if ($sel_ville && in_array($sel_ville, $villes, true)) {
        $venue_ids = get_posts([
            'post_type' => 'tribe_venue', 'post_status' => 'publish', 'posts_per_page' => -1, 'fields' => 'ids',
            'meta_query' => [['key' => '_VenueCity', 'value' => $sel_ville]],
        ]);
        $final_args['meta_query'][] = ['key' => '_EventVenueID', 'value' => $venue_ids ?: [0], 'compare' => 'IN'];
    }
    $sel_other_valid = false;
    foreach ($others as $o) {
        if ($o->slug === $sel_other) { $sel_other_valid = true; break; }
    }
    if ($sel_other_valid) {
        $final_args['tax_query'][] = ['taxonomy' => $other_taxonomy, 'field' => 'slug', 'terms' => $sel_other];
    }

    $q = new WP_Query($final_args);

    $labels = $lang === 'it'
        ? ['date' => 'Data', 'ville' => 'Città', 'other' => $is_territoire ? 'Categoria' : 'Territorio', 'tous' => 'Tutte', 'appliquer' => 'Applica']
        : ['date' => 'Date', 'ville' => 'Ville', 'other' => $is_territoire ? 'Catégorie' : 'Territoire', 'tous' => 'Tous', 'appliquer' => 'Appliquer'];
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:12px 0 0;font-family:'Nunito Sans',sans-serif;font-size:11.5px;color:#6F6B62">
        <a href="<?php echo esc_url(home_url('/')); ?>" style="color:#6F6B62;text-decoration:none">Accueil</a> / <span style="color:#1D1D1B"><?php echo esc_html($title); ?></span>
      </div>

      <div style="padding-top:12px">
        <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($title); ?></h1>
        <?php $cs_h2 = $term ? get_term_meta($term->term_id, 'cs_hub_h2', true) : ''; ?>
        <?php if ($cs_h2): ?><h2 style="margin:0 0 10px;font-family:'Nunito Sans',sans-serif;font-weight:800;font-size:15px;line-height:1.3;color:#4A4A48"><?php echo esc_html($cs_h2); ?></h2><?php endif; ?>
        <?php
        // Intro editoriale : si le terme (categorie ou territoire) a une description
        // remplie dans WordPress, on l'affiche (contenu evergreen, editable sans code,
        // fort levier SEO). Sinon, texte generique. Demande Franck 2026-07-21.
        $cs_intro = ($term && !empty($term->description)) ? trim($term->description) : '';
        if ($cs_intro === '') {
            $cs_intro = $is_territoire
                ? ($lang === 'it' ? 'Tutti gli eventi di questo territorio, aggiornati in continuo.' : 'Retrouvez tous les événements de ce territoire, mis à jour en continu.')
                : ($lang === 'it' ? 'La programmazione di questa categoria sui quattro territori, aggiornata in continuo.' : 'La programmation de cette catégorie sur les quatre territoires, mise à jour en continu.');
            $cs_intro = '<p>' . esc_html($cs_intro) . '</p>';
        } else {
            $cs_intro = wp_kses_post(wpautop($cs_intro));
        }
        ?>
        <div style="margin:0 0 18px;font-family:'Nunito Sans',sans-serif;font-size:13.5px;line-height:1.55;color:#4A4A48"><?php echo $cs_intro; ?></div>
      </div>

      <?php
      if ($is_territoire && function_exists('cs_terr_canon_data')) {
          $cs_canon_v = '';
          foreach (cs_terr_canon_data() as $ck => $cv) {
              if ((int) $cv['fr_term'] === (int) $term->term_id || (int) $cv['it_term'] === (int) $term->term_id) { $cs_canon_v = $ck; break; }
          }
          if ($cs_canon_v) {
              $cs_villes = get_posts(array('post_type' => 'page', 'post_status' => 'publish', 'posts_per_page' => -1, 'lang' => $lang, 'orderby' => 'title', 'order' => 'ASC',
                  'meta_query' => array('relation' => 'AND',
                      array('key' => 'cs_hub_territoire', 'value' => $cs_canon_v),
                      array('key' => 'cs_hub_quand', 'compare' => 'NOT EXISTS'),
                      array('relation' => 'OR',
                          array('key' => '_yoast_wpseo_meta-robots-noindex', 'compare' => 'NOT EXISTS'),
                          array('key' => '_yoast_wpseo_meta-robots-noindex', 'value' => '1', 'compare' => '!='),
                      ),
                  )));
              if ($cs_villes) {
                  $cs_lbl = ($lang === 'it') ? 'Città' : 'Villes';
                  echo '<div style="margin:0 0 20px"><div style="font-family:sans-serif;font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#6F6B62;margin-bottom:8px">' . esc_html($cs_lbl) . '</div><div style="display:flex;flex-wrap:wrap;gap:8px">';
                  foreach ($cs_villes as $vp) {
                      echo '<a href="' . esc_url(get_permalink($vp->ID)) . '" style="text-decoration:none;border:1px solid #1D1D1B;padding:6px 12px;font-family:sans-serif;font-size:12px;font-weight:700;color:#1D1D1B">' . esc_html(get_the_title($vp->ID)) . '</a>';
                  }
                  echo '</div></div>';
              }
          }
      }
      ?>
      <?php
      $cs_act = get_term_link($term); if (is_wp_error($cs_act)) { $cs_act = home_url('/'); }
      $cs_tw = ($lang === 'it') ? array('' => 'Tutti', 'aujourdhui' => 'Oggi', 'weekend' => 'Weekend', 'semaine' => 'Settimana') : array('' => 'Tous', 'aujourdhui' => "Aujourd'hui", 'weekend' => 'Ce week-end', 'semaine' => 'Cette semaine');
      echo '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">';
      foreach ($cs_tw as $cs_wk => $cs_wl) {
          $cs_wu = $cs_wk ? add_query_arg('quand', $cs_wk, $cs_act) : remove_query_arg('quand', $cs_act);
          $cs_on = ($sel_quand === $cs_wk);
          echo '<a href="' . esc_url($cs_wu) . '" style="text-decoration:none;padding:6px 12px;font-family:sans-serif;font-size:12px;font-weight:700;border:1px solid #1D1D1B;' . ($cs_on ? 'background:#1D1D1B;color:#F7F1E8' : 'background:#fff;color:#1D1D1B') . '">' . esc_html($cs_wl) . '</a>';
      }
      echo '</div>';
      ?>
      <form method="get" style="padding-bottom:16px">
        <?php if ($sel_quand): ?><input type="hidden" name="quand" value="<?php echo esc_attr($sel_quand); ?>"><?php endif; ?>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <input type="date" name="jour" value="<?php echo esc_attr($sel_date); ?>"<?php if ($dates): ?> min="<?php echo esc_attr($dates[0]); ?>" max="<?php echo esc_attr(end($dates)); ?>"<?php endif; ?> aria-label="<?php echo esc_attr($labels['date']); ?>" style="border:1px solid #1D1D1B;padding:6px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
          <?php if ($villes): ?>
          <select name="ville" style="border:1px solid #1D1D1B;padding:7px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
            <option value=""><?php echo esc_html($labels['ville']); ?></option>
            <?php foreach ($villes as $v): ?>
              <option value="<?php echo esc_attr($v); ?>" <?php selected($sel_ville, $v); ?>><?php echo esc_html($v); ?></option>
            <?php endforeach; ?>
          </select>
          <?php endif; ?>
          <?php if ($others): ?>
          <select name="filtre2" style="border:1px solid #1D1D1B;padding:7px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;background:#fff">
            <option value=""><?php echo esc_html($labels['other']); ?></option>
            <?php foreach ($others as $o): ?>
              <option value="<?php echo esc_attr($o->slug); ?>" <?php selected($sel_other, $o->slug); ?>><?php echo esc_html($o->name); ?></option>
            <?php endforeach; ?>
          </select>
          <?php endif; ?>
          <button type="submit" style="background:#1D1D1B;color:#F7F1E8;border:0;cursor:pointer;padding:7px 14px;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700"><?php echo esc_html($labels['appliquer']); ?></button>
        </div>
      </form>

      <?php if (!$q->have_posts()): ?>
        <?php
        // Message vide chaleureux et contextuel (categorie + territoire actif) plutot
        // que le plat "Aucun evenement". Le repli inter-territoires prend le relais juste
        // en dessous. Demande Franck 2026-07-21 ("c'est un peu triste").
        $cs_et = (!$is_territoire && !empty($cs_active_terr_term)) ? get_term($cs_active_terr_term) : null;
        $cs_etn = ($cs_et && !is_wp_error($cs_et)) ? $cs_et->name : '';
        if ($lang === 'it') {
            $cs_empty = $cs_etn ? sprintf('Nessun evento « %s » in programma in %s per il momento.', $title, $cs_etn) : sprintf('Nessun evento « %s » in programma per il momento.', $title);
        } else {
            $cs_empty = $cs_etn ? sprintf('Pas encore d’événement « %s » programmé en %s.', $title, $cs_etn) : sprintf('Pas encore d’événement « %s » programmé.', $title);
        }
        ?>
        <p style="font-family:'Nunito Sans',sans-serif;color:#6F6B62;font-size:13.5px"><?php echo esc_html($cs_empty); ?></p>
      <?php else: ?>
        <?php while ($q->have_posts()): $q->the_post(); echo cs_card_compact(get_the_ID()); endwhile; wp_reset_postdata(); ?>
        <div style="padding:8px 0 24px;display:flex;justify-content:center;gap:8px">
          <div style="width:32px;height:32px;display:flex;align-items:center;justify-content:center;background:#1D1D1B;color:#F7F1E8;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700">1</div>
        </div>
      <?php endif; ?>

      <?php
      // Repli inter-territoires : sur une page CATEGORIE scopee a un territoire, si le
      // resultat local est pauvre (<=3), proposer la meme categorie dans les autres
      // territoires de l'espace alpin (demande Franck 2026-07-21). "Chez toi" reste en
      // premier ; "ailleurs" est clairement separe et chaque carte porte sa pastille
      // territoire (cs_card_standard).
      if (!$is_territoire && !empty($cs_active_terr_term) && $q->found_posts <= 3 && function_exists('cs_terr_canon_data')) {
          $cs_autres = [];
          foreach (cs_terr_canon_data() as $cv) {
              $tid = (int) ($lang === 'it' ? $cv['it_term'] : $cv['fr_term']);
              if ($tid !== (int) $cs_active_terr_term) { $cs_autres[] = $tid; }
          }
          $ailleurs_q = new WP_Query([
              'post_type' => 'tribe_events', 'post_status' => 'publish', 'posts_per_page' => 6, 'lang' => $lang,
              'tax_query' => ['relation' => 'AND',
                  ['taxonomy' => $term->taxonomy, 'field' => 'term_id', 'terms' => $term->term_id],
                  ['taxonomy' => 'territoire', 'field' => 'term_id', 'terms' => $cs_autres],
              ],
              'meta_query' => [['key' => '_EventEndDate', 'value' => current_time('Y-m-d H:i:s'), 'compare' => '>=', 'type' => 'DATETIME']],
              'meta_key' => '_EventStartDate', 'orderby' => 'meta_value', 'order' => 'ASC',
          ]);
          if ($ailleurs_q->have_posts()):
              $ail_t = $lang === 'it' ? 'Altrove nello spazio sabaudo' : "Ailleurs dans l'espace sabaudo";
              $ail_s = $lang === 'it' ? 'La stessa categoria negli altri territori' : 'La même catégorie dans les autres territoires';
      ?>
        <div style="margin:26px 0 6px;border-top:2px solid #1D1D1B;padding-top:16px">
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:20px;color:#1D1D1B"><?php echo esc_html($ail_t); ?></div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62;margin-bottom:8px"><?php echo esc_html($ail_s); ?></div>
        </div>
        <?php while ($ailleurs_q->have_posts()): $ailleurs_q->the_post(); echo cs_card_compact(get_the_ID()); endwhile; wp_reset_postdata(); ?>
      <?php endif; } ?>

            <?php
      if (function_exists('cs_terr_canon_data')) {
          $cs_gargs = array('post_type' => 'post', 'post_status' => 'publish', 'posts_per_page' => 4, 'lang' => $lang, 'orderby' => 'title', 'order' => 'ASC');
          $cs_show = false;
          if ($is_territoire) {
              $cs_gcanon = '';
              foreach (cs_terr_canon_data() as $ck => $cv) { if ((int) $cv['fr_term'] === (int) $term->term_id || (int) $cv['it_term'] === (int) $term->term_id) { $cs_gcanon = $ck; break; } }
              if ($cs_gcanon) { $cs_gargs['meta_key'] = 'cs_guide_territoire'; $cs_gargs['meta_value'] = $cs_gcanon; $cs_show = true; }
          } else {
              $cs_gargs['meta_key'] = 'cs_guide_cat_term'; $cs_gargs['meta_value'] = (int) $term->term_id; $cs_show = true;
          }
          if ($cs_show) {
              $cs_guides = get_posts($cs_gargs);
              if ($cs_guides) {
                  echo '<div style="margin:8px 0 22px"><div style="font-family:sans-serif;font-size:12px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#6F6B62;margin-bottom:6px">' . (($lang === 'it') ? 'Da leggere' : 'À lire') . '</div>';
                  foreach ($cs_guides as $gp) {
                      echo '<a href="' . esc_url(get_permalink($gp->ID)) . '" style="display:block;text-decoration:none;border-top:1px solid #E3DCCE;padding:11px 0;font-family:sans-serif;font-size:14px;font-weight:700;color:#18365E">' . esc_html(get_the_title($gp->ID)) . '</a>';
                  }
                  echo '</div>';
              }
          }
      }
      ?>
      <div style="margin:0 0 24px;background:#FBF7F0;padding:16px">
        <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:700;color:#1D1D1B;margin-bottom:10px"><?php
          /* 2026-08-03 (Franck) : nommer le territoire quand le lecteur en a
             choisi un dans le bandeau. Le nom est plus concret que « votre
             territoire », et il confirme au lecteur que son choix est pris en
             compte. Repli sur la formule generique quand les 4 territoires sont
             affiches, ce qui est le cas par defaut. Les prepositions sont ecrites
             a la main : aucune regle ne donne « de la Savoie » mais « du Piemont ». */
          $cs_nl_terr = '';
          $cs_nl_actif = function_exists('cs_territoire_actif') ? cs_territoire_actif() : null;
          if ($cs_nl_actif) {
              $cs_nl_prep = ($lang === 'it')
                  ? array('savoie' => 'della Savoia', 'piemont' => 'del Piemonte',
                          'vda' => "della Valle d'Aosta", 'nice' => 'della Contea di Nizza')
                  : array('savoie' => 'de la Savoie', 'piemont' => 'du Piémont',
                          'vda' => "de la Vallée d'Aoste", 'nice' => 'du Comté de Nice');
              if (isset($cs_nl_prep[$cs_nl_actif])) { $cs_nl_terr = $cs_nl_prep[$cs_nl_actif]; }
          }
          if ($lang === 'it') {
              echo "Ricevi ogni settimana l'agenda " . ($cs_nl_terr !== '' ? $cs_nl_terr : 'del tuo territorio');
          } else {
              echo "Recevez chaque semaine l'agenda " . ($cs_nl_terr !== '' ? $cs_nl_terr : 'de votre territoire');
          }
          ?></div>
        <?php
        /* 2026-08-03 (Franck) : ce formulaire ne servait a rien. Ni action, ni
           method, ni name sur le champ e-mail : il rechargeait la page et jetait
           l adresse. Present sur les 24 archives de categorie et les 28 hubs de
           territoire, dans les deux langues. On le branche sur le circuit qui
           fonctionne deja, celui du snippet 52 : meme page cible, meme nonce,
           meme piege a robots, meme horodatage. Le contexte est transmis en
           champ cache pour un usage ulterieur -- il n est PAS encore exploite,
           l etape 2 ne propose que territoires et villes. */
        $cs_nl_page = ($lang === 'it') ? 3282 : 1703;
        $cs_nl_url  = get_permalink($cs_nl_page);
        ?>
        <form method="post" action="<?php echo esc_url($cs_nl_url); ?>" style="display:flex;border-bottom:1px solid #1D1D1B;padding-bottom:8px">
          <?php wp_nonce_field('as_newsletter', 'as_newsletter_nonce'); ?>
          <input type="hidden" name="as_ts" value="<?php echo esc_attr(time()); ?>">
          <input type="text" name="as_hp_check" value="" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px">
          <input type="hidden" name="as_contexte" value="<?php echo esc_attr($term->taxonomy . ':' . $term->slug); ?>">
          <input type="email" name="as_email" required placeholder="Votre adresse e-mail" style="flex:1;border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;color:#1D1D1B">
          <button type="submit" style="border:0;background:transparent;font-family:'Nunito Sans',sans-serif;font-size:13px;font-weight:800;color:#DC5D45;cursor:pointer">S'inscrire</button>
        </form>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});

// Titre <title> du navigateur : TEC ecrase le nom du terme par son propre format
// "Evenements depuis DATE ... > Nom" (document_title_parts, priorite 10). On reprend
// la main en priorite 20 pour n'afficher que le nom du terme (cosmetique SEO, signale
// par Franck 2026-07-20).
add_filter('document_title_parts', function ($parts) {
    if (!is_tax('territoire') && !is_tax('tribe_events_cat')) {
        return $parts;
    }
    $term = get_queried_object();
    if ($term && !empty($term->name)) {
        $parts['title'] = $term->name;
    }
    return $parts;
}, 20);