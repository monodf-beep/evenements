<?php
/*
Plugin Name: Agenda Sabauda — Bouton « Ajouter à mon agenda »
Description: Sur chaque fiche événement (The Events Calendar), affiche un bloc qui
  invite le visiteur à ajouter l'événement à SON agenda (Google / Apple / Outlook)
  « pour ne pas oublier, et inviter les personnes avec qui il veut y aller ».
  L'événement transféré est COMPLET (titre marqué du préfixe Agenda Sabauda, date/
  heure, adresse complète pour l'itinéraire, description signée + lien, FR/IT via
  Polylang). Apple/Outlook desktop passent par NOTRE fichier .ics (?cs_ics=ID) pour
  un rendu identique à Google. N'invente aucune donnée : lit l'événement réel.
  Inclut aussi cs_atc_mini() (bouton compact + menu pour les cartes de liste, avec
  bandeau "emmène quelqu'un avec toi" après un premier ajout) et
  cs_atc_inapp_script() (navigateur intégré Instagram : redirige Android vers
  Chrome, affiche une instruction sur iOS — cf. plus bas, Apple interdit la
  redirection automatique depuis un WebView tiers).
Author: Cultura Sabauda
Version: 3.0

  DÉPLOIEMENT RÉEL : ce fichier vit dans WordPress comme snippet « Code Snippets »
  (id 69, « CS — Ajouter à mon agenda »), PAS comme fichier mu-plugin sur le disque.
  Ce fichier .php dans le repo Git est un MIROIR pour revue/historique — toute
  modification doit être appliquée dans WordPress (Novamira/Code Snippets), puis
  reportée ici, jamais l'inverse.
  RÉGLAGES (facultatif) : définir CS_ATC_TITLE_PREFIX (repère de titre, défaut
  « Agenda Sabauda · ») ou CS_ATC_AUTO=false (pour placer soi-même le shortcode
  [cs_add_to_calendar]).
*/

if (!defined('ABSPATH')) { exit; }

if (!defined('CS_ATC_TITLE_PREFIX')) { define('CS_ATC_TITLE_PREFIX', 'Agenda Sabauda · '); }
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
    return CS_ATC_TITLE_PREFIX . html_entity_decode(get_the_title($post_id), ENT_QUOTES, 'UTF-8');
}

/** Adresse la plus complète possible (pour que l'itinéraire fonctionne). */
function cs_atc_location($post_id) {
    $it = function_exists('pll_get_post_language') && pll_get_post_language($post_id) === 'it';
    $parts = array();
    $vid = get_post_meta($post_id, '_EventVenueID', true);
    if ($vid) {
        $vname = get_the_title($vid);
        $addr  = get_post_meta($vid, '_VenueAddress', true);
        $city  = get_post_meta($vid, '_VenueCity', true);
        $zip   = get_post_meta($vid, '_VenueZip', true);
        if ($vname) { $parts[] = $vname; }
        if ($addr)  { $parts[] = $addr; }
        $cityline = trim($zip . ' ' . $city);
        if ($cityline !== '') { $parts[] = $cityline; }
    }
    if (empty($parts)) {
        $as = get_post_meta($post_id, 'as_ville', true);
        if ($as) { $parts[] = $as; }
    }
    $terms = get_the_terms($post_id, 'territoire');
    $tname = ($terms && !is_wp_error($terms)) ? $terms[0]->name : '';
    if (preg_match('/piemont|piémont|valle|vall|aosta|aoste/i', $tname)) { $parts[] = $it ? 'Italia' : 'Italie'; }
    elseif (preg_match('/savoie|savoia|nice|nizza|marit/i', $tname)) { $parts[] = $it ? 'Francia' : 'France'; }
    $parts = array_map(function ($x) { return trim(wp_strip_all_tags((string) $x)); }, $parts);
    $parts = array_filter($parts, function ($x) { return $x !== ''; });
    return implode(', ', $parts);
}

