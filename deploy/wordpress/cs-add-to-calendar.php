<?php
/*
Plugin Name: Agenda Sabauda — Bouton « Ajouter à mon agenda »
Description: Sur chaque fiche événement (The Events Calendar), affiche un bloc qui
  invite le visiteur à ajouter l'événement à SON agenda (Google / Apple / Outlook)
  « pour ne pas oublier, et inviter les personnes avec qui il veut y aller ».
  L'événement transféré est COMPLET (titre marqué ⛰️ pour être reconnu Agenda Sabauda
  dès la vue calendrier, date/heure, adresse complète pour l'itinéraire, description
  signée + lien). Apple/Outlook desktop passent par NOTRE fichier .ics (?cs_ics=ID)
  pour un rendu identique à Google. N'invente aucune donnée : lit l'événement réel.
Author: Cultura Sabauda
Version: 2.0

  INSTALLATION :
   A) Code Snippets : coller SANS la ligne « <?php », « Run everywhere ».
   B) mu-plugin : déposer dans wp-content/mu-plugins/cs-add-to-calendar.php.
  RÉGLAGES (facultatif) : définir CS_ATC_TITLE_PREFIX (repère de titre, défaut « ⛰️ »)
  ou CS_ATC_AUTO=false (pour placer soi-même le shortcode [cs_add_to_calendar]).
*/

if (!defined('ABSPATH')) { exit; }

if (!defined('CS_ATC_TITLE_PREFIX')) { define('CS_ATC_TITLE_PREFIX', '⛰️ '); }
// Auto-placement via wp_footer DÉSACTIVÉ par défaut : sur un site Elementor, on
// place le shortcode [cs_add_to_calendar] à la main dans le gabarit (emplacement
// maîtrisé). Mettre à true pour réactiver l'injection automatique en bas de page.
if (!defined('CS_ATC_AUTO'))         { define('CS_ATC_AUTO', false); }

/** Époque UNIX (UTC) d'un bord de l'événement (méta _...UTC de TEC, sinon date locale). */
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

/** Titre marqué du repère Agenda Sabauda (visible en vue calendrier). */
function cs_atc_title($post_id) {
    return CS_ATC_TITLE_PREFIX . get_the_title($post_id);
}

/** Adresse la plus complète possible (pour que l'itinéraire fonctionne). */
function cs_atc_location($post_id) {
    if (function_exists('tribe_get_full_address')) {
        $full = trim((string) tribe_get_full_address($post_id));
        if ($full !== '') { return $full; }
    }
    if (function_exists('tribe_get_venue')) {
        $venue = tribe_get_venue($post_id);
        $city  = function_exists('tribe_get_city') ? tribe_get_city($post_id) : '';
        $loc = trim($venue . (($venue && $city) ? ', ' : '') . $city);
        if ($loc !== '') { return $loc; }
    }
    return (string) get_post_meta($post_id, 'as_ville', true);
}

/** Description signée Agenda Sabauda + résumé propre (sans la pub de l'encart) + lien. */
function cs_atc_description($post_id, $url) {
    $out = array("Événement de l'Agenda Sabauda — l'agenda culturel des Alpes de l'espace sabaudo.");
    $raw = wp_strip_all_tags((string) get_the_excerpt($post_id));
    if ($raw === '') { $raw = wp_strip_all_tags((string) get_post_field('post_content', $post_id)); }
    $raw = trim(preg_replace('/\s+/', ' ', $raw));
    // On n'insère JAMAIS le texte de l'encart publicitaire.
    $polluted = (stripos($raw, 'Annoncer sur') !== false)
             || (stripos($raw, 'Publicité') !== false && stripos($raw, 'Agenda Sabauda') !== false);
    if ($raw !== '' && !$polluted) {
        if (function_exists('mb_strlen') && mb_strlen($raw) > 300) { $raw = mb_substr($raw, 0, 297) . '…'; }
        $out[] = '';
        $out[] = $raw;
    }
    $out[] = '';
    $out[] = 'Ajoute-le à ton agenda pour ne pas oublier, et invite les personnes avec qui tu veux y aller.';
    $out[] = '';
    $out[] = 'Toutes les infos : ' . $url;
    return implode("\n", $out);
}

