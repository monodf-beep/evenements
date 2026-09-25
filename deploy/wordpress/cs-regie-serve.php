<?php
/*
Plugin Name: Agenda Sabauda — Régie (override backoffice par bloc)
Description: Modèle « override » : chaque emplacement pub est AdSense par défaut ; si
  une campagne est active dans le backoffice pour ce bloc, sa créative REMPLACE l'AdSense
  le temps de la campagne. Ce mu-plugin expose la primitive — c'est le gabarit / Ad Inserter
  qui décide OÙ (voir « Câblage » ci-dessous). Consentement marketing (Complianz) et
  allowlist de domaine appliqués à la pub backoffice ; clic compté via /go/<id>.

  CÂBLAGE (build WordPress) — envelopper le code AdSense de CHAQUE bloc :
    [cs_slot bloc="1"]<!-- code AdSense du bloc 1 --></...>[/cs_slot]
  → si le backoffice a une campagne active pour le bloc 1, on affiche la créative ;
    sinon on affiche l'AdSense enveloppé. Rien d'autre à changer côté annonceur.

  Historique : récupéré de la prod le 2026-07-18 (sticky bas manuel-only, jamais commité
  avant), puis réécrit le 2026-07-20 en override par bloc (décision Franck : « toutes les
  pubs sont AdSense ; un annonceur créé dans le backoffice prend la place de l'AdSense »).
  L'ancien rendu sticky bas figé est retiré : le sticky bas est désormais un bloc AdSense
  comme les autres, simplement enveloppable par [cs_slot].

  Sécurité : créatives autorisées uniquement depuis agendasabauda.eu (médiathèque du site) ;
  lien uniquement vers backoffice.agendasabauda.eu (le /go/<id> de comptage) ; https exigé.
  Rollback : supprimer ce fichier (les [cs_slot] retombent alors sur l'AdSense enveloppé).
Author: Cultura Sabauda
Version: 0.2
*/
if (!defined('ABSPATH')) { exit; }
if (!defined('CS_REGIE_BACKOFFICE')) {
    define('CS_REGIE_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
}
// Anti supply-chain : on n'injecte QUE des créatives d'un domaine qu'on contrôle.
// Décision 2026-07-20 : les créatives annonceurs sont hébergées sur agendasabauda.eu.
if (!defined('CS_REGIE_IMG_HOST'))  { define('CS_REGIE_IMG_HOST',  'agendasabauda.eu'); }
if (!defined('CS_REGIE_LINK_HOST')) { define('CS_REGIE_LINK_HOST', 'backoffice.agendasabauda.eu'); }

/** URL sûre ? https + hôte égal (ou sous-domaine) du domaine autorisé. */
function cs_regie_host_ok($url, $allowed) {
    if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') { return false; }
    $host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
    $allowed = strtolower($allowed);
    return ($host === $allowed) || (substr($host, -strlen('.' . $allowed)) === '.' . $allowed);
}

/** Pubs actives du backoffice (par bloc), avec cache 5 min (transient). */
function cs_regie_serve_fetch() {
    $cached = get_transient('cs_regie_ads');
    if ($cached !== false) { return $cached; }
    $ads  = array();
    $resp = wp_remote_get(rtrim(CS_REGIE_BACKOFFICE, '/') . '/api/active-ads', array('timeout' => 4));
    if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
        $body = json_decode(wp_remote_retrieve_body($resp), true);
        if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
    }
    set_transient('cs_regie_ads', $ads, 5 * MINUTE_IN_SECONDS);
    return $ads;
}

/** Purge du cache à la demande : /?cs_regie_refresh=1 (après une modif backoffice). */
add_action('init', function () {
    if (!empty($_GET['cs_regie_refresh'])) { delete_transient('cs_regie_ads'); }
});

/**
 * HTML de la créative backoffice pour un bloc, si une campagne est active ET sûre,
 * sinon '' (le caller retombe alors sur l'AdSense). La pub est gatée « marketing »
 * (classe cs-consent-mkt posée plus bas selon le consentement Complianz).
 */
function cs_regie_manual_ad($bloc) {
    $ads  = cs_regie_serve_fetch();
    $bloc = (string) $bloc;
    if (empty($ads[$bloc]) || empty($ads[$bloc]['image']) || empty($ads[$bloc]['link'])) { return ''; }
    $img  = $ads[$bloc]['image'];
    $link = $ads[$bloc]['link'];
    if (!cs_regie_host_ok($img, CS_REGIE_IMG_HOST) || !cs_regie_host_ok($link, CS_REGIE_LINK_HOST)) { return ''; }
    $img  = esc_url($img);
    $link = esc_url($link);
    return '<div class="cs-ad cs-consent-gate" data-cs-bloc="' . esc_attr($bloc) . '" role="complementary" aria-label="Publicité">'
         . '<div class="cs-ad-lbl">Publicité</div>'
         . '<a href="' . $link . '" target="_blank" rel="noopener sponsored">'
         . '<img src="' . $img . '" alt="Publicité" loading="lazy"></a>'
         . '</div>';
}

/**
 * Shortcode d'override d'un bloc. Le code AdSense se met À L'INTÉRIEUR :
 *   [cs_slot bloc="1"]<!-- AdSense bloc 1 -->[/cs_slot]
 * → créative backoffice si campagne active pour ce bloc, sinon l'AdSense enveloppé.
 */
add_shortcode('cs_slot', function ($atts, $content = '') {
    $atts   = shortcode_atts(array('bloc' => ''), $atts);
    $manual = cs_regie_manual_ad($atts['bloc']);
    return $manual !== '' ? $manual : do_shortcode((string) $content);
});

/** Accès direct depuis un gabarit PHP : echo cs_regie_slot('3', $adsense_html); */
function cs_regie_slot($bloc, $adsense_html = '') {
    $manual = cs_regie_manual_ad($bloc);
    return $manual !== '' ? $manual : $adsense_html;
}

/**
 * Styles + gating consentement (une seule fois). La créative backoffice n'est visible
 * qu'avec le consentement marketing Complianz (cmplz_marketing=allow), comme l'AdSense.
 */
add_action('wp_footer', function () {
    if (is_admin()) { return; }
    echo '<style>'
       . '.cs-ad{max-width:100%;text-align:center;margin:0 auto}'
       . '.cs-ad-lbl{font:800 8px/1 sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#6F6B62;margin-bottom:3px}'
       . '.cs-ad img{max-width:100%;height:auto;vertical-align:middle}'
       . '.cs-consent-gate{display:none}'
       . '.cs-consent-mkt .cs-consent-gate{display:block}'
       . '</style>'
       . '<script>(function(){var r=document.documentElement;'
       . 'function ok(){return /(?:^|;)\s*cmplz_marketing=allow(?:;|$)/.test(document.cookie);}'
       . 'function ap(){if(ok())r.classList.add(\'cs-consent-mkt\');else r.classList.remove(\'cs-consent-mkt\');}'
       . 'ap();document.addEventListener(\'cmplz_status_change\',ap);})();</script>';
}, 30);
