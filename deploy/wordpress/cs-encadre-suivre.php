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
 * OÙ. Sous les ARTICLES et guides (type 'post') ET sous les FICHES d'événement. La v1 du
 * 24/09 écartait les fiches (« une ligne de plus que personne ne lit ») : les requêtes
 * Search Console de la page d'accueil, relevées le 25/09, disent l'inverse — le trafic
 * arrive par des noms d'événements (Vicoforte, Terra Madre, Collontrek…), donc par les
 * fiches. Pas dans les flux RSS (un appel à s'abonner dans un abonnement n'a pas de sens).
 *
 * DEUX CHEMINS, parce que le site en a deux :
 *  - articles : filtre the_content. SANS `in_the_loop()` — le thème rend le contenu hors de
 *    la boucle principale, la condition était donc toujours fausse (même défaut que la v1.0
 *    de cs-moment-fort-maillage.php, constaté le 24/09). La v1 de cet encadré n'aurait donc
 *    jamais rien affiché, même activée ;
 *  - fiches : le gabarit (Code Snippets n° 56) lit get_the_content(), qui ne passe PAS par
 *    the_content. On se branche sur son point d'accroche `cs_fiche_apres_corps`.
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
             // Le libellé a DÉJÀ été échappé avec le reste du texte (esc_html plus bas) :
             // l'échapper de nouveau affichait « l&#039;ajouter » pour « l'ajouter ».
             . esc_html(html_entity_decode($m[2], ENT_QUOTES, 'UTF-8')) . '</a>';
    }, esc_html($texte));
    // esc_html a neutralisé tout balisage du texte ; les marqueurs, eux, ne contiennent
    // ni < ni & et ont survécu tels quels — seuls NOS liens sont du HTML.
    return '<aside class="cs-suivre" lang="' . esc_attr($lang) . '"><p>' . $html . '</p></aside>';
}
}

if (!function_exists('cs_encadre_suivre_voulu')) {
function cs_encadre_suivre_voulu() {
    $actif  = (string) get_option('cs_encadre_suivre_actif', '0') === '1';
    $apercu = isset($_GET['cs_encadre_suivre']) && $_GET['cs_encadre_suivre'] === '1';
    return $actif || $apercu;
}
}

if (!function_exists('cs_encadre_suivre_langue')) {
function cs_encadre_suivre_langue($id) {
    return function_exists('pll_get_post_language') ? (pll_get_post_language($id) ?: 'fr') : 'fr';
}
}

// Articles et guides.
add_filter('the_content', function ($content) {
    static $pose = false;
    // did_action('wp_head') : Yoast et les métadonnées de partage passent le contenu dans
    // the_content pendant l'en-tête ; sans cette garde, l'encadré partirait dans une méta.
    if ($pose || is_admin() || is_feed() || !is_singular('post') || !did_action('wp_head')) { return $content; }
    $id = (int) get_queried_object_id();
    if (!$id || (int) get_the_ID() !== $id || !cs_encadre_suivre_voulu()) { return $content; }
    $bloc = cs_encadre_suivre_html(cs_encadre_suivre_langue($id));
    if ($bloc === '') { return $content; }
    $pose = true;
    return $content . $bloc;
}, 30);

// Fiches d'événement : point d'accroche du gabarit (Code Snippets n° 56).
add_action('cs_fiche_apres_corps', function ($event_id) {
    static $pose = false;
    if ($pose || !cs_encadre_suivre_voulu()) { return; }
    $bloc = cs_encadre_suivre_html(cs_encadre_suivre_langue((int) $event_id));
    if ($bloc === '') { return; }
    $pose = true;
    echo $bloc;
}, 20);

add_action('wp_head', function () {
    if (!is_singular(array('post', 'tribe_events')) || !cs_encadre_suivre_voulu()) { return; }
    echo '<style id="cs-suivre">'
        . '.cs-suivre{margin:40px 0 8px;padding:18px 22px;border-left:3px solid #DC5D45;background:rgba(201,191,173,.18);}'
        . '.cs-suivre p{margin:0;font-size:.95em;line-height:1.55;}'
        . '.cs-suivre a{font-weight:700;text-decoration:underline;text-underline-offset:3px;}'
        . '</style>';
});