/** Échappe une valeur texte pour un champ iCalendar (RFC 5545). */
function cs_atc_ics_escape($t) {
    return str_replace(array("\\", ";", ",", "\r\n", "\n", "\r"),
                       array("\\\\", "\\;", "\\,", "\\n", "\\n", "\\n"), (string) $t);
}

// ---- Notre fichier .ics : https://agendasabauda.eu/?cs_ics=ID ----
add_action('init', function () {
    if (empty($_GET['cs_ics'])) { return; }
    $id = (int) $_GET['cs_ics'];
    if (!$id || get_post_type($id) !== 'tribe_events') { status_header(404); exit; }

    $start = cs_atc_epoch($id, 'start');
    if (!$start) { status_header(404); exit; }
    $end = cs_atc_epoch($id, 'end');
    if (!$end || $end < $start) { $end = $start + 3600; }
    $allday = get_post_meta($id, '_EventAllDay', true) === 'yes';
    $url = get_permalink($id);

    $lines = array('BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Agenda Sabauda//FR', 'CALSCALE:GREGORIAN',
                   'METHOD:PUBLISH', 'BEGIN:VEVENT',
                   'UID:evt-' . $id . '@agendasabauda.eu',
                   'DTSTAMP:' . gmdate('Ymd\THis\Z'));
    if ($allday) {
        $ls = get_post_meta($id, '_EventStartDate', true);
        $le = get_post_meta($id, '_EventEndDate', true);
        $ds = $ls ? date('Ymd', strtotime($ls)) : gmdate('Ymd', $start);
        $de = date('Ymd', ($le ? strtotime($le) : $end) + 86400); // fin exclusive
        $lines[] = 'DTSTART;VALUE=DATE:' . $ds;
        $lines[] = 'DTEND;VALUE=DATE:' . $de;
    } else {
        $lines[] = 'DTSTART:' . gmdate('Ymd\THis\Z', $start);
        $lines[] = 'DTEND:'   . gmdate('Ymd\THis\Z', $end);
    }
    $lines[] = 'SUMMARY:'     . cs_atc_ics_escape(cs_atc_title($id));
    $lines[] = 'DESCRIPTION:' . cs_atc_ics_escape(cs_atc_description($id, $url));
    $loc = cs_atc_location($id);
    if ($loc !== '') { $lines[] = 'LOCATION:' . cs_atc_ics_escape($loc); }
    $lines[] = 'URL:' . cs_atc_ics_escape($url);
    $lines[] = 'ORGANIZER;CN=Agenda Sabauda:MAILTO:contact@agendasabauda.eu';
    $lines[] = 'END:VEVENT';
    $lines[] = 'END:VCALENDAR';

    nocache_headers();
    header('Content-Type: text/calendar; charset=utf-8');
    header('Content-Disposition: attachment; filename="agenda-sabauda-' . $id . '.ics"');
    echo implode("\r\n", $lines) . "\r\n";
    exit;
}, 0);

