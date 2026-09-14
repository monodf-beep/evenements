<?php
/**
 * Expression clé Yoast des pages de GABARIT — dry-run par défaut, ne change rien.
 *
 * À exécuter par le canal Novamira, jamais installé comme mu-plugin.
 *
 * POURQUOI — mesuré le 2026-09-15 : 306 pages publiées, **50 seulement** portent une
 * expression clé. Franck, capture du back-office de l'accueil à l'appui : « la page
 * d'accueil et de manière générale les pages ont un SEO très mauvais ». Les dix points
 * rouges qu'il voyait disent tous la même chose — « aucune expression clé principale n'a
 * été définie ». Sans elle Yoast n'a rien à analyser : ce n'est pas un défaut de
 * rédaction, c'est un champ vide.
 *
 * Les FICHES (tribe_events) ne sont PAS concernées : `scripts/seo_batch.py` s'en occupe
 * tous les jours (cap 25 depuis le 09/09) et `scripts/recale_cles_seo.py` recale les
 * anciennes. Les PAGES, elles, n'ont jamais été traitées par personne — c'est un trou
 * distinct, pas un doublon de ce travail-là.
 *
 * PÉRIMÈTRE, ET POURQUOI IL S'ARRÊTE LÀ. Ce fichier ne touche QUE les pages dont le titre
 * commence par « Que faire » ou « Cosa fare » : 193 pages, un gabarit lieu × période ×
 * langue (« Que faire à Aix-les-Bains ce week-end ? », « Cosa fare ad Asti oggi? »). Pour
 * celles-là l'expression clé EST le titre, au point d'interrogation près — c'est
 * littéralement ce qu'un visiteur tape. Aucune rédaction, aucun jugement, aucun LLM.
 *
 * Les 63 AUTRES pages sans clé ne sont pas ici, et c'est délibéré (règle 6 : une file ne
 * doit contenir que ce qu'on peut faire) :
 *
 *   • une douzaine sont des pages légales ou utilitaires — mentions légales, politique
 *     de cookies, confidentialité, crédits photos, plan du site, recherche, et leurs
 *     jumelles italiennes. Leur bon réglage SEO est `noindex`, PAS une expression clé :
 *     leur donner une clé les ferait concourir pour des requêtes qu'on ne veut pas ;
 *   • une cinquantaine sont de vraies pages éditoriales — l'accueil, les hubs de
 *     territoire (« Savoie », « Piémont », « Comté de Nice »…), les hubs de ville
 *     (« Chamonix », « Monferrato »…), « À propos », « Infos utiles », « Où manger ».
 *     Leur titre ne dit pas la requête : « Savoie » n'est pas ce qu'on tape. Il faut
 *     ÉCRIRE leur clé, donc appliquer la doctrine éditoriale (voix + vocabulaire
 *     Obsidian, cf. CLAUDE.md et .claude/skills/redaction-agenda-sabauda).
 *
 * CE QU'IL NE FAIT PAS ENCORE. Il pose l'expression clé, pas le titre SEO ni la
 * méta-description — ces deux-là sont du texte LU par un humain dans Google, donc de la
 * rédaction, donc soumis à la doctrine. Les écrire sans elle serait exactement la faute
 * que Franck signale depuis le 06/09. Deuxième passe, une fois la voix récupérée.
 *
 * Conséquence honnête sur le résultat : poser la clé éteint le point « aucune expression
 * clé définie » et débloque l'analyse, elle ne rend pas la page verte à elle seule — les
 * contrôles « clé dans le titre SEO », « dans la méta description », « dans
 * l'introduction » resteront rouges tant que la deuxième passe n'a pas eu lieu.
 *
 * RÉVERSIBLE : la clé est une méta. `$EFFACER = true` la retire des pages que ce script
 * a posées (elles seules — on ne touche jamais aux 50 déjà pourvues).
 */

global $wpdb;

$APPLIQUER = false;   // ← passer à true pour écrire
$EFFACER   = false;   // ← retire ce que ce script a posé (marqueur cs_cle_auto)

$pages = $wpdb->get_results(
    "SELECT p.ID, p.post_title, COALESCE(y.meta_value,'') kw
       FROM {$wpdb->posts} p
       LEFT JOIN {$wpdb->postmeta} y ON y.post_id = p.ID AND y.meta_key = '_yoast_wpseo_focuskw'
      WHERE p.post_type = 'page' AND p.post_status = 'publish'
      ORDER BY p.ID", ARRAY_A);

$prevus = array(); $ignores_deja = 0; $hors_gabarit = 0; $ecrits = 0; $effaces = 0;

foreach ($pages as $p) {
    $titre = trim($p['post_title']);

    // Gabarit seulement — tout le reste demande une clé ÉCRITE (cf. en-tête).
    if (!preg_match('/^(Que faire|Cosa fare)\b/u', $titre)) { $hors_gabarit++; continue; }

    // Jamais écraser une clé posée à la main : elle vaut mieux que la nôtre.
    $auto = get_post_meta($p['ID'], 'cs_cle_auto', true);
    if (trim($p['kw']) !== '' && !$auto) { $ignores_deja++; continue; }

    if ($EFFACER) {
        if ($auto) {
            delete_post_meta($p['ID'], '_yoast_wpseo_focuskw');
            delete_post_meta($p['ID'], 'cs_cle_auto');
            $effaces++;
        }
        continue;
    }

    // L'expression clé, c'est le titre sans sa ponctuation finale. L'espace insécable
    // français devant « ? » compte comme un espace : sans ce nettoyage la clé traînerait
    // un blanc que Yoast ne retrouverait dans aucun texte.
    $cle = preg_replace('/\s*[?!]+\s*$/u', '', $titre);
    $cle = trim(preg_replace('/\x{00A0}|\x{202F}/u', ' ', $cle));
    $cle = trim(preg_replace('/\s+/u', ' ', $cle));
    if ($cle === '') { continue; }

    if (count($prevus) < 15) { $prevus[] = $p['ID'] . ' | ' . $titre . '  →  ' . $cle; }

    if ($APPLIQUER) {
        update_post_meta($p['ID'], '_yoast_wpseo_focuskw', $cle);
        update_post_meta($p['ID'], 'cs_cle_auto', '1');
        $ecrits++;
    }
}

// RECOMPTE APRÈS écriture, jamais la longueur d'une liste (règle 6).
$avec = (int) $wpdb->get_var(
    "SELECT COUNT(DISTINCT p.ID) FROM {$wpdb->posts} p
       JOIN {$wpdb->postmeta} m ON m.post_id = p.ID
            AND m.meta_key = '_yoast_wpseo_focuskw' AND m.meta_value <> ''
      WHERE p.post_type = 'page' AND p.post_status = 'publish'");

return array(
    '_mode'                     => $EFFACER ? 'EFFACEMENT' : ($APPLIQUER ? 'ÉCRITURE' : 'dry-run — rien écrit'),
    'pages_publiees'            => count($pages),
    'hors_gabarit_non_touchees' => $hors_gabarit,
    'deja_pourvues_respectees'  => $ignores_deja,
    'a_poser'                   => count($pages) - $hors_gabarit - $ignores_deja,
    'ecrites'                   => $ecrits,
    'effacees'                  => $effaces,
    'RECOMPTE_pages_avec_cle'   => $avec,
    'exemples'                  => $prevus,
);