/** Description signée Agenda Sabauda + résumé propre (sans la pub de l'encart) + lien. */
function cs_atc_description($post_id, $url) {
    $it = function_exists('pll_get_post_language') && pll_get_post_language($post_id) === 'it';
    $out = array($it ? "Evento dell'Agenda Sabauda, l'agenda culturale delle Alpi dello spazio sabaudo." : "Événement de l'Agenda Sabauda, l'agenda culturel des Alpes de l'espace sabaudo.");
    $raw = html_entity_decode(wp_strip_all_tags((string) get_the_excerpt($post_id)), ENT_QUOTES, 'UTF-8');
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
    $out[] = $it ? 'Aggiungilo al tuo calendario per non dimenticarlo, e invita chi vuoi.' : 'Ajoute-le à ton agenda pour ne pas oublier, et invite les personnes avec qui tu veux y aller.';
    $out[] = '';
    $out[] = ($it ? 'Tutte le info : ' : 'Toutes les infos : ') . $url;
    return implode("\n", $out);
}

/** Échappe une valeur texte pour un champ iCalendar (RFC 5545). */
function cs_atc_ics_escape($t) {
    return str_replace(array("\\", ";", ",", "\r\n", "\n", "\r"),
                       array("\\\\", "\\;", "\\,", "\\n", "\\n", "\\n"), (string) $t);
}

/** Bandeau navigateur intégré Instagram : redirige Android vers Chrome (fiable),
 * affiche une instruction sur iOS (Apple interdit la redirection automatique
 * depuis un WebView tiers — aucun contournement possible côté code). */
