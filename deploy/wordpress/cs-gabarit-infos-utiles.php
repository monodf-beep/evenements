<?php
/*
Plugin Name: Agenda Sabauda — Gabarit "Infos utiles" / "Informazioni utili"
Description: Pages 1768 (FR) / 1791 (IT) affichaient le template WP par defaut
  (sidebar Recherche/Recent Posts/Recent Comments) faute de gabarit dedie -- meme
  symptome que les pages "selection" trouve plus tot le 2026-07-20. Gabarit simple
  H1 + the_content() (700px), sur le modele exact de apropos-template.php (snippet
  48), mais reprend le VRAI contenu du post (the_content) plutot que du texte fige
  dans le PHP -- Franck a demande un contenu miroir FR/IT edite directement sur les
  posts, pas codé en dur.
*/
if (!defined('ABSPATH')) { exit; }

add_action('template_redirect', function () {
    // 2170 = "Chi siamo" (traduction IT de "A propos" 933, creee le 2026-07-20) :
    // meme gabarit editorial simple, le titre vient du post lui-meme.
    if (is_admin() || !is_page([1768, 1791, 2170])) {
        return;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $h1 = is_page(2170) ? get_the_title() : ($lang === 'it' ? 'Informazioni utili' : 'Infos utiles');

    get_header();
    ?>
    <div style="max-width:700px;margin:0 auto;padding:0 20px">

      <div style="padding:32px 0 8px">
        <h1 style="margin:0 0 20px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:32px;line-height:1.05;color:#1D1D1B;letter-spacing:0.02em"><?php echo esc_html($h1); ?></h1>
      </div>

      <div style="padding-bottom:40px;font-family:'Nunito Sans',sans-serif;font-size:15px;line-height:1.65;color:#1D1D1B">
        <?php the_content(); ?>
      </div>

    </div>
    <?php
    get_footer();
    exit;
});
