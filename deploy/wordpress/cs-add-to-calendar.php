<?php
/*
Plugin Name: Agenda Sabauda — Bouton « Ajouter à mon agenda »
Description: Ajoute un shortcode [cs_add_to_calendar] qui affiche, sur une fiche
  événement (The Events Calendar), des boutons permettant au VISITEUR d'ajouter
  l'événement à son propre agenda : Google Agenda, Apple (fichier .ics) et Outlook.
  Ne fabrique aucune donnée : lit la date/lieu réels de l'événement. À déposer dans
  le gabarit Elementor de la fiche événement (widget « Shortcode »).
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION :
   A) Code Snippets : coller SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-add-to-calendar.php.
  UTILISATION : placer le shortcode [cs_add_to_calendar] dans le gabarit de la
  fiche événement (Elementor → widget « Shortcode »), là où on veut le bouton.
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Époque UNIX (UTC) d'un bord de l'événement. Préfère la méta _...UTC de TEC ;
 * sinon convertit la date locale via le fuseau du site. 0 si introuvable.
 */
function cs_atc_epoch($post_id, $which) {
    $utc_key   = $which === 'start' ? '_EventStartDateUTC' : '_EventEndDateUTC';
    $local_key = $which === 'start' ? '_EventStartDate'    : '_EventEndDate';
    $utc = get_post_meta($post_id, $utc_key, true);
    if ($utc) { return strtotime($utc . ' UTC'); }
    $local = get_post_meta($post_id, $local_key, true);
    if ($local) {
        try { $d = new DateTime($local, wp_timezone()); return $d->getTimestamp(); }
        catch (Exception $e) { return 0; }
    }
    return 0;
}

/** Lieu lisible : nom du lieu TEC + ville, ou repli sur la méta as_ville. */
function cs_atc_location($post_id) {
    $loc = '';
    if (function_exists('tribe_get_venue')) {
        $venue = tribe_get_venue($post_id);
        $city  = function_exists('tribe_get_city') ? tribe_get_city($post_id) : '';
        $loc = trim($venue . (($venue && $city) ? ', ' : '') . $city);
    }
    if ($loc === '') { $loc = (string) get_post_meta($post_id, 'as_ville', true); }
    return $loc;
}

add_shortcode('cs_add_to_calendar', function () {
    $id = get_the_ID();
    if (!$id || get_post_type($id) !== 'tribe_events') { return ''; }

    $start = cs_atc_epoch($id, 'start');
    if (!$start) { return ''; }                 // pas de date → pas de bouton
    $end = cs_atc_epoch($id, 'end');
    if (!$end || $end < $start) { $end = $start + 3600; }

    $allday = get_post_meta($id, '_EventAllDay', true) === 'yes';
    $title  = get_the_title($id);
    $url    = get_permalink($id);
    $loc    = cs_atc_location($id);
    $details = 'Agenda Sabauda — ' . $url;

    // --- Google Agenda ---
    if ($allday) {
        $g_start = get_post_meta($id, '_EventStartDate', true);
        $g_end   = get_post_meta($id, '_EventEndDate', true);
        $gs = $g_start ? date('Ymd', strtotime($g_start)) : gmdate('Ymd', $start);
        // Google : la date de fin est EXCLUSIVE pour un événement « journée entière ».
        $ge = date('Ymd', ($g_end ? strtotime($g_end) : $end) + 86400);
        $dates = $gs . '/' . $ge;
    } else {
        $dates = gmdate('Ymd\THis\Z', $start) . '/' . gmdate('Ymd\THis\Z', $end);
    }
    $google = 'https://calendar.google.com/calendar/render?action=TEMPLATE'
        . '&text='     . rawurlencode($title)
        . '&dates='    . $dates
        . '&details='  . rawurlencode($details)
        . '&location=' . rawurlencode($loc);

    // --- Outlook (web) ---
    $outlook = 'https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent'
        . '&subject=' . rawurlencode($title)
        . '&startdt=' . rawurlencode(gmdate('Y-m-d\TH:i:s\Z', $start))
        . '&enddt='   . rawurlencode(gmdate('Y-m-d\TH:i:s\Z', $end))
        . '&body='    . rawurlencode($details)
        . '&location='. rawurlencode($loc);

    // --- Apple / .ics : réutilise le flux natif de The Events Calendar ---
    $ics = function_exists('tribe_get_single_ical_link') ? tribe_get_single_ical_link() : '';

    // --- Rendu (styles inline pour ne dépendre d'aucun thème) ---
    $btn = 'display:inline-block;margin:.25rem .4rem .25rem 0;padding:.5rem .9rem;'
         . 'border:1px solid #c9c2b4;border-radius:.5rem;background:#faf8f3;color:#3a2f1e;'
         . 'font-weight:600;text-decoration:none;line-height:1.2;';
    ob_start(); ?>
    <div class="cs-add-to-calendar" style="margin:1rem 0;">
        <div style="font-weight:700;margin-bottom:.4rem;">Ajouter à mon agenda</div>
        <a href="<?php echo esc_url($google); ?>" target="_blank" rel="nofollow noopener"
           style="<?php echo esc_attr($btn); ?>">📅 Google Agenda</a>
        <?php if ($ics) : ?>
        <a href="<?php echo esc_url($ics); ?>"
           style="<?php echo esc_attr($btn); ?>">🍎 Apple / iCal</a>
        <?php endif; ?>
        <a href="<?php echo esc_url($outlook); ?>" target="_blank" rel="nofollow noopener"
           style="<?php echo esc_attr($btn); ?>">📆 Outlook</a>
    </div>
    <?php
    return ob_get_clean();
});
