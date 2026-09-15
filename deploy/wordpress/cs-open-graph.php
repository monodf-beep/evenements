<?php
/*
Plugin Name: Agenda Sabauda — Metadonnees de partage (Open Graph / Twitter)
Description: Constat 2026-07-20 : partager une page du site donnait un rendu pauvre.
  Yoast produisait bien des balises, mais avec de vrais defauts : og:image ABSENTE sur
  presque toutes les pages (listes, selections, hubs, pages editoriales), descriptions
  aspirees du contenu et donc absurdes ("Publicite Annoncer sur Agenda Sabauda",
  "Immagine da definire Itinerario da definire"), titres plats, et og:locale toujours
  fr_FR meme sur une fiche italienne.

  Ce fichier reprend la main sur les balises de partage, par TYPE de page, avec des
  textes editoriaux ecrits (jamais aspires) et une image de marque 1200x630 par langue.
  Les fiches evenement gardent leur propre visuel (plus parlant qu'un logo) ; l'image de
  marque sert de repli partout ailleurs.

  Priorite 5 sur wp_head : passe AVANT Yoast (10). Les doublons Yoast sont neutralises
  via ses filtres officiels (wpseo_opengraph_*), sans desactiver le plugin.

  Rollback : supprimer ce fichier (Yoast reprend seul la main).
*/
if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_og_image')) {
function cs_og_image($lang) {
    $base = 'https://agendasabauda.eu/wp-content/uploads/2026/07/';
    return $base . ($lang === 'it' ? 'og-agenda-sabauda-it.png' : 'og-agenda-sabauda-fr.png');
}
}


if (!function_exists('cs_og_crop')) {
/**
 * Renvoie l'URL d'une version 1200x630 (ratio 1.91:1 attendu par les reseaux) de la
 * vignette. Les visuels d'evenement sont en 4:3 : partages tels quels, ils sont rognes
 * ou cadres de bandes noires. La version OG est generee A LA DEMANDE puis reutilisee
 * (pas de regeneration massive de la mediatheque).
 */
function cs_og_crop($attachment_id) {
    $src = wp_get_attachment_image_src($attachment_id, 'cs_og_1200x630');
    if ($src && (int) $src[1] === 1200 && (int) $src[2] === 630) {
        return $src[0];
    }
    $fichier = get_attached_file($attachment_id);
    if (!$fichier || !file_exists($fichier)) {
        return null;
    }
    $editor = wp_get_image_editor($fichier);
    if (is_wp_error($editor)) {
        return null;
    }
    $editor->resize(1200, 630, true); // true = recadrage centre
    $dest = $editor->generate_filename('og1200x630');
    $saved = $editor->save($dest);
    if (is_wp_error($saved)) {
        return null;
    }
    // enregistre la taille pour ne la regenerer qu'une fois
    $meta = wp_get_attachment_metadata($attachment_id);
    if (is_array($meta)) {
        $meta['sizes']['cs_og_1200x630'] = [
            'file' => basename($saved['path']), 'width' => 1200, 'height' => 630,
            'mime-type' => $saved['mime-type'] ?? 'image/jpeg',
        ];
        wp_update_attachment_metadata($attachment_id, $meta);
    }
    $up = wp_upload_dir();
    return trailingslashit($up['baseurl']) . _wp_get_attachment_relative_path($fichier) . '/' . basename($saved['path']);
}
}