function cs_atc_inapp_script($it) {
    static $done = false;
    if ($done) { return ''; }
    $done = true;
    $msg = $it
        ? 'Per aggiungere questo evento al tuo calendario: tocca i ⋯ in alto, poi «Apri nel browser».'
        : 'Pour ajouter cet événement à ton agenda : touche les ⋯ en haut de l’écran, puis « Ouvrir dans le navigateur ».';
    ob_start(); ?>
    <script>
    (function(){
        var ua = navigator.userAgent || '';
        if (ua.indexOf('Instagram') === -1) { return; }
        if (/Android/i.test(ua)) {
            var target = location.href.replace(/^https?:\/\//, '');
            var fallback = encodeURIComponent(location.href);
            location.href = 'intent://' + target + '#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=' + fallback + ';end';
            return;
        }
        document.addEventListener('DOMContentLoaded', function () {
            var box = document.querySelector('.cs-add-to-calendar');
            if (!box || !box.parentNode) { return; }
            var banner = document.createElement('div');
            banner.style.cssText = 'margin:0 0 10px;padding:10px 14px;background:#FFF4D6;border:1px solid #E3C876;border-radius:6px;font-family:\'Nunito Sans\',sans-serif;font-size:13px;color:#5B4A16';
            banner.textContent = <?php echo json_encode($msg); ?>;
            box.parentNode.insertBefore(banner, box);
        });
    })();
    </script>
    <?php
    return ob_get_clean();
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
function cs_atc_urls($id) {
    if (!$id || get_post_type($id) !== 'tribe_events') { return null; }
    $it = function_exists('pll_get_post_language') && pll_get_post_language($id) === 'it';
    $start = cs_atc_epoch($id, 'start');
    if (!$start) { return null; }                // pas de date -> pas de bouton
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
    $ics = add_query_arg('cs_ics', $id, home_url('/'));

    return array('it' => $it, 'google' => $google, 'outlook' => $outlook, 'ics' => $ics);
}

function cs_atc_render($id) {
    $u = cs_atc_urls($id);
    if (!$u) { return ''; }
    $it = $u['it']; $google = $u['google']; $outlook = $u['outlook']; $ics = $u['ics'];

    $btn = 'display:inline-block;margin:0 8px 8px 0;padding:9px 14px;border:1px solid #1D1D1B;background:#fff;color:#1D1D1B;font-family:sans-serif;font-size:13px;font-weight:700;text-decoration:none;line-height:1.2;';
    ob_start(); ?>
    <div class="cs-add-to-calendar" style="margin:24px 0;padding:18px 20px;border:1px solid #E3DCCE;background:#FBF7F0">
        <div style="font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:18px;color:#1D1D1B;margin-bottom:4px"><?php echo $it ? 'Aggiungilo al tuo calendario' : 'Ajoute-le à ton agenda'; ?></div>
        <div style="font-family:'Nunito Sans',sans-serif;font-size:13px;color:#6F6B62;margin-bottom:12px"><?php echo $it ? 'Per non dimenticarlo, e invita le persone con cui vuoi andarci.' : 'Pour ne pas oublier, et invite les personnes avec qui tu veux y aller.'; ?></div>
        <a href="<?php echo esc_url($google); ?>" target="_blank" rel="nofollow noopener" style="<?php echo esc_attr($btn); ?>">📅 Google Agenda</a>
        <a href="<?php echo esc_url($ics); ?>" style="<?php echo esc_attr($btn); ?>">🍎 Apple / iCal</a>
        <a href="<?php echo esc_url($outlook); ?>" target="_blank" rel="nofollow noopener" style="<?php echo esc_attr($btn); ?>">📆 Outlook</a>
    </div>
    <?php
    echo cs_atc_inapp_script($it);
    return ob_get_clean();
}

/** Bouton compact + menu (Google/Apple/Outlook) pour les cartes de liste. */
function cs_atc_mini($id) {
    $u = cs_atc_urls($id);
    if (!$u) { return ''; }
    $it = $u['it'];
    $label = 'Agenda';
    $item1 = $it ? 'Google Calendar' : 'Google Agenda';
    $item2 = 'Apple / iCal';
    $item3 = 'Outlook';
    $inv_titre = $it ? 'Porta qualcuno con te' : 'Emmene quelqu\'un avec toi';
    $inv_texte = $it
        ? "L'evento e nella tua agenda. Apri Google Calendar (o Outlook) e aggiungi l'email di una persona cara come invitato: ricevera l'invito direttamente."
        : "L'evenement est dans ton agenda. Ouvre Google Agenda (ou Outlook) et ajoute l'e-mail d'un proche comme invite : il recevra l'invitation directement.";
    $inv_compris = $it ? 'Capito' : 'Compris';
    static $style_done = false;
    ob_start();
    if (!$style_done) {
        $style_done = true;
        ?>
        <style>
        .cs-card-title-link{position:static}
        .cs-card-title-link::after{content:'';position:absolute;inset:0}
        .cs-card-row{position:relative;z-index:0} .cs-card-row:has(.cs-atc-mini[open]){z-index:50} .cs-atc-mini{position:relative;z-index:2}
        .cs-atc-mini summary{list-style:none;cursor:pointer}
        .cs-atc-mini summary::-webkit-details-marker{display:none}
        .cs-atc-mini summary::marker{content:''}
        .cs-atc-mini[open] summary{background:#EFE7D6}
        .cs-atc-mini__menu{position:absolute;top:calc(100% + 4px);left:0;z-index:10;background:#fff;border:1px solid #E3DCCE;border-radius:6px;min-width:150px;padding:4px}
        .cs-atc-mini__menu a{display:block;padding:8px 10px;font-family:'Nunito Sans',sans-serif;font-size:12px;color:#1D1D1B;text-decoration:none;border-radius:4px}
        .cs-atc-mini__menu a:hover{background:#FBF7F0}
        .cs-invite-banner{position:relative;z-index:1;display:flex;align-items:center;gap:14px;background:#FBF7F0;border:1px solid #E3DCCE;border-radius:8px;padding:12px 14px;margin:2px 0 0}
        .cs-invite-banner__img{width:72px;height:72px;flex-shrink:0}
        @media (min-width:600px){ .cs-invite-banner__img{width:96px;height:96px} }
        @media (min-width:900px){ .cs-invite-banner__img{width:120px;height:120px} }
        .cs-invite-banner__body{flex:1;min-width:0}
        .cs-invite-banner__title{font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:14.5px;color:#1D1D1B;margin:0 0 4px}
        .cs-invite-banner__text{font-family:'Nunito Sans',sans-serif;font-size:12.5px;line-height:1.5;color:#4A4A48;margin:0 0 8px}
        .cs-invite-banner__close{border:0;background:transparent;padding:0;font-family:'Nunito Sans',sans-serif;font-size:12px;font-weight:700;color:#8A6D3B;text-decoration:underline;cursor:pointer}
        </style>
        <script>
        (function(){
            document.addEventListener('click', function(e){
                var open = document.querySelector('.cs-atc-mini[open]');
                if (!open) { return; }
                if (open.contains(e.target)) { return; }
                var card = open.closest('.cs-card-row');
                if (card && card.contains(e.target)) { e.preventDefault(); }
                open.removeAttribute('open');
            }, true);
            function csInsertInviteBanner(card){
                if (!card || (card.nextElementSibling && card.nextElementSibling.classList.contains('cs-invite-banner'))) { return; }
                var tpl = card.querySelector('.cs-invite-tpl');
                if (!tpl) { return; }
                var node = tpl.content.firstElementChild.cloneNode(true);
                card.insertAdjacentElement('afterend', node);
                var closeBtn = node.querySelector('.cs-invite-banner__close');
                if (closeBtn) { closeBtn.addEventListener('click', function(){ node.remove(); }); }
            }
            document.addEventListener('click', function(e){
                var link = e.target.closest('.cs-atc-mini__link');
                if (!link) { return; }
                var mini = link.closest('.cs-atc-mini');
                if (mini) { mini.removeAttribute('open'); }
                var card = link.closest('.cs-card-row');
                if (!card || sessionStorage.getItem('cs_invite_shown')) { return; }
                var eventId = mini ? mini.getAttribute('data-event-id') : '';
                sessionStorage.setItem('cs_invite_shown', '1');
                if (eventId) { sessionStorage.setItem('cs_invite_pending', eventId); }
                csInsertInviteBanner(card);
            }, true);
            document.addEventListener('DOMContentLoaded', function(){
                var csPendingId = sessionStorage.getItem('cs_invite_pending');
                if (!csPendingId) { return; }
                sessionStorage.removeItem('cs_invite_pending');
                var csPendingCard = document.querySelector('.cs-card-row[data-event-id="' + csPendingId.replace(/"/g, '') + '"]');
                if (csPendingCard) { csInsertInviteBanner(csPendingCard); }
            });
        })();
        </script>
        <?php
    }
    ?>
    <details class="cs-atc-mini" data-event-id="<?php echo esc_attr($id); ?>">
      <summary style="display:inline-flex;align-items:center;gap:3px;background:#FBF7F0;border:1px solid #C9BFAD;border-radius:20px;padding:5px 9px 5px 7px;font-family:'Nunito Sans',sans-serif;font-size:10px;font-weight:700;color:#1D1D1B" aria-label="<?php echo $it ? 'Aggiungi al calendario' : 'Ajouter à mon agenda'; ?>">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1D1D1B" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12.5 21h-6.5a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v5"></path><path d="M16 3v4"></path><path d="M8 3v4"></path><path d="M4 11h16"></path><path d="M16 19h6"></path><path d="M19 16v6"></path></svg>
        <?php echo esc_html($label); ?>
      </summary>
      <div class="cs-atc-mini__menu">
        <a class="cs-atc-mini__link" href="<?php echo esc_url($u['google']); ?>" target="_blank" rel="nofollow noopener"><?php echo esc_html($item1); ?></a>
        <a class="cs-atc-mini__link" href="<?php echo esc_url($u['ics']); ?>"><?php echo esc_html($item2); ?></a>
        <a class="cs-atc-mini__link" href="<?php echo esc_url($u['outlook']); ?>" target="_blank" rel="nofollow noopener"><?php echo esc_html($item3); ?></a>
      </div>
    </details>
    <template class="cs-invite-tpl">
      <div class="cs-invite-banner">
        <?php $cs_inv_img = get_option('cs_invite_illustration_url', ''); if ($cs_inv_img): ?><img class="cs-invite-banner__img" src="<?php echo esc_url($cs_inv_img); ?>" alt="" aria-hidden="true"><?php else: ?><div class="cs-invite-banner__img" aria-hidden="true"></div><?php endif; ?>
        <div class="cs-invite-banner__body">
          <div class="cs-invite-banner__title"><?php echo esc_html($inv_titre); ?></div>
          <div class="cs-invite-banner__text"><?php echo esc_html($inv_texte); ?></div>
          <button type="button" class="cs-invite-banner__close"><?php echo esc_html($inv_compris); ?></button>
        </div>
      </div>
    </template>
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
