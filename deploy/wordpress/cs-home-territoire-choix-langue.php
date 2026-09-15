<?php
/*
Plugin Name: Agenda Sabauda — Choix de langue Piémont/Vallée d'Aoste + libellé dynamique
Description: Correctifs demandes par Franck le 2026-07-20 sur le switcher territoire de la
  home :
  1) Cliquer sur Piémont/Vallee d'Aoste (territoires bilingues) ne doit PLUS basculer
     automatiquement en italien -- une page de choix intermediaire demande la langue.
  2) Le libelle "Vous regardez X" / "Stai guardando X" doit refleter la vraie selection
     courante (?as_territoire=), pas rester fige sur Savoie/Savoia.
  3) Le filtre FR (cs-home-territoire-filtre.php) est etendu pour accepter piemont/
     vallee-d-aoste cote FR (choix "continuer en francais"), pas seulement Savoie/Nice.

  Rollback : supprimer ce fichier. Les liens "Piemont"/"Vallee d'Aoste" du switcher
  retomberaient alors sur une page de choix inexistante (404) -- remettre aussi les hrefs
  directs vers /it/ si rollback total souhaite (cf. historique git du post_content).
*/
if (!defined('ABSPATH')) { exit; }

// 1) Page de choix de langue, interceptee sur les home FR/IT via ?choix_territoire=<slug fr>.
add_action('template_redirect', function () {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (is_admin() || !is_page($home_ids) || empty($_GET['choix_territoire'])) {
        return;
    }

    $slug = sanitize_title(wp_unslash($_GET['choix_territoire']));
    $noms = [
        'piemont' => ['fr' => 'Piémont', 'it' => 'Piemonte', 'it_slug' => 'piemonte'],
        'vallee-d-aoste' => ['fr' => "Vallée d'Aoste", 'it' => "Valle d'Aosta", 'it_slug' => 'valle-d-aosta'],
    ];
    if (!isset($noms[$slug])) {
        return;
    }
    $n = $noms[$slug];

    get_header();
    ?>
    <div style="max-width:500px;margin:0 auto;padding:40px 20px;text-align:center">
      <h1 style="margin:0 0 10px;font-family:'La Semplicita','Saira Condensed',sans-serif;font-weight:600;font-size:26px;color:#1D1D1B"><?php echo esc_html($n['fr']); ?> / <?php echo esc_html($n['it']); ?></h1>
      <p style="margin:0 0 28px;font-family:'Nunito Sans',sans-serif;font-size:14px;color:#4A4A48">Dans quelle langue veux-tu continuer ? <br>In quale lingua vuoi continuare?</p>
      <div style="display:flex;flex-direction:column;gap:12px">
        <a href="<?php echo esc_url('https://agendasabauda.eu/explore/' . $slug . '/'); ?>" style="display:block;text-decoration:none;background:#1D1D1B;color:#F7F1E8;padding:14px;font-family:'Nunito Sans',sans-serif;font-size:14px;font-weight:700">Continuer en français</a>
        <a href="<?php echo esc_url('https://agendasabauda.eu/it/scopri/' . $n['it_slug'] . '/'); ?>" style="display:block;text-decoration:none;background:#DC5D45;color:#F7F1E8;padding:14px;font-family:'Nunito Sans',sans-serif;font-size:14px;font-weight:700">Continua in italiano</a>
      </div>
    </div>
    <?php
    get_footer();
    exit;
}, 5);

// 2) Libelle actif dynamique ("Vous regardez X") sur les 2 bandeaux (desktop + mobile), qui
// partagent tous deux exactement le meme balisage <strong style="color:#DC5D45">NOM</strong>.
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : [928];
    if (!is_page($home_ids) || empty($_GET['as_territoire'])) {
        return $content;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $param = sanitize_title(wp_unslash($_GET['as_territoire']));

    $names_fr = ['savoie' => 'Savoie', 'piemont' => 'Piémont', 'vallee-d-aoste' => "Vallée d'Aoste", 'comte-de-nice' => 'Comté de Nice'];
    $names_it = ['piemonte' => 'Piemonte', 'valle-d-aosta' => "Valle d'Aosta", 'savoia' => 'Savoia', 'contea-di-nizza' => 'Contea di Nizza'];
    $names = $lang === 'it' ? $names_it : $names_fr;

    if (!isset($names[$param])) {
        return $content;
    }

    $default_name = $lang === 'it' ? 'i 4 territori' : 'les 4 territoires';
    $new_name = $names[$param];
    if ($new_name === $default_name) {
        return $content;
    }

    $content = str_replace(
        '<strong style="color:#DC5D45">' . esc_html($default_name) . '</strong>',
        '<strong style="color:#DC5D45">' . esc_html($new_name) . '</strong>',
        $content
    );

    return $content;
}, 20);

// 3) Extension du filtre FR (cs-home-territoire-filtre.php ne gerait que Savoie/Nice cote FR)
// pour accepter aussi piemont/vallee-d-aoste : cas "continuer en francais" depuis le choix
// de langue ci-dessus. Meme mecanisme (tax_query sur les requetes 14-21), scope different
// (fichier different = nouveau comportement, convention du site).
add_filter('jet-engine/query-builder/types/posts-query/args', function ($args, $query) {
    if (empty($query->id) || !in_array((int) $query->id, [14, 15, 16, 17, 18, 19, 20, 21], true)) {
        return $args;
    }
    if (empty($_GET['as_territoire'])) {
        return $args;
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : '';
    if ($lang !== 'fr') {
        return $args;
    }
    $param = sanitize_title(wp_unslash($_GET['as_territoire']));

    $map = ['piemont' => 6, 'vallee-d-aoste' => 8];
    if (!isset($map[$param])) {
        return $args;
    }

    $args['tax_query'] = $args['tax_query'] ?? [];
    $args['tax_query'][] = [
        'taxonomy' => 'territoire',
        'field'    => 'term_id',
        'terms'    => $map[$param],
    ];

    return $args;
}, 10, 2);

/* 2026-08-02 (Franck) : aligne le LIBELLE DU LIEN de la barre territoire des home
   sur celui des pages internes. Le libelle est fige dans le contenu Gutenberg
   ("Changer de territoire"), alors que la barre globale des pages internes dit
   desormais "Choisir un territoire" tant qu'aucun territoire n'est selectionne
   (l'appel a l'action est porte par le lien, cf. cs-territoire-persistant.php).
   Sans ce filtre, deux libelles differents cohabitaient pour le meme etat selon
   qu'on etait sur une home ou sur le reste du site. */
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928, 1717);
    if (!is_page($home_ids)) { return $content; }
    if (!function_exists('cs_territoire_actif') || cs_territoire_actif()) { return $content; }
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $from = $lang === 'it' ? 'Cambia territorio' : 'Changer de territoire';
    $to   = $lang === 'it' ? 'Scegli un territorio' : 'Choisir un territoire';
    return str_replace('>' . $from . '<', '>' . $to . '<', $content);
}, 21);
