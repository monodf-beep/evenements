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
 *
 * CORRIGÉ le 04/09 (Franck, capture d'écran de /que-faire-a-ivrea/) : le bloc
 * "Ne ratez pas" (événements déjà commencés) affichait "Deja commences,
 * encore a l affiche" et "Gia in corso" — accents absents dans le SOURCE PHP
 * lui-même, pas un problème d'encodage d'affichage. Corrigé ici, poussé en
 * base (id 21) et vérifié en ligne : "Déjà commencés, encore à l'affiche".
 * Plusieurs commentaires de code voisins avaient la même faute ; corrigés par
 * cohérence (« les commentaires sont la vraie documentation », CLAUDE.md).
 */

if (!function_exists('cs_pill_class')) {
    function cs_pill_class($territory_name) {
        // 2026-07-30 : robuste FR + IT (accents variables). L'ancienne version
        // ne matchait que les noms francais ("Piemont" sans accent italien
        // "Piemonte" ne matchait jamais, idem Savoia/Valle d'Aosta/Nizza) :
        // les pilules restaient non colorees sur tout contenu en langue IT.
        $name = mb_strtolower($territory_name);
        $map = [
            'as-pill--savoie' => ['savoie', 'savoia'],
            'as-pill--piemonte' => ['piémont', 'piemont'],
            'as-pill--vallee-aoste' => ["vallée d'aoste", "vallee d'aoste", 'valle d'],
            'as-pill--nice' => ['nice', 'nizza'],
        ];
        foreach ($map as $class => $needles) {
            foreach ($needles as $needle) {
                if (mb_strpos($name, $needle) !== false) {
                    return $class;
                }
            }
        }
        return '';
    }
}

if (!function_exists('cs_venue_nom_court')) {
    // 2026-08-02 (Franck) : "pas besoin de l adresse postale sur la carte, le nom du
    // lieu suffit". Beaucoup de fiches lieu ont l adresse collee au nom entre
    // parentheses ("Le Rendez-Vous (119 Route des Pres Rollier)"), ce qui allongeait
    // la ligne pour rien sur une vignette.
    // On ne coupe PAS toutes les parentheses : sur 30 lieux concernes, une bonne
    // moitie porte une precision utile -- "Le Point Commun (espace d art
    // contemporain)", "Cinema Massimo (Sala 2)", "Esplanade du Lac (Festival
    // Musilac)". On ne retire donc que ce qui ressemble a une adresse : contenu
    // commencant par un numero, ou par un type de voie (rue, route, place, quai...).
    // La parenthese doit etre precedee d un espace, sinon on casserait "Ba(r)uhaus".
    // L adresse complete reste evidemment affichee sur la fiche evenement.
    function cs_venue_nom_court($titre) {
        $voies = 'rue|route|av|ave|avenue|bd|boulevard|chemin|quai|place|esplanade|allee|all\x{00E9}e|impasse|cours|promenade|via|piazza|corso|viale|largo|vicolo|strada|piazzale';
        $out = preg_replace('/\s*\((?:\d|(?:' . $voies . ')\b)[^)]*\)\s*$/iu', '', $titre);
        $out = trim($out);
        return $out !== '' ? $out : $titre;
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
        $venue_title = cs_venue_nom_court(get_the_title($venue_id));
        $city = get_post_meta($venue_id, '_VenueCity', true);
        // 2026-07-31 (Franck) : le Venue est PARTAGE entre les 2 langues (une seule
        // fiche lieu), _VenueCity garde donc la langue source (souvent italien) meme
        // sur la fiche FR. Seuls Torino/Turin et Aosta/Aoste ont un vrai exonyme
        // francais etabli -- le reste (Ivrea, Vercelli, Cuneo...) n'en a pas et reste
        // normalement en italien. Applique selon la langue de l'EVENEMENT.
        if ($city) {
            $lang = function_exists('pll_get_post_language') ? pll_get_post_language($event_id) : null;
            if ($lang === 'fr') {
                $city = str_ireplace(array('Torino', 'Aosta'), array('Turin', 'Aoste'), $city);
            } elseif ($lang === 'it') {
                $city = str_ireplace(array('Turin', 'Aoste'), array('Torino', 'Aosta'), $city);
            }
        }
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
        $lg = function_exists('pll_get_post_language') ? pll_get_post_language($event_id) : 'fr';
        $is_it = ($lg === 'it');
        $today = current_time('Y-m-d');
        $s_day = date('Y-m-d', $start_ts);
        $e_day = date('Y-m-d', $end_ts);
        if ($s_day < $today && $e_day >= $today) {
            return ($is_it ? 'Fino al ' : "Jusqu'au ") . date('d/m', $end_ts);
        }
        if ($e_day === $s_day) {
            return date('d/m', $start_ts);
        }
        if (date('m-Y', $start_ts) === date('m-Y', $end_ts)) {
            return date('d', $start_ts) . '–' . date('d/m', $end_ts);
        }
        return date('d/m', $start_ts) . '–' . date('d/m', $end_ts);
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

if (!function_exists('cs_event_free_badge')) {
    // 2026-08-03 : la gratuite est la seule information de prix qui a sa place sur
    // une carte. Guida Torino, la reference du secteur, n affiche jamais de tarif
    // en liste mais traite « Eventi Gratis » comme une categorie visible. On copie
    // la decision, pas le vocabulaire : pas de tarif, pas de fourchette, et rien du
    // tout quand l evenement est payant ou que l information manque. Un « payant »
    // ou un « tarif non communique » serait du bruit sur chaque carte.
    // Langue lue sur la FICHE et non sur la page, comme cs_event_date_short().
    function cs_event_free_badge($event_id, $extra_class = '') {
        if ((int) get_post_meta($event_id, 'as_gratuit', true) !== 1) {
            return '';
        }
        $lang = function_exists('pll_get_post_language') ? pll_get_post_language($event_id) : 'fr';
        $mot = ($lang === 'it') ? 'Gratis' : 'Gratuit';
        $cls = trim('cs-card-free ' . $extra_class);
        return '<span class="' . esc_attr($cls) . '">' . esc_html($mot) . '</span>';
    }
}

if (!function_exists('cs_card_standard')) {
    // Carte "standard" — image 3:2 pleine largeur + date + titre + lieu·ville + pilule.
    function cs_card_standard($event_id) {
        $img = get_the_post_thumbnail($event_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: cs_fallback_visual($event_id);
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <a href="<?php echo esc_url(get_permalink($event_id)); ?>" style="display:block;text-decoration:none;border-top:1px solid #E3DCCE;padding-top:16px;margin-bottom:18px">
          <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px;margin-bottom:8px"><?php echo $img; ?></div>
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:10.5px;font-weight:800;color:#1D1D1B"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
            <?php echo cs_event_free_badge($event_id); ?>
          </div>
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

if (!function_exists('cs_fallback_visual')) {
    function cs_fallback_visual($event_id) {
        // Visuel de repli par territoire x categorie (48 JPEG mediatheque, noms
        // fallback-{territoire-fr}-{categorie-fr}.jpg = slug attachment). Ajoute 2026-07-22.
        // Repli sur l'aplat couleur ci-dessous si le fichier n'existe pas encore.
        $cs_terr_slug = '';
        if (function_exists('cs_terr_canon_data')) {
            $cs_cd = cs_terr_canon_data();
            $cs_tt = wp_get_post_terms($event_id, 'territoire', array('fields' => 'ids'));
            if ($cs_tt && !is_wp_error($cs_tt)) {
                foreach ($cs_cd as $cs_d) {
                    if (in_array((int) $cs_d['fr_term'], $cs_tt, true) || in_array((int) $cs_d['it_term'], $cs_tt, true)) { $cs_terr_slug = $cs_d['fr_slug']; break; }
                }
            }
        }
        $cs_cat_slug = '';
        $cs_fcats = get_the_terms($event_id, 'tribe_events_cat');
        if ($cs_fcats && !is_wp_error($cs_fcats)) {
            $cs_ct = $cs_fcats[0];
            $cs_fr_id = function_exists('pll_get_term') ? pll_get_term($cs_ct->term_id, 'fr') : 0;
            $cs_frt = $cs_fr_id ? get_term($cs_fr_id) : null;
            $cs_cat_slug = ($cs_frt && !is_wp_error($cs_frt)) ? $cs_frt->slug : $cs_ct->slug;
        }
        if ($cs_terr_slug && $cs_cat_slug) {
            $cs_att = get_page_by_path('fallback-' . $cs_terr_slug . '-' . $cs_cat_slug, OBJECT, 'attachment');
            if ($cs_att) {
                $cs_src = wp_get_attachment_image_url($cs_att->ID, 'large');
                if (!$cs_src) { $cs_src = wp_get_attachment_url($cs_att->ID); }
                if ($cs_src) {
                    return '<img src="' . esc_url($cs_src) . '" alt="" loading="lazy" style="width:100%;height:100%;object-fit:cover" />';
                }
            }
        }
        $cats = get_the_terms($event_id, 'tribe_events_cat');
        $cat = ($cats && !is_wp_error($cats)) ? html_entity_decode($cats[0]->name) : '';
        $terms = get_the_terms($event_id, 'territoire');
        $tname = ($terms && !is_wp_error($terms)) ? $terms[0]->name : '';
        $col = '#6B5B4A';
        $pal = array('Savoie'=>'#3E5C74','Savoia'=>'#3E5C74','Piemont'=>'#8A3E28','Piemonte'=>'#8A3E28','Vall'=>'#3F6B47','Valle'=>'#3F6B47','Nice'=>'#B96A2E','Nizza'=>'#B96A2E');
        foreach ($pal as $k=>$v){ if (mb_stripos($tname,$k)!==false){ $col=$v; break; } }
        $mono = 'https://agendasabauda.eu/wp-content/uploads/2026/07/agenda-sabauda-monogramme-as-512.png';
        $out  = '<div style="width:100%;height:100%;position:relative;overflow:hidden;background:' . $col . ';display:flex;align-items:center;justify-content:center">';
        $out .= '<div style="position:absolute;inset:0;background:url(' . $mono . ') center/52% no-repeat;opacity:0.12;filter:brightness(0) invert(1)"></div>';
        if ($cat !== '') { $out .= '<div style="position:relative;font-family:sans-serif;font-size:clamp(11px,2.4vw,18px);font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#F7F1E8;text-align:center;padding:0 12px;line-height:1.3">' . esc_html($cat) . '</div>'; }
        $out .= '</div>';
        return $out;
    }
}
if (!function_exists('cs_card_compact')) {
    // Carte "compacte/liste" — vignette 88px à gauche + texte à droite.
    function cs_card_compact($event_id) {
        $img = get_the_post_thumbnail($event_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: cs_fallback_visual($event_id);
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <div class="cs-card-row" data-event-id="<?php echo esc_attr($event_id); ?>" style="position:relative;display:flex;gap:12px;border-top:1px solid #E3DCCE;padding:14px 0">
          <div style="width:130px;flex-shrink:0;align-self:flex-start;aspect-ratio:4/3;overflow:hidden;background:#FBF7F0;border-radius:3px"><?php echo $img; ?></div>
          <div style="flex:1;min-width:0">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
              <div style="font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:800;color:#1D1D1B"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
              <?php echo cs_event_free_badge($event_id); ?>
              <?php echo function_exists('cs_atc_mini') ? cs_atc_mini($event_id) : ''; ?>
            </div>
            <div style="margin-bottom:4px"><a href="<?php echo esc_url(get_permalink($event_id)); ?>" class="cs-card-title-link" style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:15px;line-height:1.2;color:#1D1D1B;text-decoration:none"><?php echo esc_html(get_the_title($event_id)); ?></a></div>
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
              <?php if ($venue): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:11px;color:#6F6B62"><?php echo $venue; ?></div><?php endif; ?>
              <?php echo cs_event_territory_pill($event_id); ?>
            </div>
          </div>
        </div>
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
    function cs_render_day_groups(WP_Query $query, $card_renderer = 'cs_card_compact', $ref_date = null) {
        if (!$query->have_posts()) {
            return '';
        }
        // 2026-08-02 (Franck) : la reference est la FENETRE CONSULTEE, pas la date du
        // jour. Sur "Week-end du 28 au 30 aout" on voyait des entetes MERCREDI 19,
        // LUNDI 24, MARDI 25 : ces evenements chevauchent bien le week-end, mais leur
        // date de DEBUT tombe en semaine, et comme la reference etait aujourd hui
        // (02/08) ils passaient pour des evenements "a venir" a grouper par jour.
        // Avec la fenetre pour reference, tout ce qui commence avant elle bascule dans
        // "Ne ratez pas", et seuls les jours de la fenetre ont un entete.
        // DEUX references distinctes, et c est necessaire :
        //  - $today = debut de la FENETRE consultee -> sert a decider ce qui est
        //    "déjà commencé" (donc bascule dans "Ne ratez pas") ;
        //  - $real = la VRAIE date du jour -> sert aux libelles "Aujourd hui" et
        //    "Demain", qui n ont de sens que par rapport a maintenant. Les confondre
        //    faisait afficher "Aujourd hui" en tete d un week-end de fin aout.
        $today = $ref_date ? substr($ref_date, 0, 10) : current_time('Y-m-d');
        $real = current_time('Y-m-d');
        $tomorrow = date('Y-m-d', strtotime($real . ' +1 day'));
        $cs_is_it = function_exists('pll_current_language') && pll_current_language() === 'it';
        $current_day = null;
        $cs_ongoing_html = '';
        $cs_ongoing_n = 0;
        ob_start();
        while ($query->have_posts()) {
            $query->the_post();
            $event_id = get_the_ID();
            $start = get_post_meta($event_id, '_EventStartDate', true);
            $day = $start ? date('Y-m-d', strtotime($start)) : '';
            // Événements déjà commencés (expos longue durée) : un seul en-tête
            // "En ce moment" au lieu d'un entete par date de debut passee (bug
            // "JEUDI 1 JANVIER" signale par Franck le 2026-07-21). L'ordre de la
            // requete est start ASC, donc ces evenements sont contigus en tete.
            $bucket = ($day && $day < $today) ? '__ongoing__' : $day;
            // 2026-08-02 (Franck) : les événements déjà commencés (expos longue durée,
            // festivals sur plusieurs semaines) sont MIS DE COTE et rendus a la FIN, sous
            // "Ne ratez pas". Avant, la requete etant triee par date de debut croissante,
            // ils remontaient mecaniquement en tete de page : on ouvrait "Ce week-end" et
            // les 4 premieres fiches etaient des expositions courant jusqu en octobre.
            // La page ne repondait donc pas a sa propre question. Ils gardent leur place --
            // une expo qui dure reste une vraie sortie du week-end -- mais après ce qui
            // commence vraiment dans la fenetre.
            if ($bucket === '__ongoing__') {
                ob_start();
                echo call_user_func($card_renderer, $event_id);
                $cs_ongoing_html .= ob_get_clean();
                $cs_ongoing_n++;
                continue;
            }
            if ($bucket !== $current_day) {
                $current_day = $bucket;
                if ($bucket === '__ongoing__') {
                    $label = $cs_is_it ? 'In questo momento' : 'En ce moment';
                } elseif ($day === $real) {
                    $label = $cs_is_it ? 'Oggi' : "Aujourd'hui";
                } elseif ($day === $tomorrow) {
                    $label = $cs_is_it ? 'Domani' : 'Demain';
                } elseif ($day) {
                    $label = ucfirst(date_i18n('l j F', strtotime($day)));
                } else {
                    $label = '';
                }
                if ($label) {
                    ?>
                    <div class="cs-day-head" style="display:flex;align-items:center;gap:10px;margin:22px 0 6px">
                      <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#6F6B62;white-space:nowrap"><?php echo esc_html($label); ?></div>
                      <div style="flex:1;height:1px;background:#E3DCCE"></div>
                    </div>
                    <?php
                }
            }
            echo call_user_func($card_renderer, $event_id);
        }
        // Bloc "Ne ratez pas" : ce qui court déjà, après ce qui commence.
        if ($cs_ongoing_n > 0) {
            $cs_lbl = $cs_is_it ? 'Da non perdere' : 'Ne ratez pas';
            $cs_sub = $cs_is_it
                ? 'Già in corso, ancora per qualche tempo'
                : 'Déjà commencés, encore à l\'affiche';
            ?>
            <div class="cs-day-head" style="display:flex;align-items:center;gap:10px;margin:34px 0 2px">
              <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-size:13px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#1D1D1B;white-space:nowrap"><?php echo esc_html($cs_lbl); ?></div>
              <div style="flex:1;height:1px;background:#E3DCCE"></div>
            </div>
            <div style="font-family:'Nunito Sans',sans-serif;font-size:12px;color:#6F6B62;margin:0 0 10px"><?php echo esc_html($cs_sub); ?></div>
            <?php
            echo $cs_ongoing_html;
        }
        wp_reset_postdata();
        return ob_get_clean();
    }
}

if (!function_exists('cs_card_rail')) {
    // Carte de rail (150px, horizontal scroll) — fiche événement.
    function cs_card_rail($event_id) {
        $img = get_the_post_thumbnail($event_id, 'medium', ['style' => 'width:100%;height:100%;object-fit:cover']);
        $img = $img ?: cs_fallback_visual($event_id);
        $venue = cs_event_venue_line($event_id);
        ob_start();
        ?>
        <a href="<?php echo esc_url(get_permalink($event_id)); ?>" style="flex-shrink:0;width:150px;text-decoration:none">
          <div style="aspect-ratio:3/2;overflow:hidden;background:#FBF7F0;border-radius:3px;margin-bottom:6px"><?php echo $img; ?></div>
          <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-bottom:2px">
            <div style="font-family:'Nunito Sans',sans-serif;font-size:9.5px;font-weight:800;color:#1D1D1B"><?php echo esc_html(cs_event_date_short($event_id)); ?></div>
            <?php echo cs_event_free_badge($event_id); ?>
          </div>
          <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:13.5px;line-height:1.2;color:#1D1D1B;margin-bottom:3px"><?php echo esc_html(get_the_title($event_id)); ?></div>
          <?php if ($venue): ?><div style="font-family:'Nunito Sans',sans-serif;font-size:10.5px;color:#6F6B62;margin-bottom:4px"><?php echo $venue; ?></div><?php endif; ?>
          <?php echo cs_event_territory_pill($event_id); ?>
        </a>
        <?php
        return ob_get_clean();
    }
}
