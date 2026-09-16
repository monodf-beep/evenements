<?php
/**
 * SEO des ARTICLES « Curiosités » — expression clé, titre SEO, méta-description.
 * Dry-run par défaut ; à exécuter par le canal Novamira, jamais installé comme mu-plugin.
 *
 * D'OÙ ÇA VIENT — 2026-09-16, Franck : « le SEO des articles est très mauvais, tout en
 * rouge, presque tout ». MESURÉ AVANT D'ÉCRIRE, sur les 24 articles publiés (type post) :
 *
 *   • les 12 GUIDES portent déjà clé + titre SEO + description, tous les douze. Ceux qui
 *     affichent « Non disponible » dans la colonne Score SEO n'ont simplement jamais été
 *     ouverts dans l'éditeur : Yoast calcule ce score dans le NAVIGATEUR, jamais côté
 *     serveur. Preuve : « Où manger à Turin » (FR, ouvert) affiche « Bon » (85) ; sa
 *     jumelle italienne, avec les MÊMES trois champs remplis, affiche « Non disponible » ;
 *   • les 10 CURIOSITÉS (5 paires FR/IT publiées le 06/09) n'ont RIEN : ni clé, ni titre
 *     SEO, ni description. C'est le rouge réel, et c'est ce que ce fichier remplit.
 *
 * LA CLÉ EST CELLE DU TITRE — « curiosités de Turin », « curiosità di Annecy » — parce
 * qu'elle y figure telle quelle (Yoast vérifie la clé dans le titre SEO, la description
 * et l'introduction ; les trois sont couverts). Search Console, 28 jours : ces pages ont
 * ZÉRO impression sur leur propre adresse, donc aucune requête mesurée ne pouvait guider
 * un autre choix. En revanche les Italiens tapent bien « [ville] cosa vedere » sur ce
 * site (Annemasse, Sallanches, Saint-Jean-de-Maurienne, Aix-les-Bains, Ivrea) : les trois
 * descriptions italiennes des villes françaises (Chambéry, Annecy, Nizza) s'ouvrent donc
 * sur « Cosa vedere a … » — c'est l'angle croisé de docs/CURIOSITES.md §2, le seul où un
 * site neuf a une chance.
 *
 * DOCTRINE. Textes lus par un humain dans Google : voix et vocabulaire Obsidian appliqués
 * (CLAUDE.md, skill redaction-agenda-sabauda). Passés à `utils.vocabulaire.trouver()` sur
 * une note reconstituée des huit règles : aucune occurrence. Pas de tiret cadratin. Titres
 * ≤ 60, descriptions ≤ 156, clé présente dans les deux, vérifié par `utils.seo.cle_dans_texte`.
 * Aucun fait dans une description qui ne soit déjà dans l'introduction de l'article.
 *
 * CE QUE ÇA NE FAIT PAS. La densité Yoast restera basse : la clé exacte n'apparaît pas
 * dans le corps des articles, et ce fichier ne touche JAMAIS au corps — une phrase de
 * l'introduction relue par Franck est la seule voie propre, et elle passe par lui.
 *
 * RÉVERSIBLE : ne touche que ces dix identifiants ; ne remplace jamais un texte existant
 * qui ne porte pas notre marqueur ; sauvegarde l'ancien dans cs_*_avant ;
 * `$EFFACER = true` retire ce que ce script a posé, et lui seul.
 * DESCRIPTIONS RACCOURCIES le 16/09 au soir : Yoast ajoute la date (« Sep 6, 2026 » + 3) à la
 * longueur mesurée, le plafond utile est 140 et non 156 (voir utils/seo.py). Les dix
 * descriptions ci-dessous tiennent en 119 à 140 caractères ; ré-appliquées le même soir.
 */

global $wpdb;

$APPLIQUER = false;
$EFFACER   = false;

$ARTICLES = array(
    8227 => array('cle' => 'curiosités de Turin',
        'titre' => 'Six curiosités de Turin que les Turinois eux-mêmes oublient',
        'desc'  => 'Six curiosités de Turin, de la Piazza San Carlo à Collegno : deux mille ans sous le pavé, façades mal lues, la ville qui a fait l\'Italie.'),
    8228 => array('cle' => 'curiosità di Torino',
        'titre' => 'Sei curiosità di Torino che i torinesi stessi dimenticano',
        'desc'  => 'Sei curiosità di Torino, da Piazza San Carlo a Collegno: duemila anni sotto il selciato, facciate lette male, la città che fece l\'Italia.'),
    8229 => array('cle' => 'curiosités de Chambéry',
        'titre' => 'Cinq curiosités de Chambéry que même les Savoyards ignorent',
        'desc'  => 'Cinq curiosités de Chambéry, de la fontaine des Éléphants aux Charmettes : ce qui manque aux éléphants, ce que cache la cathédrale.'),
    8230 => array('cle' => 'curiosità di Chambéry',
        'titre' => 'Cinque curiosità di Chambéry che i savoiardi non conoscono',
        'desc'  => 'Cosa vedere a Chambéry, dal centro barocco alla campagna di Rousseau: cinque curiosità di Chambéry, dalla fontana alla cattedrale.'),
    8231 => array('cle' => 'curiosités d\'Aoste',
        'titre' => 'Six curiosités d\'Aoste que même les Valdôtains oublient',
        'desc'  => 'Six curiosités d\'Aoste au-delà des ruines romaines : cinq langues, une assemblée de cinq siècles, un château qu\'on ne montre jamais.'),
    8232 => array('cle' => 'curiosità di Aosta',
        'titre' => 'Sei curiosità di Aosta che nemmeno i valdostani conoscono',
        'desc'  => 'Sei curiosità di Aosta oltre le rovine romane: una città a cinque lingue, un\'assemblea di cinque secoli, un castello che non si mostra mai.'),
    8233 => array('cle' => 'curiosités d\'Annecy',
        'titre' => 'Sept curiosités d\'Annecy que même les Savoyards ignorent',
        'desc'  => 'Sept curiosités d\'Annecy au-delà du lac : deux femmes que l\'histoire a tues, un duc devenu pape, une chocolaterie disparue du quai.'),
    8234 => array('cle' => 'curiosità di Annecy',
        'titre' => 'Sette curiosità di Annecy che nemmeno i savoiardi conoscono',
        'desc'  => 'Cosa vedere ad Annecy oltre il lago: sette curiosità di Annecy, due donne taciute dalla storia, un duca diventato papa.'),
    8235 => array('cle' => 'curiosités de Nice',
        'titre' => 'Trois curiosités de Nice que même les Nissarts oublient',
        'desc'  => 'Trois curiosités de Nice au-delà de la Promenade des Anglais : le siège franco-ottoman de 1543, une cuisine venue de l\'autre côté de la mer.'),
    8236 => array('cle' => 'curiosità di Nizza',
        'titre' => 'Tre curiosità di Nizza che nemmeno i nizzardi conoscono',
        'desc'  => 'Cosa vedere a Nizza oltre la Promenade des Anglais: tre curiosità di Nizza, l\'assedio franco-ottomano del 1543, una cucina venuta dal mare.'),
);

