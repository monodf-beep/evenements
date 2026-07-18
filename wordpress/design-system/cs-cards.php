<?php
/**
 * Composants carte événement partagés — SOURCE RÉELLE (brief §8.1 + maquettes
 * Fiche Evenement / Hub Categorie / Liste Evenements, projet "Brief design
 * agenda Sabaudo", lues le 2026-07-13). Remplace l'usage généralisé de
 * .ag-row (qui vient d'un autre fichier, ui_kits/agenda/kit.css — une mini-app
 * différente, PAS la grammaire de carte du site public).
 *
 * Grammaire de carte (brief §8.1) : image 3:2, date lisible sans clic, titre
 * 2 lignes max, lieu + ville, pilule territoire COLORÉE (une couleur par
 * territoire, brief §1.2/§3 — pas une bordure grise neutre), carte cliquable.
 * 2 variantes implémentées ici : "standard" (À la une, Hubs) et "compacte"
 * (Ce week-end, Tout l'agenda, rails).
 *
 * Chargé par chaque snippet PHP qui en a besoin (pas un snippet séparé —
 * inclus via require_once depuis les fichiers qui l'utilisent).
 */

if (!function_exists('cs_pill_class')) {
    function cs_pill_class($territory_name) {
        $map = [
            'Savoie' => 'as-pill--savoie',
            'Piémont' => 'as-pill--piemonte',
            "Vallée d'Aoste" => 'as-pill--vallee-aoste',
            'Nice' => 'as-pill--nice',
            'Comté de Nice' => 'as-pill--nice',
        ];
        foreach ($map as $needle => $class) {
            if (strpos($territory_name, $needle) !== false) {
                return $class;
            }
        }
        return '';
    }
}

if (!function_exists('cs_event_venue_line')) {
    // "Lieu · Ville" — TEC stocke le lieu en post lié (tribe_venue) ; on lit son
    // titre + sa ville (meta _VenueCity) via l'API TEC native.
    function cs_event_venue_line($event_id) {
        $venue_id = get_post_meta($event_id, '_EventVenueID', true);
        if (!$venue_id) {
            return '';
        }
        $venue_title = get_the_title($venue_id);
        $city = get_post_meta($venue_id, '_VenueCity', true);
        if ($venue_title && $city) {
            return esc_html($venue_title) . ' · ' . esc_html($city);
        }
        return esc_html($venue_title ?: $city);
    }
}

if (!function_exists('cs_event_date_short')) {
    // Formatage bref "04–05/07" ou "05/07" — même limitation connue que le
    // reste du site (date brute si le format échoue), mais on tente un format
    // correct ici puisqu'on contrôle le PHP directement (pas de dépendance à
    // JetEngine date_format).
    function cs_event_date_short($event_id) {
        $start = get_post_meta($event_id, '_EventStartDate', true);
        $end = get_post_meta($event_id, '_EventEndDate', true);
        if (!$start) {
            return '';
        }
        $start_ts = strtotime($start);
        if (!$start_ts) {
            return esc_html($start);
        }
        $end_ts = $end ? strtotime($end) : $start_ts;
        if ($end_ts && date('Y-m-d', $end_ts) !== date('Y-m-d', $start_ts)) {
            return date('d', $start_ts) . '–' . date('d/m', $end_ts);
        }
        return date('d/m', $start_ts);
    }
}

if (!function_exists('cs_event_territory_pill')) {
    function cs_event_territory_pill($event_id, $extra_class = '') {
        $terms = get_the_terms($event_id, 'territoire');
        if (!$terms || is_wp_error($terms)) {
            return '';
        }
        $name = $terms[0]->name;
        $pill = cs_pill_class($name);
        return '<span class="as-pill ' . esc_attr($pill) . ' ' . esc_attr($extra_class) . '">' . esc_html($name) . '</span>';
    }
}