// ---- Le bloc affiché sur la fiche (rendu réutilisable) ----
function cs_atc_render($id) {
    if (!$id || get_post_type($id) !== 'tribe_events') { return ''; }
    $start = cs_atc_epoch($id, 'start');
    if (!$start) { return ''; }                 // pas de date → pas de bouton
    $end = cs_atc_epoch($id, 'end');
    if (!$end || $end < $start) { $end = $start + 3600; }
    $allday = get_post_meta($id, '_EventAllDay', true) === 'yes';

    $title   = cs_atc_title($id);
    $url     = get_permalink($id);
    $loc     = cs_atc_location($id);
    $details = cs_atc_description($id, $url);

    if ($allday) {
        $ls = get_post_meta($id, '_EventStartDate', true);
        $le = get_post_meta($id, '_EventEndDate', true);
        $gs = $ls ? date('Ymd', strtotime($ls)) : gmdate('Ymd', $start);
        $ge = date('Ymd', ($le ? strtotime($le) : $end) + 86400);
        $dates = $gs . '/' . $ge;
    } else {
        $dates = gmdate('Ymd\THis\Z', $start) . '/' . gmdate('Ymd\THis\Z', $end);
    }
    $google = 'https://calendar.google.com/calendar/render?action=TEMPLATE'
        . '&text='     . rawurlencode($title)
        . '&dates='    . $dates
        . '&details='  . rawurlencode($details)
        . '&location=' . rawurlencode($loc);
    $outlook = 'https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent'
        . '&subject=' . rawurlencode($title)
        . '&startdt=' . rawurlencode(gmdate('Y-m-d\TH:i:s\Z', $start))
        . '&enddt='   . rawurlencode(gmdate('Y-m-d\TH:i:s\Z', $end))
        . '&body='    . rawurlencode($details)
        . '&location='. rawurlencode($loc);
    $ics = add_query_arg('cs_ics', $id, home_url('/'));   // notre .ics (Apple/Outlook desktop)

    $btn = 'display:inline-block;margin:.25rem .4rem .25rem 0;padding:.55rem .95rem;'
         . 'border:1px solid #c9c2b4;border-radius:.5rem;background:#faf8f3;color:#3a2f1e;'
         . 'font-weight:600;text-decoration:none;line-height:1.2;';
    ob_start(); ?>
    <div class="cs-add-to-calendar" style="margin:1.25rem 0;padding:1rem 1.1rem;border:1px solid #e7e1d4;border-radius:.75rem;background:#fdfcf9;">
        <div style="font-weight:800;font-size:1.05rem;margin-bottom:.15rem;">Ajoute-le à ton agenda</div>
        <div style="margin-bottom:.7rem;color:#5b5240;">Pour ne pas oublier — et invite les personnes avec qui tu veux y aller.</div>
        <a href="<?php echo esc_url($google); ?>" target="_blank" rel="nofollow noopener" style="<?php echo esc_attr($btn); ?>">📅 Google Agenda</a>
        <a href="<?php echo esc_url($ics); ?>" style="<?php echo esc_attr($btn); ?>">🍎 Apple / iCal</a>
        <a href="<?php echo esc_url($outlook); ?>" target="_blank" rel="nofollow noopener" style="<?php echo esc_attr($btn); ?>">📆 Outlook</a>
    </div>
    <?php
    return ob_get_clean();
}

// Shortcode : résout l'ID depuis la boucle, sinon depuis l'objet interrogé.
add_shortcode('cs_add_to_calendar', function () {
    $id = get_the_ID();
    if (!$id || get_post_type($id) !== 'tribe_events') { $id = get_queried_object_id(); }
    return cs_atc_render($id);
});

// ---- Affichage automatique, INDÉPENDANT du constructeur ----
// The Events Calendar/Elementor/GeneratePress ne passent pas toujours par
// the_content : on ne peut donc pas s'y fier. wp_footer, lui, s'exécute TOUJOURS.
// On y dépose l'encadré (fabriqué côté serveur) puis un petit script le place au
// bon endroit dans la fiche. Aucune dépendance à un thème ou un builder.
add_action('wp_footer', function () {
    if (!CS_ATC_AUTO || !is_singular('tribe_events')) { return; }
    $box = cs_atc_render(get_queried_object_id());
    if ($box === '') { return; }
    ?>
    <template id="cs-atc-tpl"><?php echo $box; ?></template>
    <script>
    (function () {
        if (document.querySelector('.cs-add-to-calendar')) { return; }
        var tpl = document.getElementById('cs-atc-tpl');
        if (!tpl || !tpl.content || !tpl.content.firstElementChild) { return; }
        var node = tpl.content.firstElementChild.cloneNode(true);
        var sel = [
            '.elementor-widget-theme-post-content .elementor-widget-container',
            '.tribe-events-single', '.tribe_events .entry-content',
            'article .entry-content', '.entry-content', '.inside-article',
            'main', '#primary', '#content'
        ];
        var host = null;
        for (var i = 0; i < sel.length; i++) {
            var e = document.querySelector(sel[i]);
            if (e) { host = e; break; }
        }
        (host || document.body).appendChild(node);
    })();
    </script>
    <?php
}, 99);