$ecrits = 0; $effaces = 0; $respectes = 0; $absents = 0; $lignes = array();

foreach ($ARTICLES as $id => $t) {
    $p = get_post($id);
    if (!$p || $p->post_type !== 'post') { $absents++; $lignes[] = "$id : ABSENT ou pas un article"; continue; }
    $auto_cle = get_post_meta($id, 'cs_cle_auto', true);
    $auto_txt = get_post_meta($id, 'cs_texte_auto', true);

    if ($EFFACER) {
        if ($auto_cle) { delete_post_meta($id, '_yoast_wpseo_focuskw'); delete_post_meta($id, 'cs_cle_auto'); }
        if ($auto_txt) { delete_post_meta($id, '_yoast_wpseo_title'); delete_post_meta($id, '_yoast_wpseo_metadesc'); delete_post_meta($id, 'cs_texte_auto'); }
        if ($auto_cle || $auto_txt) { $effaces++; }
        continue;
    }

    $cle_ex = trim((string) get_post_meta($id, '_yoast_wpseo_focuskw', true));
    $tit_ex = trim((string) get_post_meta($id, '_yoast_wpseo_title', true));
    $des_ex = trim((string) get_post_meta($id, '_yoast_wpseo_metadesc', true));
    // Un texte écrit à la main vaut mieux que le nôtre : on ne l'écrase jamais.
    if ((!$auto_cle && $cle_ex !== '') || (!$auto_txt && ($tit_ex !== '' || $des_ex !== ''))) {
        $respectes++; $lignes[] = "$id : texte manuel présent, respecté"; continue;
    }
    $lignes[] = $id . ' ' . pll_get_post_language($id) . " [" . mb_strlen($t['titre']) . "] " . $t['titre']
              . "\n        clé « " . $t['cle'] . " »\n        [" . mb_strlen($t['desc']) . "] " . $t['desc'];
    if ($APPLIQUER) {
        if ($cle_ex !== '') { update_post_meta($id, 'cs_cle_avant', $cle_ex); }
        if ($tit_ex !== '') { update_post_meta($id, 'cs_titre_avant', $tit_ex); }
        if ($des_ex !== '') { update_post_meta($id, 'cs_desc_avant', $des_ex); }
        update_post_meta($id, '_yoast_wpseo_focuskw', $t['cle']);
        update_post_meta($id, '_yoast_wpseo_title', $t['titre']);
        update_post_meta($id, '_yoast_wpseo_metadesc', $t['desc']);
        update_post_meta($id, 'cs_cle_auto', '1');
        update_post_meta($id, 'cs_texte_auto', '1');
        $ecrits++;
    }
}

// RECOMPTE en base après écriture, jamais la longueur d'une liste (règle 6).
$sans_cle = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->posts} p
      WHERE p.post_type = 'post' AND p.post_status = 'publish'
        AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} m WHERE m.post_id = p.ID
                        AND m.meta_key = '_yoast_wpseo_focuskw' AND m.meta_value <> '')");
$sans_desc = (int) $wpdb->get_var(
    "SELECT COUNT(*) FROM {$wpdb->posts} p
      WHERE p.post_type = 'post' AND p.post_status = 'publish'
        AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} m WHERE m.post_id = p.ID
                        AND m.meta_key = '_yoast_wpseo_metadesc' AND m.meta_value <> '')");

return array(
    '_mode'                         => $EFFACER ? 'EFFACEMENT' : ($APPLIQUER ? 'ÉCRITURE' : 'dry-run — rien écrit'),
    'articles_vises'                => count($ARTICLES),
    'ecrits'                        => $ecrits,
    'effaces'                       => $effaces,
    'textes_manuels_respectes'      => $respectes,
    'absents'                       => $absents,
    'RECOMPTE_articles_sans_cle'    => $sans_cle,
    'RECOMPTE_articles_sans_desc'   => $sans_desc,
    'detail'                        => $lignes,
);