if (!function_exists('cs_card_standard')) {
    // Carte "standard" — image 3:2 pleine largeur + date + titre + lieu·ville + pilule.
    function cs_card_standard($event_id) {
        $img = get_the_post_thumbnail($event_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: '<div style="width:100%;height:100%;background:#FBF7F0"></div>';
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <a href="<?php echo esc_url(get_permalink($event_id)); ?>" style="display:block;text-decoration:none;border-top:1px solid #E3DCCE;padding-top:16px;margin-bottom:18px">
          <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px;margin-bottom:8px"><?php echo $img; ?></div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:10.5px;font-weight:800;color:#1D1D1B;margin-bottom:3px"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
          <h3 style="margin:0 0 4px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:17px;line-height:1.22;color:#1D1D1B"><?php echo esc_html(get_the_title($event_id)); ?></h3>
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <?php if ($venue): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62"><?php echo $venue; ?></div><?php endif; ?>
            <?php echo cs_event_territory_pill($event_id); ?>
          </div>
        </a>
        <?php
        return ob_get_clean();
    }
}

if (!function_exists('cs_card_compact')) {
    // Carte "compacte/liste" — vignette 88px à gauche + texte à droite.
    function cs_card_compact($event_id) {
        $img = get_the_post_thumbnail($event_id, 'thumbnail', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: '<div style="width:100%;height:100%;background:#FBF7F0"></div>';
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <a href="<?php echo esc_url(get_permalink($event_id)); ?>" style="display:flex;gap:12px;text-decoration:none;border-top:1px solid #E3DCCE;padding:14px 0">
          <div style="width:88px;flex-shrink:0;aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px"><?php echo $img; ?></div>
          <div style="flex:1;min-width:0">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:800;color:#1D1D1B;margin-bottom:3px"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
            <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:15px;line-height:1.2;color:#1D1D1B;margin-bottom:4px"><?php echo esc_html(get_the_title($event_id)); ?></div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              <?php if ($venue): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62"><?php echo $venue; ?></div><?php endif; ?>
              <?php echo cs_event_territory_pill($event_id); ?>
            </div>
          </div>
        </a>
        <?php
        return ob_get_clean();
    }
}

if (!function_exists('cs_render_day_groups')) {
    /**
     * Groupement par jour — au-dessus de chaque changement de date dans une
     * liste triée par _EventStartDate ASC : en-tête de groupe (règle
     * horizontale + libellé "Aujourd'hui"/"Demain"/date longue type
     * "Vendredi 24 juillet"), suivi des cartes du jour rendues par
     * $card_renderer (cs_card_compact par défaut, ou cs_card_standard —
     * n'importe quel callable(int $event_id): string pour rester réutilisable).
     *
     * $query : un WP_Query DÉJÀ exécuté (post_type tribe_events, trié par
     * _EventStartDate ASC) — cette fonction ne filtre/trie rien elle-même,
     * l'appelant garde la main sur la requête. Consomme la boucle
     * ($query->the_post()) et fait le wp_reset_postdata() lui-même.
     */
    function cs_render_day_groups(WP_Query $query, $card_renderer = 'cs_card_compact') {
        if (!$query->have_posts()) {
            return '';
        }
        $today = current_time('Y-m-d');
        $tomorrow = date('Y-m-d', strtotime($today . ' +1 day'));
        $current_day = null;
        ob_start();
        while ($query->have_posts()) {
            $query->the_post();
            $event_id = get_the_ID();
            $start = get_post_meta($event_id, '_EventStartDate', true);
            $day = $start ? date('Y-m-d', strtotime($start)) : '';
            if ($day !== $current_day) {
                $current_day = $day;
                if ($day === $today) {
                    $label = "Aujourd'hui";
                } elseif ($day === $tomorrow) {
                    $label = 'Demain';
                } elseif ($day) {
                    $label = ucfirst(date_i18n('l j F', strtotime($day)));
                } else {
                    $label = '';
                }
                if ($label) {
                    ?>
                    <div style="display:flex;align-items:center;gap:10px;margin:22px 0 6px">
                      <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#6F6B62;white-space:nowrap"><?php echo esc_html($label); ?></div>
                      <div style="flex:1;height:1px;background:#E3DCCE"></div>
                    </div>
                    <?php
                }
            }
            echo call_user_func($card_renderer, $event_id);
        }
        wp_reset_postdata();
        return ob_get_clean();
    }
}

if (!function_exists('cs_card_rail')) {
    // Carte de rail (150px, horizontal scroll) — fiche événement.
    function cs_card_rail($event_id) {
        $img = get_the_post_thumbnail($event_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: '<div style="width:100%;height:100%;background:#FBF7F0"></div>';
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <a href="<?php echo esc_url(get_permalink($event_id)); ?>" style="flex-shrink:0;width:150px;text-decoration:none">
          <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px;margin-bottom:6px"><?php echo $img; ?></div>
          <div style="font-family:'Nunito Sans',sans-serif;font-size:9.5px;font-weight:800;color:#1D1D1B;margin-bottom:2px"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:13.5px;line-height:1.2;color:#1D1D1B;margin-bottom:3px"><?php echo esc_html(get_the_title($event_id)); ?></div>
          <?php if ($venue): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:10.5px;color:#6F6B62;margin-bottom:4px"><?php echo $venue; ?></div><?php endif; ?>
          <?php echo cs_event_territory_pill($event_id); ?>
        </a>
        <?php
        return ob_get_clean();
    }
}
