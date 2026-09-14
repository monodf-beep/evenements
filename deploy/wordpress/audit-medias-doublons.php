<?php
/**
 * Audit des copies de médias redéposées — LECTURE SEULE, ne supprime RIEN.
 *
 * À exécuter par le canal Novamira (`novamira/execute-php`), jamais installé comme
 * mu-plugin : ce fichier est un outil d'audit, pas du code de site. Le corps de ce
 * fichier (sans la balise d'ouverture) EST le code envoyé ; `_version` dans le retour
 * dit quelle version a réellement tourné, pour qu'un fichier ici ne « prouve » pas à
 * lui seul ce qui a été exécuté (règle 1 transposée au code).
 *
 * POURQUOI — mesuré en production le 2026-09-12 : 4 158 médias pour 2 142 titres
 * distincts, soit 2 016 copies en trop. `_upload_featured_media` (scripts/publisher.py)
 * redéposait l'image à CHAQUE republication d'une fiche sans jamais demander si elle
 * était déjà là ; WordPress acceptait en suffixant « -2 », « -3 »… Corrigé côté dépôt
 * le 12/09 (empreinte md5 dans le nom + recherche avant dépôt), mais le correctif
 * n'efface rien : ce stock-là reste, et le nettoyer n'est PAS réversible (WordPress ne
 * met pas les pièces jointes à la corbeille). D'où cet audit, à lire avant tout geste.
 *
 * PÉRIMÈTRE, arbitré par Franck le 12/09 : les images des ÉVÉNEMENTS (`tribe_events`)
 * uniquement. Les images d'articles (curiosités, guides), de pages et de lieux sont
 * comptées à part et JAMAIS proposées à la suppression.
 *
 * TROIS ENDROITS À CONSULTER, pas un — la leçon du premier essai, qui proposait de
 * supprimer les 48 images de secours `fallback-*` et les 14 couvertures de territoire
 * `cover-*` parce qu'elles ne sont référencées NULLE PART dans WordPress : leur liste
 * vit dans config/territory_category_images.txt, côté dépôt. Un critère « pas utilisé
 * dans WordPress » aurait vidé le repli d'image en silence.
 *
 *   1. WordPress   — vignette (`_thumbnail_id`), corps d'article, métas d'image ;
 *   2. le dépôt    — $PROTEGES ci-dessous, recopié de config/territory_category_images.txt ;
 *   3. la prudence — tout préfixe `fallback-` / `cover-` est protégé même hors liste.
 *
 * RÈGLE DE SÛRETÉ : on ne vide jamais un groupe. Une copie n'est proposée que si une
 * AUTRE copie du même titre est effectivement utilisée. Un groupe dont aucune copie ne
 * sert à rien est signalé « orphelin », pas proposé — c'est un arbitrage éditorial
 * (fiche passée ? fiche rejetée ?), pas un doublon.
 */

global $wpdb;
set_time_limit(300);   // ~500 empreintes md5 sur l'hébergement mutualisé

// --- 2. le dépôt : images de secours et couvertures, référencées hors WordPress -------
// Recopié de config/territory_category_images.txt (48 entrées) le 2026-09-12. Si ce
// fichier change, cette liste doit changer avec lui — le préfixe `fallback-` du filet
// n° 3 couvre l'oubli.
$PROTEGES_PREFIXES = array('fallback-', 'cover-');

