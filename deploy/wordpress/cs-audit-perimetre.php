<?php
/*
Plugin Name: Agenda Sabauda — Périmètre des audits (règle 5)
Description: Ne garde, dans les RAPPORTS des audits quotidiens, que ce sur quoi
  un geste est encore possible : les événements à venir, ceux en cours, ceux
  dont la date manque. Ce qui est passé ou à la corbeille est écarté du
  message — jamais de la base.

  ── POURQUOI ────────────────────────────────────────────────────────────────
  Le 2026-08-17, les trois audits d'événements (Code Snippets #130 doctrine,
  #135 et #136 garde-fous) ont signalé 25 fiches. Vérifié une par une :
  12 étaient PASSÉES — six depuis juillet, une depuis le 9 juillet — et 3
  étaient à la corbeille. Aucune de leurs requêtes ne filtrait les dates ;
  elles balayaient tout `publish` + `draft` depuis toujours.

  C'est le compteur du 2026-08-11 qui recommence, celui que Franck a renvoyé
  d'un « 548 tâches ! c'est ingérable » : la moitié des lignes désignait un
  travail qui ne sert personne, et cette moitié CACHAIT l'autre. Réparer une
  fiche dont l'événement a eu lieu ne rend service à personne — elle ne sera
  pas republiée, plus aucun visiteur ne la cherche. Mais « vocabulaire
  proscrit » sur une fiche encore en ligne le 5 septembre mérite un geste.

  ── CE QUE CE FICHIER FAIT, ET CE QU'IL NE FAIT PAS ─────────────────────────
  Il filtre le RAPPORT, pas la base : les audits continuent d'enregistrer leurs
  résultats complets dans leurs options (`cs_doctrine_audit`, `cs_gardefous_dates`,
  `cs_gardefous2`). Écarter le passé d'un message, oui ; le supprimer d'une base
  sur ce seul motif, non — une mauvaise fusion peut avoir corrompu la date
  (WP#6798 portait celle d'un autre événement).

  Trois précautions tirées de la règle 5 :
  • c'est la date de FIN qui décide, jamais la date de début seule — une
    exposition de mai à septembre compte tout l'été ;
  • une fiche SANS DATE n'est PAS un événement passé : c'est une donnée
    manquante, elle est GARDÉE (et comptée à part) ;
  • ce qui n'est pas un événement (un guide, une page) n'a pas de date de fin :
    c'est gardé aussi. La fraîcheur des guides est le sujet de l'audit #138,
    qui a ses propres règles et ne passe pas par ici.

  ── LE COMPTEUR DIT SON PÉRIMÈTRE ───────────────────────────────────────────
  `cs_audit_mention_ecartes()` rend la phrase à coller sous un rapport. Elle est
  OBLIGATOIRE dès qu'une ligne a été écartée : un nombre qui a rétréci sans dire
  pourquoi est un nombre qu'on croira faux, et un « 0 » doit pouvoir se
  distinguer d'un audit qui n'a rien examiné (règle 6).

INSTALLATION : déposer dans wp-content/mu-plugins/. Rollback : supprimer — les
  audits retrouvent alors leur comportement d'avant (ils testent l'existence de
  ces fonctions avant de les appeler).
*/

if (!defined('ABSPATH')) { exit; }

/**
 * Trie une liste d'identifiants selon la règle 5.
 *
 * @param int[] $ids
 * @return array{gardes: int[], passes: int, corbeille: int, sans_date: int, introuvables: int}
 */
