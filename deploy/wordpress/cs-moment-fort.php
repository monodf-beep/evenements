<?php
/*
Plugin Name: Agenda Sabauda — Encart « moment fort » sur les home
Description: Un rendez-vous qui compte (Journées du patrimoine, Nuit des musées, Carnaval
  d'Ivrée…) mérite mieux qu'une ligne noyée dans le flux : un encart en tête de home, avec
  deux ou trois cartes d'événement et un lien vers la page dédiée.

  DEMANDE DE FRANCK, 22/09/2026 : « il faudrait peut-être un espèce d'encart qui puisse
  montrer quelques cartes d'événements et qu'on invite à cliquer pour en savoir plus vers
  une page dédiée ».

  CE QUI REND CE DISPOSITIF SÛR, ET POURQUOI IL FALLAIT Y PENSER AVANT D'ÉCRIRE :

  1. UN SEUIL. L'encart ne s'affiche que s'il a de quoi le remplir (`seuil`, 3 par
     défaut). Sans ça il se serait affiché vide, et on l'aurait découvert par une capture
     d'écran de Franck — c'est exactement ce qui est arrivé à la page /choisir/ la veille.
     Mesuré le 22/09 avant d'écrire : l'agenda n'avait que SEPT fiches sur le week-end des
     Giornate Europee del Patrimonio, dont une seule les citant. Un encart posé ce jour-là
     aurait été vide ou hors sujet.

  2. UNE FENÊTRE, DONC UNE EXTINCTION AUTOMATIQUE. `affiche_du` / `affiche_au` : l'encart
     s'allume seul et s'éteint seul. C'est la règle 3 du CLAUDE.md — tout état qui écarte
     ou met en avant quelque chose doit avoir quelqu'un qui le rouvre, et « un humain qui
     pense à le retirer » n'est pas une réponse. Ici, c'est le calendrier.

  3. UN ZÉRO QUI DIT D'OÙ IL VIENT. Quand l'encart ne s'affiche pas, la source de la page
     porte un commentaire disant lequel des deux cas s'est produit : hors fenêtre, ou
     sous le seuil avec le nombre trouvé. Sans ça, « rien ne s'affiche » ne distingue pas
     une panne d'une absence.

  4. UN COMPTEUR QUI DIT CE QU'IL COMPTE. Le lien annonce le nombre RÉEL d'événements de
     la période, pas le nombre de cartes montrées.

  TEXTES ÉDITORIAUX. Les titres et chapôs ci-dessous sont du texte destiné au site : ils
  doivent passer la doctrine de rédaction (voix + vocabulaire interdit + charte) AVANT
  déploiement. Tant que ce n'est pas fait, ne pas pousser ce fichier en ligne.

  Rollback : supprimer ce fichier. Rien n'est écrit en base, aucun réglage à défaire.
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_moments_forts')) {
/**
 * Les moments forts, en dur.
 *
 * POURQUOI PAS UN FICHIER DE CONFIG DU DÉPÔT : ce mu-plugin s'exécute sur l'hébergement
 * WordPress (OVH), qui n'a aucun accès au dépôt ni au VPS. `config/calendrier_categories.json`
 * et consorts vivent côté pipeline ; ici, la liste doit être dans le fichier.
 *
 * Dates au format Y-m-d, bornes INCLUSES.
 */
function cs_moments_forts() {
    return array(
        array(
            'slug'       => 'patrimoine-piemont',
            'affiche_du' => '2026-09-22',
            'affiche_au' => '2026-09-27',
            'debut'      => '2026-09-26',
            'fin'        => '2026-09-27',
            'seuil'      => 3,
            'territoire' => array('fr' => 'piemont', 'it' => 'piemonte'),
            'kicker'     => array('fr' => 'Samedi 26 & dimanche 27 septembre',
                                  'it' => 'Sabato 26 e domenica 27 settembre'),
            'titre'      => array('fr' => 'Journées européennes du patrimoine en Piémont',
                                  'it' => 'Giornate Europee del Patrimonio in Piemonte'),
            'chapo'      => array(
                'fr' => "Samedi soir, les musées d'État ouvrent jusqu'à 22 h pour 1 €. En France, c'était le week-end dernier ; de l'autre côté du col, c'est maintenant.",
                'it' => "Sabato sera i musei statali restano aperti fino alle 22 a 1 euro. In Francia è stato il fine settimana scorso; da questa parte del colle, è adesso."),
            'page'       => array('fr' => 'https://agendasabauda.eu/selections/journees-du-patrimoine-piemont/',
                                  'it' => 'https://agendasabauda.eu/it/selezioni/giornate-del-patrimonio-piemonte/'),
            'lien'       => array('fr' => 'Voir les %d événements du week-end',
                                  'it' => 'Vedi i %d eventi del fine settimana'),
        ),
    );
}
}

