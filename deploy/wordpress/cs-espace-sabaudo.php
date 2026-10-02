<?php
/**
 * Plugin Name: CS - Accueil : ce qu'est l'espace sabaudo
 * Description: Une ligne en bas des deux pages d'accueil (FR 928, IT 1717) qui dit ce que recouvre « espace sabaudo ».
 *
 * POURQUOI (25/09/2026). Les titres des deux accueils sont passés à « Agenda Sabauda :
 * sorties et culture dans l'espace sabaudo » (parti pris validé par Franck le 25/09 : le
 * titre porte l'identité, pas la liste des territoires). Condition posée ce jour-là : le
 * terme doit être expliqué sur la page, sinon c'est du jargon. Franck a choisi le BAS de
 * page : en haut, quarante mots repoussaient l'agenda d'un demi-écran sur mobile.
 *
 * LE TEXTE N'EST PAS ICI. Il vit dans les options `cs_espace_sabaudo_texte_fr` et
 * `cs_espace_sabaudo_texte_it` (même principe que cs-encadre-suivre.php) : un texte
 * éditorial se corrige sans toucher au code. Option vide = rien dans cette langue.
 *
 * PAS DANS LA PAGE 928. La version IT de l'accueil est dérivée de la FR par un dictionnaire
 * str_replace (Code Snippets n° 71), qui décroche en silence dès que la page FR change
 * (une quinzaine de clés orphelines relevées dans son en-tête). Ajouter la phrase au
 * contenu aurait demandé une clé de plus, fragile comme les autres. Ici, chaque langue lit
 * son propre texte.
 *
 * OÙ ÇA S'ACCROCHE. L'accueil est rendu par le snippet 29 via un apply_filters('the_content')
 * MANUEL, hors de la boucle : in_the_loop() et is_main_query() n'y sont jamais vrais (même
 * piège que la v1 du snippet 71). On ne vérifie donc que la page. La ligne s'ajoute en FIN
 * de contenu, après les deux gabarits (mobile et bureau), donc juste avant le pied de page.
 *
 * ACTIVATION. Inerte tant que `cs_espace_sabaudo_actif` ne vaut pas 1. Aperçu sans rien
 * activer : ?cs_espace_sabaudo=1. Retour arrière : option à 0.
 */
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_espace_sabaudo_html')) {
function cs_espace_sabaudo_html($lang) {
    $texte = trim((string) get_option('cs_espace_sabaudo_texte_' . ($lang === 'it' ? 'it' : 'fr'), ''));
    if ($texte === '') { return ''; }
    return '<aside class="cs-espace-sabaudo" lang="' . esc_attr($lang) . '"><p>' . esc_html($texte) . '</p></aside>'
         . '<style id="cs-espace-sabaudo">'
         . '.cs-espace-sabaudo{max-width:720px;margin:36px auto 28px;padding:18px 20px 0;border-top:1px solid #1D1D1B;text-align:center}'
         . '.cs-espace-sabaudo p{margin:0;font-family:\'Nunito Sans\',sans-serif;font-size:13.5px;line-height:1.6;color:#6F6B62}'
         . '</style>';
}
}

add_filter('the_content', function ($content) {
    static $pose = false;
    // did_action('wp_head') : un passage du contenu pendant l'en-tête (métadonnées) ne doit
    // ni recevoir la ligne ni consommer l'unique pose autorisée.
    if ($pose || is_admin() || is_feed() || !did_action('wp_head') || !is_page(array(928, 1717))) { return $content; }
    $actif  = (string) get_option('cs_espace_sabaudo_actif', '0') === '1';
    $apercu = isset($_GET['cs_espace_sabaudo']) && $_GET['cs_espace_sabaudo'] === '1';
    if (!$actif && !$apercu) { return $content; }
    $bloc = cs_espace_sabaudo_html(is_page(1717) ? 'it' : 'fr');
    if ($bloc === '') { return $content; }
    $pose = true;
    return $content . $bloc;
}, 99);