if (!function_exists('cs_og_couper')) {
// Coupe proprement sur un mot entier (les reseaux tronquent brutalement sinon).
function cs_og_couper($texte, $max) {
    $texte = trim(preg_replace('/\s+/', ' ', $texte));
    if (mb_strlen($texte) <= $max) {
        return $texte;
    }
    $coupe = mb_substr($texte, 0, $max - 1);
    $espace = mb_strrpos($coupe, ' ');
    if ($espace !== false && $espace > $max * 0.6) {
        $coupe = mb_substr($coupe, 0, $espace);
    }
    return rtrim($coupe, " ,;:.") . "\xE2\x80\xA6";
}
}
if (!function_exists('cs_og_data')) {
/**
 * Renvoie [titre, description, image, type] selon la page courante.
 * Textes ECRITS, jamais extraits du contenu : c'est ce qui distingue un partage
 * lisible d'un partage rempli de "Publicite" et de textes de remplissage.
 */
function cs_og_data() {
    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $it = ($lang === 'it');
    $site = 'Agenda Sabauda';
    $img = cs_og_image($lang);
    $type = 'website';

    $baseline = $it
        ? "L'agenda culturale dello spazio sabaudo : Savoia, Piemonte, Valle d'Aosta e Nizza."
        : "L'agenda culturel de l'espace sabaudo : Savoie, Piémont, Vallée d'Aoste et Nice.";

    // --- Fiche evenement : le visuel de l'evenement prime ---
    if (is_singular('tribe_events')) {
        $id = get_queried_object_id();
        $titre = html_entity_decode(get_the_title($id), ENT_QUOTES, 'UTF-8');
        $venue_id = get_post_meta($id, '_EventVenueID', true);
        $lieu = $venue_id ? get_the_title($venue_id) : '';
        $ville = $venue_id ? get_post_meta($venue_id, '_VenueCity', true) : '';
        $start = get_post_meta($id, '_EventStartDate', true);
        $quand = $start ? date_i18n('j F Y', strtotime($start)) : '';
        $ou = trim($lieu . ($ville ? ', ' . $ville : ''));
        $desc = trim(($quand ? ($it ? "Il $quand" : "Le $quand") : '') . ($ou ? ' · ' . $ou : ''));
        if ($desc === '') { $desc = $baseline; }
        if (has_post_thumbnail($id)) {
            $crop = cs_og_crop(get_post_thumbnail_id($id));
            if ($crop) { $img = $crop; }
        }
        return [$titre, $desc, $img, 'article'];
    }

    // --- Fiche selection (carrousel) ---
    if (is_singular('selection')) {
        $id = get_queried_object_id();
        $titre = html_entity_decode(get_the_title($id), ENT_QUOTES, 'UTF-8');
        $intro = wp_strip_all_tags((string) get_post_meta($id, 'sel_intro', true));
        $desc = $intro !== '' ? $intro : $baseline;
        if (has_post_thumbnail($id)) {
            $crop = cs_og_crop(get_post_thumbnail_id($id));
            if ($crop) { $img = $crop; }
        }
        return [$titre, $desc, $img, 'article'];
    }

    // --- Archives : territoire, categorie, type de lieu ---
    if (is_tax(['territoire', 'tribe_events_cat', 'type_de_lieu'])) {
        $term = get_queried_object();
        $nom = $term ? html_entity_decode($term->name, ENT_QUOTES, 'UTF-8') : '';
        if (is_tax('territoire')) {
            $titre = $it ? "$nom : cosa fare" : "$nom : que faire ?";
            $desc = $it
                ? "Tutti gli eventi in $nom, aggiornati in continuo : concerti, mostre, sagre, feste e appuntamenti per le famiglie."
                : "Tous les événements en $nom, mis à jour en continu : concerts, expositions, sagre, fêtes et sorties en famille.";
        } elseif (is_tax('type_de_lieu')) {
            $titre = $it ? "$nom : gli eventi" : "$nom : les événements";
            $desc = $it
                ? "Gli eventi nei musei dei quattro territori alpini, aggiornati in continuo."
                : "Les événements dans les musées des quatre territoires alpins, mis à jour en continu.";
        } else {
            $titre = $nom;
            $desc = $it
                ? "La programmazione $nom sui quattro territori alpini : Savoia, Piemonte, Valle d'Aosta e Nizza."
                : "La programmation $nom sur les quatre territoires alpins : Savoie, Piémont, Vallée d'Aoste et Nice.";
        }
        return [$titre, $desc, $img, 'website'];
    }

    // --- Pages listes connues (gabarits PHP) ---
    if (is_page()) {
        $pid = get_queried_object_id();
        $listes = [
            929  => ['fr', "Que faire aujourd'hui ?", "Les événements du jour dans les quatre territoires alpins."],
            931  => ['fr', "Que faire cette semaine ?", "Tous les événements de la semaine dans les quatre territoires alpins."],
            930  => ['fr', "Que faire ce week-end ?", "La sélection du week-end : concerts, expositions, sagre, fêtes et sorties en famille."],
            932  => ['fr', "Tout l'agenda", "L'agenda complet des quatre territoires alpins, mis à jour en continu."],
            1789 => ['it', "Cosa fare questo weekend ?", "La selezione del weekend : concerti, mostre, sagre, feste e appuntamenti per le famiglie."],
            1790 => ['it', "Tutti gli eventi", "L'agenda completo dei quattro territori alpini, aggiornato in continuo."],
        ];
        if (isset($listes[$pid])) {
            return [$listes[$pid][1], $listes[$pid][2], $img, 'website'];
        }
        // Autres pages (editoriales) : titre reel + extrait redige s'il existe
        $titre = html_entity_decode(get_the_title($pid), ENT_QUOTES, 'UTF-8');
        $ex = get_post_field('post_excerpt', $pid);
        $desc = $ex !== '' ? wp_strip_all_tags($ex) : $baseline;
        if (is_front_page() || $pid === 928 || $pid === 1717) {
            $titre = $it ? "Agenda Sabauda : cosa fare, dove mangiare" : "Agenda Sabauda : quoi faire, où manger";
            $desc = $baseline;
        }
        return [$titre, $desc, $img, 'website'];
    }

    return [$site, $baseline, $img, $type];
}
}