if (!function_exists('cs_moment_fort_actif')) {
/** Le moment dont la fenêtre couvre aujourd'hui, ou null. Le premier trouvé gagne. */
function cs_moment_fort_actif($aujourdhui = null) {
    $aujourdhui = $aujourdhui ?: current_time('Y-m-d');
    foreach (cs_moments_forts() as $m) {
        if ($aujourdhui >= $m['affiche_du'] && $aujourdhui <= $m['affiche_au']) {
            return $m;
        }
    }
    return null;
}
}

if (!function_exists('cs_moment_fort_evenements')) {
/**
 * Les fiches de la période, dans la langue courante.
 *
 * Renvoie array('total' => int, 'cartes' => array). Le total sert au libellé du lien ; les
 * cartes sont les premières par date de début. Cache d'une heure, dix minutes si c'est
 * vide — un vide qui vient d'une panne ne doit pas être figé pour une heure.
 */
function cs_moment_fort_evenements($moment, $lang, $nb_cartes = 3) {
    $terme = isset($moment['territoire'][$lang]) ? $moment['territoire'][$lang] : '';
    if (!$terme) {
        return array('total' => 0, 'cartes' => array());
    }
    $cle = 'cs_moment_' . $moment['slug'] . '_' . $lang;
    $cache = get_transient($cle);
    if (is_array($cache)) {
        return $cache;
    }

    $args = array(
        'post_type'           => 'tribe_events',
        'post_status'         => 'publish',
        'posts_per_page'      => 60,
        'ignore_sticky_posts' => true,
        'lang'                => $lang,
        'tax_query'           => array(array('taxonomy' => 'territoire', 'field' => 'slug', 'terms' => $terme)),
        'meta_query'          => array('debut' => array(
            'key'     => '_EventStartDate',
            'value'   => array($moment['debut'] . ' 00:00:00', $moment['fin'] . ' 23:59:59'),
            'compare' => 'BETWEEN',
            'type'    => 'DATETIME',
        )),
        'orderby'             => array('debut' => 'ASC'),
    );
    $q = new WP_Query($args);

    $cartes = array();
    foreach (array_slice($q->posts, 0, $nb_cartes) as $p) {
        $debut = get_post_meta($p->ID, '_EventStartDate', true);
        $cartes[] = array(
            'id'    => $p->ID,
            'titre' => get_the_title($p),
            'url'   => get_permalink($p),
            'image' => get_the_post_thumbnail_url($p, 'medium_large'),
            'jour'  => $debut ? (int) substr($debut, 8, 2) : 0,
            'mois'  => $debut ? (int) substr($debut, 5, 2) : 0,
            'ville' => get_post_meta($p->ID, 'as_ville', true),
        );
    }
    wp_reset_postdata();

    $out = array('total' => count($q->posts), 'cartes' => $cartes);
    set_transient($cle, $out, $out['total'] ? HOUR_IN_SECONDS : 10 * MINUTE_IN_SECONDS);
    return $out;
}
}

