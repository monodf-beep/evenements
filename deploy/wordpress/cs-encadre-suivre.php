<?php
/**
 * Plugin Name: CS - Encadré « nous suivre sur Google » en bas des articles
 * Description: Invite le lecteur d'un article à suivre le site sur Google Discover et à l'ajouter à ses sources préférées de Google.
 *
 * POURQUOI (24/09/2026). Vu par Franck sur guidatorino.com, en bas de chaque article :
 * « seguiteci su Google Discover e aggiungete Guidatorino.com alle Fonti preferite di
 * Google ». Deux liens, lus dans leur code : la page Google du site
 * (profile.google.com/cp/…, où l'on « suit » un site pour Discover) et la page des
 * sources préférées (google.com/preferences/source?q=<domaine>). La page Google
 * d'agendasabauda.eu existe déjà (mesuré le 24/09 : 200, titre « agendasabauda.eu |
 * Google »).
 *
 * OÙ, ET PAS AILLEURS. Sous les ARTICLES et guides (type 'post') seulement, jamais sous une
 * fiche d'événement : le lecteur d'un guide est celui qui peut revenir ; sur une fiche, ce
 * serait une ligne de plus que personne ne lit. Pas dans les flux RSS non plus (un appel à
 * s'abonner à l'intérieur d'un abonnement n'a pas de sens).
 *
 * LE TEXTE N'EST PAS ICI. Il vit dans les options `cs_encadre_suivre_texte_fr` et
 * `cs_encadre_suivre_texte_it` — un texte éditorial se relit et se corrige sans toucher au
 * code, et passe par la doctrine de rédaction avant d'être posé. Deux marqueurs y placent
 * les liens : {discover:libellé} et {sources:libellé}. Option vide = rien d'affiché
 * dans cette langue.
 *
 * ACTIVATION. Inerte tant que l'option `cs_encadre_suivre_actif` ne vaut pas 1. Aperçu sur
 * un article sans rien activer : ?cs_encadre_suivre=1. Retour arrière : option à 0.
 */
if (!defined('ABSPATH')) { exit; }

if (!defined('CS_SUIVRE_DOMAINE')) { define('CS_SUIVRE_DOMAINE', 'agendasabauda.eu'); }

if (!function_exists('cs_encadre_suivre_liens')) {
function cs_encadre_suivre_liens() {
    $d = CS_SUIVRE_DOMAINE;
    // Identifiant de la page Google du site : message protobuf {2: {1: <domaine>}} en
    // base64 — le même schéma que celui de guidatorino.com (EhEKD2d1aWRhdG9yaW5vLmNvbQ==
    // = \x12\x11\x0a\x0f + « guidatorino.com »). Pour notre domaine :
    // EhIKEGFnZW5kYXNhYmF1ZGEuZXU=, vérifié en ligne le 24/09.
    $pb = "\x12" . chr(strlen($d) + 2) . "\x0a" . chr(strlen($d)) . $d;
    return array(
        'discover' => 'https://profile.google.com/cp/' . base64_encode($pb),
        'sources'  => 'https://google.com/preferences/source?q=' . rawurlencode($d),
    );
}
}

if (!function_exists('cs_encadre_suivre_html')) {
function cs_encadre_suivre_html($lang) {
    $texte = trim((string) get_option('cs_encadre_suivre_texte_' . ($lang === 'it' ? 'it' : 'fr'), ''));
    if ($texte === '') { return ''; }
    $liens = cs_encadre_suivre_liens();
    $html = preg_replace_callback('/\{(discover|sources):([^}]+)\}/u', function ($m) use ($liens) {
        return '<a href="' . esc_url($liens[$m[1]]) . '" target="_blank" rel="noopener nofollow">'
             . esc_html($m[2]) . '</a>';
    }, esc_html($texte));
    // esc_html a neutralisé tout balisage du texte ; les marqueurs, eux, ne contiennent
    // ni < ni & et ont survécu tels quels — seuls NOS liens sont du HTML.
    return '<aside class="cs-suivre" lang="' . esc_attr($lang) . '"><p>' . $html . '</p></aside>';
}
}

add_filter('the_content', function ($content) {
    if (is_feed() || !is_singular('post') || !in_the_loop() || !is_main_query()) { return $content; }
    $actif  = (string) get_option('cs_encadre_suivre_actif', '0') === '1';
    $apercu = isset($_GET['cs_encadre_suivre']) && $_GET['cs_encadre_suivre'] === '1';
    if (!$actif && !$apercu) { return $content; }
    $lang = function_exists('pll_get_post_language') ? (pll_get_post_language(get_the_ID()) ?: 'fr') : 'fr';
    $bloc = cs_encadre_suivre_html($lang);
    return $bloc === '' ? $content : $content . $bloc;
}, 30);

add_action('wp_head', function () {
    if (!is_singular('post')) { return; }
    $actif  = (string) get_option('cs_encadre_suivre_actif', '0') === '1';
    if (!$actif && !(isset($_GET['cs_encadre_suivre']) && $_GET['cs_encadre_suivre'] === '1')) { return; }
    echo '<style id="cs-suivre">'
        . '.cs-suivre{margin:40px 0 8px;padding:18px 22px;border-left:3px solid #DC5D45;background:rgba(201,191,173,.18);}'
        . '.cs-suivre p{margin:0;font-size:.95em;line-height:1.55;}'
        . '.cs-suivre a{font-weight:700;text-decoration:underline;text-underline-offset:3px;}'
        . '</style>';
});
