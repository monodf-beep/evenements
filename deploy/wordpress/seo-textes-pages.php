<?php
/**
 * Titre SEO et méta-description des pages de GABARIT — dry-run par défaut.
 *
 * Suite de `seo-cles-pages.php`, qui a posé l'expression clé de 193 pages le 2026-09-15.
 * Poser la clé éteint le point « aucune expression clé définie » ; elle ne rend pas la
 * page verte à elle seule, parce que Yoast vérifie AUSSI que la clé figure dans le titre
 * SEO et dans la méta-description. Ce fichier-ci écrit ces deux textes.
 *
 * POURQUOI CES PAGES-LÀ, ET PAS L'ACCUEIL. Mesuré le 15/09 sur 28 jours de Search
 * Console : sur les 40 premiers mots-clés du site, AUCUN ne contient « Savoie »,
 * « Piémont », « Vallée d'Aoste », « Nice » comme territoire, ni « agenda culturel ».
 * Les visiteurs tapent deux choses, et deux seulement : le NOM d'un événement (« fiera di
 * vicoforte 2026 », « vercelli chagall ») ou une VILLE plus une PÉRIODE (« annecy ce
 * weekend », « que faire à albertville aujourd'hui », « oggi ad asti », « mentone oggi »).
 * Ces pages de gabarit sont exactement la seconde forme — et elles sortent en 25ᵉ, 34ᵉ,
 * 52ᵉ, 57ᵉ position, donc jamais cliquées. C'est là que le texte change quelque chose.
 *
 * LA DESCRIPTION SE CONSTRUIT SUR L'EXPRESSION CLÉ DÉJÀ POSÉE, jamais sur un titre
 * reconstruit. La clé est le titre de la page moins son point d'interrogation, donc elle
 * porte déjà la bonne préposition (« à Chambéry », « ad Asti », « nello Chablais ») —
 * les deviner aurait fabriqué du faux italien une ville sur trois.
 *
 * DOCTRINE ÉDITORIALE. Une méta-description est un texte LU par un humain dans Google :
 * voix et vocabulaire d'Obsidian s'appliquent (CLAUDE.md, skill redaction-agenda-sabauda).
 * Les deux gabarits ont été passés à `utils.vocabulaire.trouver()` — aucune occurrence —
 * et contrôlés aux deux extrêmes de longueur : 151 caractères pour la ville au nom le plus
 * long (Saint-Jean-de-Maurienne, « cette semaine »), 105 pour la plus courte. Pas de tiret
 * cadratin, pas de superlatif, pas de formule d'appel au lecteur, pas de voix passive.
 *
 * LE TITRE SEO reprend le titre de la page, qui EST la requête. La marque n'est ajoutée
 * que si le tout tient sous 60 caractères — « Que faire à Saint-Jean-de-Maurienne cette
 * semaine ? » en fait déjà 55, la lui coller dessus la ferait tronquer par Google.
 *
 * DEUXIÈME PASSE, 15/09 au soir. Le premier jet épargnait toute page portant déjà un
 * titre ou une description — 54 pages. L'audit des 306 a montré que ces 54 avaient TOUTES
 * le même défaut : elles portent l'expression clé posée par `seo-cles-pages.php`, mais
 * leur description, écrite avant, ne la contient pas. Yoast restait donc rouge dessus.
 * Elles ont été réécrites avec le gabarit, l'ancien texte SAUVEGARDÉ dans `cs_desc_avant`
 * et `cs_titre_avant` — un geste ne se défait pour de bon que si on garde ce qu'il
 * remplace. Recompté après : il ne reste qu'UNE page dans ce cas sur tout le site.
 *
 * ET TREIZE PAGES DE VILLE disaient « Sortir à X : agenda des sorties » quand leur clé,
 * et surtout les requêtes RÉELLES, disent « que faire à X » (« que faire à albertville
 * aujourd'hui », « agenda menton », mesurés en Search Console). Titres alignés en gardant
 * leur structure, la marque retirée quand l'ensemble dépassait 60 caractères. Recompté :
 * plus aucune page du site n'a sa clé absente de son titre.
 *
 * Une faute de grammaire trouvée au passage : la page Chablais italienne portait la clé
 * « cosa fare nel Chablais » alors que son titre et tout le reste du site écrivent
 * « nello Chablais ». C'est la CLÉ qui a été corrigée, pas les textes.
 *
 * RÉVERSIBLE, et prudent avec ce qui a été écrit à la main : on ne touche qu'aux pages
 * marquées `cs_cle_auto` (celles de `seo-cles-pages.php`), et on ne remplace un titre ou
 * une description existants que s'ils portent notre propre marqueur `cs_texte_auto`.
 * `$EFFACER = true` retire ce que ce script a posé, et lui seul.
 */

global $wpdb;

$APPLIQUER = false;
$EFFACER   = false;