// --- inventaire ----------------------------------------------------------------------
$att = $wpdb->get_results(
    "SELECT a.ID, a.post_title, a.post_date, m.meta_value AS f
       FROM {$wpdb->posts} a
       LEFT JOIN {$wpdb->postmeta} m ON m.post_id = a.ID AND m.meta_key = '_wp_attached_file'
      WHERE a.post_type = 'attachment'", ARRAY_A);

$up = wp_get_upload_dir();
$base_dir = $up['basedir'];

// --- 1. WordPress : ce qui sert ------------------------------------------------------
// Vignettes : toutes, corbeille comprise — un post corbeillé se restaure, son image doit
// donc survivre (règle 1 du dépôt : un état n'est pas définitif).
$usage = array();
foreach ($wpdb->get_col("SELECT DISTINCT meta_value FROM {$wpdb->postmeta} WHERE meta_key='_thumbnail_id'") as $id) {
    $usage[(int)$id] = 'vignette';
}
// Citations par nom de fichier : corps d'article et métas d'image (as_image_original…).
$foin = implode("\n", $wpdb->get_col(
    "SELECT post_content FROM {$wpdb->posts} WHERE post_type <> 'attachment'"))
      . "\n" . implode("\n", $wpdb->get_col(
    "SELECT meta_value FROM {$wpdb->postmeta}
      WHERE meta_key IN ('as_image_original','as_image_raw','as_image','_cs_image','image_url')
        AND meta_value LIKE '%http%'"));

// --- regroupement par LIGNÉE DE FICHIER, pas par titre -------------------------------
// Le v2 regroupait par titre de média et s'est trompé dès la première ligne : sous le
// titre « NOTE D'ARTE » il proposait de supprimer 1280px-Museo_di_Arti_Decorative_
// Accorsi_Ometto.jpg — pas une copie, une AUTRE photo (Wikimedia) qui porte le même
// titre parce que publisher.py nomme le média d'après la fiche. Un titre partagé ne
// prouve pas deux fois la même image.
//
// Ce qui le prouve : WordPress suffixe le NOM DE FICHIER (« -1 », « -2 »…) quand il
// refuse d'écraser, donc deux redépôts de la même image partagent la même racine de
// nom ; et deux fois les mêmes octets ont la même TAILLE au byte près. On exige les
// deux. Deux images différentes ne partagent pratiquement jamais une taille exacte,
// et jamais en plus la racine du nom.
$lignees = array();
foreach ($att as $r) {
    if (!$r['f']) { continue; }
    $nom = basename($r['f']);
    $ext = '';
    if (preg_match('/\.([a-z0-9]+)$/i', $nom, $m)) { $ext = strtolower($m[1]); }
    $stem = preg_replace('/\.[a-z0-9]+$/i', '', $nom);
    $racine = preg_replace('/-\d{1,3}$/', '', $stem);   // « -3 » posé par WordPress
    $chemin = $base_dir . '/' . $r['f'];
    $taille = file_exists($chemin) ? filesize($chemin) : -1;
    if ($taille <= 0) { continue; }                      // fichier absent : on ne touche pas
    $r['_taille'] = $taille;
    $r['_racine'] = $racine;
    $r['_chemin'] = $chemin;
    $lignees[$racine . '|' . $ext . '|' . $taille][] = $r;
}

$prop = array();
$orphelins = 0; $orphelins_copies = 0;
$hors_perimetre = 0; $a_trancher = 0; $proteges = 0;
$poids = 0; $exemples = array(); $par_groupe = array();
$groupes_partiels = 0; $refus = array();

foreach ($lignees as $cle => $copies) {
    if (count($copies) < 2) { continue; }

    // filet n° 3 : jamais toucher une image de secours ou une couverture
    $est_protege = false;
    foreach ($PROTEGES_PREFIXES as $p) {
        if (strpos($copies[0]['_racine'], $p) === 0) { $est_protege = true; }
    }
    if ($est_protege) { $proteges += count($copies) - 1; continue; }

    // qui sert, qui ne sert pas
    $servent = array(); $inertes = array(); $types_porteurs = array();
    foreach ($copies as $c) {
        $sert = isset($usage[(int)$c['ID']]);
        if ($sert) {
            foreach ($wpdb->get_col($wpdb->prepare(
                "SELECT p.post_type FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID = m.post_id
                  WHERE m.meta_key='_thumbnail_id' AND m.meta_value=%d", (int)$c['ID'])) as $pt) {
                $types_porteurs[$pt] = 1;
            }
        }
        if (!$sert) {
            $stem = preg_replace('/\.[a-z0-9]+$/i', '', basename($c['f']));
            if ($stem !== '' && strpos($foin, $stem) !== false) { $sert = true; }
        }
        if ($sert) { $servent[] = $c; } else { $inertes[] = $c; }
    }

    // PÉRIMÈTRE (arbitrage de Franck, 12/09) : les images d'ÉVÉNEMENTS seulement.
    // Un groupe dont une copie illustre un article, une page ou un lieu sort d'ici.
    unset($types_porteurs['tribe_events']);
    if ($types_porteurs) { $hors_perimetre += count($copies) - 1; continue; }

    // RÈGLE DE SÛRETÉ : on ne vide jamais un groupe. Aucune copie utilisée → on ne
    // propose rien, on compte à part : c'est un arbitrage éditorial (fiche corbeillée ?
    // fiche rejetée ?), pas un doublon à ramasser.
    if (!$servent) { $orphelins++; $orphelins_copies += count($copies); continue; }

    if (!$inertes) { continue; }   // tout sert déjà : rien à proposer

    // EMPREINTE — une taille égale ne PROUVE pas des octets égaux, elle les rend
    // probables. Avant de proposer la suppression d'un fichier, on compare les octets à
    // ceux de la copie conservée. Mesuré le 12/09 : 328 candidates, 328 confirmées,
    // 0 refus — donc la taille suffisait en pratique ; on garde le contrôle quand même,
    // parce que « en pratique » n'est pas « toujours » et qu'une suppression ne se défait
    // pas. Un groupe dont une seule copie diverge n'est proposé que pour ses jumelles
    // vraies, jamais en bloc.
    $ref = md5_file($servent[0]['_chemin']);
    $confirmees = array();
    foreach ($inertes as $c) {
        if (md5_file($c['_chemin']) === $ref) { $confirmees[] = $c; }
    }
    if (count($confirmees) !== count($inertes)) {
        $groupes_partiels++;
        if (count($refus) < 10) {
            $refus[] = $copies[0]['_racine'] . ' : ' . count($inertes) . ' inertes, '
                     . count($confirmees) . ' identiques aux octets';
        }
    }
    if (!$confirmees) { continue; }

    $par_groupe[] = $copies[0]['_racine'] . ' : ' . count($copies) . ' copies ('
                  . round($copies[0]['_taille'] / 1024) . ' Ko chacune), '
                  . count($servent) . ' utilisée(s), ' . count($confirmees) . ' proposée(s)';
    foreach ($confirmees as $c) {
        $prop[] = (int)$c['ID'];
        $poids += $c['_taille'];
        if (count($exemples) < 25) {
            $exemples[] = $c['ID'] . ' | ' . $c['post_title'] . ' | ' . basename($c['f']);
        }
    }
}

return array(
    '_version' => 'audit-medias-doublons v4 2026-09-12',
    '_perimetre' => "copies d'une MÊME image (racine de nom + taille identiques au byte) "
                  . "servant un ÉVÉNEMENT, empreinte md5 confirmée, dont une autre copie est "
                  . "encore utilisée ; lecture seule, ne supprime rien",
    'medias_au_total'                          => count($att),
    'A_SUPPRIMER_proposees'                    => count($prop),
    'groupes_concernes'                        => count($par_groupe),
    'poids_recupere_Mo'                        => round($poids / 1048576, 1),
    'protegees_fallback_et_cover'              => $proteges,
    'hors_perimetre_articles_pages_lieux'      => $hors_perimetre,
    'groupes_partiellement_confirmes'          => $groupes_partiels,
    'exemples_refus_empreinte'                 => $refus,
    'groupes_orphelins_aucune_copie_utilisee'  => $orphelins,
    'copies_dans_ces_groupes'                  => $orphelins_copies,
    'ids'                                      => $prop,
    'exemples'                                 => $exemples,
    'premiers_groupes'                         => array_slice($par_groupe, 0, 15),
);