if (!function_exists('cs_moment_fort_date_courte')) {
/** « Sam. 26 sept. » / « Sab. 26 set. » — table en dur, cf. cs-home-territoire-choix-langue. */
function cs_moment_fort_date_courte($jour, $mois, $lang) {
    $mfr = array(1 => 'janv.', 'fév.', 'mars', 'avril', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.');
    $mit = array(1 => 'genn.', 'febbr.', 'mar.', 'apr.', 'magg.', 'giugno', 'luglio', 'ag.', 'set.', 'ott.', 'nov.', 'dic.');
    $t = $lang === 'it' ? $mit : $mfr;
    $mois = (int) $mois;
    if (!$mois || !isset($t[$mois]) || !$jour) {
        return '';
    }
    return ((int) $jour) . ' ' . $t[$mois];
}
}

if (!function_exists('cs_moment_fort_html')) {
/** L'encart, ou '' si le moment n'a pas de quoi se montrer. */
function cs_moment_fort_html($moment, $lang) {
    $seuil = isset($moment['seuil']) ? (int) $moment['seuil'] : 3;
    $data = cs_moment_fort_evenements($moment, $lang);

    if ($data['total'] < $seuil) {
        // Le zéro doit dire d'où il vient : sous le seuil, avec le compte trouvé.
        return '<!-- cs-moment-fort : ' . esc_html($moment['slug']) . ' [' . esc_html($lang)
             . '] ' . (int) $data['total'] . ' fiche(s) pour un seuil de ' . $seuil . ' — encart masqué -->';
    }

    $fleche = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M3.4 12.3c4.6-.5 11.5-.7 17.1-.6"/><path d="M14.6 6.1c1.9 2.1 4 4.1 5.9 5.6c-2 1.6-4.1 3.6-5.8 5.9"/></svg>';

    $h = '<div class="cs-mf">';
    $h .= '<span class="cs-mf__kicker">' . esc_html($moment['kicker'][$lang]) . '</span>';
    $h .= '<h2 class="cs-mf__titre">' . esc_html($moment['titre'][$lang]) . '</h2>';
    $h .= '<p class="cs-mf__chapo">' . esc_html($moment['chapo'][$lang]) . '</p>';

    $h .= '<div class="cs-mf__cartes">';
    foreach ($data['cartes'] as $c) {
        $date = cs_moment_fort_date_courte($c['jour'], $c['mois'], $lang);
        $eyebrow = trim($date . ($c['ville'] ? ' · ' . $c['ville'] : ''));
        $h .= '<a class="cs-mf__carte" href="' . esc_url($c['url']) . '">';
        $h .= '<span class="cs-mf__img">';
        // Pas d'image : on laisse la case vide plutôt qu'un visuel inadapté (charte §9).
        $h .= $c['image'] ? '<img src="' . esc_url($c['image']) . '" alt="" loading="lazy">' : '';
        $h .= '</span>';
        $h .= '<span class="cs-mf__eyebrow">' . esc_html($eyebrow) . '</span>';
        $h .= '<span class="cs-mf__titre-carte">' . esc_html($c['titre']) . '</span>';
        $h .= '</a>';
    }
    $h .= '</div>';

    // Le compteur annonce le total de la période, pas le nombre de cartes montrées.
    $h .= '<a class="cs-mf__tout" href="' . esc_url($moment['page'][$lang]) . '">'
        . esc_html(sprintf($moment['lien'][$lang], $data['total'])) . ' ' . $fleche . '</a>';

    return $h . '</div>';
}
}

if (!function_exists('cs_moment_fort_css')) {
function cs_moment_fort_css() {
    return '<style id="cs-moment-fort">
.cs-mf{margin:26px 20px 8px;padding:18px 16px 16px;background:#FBF7F0;border:1.5px solid #1D1D1B;border-radius:4px;transform:rotate(-0.5deg);font-family:\'Nunito Sans\',sans-serif;box-sizing:border-box}
.cs-mf *{box-sizing:border-box}
.cs-mf__kicker{display:block;font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#DC5D45;margin-bottom:6px}
.cs-mf__titre{font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:23px;line-height:1.06;letter-spacing:.02em;color:#1D1D1B;margin:0 0 7px}
.cs-mf__chapo{margin:0 0 15px;font-size:13px;line-height:1.5;color:#4A4A48}
.cs-mf__cartes{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cs-mf__carte{display:block;text-decoration:none;color:#1D1D1B;min-width:0}
.cs-mf__carte:nth-child(3){display:none}
.cs-mf__img{display:block;aspect-ratio:3/2;overflow:hidden;background:#F7F1E8;border-radius:3px;margin-bottom:8px}
.cs-mf__img img{width:100%;height:100%;object-fit:cover;display:block}
.cs-mf__eyebrow{display:block;font-size:10.5px;font-weight:800;color:#1D1D1B;margin-bottom:3px}
.cs-mf__titre-carte{display:block;font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:15.5px;line-height:1.22}
.cs-mf__carte:hover .cs-mf__titre-carte{text-decoration:underline;text-underline-offset:3px}
.cs-mf__tout{display:flex;align-items:center;gap:7px;margin-top:14px;padding-top:11px;border-top:1px solid #1D1D1B;font-size:13px;font-weight:800;color:#1D1D1B;text-decoration:none}
@media(min-width:900px){
 .cs-mf{margin:30px 0 10px;padding:24px 24px 20px;transform:rotate(-0.4deg)}
 .cs-mf__titre{font-size:30px}
 .cs-mf__chapo{font-size:14px;max-width:62ch}
 .cs-mf__cartes{grid-template-columns:repeat(3,1fr);gap:18px}
 .cs-mf__carte:nth-child(3){display:block}
 .cs-mf__titre-carte{font-size:16.5px}
}
</style>';
}
}

/**
 * Insertion : juste avant « À la une », sur les DEUX gabarits de la home.
 *
 * Le marqueur `<!-- A LA UNE -->` est dans le CONTENU Gutenberg des pages 928 (FR) et
 * 1717 (IT), et il y figure deux fois — une pour le gabarit mobile, une pour le bureau.
 * Les deux variantes cohabitent dans le DOM, masquées l'une ou l'autre par media query :
 * insérer aux deux endroits est donc correct, et c'est le seul moyen d'être vu dans les
 * deux cas. Vérifié le 22/09 sur le HTML servi par le site.
 */
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928, 1717);
    if (is_admin() || !is_page($home_ids) || strpos($content, '<!-- A LA UNE -->') === false) {
        return $content;
    }

    $moment = cs_moment_fort_actif();
    if (!$moment) {
        return str_replace('<!-- A LA UNE -->', '<!-- cs-moment-fort : aucun moment dans sa fenêtre aujourd\'hui --><!-- A LA UNE -->', $content);
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    if (!isset($moment['titre'][$lang])) {
        return $content;
    }

    $encart = cs_moment_fort_html($moment, $lang);
    return str_replace('<!-- A LA UNE -->', cs_moment_fort_css() . $encart . '<!-- A LA UNE -->', $content);
}, 22);
