<?php
/**
 * Méta-description des 13 pages écrites À LA MAIN qui dépassaient 140 caractères — dry-run
 * par défaut.
 *
 * D'OÙ ÇA VIENT. Le 17/09/2026, `seo-textes-pages.php` a réécrit les 193 pages de gabarit
 * (« Que faire à X aujourd'hui… ») sous 140 caractères, plafond réel de Yoast une fois la
 * date de la page ajoutée (voir utils/seo.py, `_META_SEO_CIBLE`). Recompté en base après :
 * il restait 13 pages entre 148 et 164 caractères, toutes écrites à la main (aucun marqueur
 * `cs_texte_auto`), que ce script-là respecte à dessein. Ce sont les pages de VILLE et de
 * TERRITOIRE (Turin, Nice, Aoste, Chambéry, Chablais, province de Turin, en deux langues)
 * plus « Où manger » / « Dove Mangiare ». Les treize textes ci-dessous sont les mêmes,
 * coupés sur leur dernière proposition ; la clé reste en tête, la voix ne change pas.
 * Proposés à Franck, qui a dit « ok » le 17/09 au soir.
 *
 * APPLIQUÉ le 17/09/2026 à 23h, depuis la session (canal Novamira, même code que ci-dessous
 * avec $APPLIQUER = true) : 13 écrites, 13 anciens textes sauvegardés dans `cs_desc_avant`,
 * et recompté en base : 0 page publiée avec une description de plus de 140 caractères
 * (il y en avait 58 le matin même). Ces pages sont à renoter à la main — une méta ne
 * change pas post_modified, le cron ne les reverra pas :
 *   .venv/bin/python -m scripts.yoast_scores --ids 2464 2472 2444 1811 1812 2468 2473 6118 2469 2466 2467 2443 6109 --tout --apply
 *
 * RÉVERSIBLE : l'ancien texte est sauvegardé dans `cs_desc_avant` (jamais écrasé s'il
 * existe déjà). `$RETABLIR = true` le remet en place.
 */
global $wpdb;

$APPLIQUER = false;
$RETABLIR  = false;

$TEXTES = array(
    2464 => "Que faire à Turin ? Concerts, expositions, marchés et festivals : l'agenda des sorties de l'ancienne capitale des États de Savoie.",
    2472 => "Que faire dans le Chablais : concerts, expositions, festivals et fêtes, de Thonon au Léman jusqu'aux Portes du Soleil. L'agenda des sorties.",
    2444 => "Cosa fare a Chambéry? Concerti, mostre, spettacoli, mercati e festival: l'agenda delle uscite dell'antica capitale dei duchi di Savoia.",
    1811 => "Où bien manger, de Turin à Nice : piole turinoises, tables valdôtaines, cuisine nissarde labellisée et fermes-auberges de Haute-Savoie.",
    1812 => "Dove mangiare bene, da Torino a Nizza: piole torinesi, tavole valdostane, cucina nizzarda certificata e fattorie-locanda dell'Alta Savoia.",
    2468 => "Que faire à Aoste : expositions, concerts, marchés, fêtes et rendez-vous valdôtains. Au pied de l'arc d'Auguste, l'agenda de la ville.",
    2473 => "Cosa fare nello Chablais: concerti, mostre, festival e feste, da Thonon al Lemano fino alle Portes du Soleil. L'agenda degli eventi.",
    6118 => "Cosa fare nella provincia di Torino? L'agenda degli eventi di Torino e della sua area metropolitana: Rivoli, Moncalieri, Ivrea e oltre.",
    2469 => "Cosa fare ad Aosta: mostre, concerti, mercati, feste e appuntamenti valdostani. Ai piedi dell'Arco d'Augusto, l'agenda della città.",
    2466 => "Que faire à Nice ? Concerts, expositions, spectacles, marchés et festivals : l'agenda des sorties de la capitale du comté de Nice.",
    2467 => "Cosa fare a Nizza? Concerti, mostre, spettacoli, mercati e festival: l'agenda delle uscite della capitale della Contea di Nizza.",
    2443 => "Que faire à Chambéry ? Concerts, expos, spectacles, marchés et festivals : l'agenda des sorties de la cité des ducs de Savoie.",
    6109 => "Que faire dans la province de Turin ? L'agenda des événements de Turin et de son agglomération : Rivoli, Moncalieri, Ivrea et au-delà.",
);

$ecrits = 0; $retablis = 0; $rapport = array();
foreach ($TEXTES as $id => $desc) {
    $p = get_post((int) $id);
    if (!$p || $p->post_status !== 'publish') { $rapport[] = "$id : absente ou non publiée"; continue; }
    $avant = (string) get_post_meta($id, '_yoast_wpseo_metadesc', true);
    if ($RETABLIR) {
        $sauve = (string) get_post_meta($id, 'cs_desc_avant', true);
        if ($sauve !== '') { update_post_meta($id, '_yoast_wpseo_metadesc', $sauve); delete_post_meta($id, 'cs_desc_avant'); $retablis++; }
        continue;
    }
    $rapport[] = $id . ' ' . $p->post_title . ' : ' . mb_strlen($avant) . ' → ' . mb_strlen($desc);
    if ($APPLIQUER && $avant !== $desc) {
        if ((string) get_post_meta($id, 'cs_desc_avant', true) === '') { update_post_meta($id, 'cs_desc_avant', $avant); }
        update_post_meta($id, '_yoast_wpseo_metadesc', $desc);
        $ecrits++;
    }
}
// RECOMPTE en base, jamais la longueur d'une liste (règle 6).
$plus140 = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID = m.post_id
      WHERE p.post_type = 'page' AND p.post_status = 'publish'
        AND m.meta_key = '_yoast_wpseo_metadesc' AND CHAR_LENGTH(m.meta_value) > 140");
return array(
    '_mode'                        => $RETABLIR ? 'RÉTABLISSEMENT' : ($APPLIQUER ? 'ÉCRITURE' : 'dry-run — rien écrit'),
    'ecrites'                      => $ecrits,
    'retablies'                    => $retablis,
    'RECOMPTE_pages_desc_plus_140' => $plus140,
    'detail'                       => $rapport,
);