// Neutralise les balises de partage de Yoast (sans desactiver le plugin, qui continue
// de gerer titre SEO, meta description, canonique, sitemaps et donnees structurees).
// Les filtres historiques (wpseo_opengraph_*) ne suffisent PAS : depuis Yoast 14 la
// sortie passe par des "presenters", d'ou l'og:image en double constatee le 2026-07-20.
add_filter('wpseo_frontend_presenters', function ($presenters) {
    return array_values(array_filter($presenters, function ($p) {
        $n = is_object($p) ? get_class($p) : (string) $p;
        return !preg_match('/(Open_Graph|OpenGraph|Twitter)/i', $n);
    }));
}, 99);

add_action('wp_head', function () {
    if (is_admin() || is_feed() || is_404()) { return; }
    list($titre, $desc, $img, $type) = cs_og_data();

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $locale = ($lang === 'it') ? 'it_IT' : 'fr_FR';
    $alt    = ($lang === 'it') ? 'fr_FR' : 'it_IT';

    // Cibles reseaux : ~60 pour le titre, ~125 pour la description (au-dela, les
    // apercus tronquent, surtout sur mobile).
    $titre = cs_og_couper($titre, 60);
    $desc  = cs_og_couper($desc, 125);

    // og:url DOIT correspondre a la canonique : Facebook identifie une page par cette
    // URL. La construction via $wp->request omettait le prefixe de langue (/it/),
    // ce qui rattachait les partages a la mauvaise adresse (constat 2026-07-20).
    if (is_singular()) {
        $url = get_permalink(get_queried_object_id());
    } elseif (is_tax()) {
        $lien = get_term_link(get_queried_object());
        $url = is_wp_error($lien) ? home_url('/') : $lien;
    } elseif (is_front_page()) {
        $url = function_exists('pll_home_url') ? pll_home_url() : home_url('/');
    } else {
        $url = home_url($GLOBALS['wp']->request ? '/' . $GLOBALS['wp']->request . '/' : '/');
    }

    $tags = [
        ['property', 'og:site_name',  'Agenda Sabauda'],
        ['property', 'og:type',       $type],
        ['property', 'og:title',      $titre],
        ['property', 'og:description',$desc],
        ['property', 'og:image',      $img],
        ['property', 'og:image:width','1200'],
        ['property', 'og:image:height','630'],
        ['property', 'og:image:alt',  $titre],
        ['property', 'og:url',        $url],
        ['property', 'og:locale',     $locale],
        ['property', 'og:locale:alternate', $alt],
        ['name',     'twitter:card',  'summary_large_image'],
        ['name',     'twitter:title', $titre],
        ['name',     'twitter:description', $desc],
        ['name',     'twitter:image', $img],
    ];
    echo "\n<!-- Agenda Sabauda : metadonnees de partage -->\n";
    foreach ($tags as $t) {
        printf('<meta %s="%s" content="%s" />' . "\n", $t[0], esc_attr($t[1]), esc_attr($t[2]));
    }
}, 5);