function cs_audit_devant_nous(array $ids): array {
    $aujourdhui = current_time('Y-m-d');
    $gardes = [];
    $passes = 0;
    $corbeille = 0;
    $sans_date = 0;
    $introuvables = 0;

    foreach ($ids as $id) {
        $id = (int) $id;
        $post = $id ? get_post($id) : null;
        if (!$post) { $introuvables++; continue; }
        if (in_array($post->post_status, ['trash', 'auto-draft'], true)) {
            $corbeille++;
            continue;
        }
        if ($post->post_type !== 'tribe_events') {
            // Guide, page, fiche lieu : pas de date de fin, donc rien à conclure.
            $gardes[] = $id;
            continue;
        }
        // La FIN décide. À défaut de fin, le début. Jamais l'inverse.
        $fin = (string) get_post_meta($id, '_EventEndDate', true);
        if (trim($fin) === '') { $fin = (string) get_post_meta($id, '_EventStartDate', true); }
        $fin = substr(trim($fin), 0, 10);
        if ($fin === '') {
            // Donnée manquante, pas événement terminé : on garde (règle 5).
            $sans_date++;
            $gardes[] = $id;
            continue;
        }
        if ($fin < $aujourdhui) { $passes++; continue; }
        $gardes[] = $id;
    }

    return ['gardes' => $gardes, 'passes' => $passes, 'corbeille' => $corbeille,
            'sans_date' => $sans_date, 'introuvables' => $introuvables];
}

/** Raccourci : la liste filtrée seule, quand le détail ne sert pas. */
function cs_audit_filtrer(array $ids): array {
    return cs_audit_devant_nous($ids)['gardes'];
}

/**
 * Paires de fiches lieu (« 47/62 ») : un lieu n'a pas de date. On garde la paire
 * si AU MOINS UN des deux lieux est encore utilisé par un événement à venir —
 * sinon la ville fausse n'est plus affichée à personne.
 *
 * @param string[] $paires  au format "47/62"
 * @return array{gardes: string[], ecartes: int}
 */
function cs_audit_lieux_actifs(array $paires): array {
    global $wpdb;
    if (!$paires) { return ['gardes' => [], 'ecartes' => 0]; }
    $aujourdhui = current_time('Y-m-d');
    $actifs = $wpdb->get_col($wpdb->prepare(
        "SELECT DISTINCT v.meta_value + 0 FROM {$wpdb->postmeta} v
         JOIN {$wpdb->posts} p ON p.ID = v.post_id
         JOIN {$wpdb->postmeta} f ON f.post_id = p.ID AND f.meta_key = '_EventEndDate'
         WHERE v.meta_key = '_EventVenueID'
           AND p.post_type = 'tribe_events'
           AND p.post_status IN ('publish', 'draft')
           AND SUBSTRING(f.meta_value, 1, 10) >= %s",
        $aujourdhui
    ));
    $actifs = array_map('intval', (array) $actifs);
    $gardes = [];
    foreach ($paires as $paire) {
        $deux = array_map('intval', explode('/', (string) $paire));
        foreach ($deux as $lieu) {
            if (in_array($lieu, $actifs, true)) { $gardes[] = $paire; continue 2; }
        }
    }
    return ['gardes' => $gardes, 'ecartes' => count($paires) - count($gardes)];
}

/**
 * La phrase de périmètre à coller sous un rapport. Chaîne vide si rien n'a été
 * écarté — dans ce cas le rapport parle déjà de tout ce qui existe.
 *
 * @param array $stats  cumul des retours de cs_audit_devant_nous()
 */
function cs_audit_mention_ecartes(array $stats): string {
    $bouts = [];
    if (!empty($stats['passes']))       { $bouts[] = $stats['passes'] . ' passe(s)'; }
    if (!empty($stats['corbeille']))    { $bouts[] = $stats['corbeille'] . ' a la corbeille'; }
    if (!empty($stats['introuvables'])) { $bouts[] = $stats['introuvables'] . ' introuvable(s)'; }
    if (!$bouts) { return ''; }
    $mention = '_Perimetre : evenements encore devant nous. '
        . implode(', ', $bouts) . ' ecarte(s) du rapport (toujours en base)._';
    if (!empty($stats['sans_date'])) {
        $mention .= chr(10) . '_Dont ' . $stats['sans_date']
            . ' fiche(s) sans date, gardee(s) : donnee manquante, pas evenement termine._';
    }
    return $mention;
}

/** Additionne plusieurs retours de cs_audit_devant_nous(). */
function cs_audit_cumuler(array ...$stats): array {
    $total = ['passes' => 0, 'corbeille' => 0, 'sans_date' => 0, 'introuvables' => 0];
    foreach ($stats as $s) {
        foreach (array_keys($total) as $k) { $total[$k] += (int) ($s[$k] ?? 0); }
    }
    return $total;
}