// RACCOURCI le 2026-09-16 : Yoast ajoute la DATE de la page (« Juil 21, 2026 » + 3) à la
// longueur qu'il mesure, pour tout contenu, pages comprises — lu dans son code sur le
// serveur (description-data-provider.php). Le plafond utile est donc 140, pas 156, et
// 58 de ces pages sortaient orange avec le gabarit précédent (102 caractères de suffixe
// + « Que faire à Saint-Jean-de-Maurienne cette semaine » = 151). Suffixe ramené à 89 /
// 79 : la clé la plus longue (« Que faire dans la province d'Alexandrie cette semaine »,
// 53) donne 139. Le dry-run du 17/09 avait montré 2 pages à 142 avec « et en italien » :
// c'est la mesure, pas l'estimation, qui a fixé le suffixe français à 86.
//
// APPLIQUÉ le 17/09/2026 à midi, après le dry-run : 193 pages de gabarit, 193 réécrites,
// 45 dépassaient 140 avant, 0 après parmi elles (recompté en base : il reste 13 pages
// au-dessus de 140, toutes écrites à la main — voir seo-desc-pages-manuelles.php). Puis renotées par
// `scripts.yoast_scores --types page --tout --apply`, puisqu'une méta ne change pas
// post_modified et que le cron ne les aurait pas revues.
$SUFFIXE = array(
    'fr' => " : expositions, concerts, marchés et fêtes, horaires et lieux. En français et italien.",
    'it' => ": mostre, concerti, mercati e feste, orari e luoghi. In italiano e in francese.",
);
$MARQUE = ' | Agenda Sabauda';
$MAX_TITRE = 60;

$pages = $wpdb->get_results(
    "SELECT p.ID, p.post_title FROM {$wpdb->posts} p
       JOIN {$wpdb->postmeta} a ON a.post_id = p.ID AND a.meta_key = 'cs_cle_auto'
      WHERE p.post_type = 'page' AND p.post_status = 'publish'
      ORDER BY p.ID", ARRAY_A);

$ecrits = 0; $effaces = 0; $respectes = 0; $sans_langue = 0; $exemples = array();

foreach ($pages as $p) {
    $id  = (int) $p['ID'];
    $cle = get_post_meta($id, '_yoast_wpseo_focuskw', true);
    if (trim($cle) === '') { continue; }

    $auto = get_post_meta($id, 'cs_texte_auto', true);

    if ($EFFACER) {
        if ($auto) {
            delete_post_meta($id, '_yoast_wpseo_title');
            delete_post_meta($id, '_yoast_wpseo_metadesc');
            delete_post_meta($id, 'cs_texte_auto');
            $effaces++;
        }
        continue;
    }

    // Un texte écrit à la main vaut mieux que le nôtre : on ne l'écrase jamais.
    $t_existant = get_post_meta($id, '_yoast_wpseo_title', true);
    $d_existant = get_post_meta($id, '_yoast_wpseo_metadesc', true);
    if (!$auto && (trim($t_existant) !== '' || trim($d_existant) !== '')) { $respectes++; continue; }

    if (strpos($cle, 'Que faire') === 0)      { $lang = 'fr'; }
    elseif (strpos($cle, 'Cosa fare') === 0)  { $lang = 'it'; }
    else { $sans_langue++; continue; }

    $titre = trim($p['post_title']);
    if (mb_strlen($titre . $MARQUE) <= $MAX_TITRE) { $titre .= $MARQUE; }
    $desc = $cle . $SUFFIXE[$lang];

    if (count($exemples) < 12) {
        $exemples[] = $id . ' [' . mb_strlen($titre) . '] ' . $titre
                    . "\n        [" . mb_strlen($desc) . '] ' . $desc;
    }

    if ($APPLIQUER) {
        update_post_meta($id, '_yoast_wpseo_title', $titre);
        update_post_meta($id, '_yoast_wpseo_metadesc', $desc);
        update_post_meta($id, 'cs_texte_auto', '1');
        $ecrits++;
    }
}

// RECOMPTE en base après écriture, jamais la longueur d'une liste (règle 6).
$avec_desc = (int) $wpdb->get_var(
    "SELECT COUNT(DISTINCT p.ID) FROM {$wpdb->posts} p
       JOIN {$wpdb->postmeta} m ON m.post_id = p.ID
            AND m.meta_key = '_yoast_wpseo_metadesc' AND m.meta_value <> ''
      WHERE p.post_type = 'page' AND p.post_status = 'publish'");

return array(
    '_mode'                       => $EFFACER ? 'EFFACEMENT' : ($APPLIQUER ? 'ÉCRITURE' : 'dry-run — rien écrit'),
    'pages_de_gabarit'            => count($pages),
    'ecrites'                     => $ecrits,
    'effacees'                    => $effaces,
    'textes_manuels_respectes'    => $respectes,
    'langue_non_reconnue'         => $sans_langue,
    'RECOMPTE_pages_avec_desc'    => $avec_desc,
    'exemples'                    => $exemples,
);
