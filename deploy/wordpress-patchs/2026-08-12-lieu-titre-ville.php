<?php
/*
CORRECTIF UNIQUE — snippet Code Snippets n° 6 « CS Publish — Endpoint TEC (cs/v1/event) ».

POURQUOI UN FICHIER À PART, ET PAS UN DÉPLOIEMENT NORMAL. `cs-publish.php` n'est pas un
fichier sur le serveur : il est collé dans Code Snippets, en base (`wp_snippets`), et
aucun dépôt de fichier ne l'atteint — voir docs/DEPLOIEMENT_WORDPRESS.md. On a passé la
matinée du 2026-08-12 à réparer un transport SFTP/FTPS pour livrer un fichier que
WordPress n'exécute pas.

CE QU'IL CORRIGE. La fiche lieu de WordPress est retrouvée par son TITRE SEUL
(`get_page_by_title`). Toutes les « Salle des Fêtes » de la région tombent donc sur une
seule fiche, avec une seule ville : constaté sur deux fiches EN LIGNE, Margencel (926) et
Draillant (925). L'une des deux communes affiche celle de l'autre. Et une fiche lieu créée
avec une ville fausse le restait pour toujours — cas réel, `_VenueCity = Aosta` pour le
Forte di Bard, qui est à Bard.

COMMENT LE LANCER — par Novamira (`novamira/execute-php`), en collant TOUT le code
ci-dessous SANS la ligne « <?php ». Il est IDEMPOTENT : relancé, il constate que c'est
déjà fait et ne touche à rien.

CE QU'IL FAIT AVANT D'ÉCRIRE, dans cet ordre, et il s'arrête au premier refus :
  1. sauvegarde l'état actuel dans l'option `cs_publish_backup_20260812` (règle 4 : le
     filet d'abord). Retour arrière en une requête, écrite en bas de ce fichier ;
  2. vérifie que CHACUN des quatre remplacements trouve son ancre exactement une fois —
     zéro ou deux, on n'écrit pas. Un correctif qui s'applique « à peu près » sur un
     endpoint de publication est pire que pas de correctif ;
  3. passe le résultat à `token_get_all(..., TOKEN_PARSE)`, qui lève une ParseError sur un
     code invalide. C'est un vrai `php -l`, exécutable là où il n'y a pas de binaire php.
     Le site est resté injoignable deux jours le 2026-08-08 pour un « === » : ce contrôle
     est le seul moment où l'erreur coûte encore zéro ;
  4. seulement alors, écrit — puis RELIT la ligne en base et compare son empreinte à celle
     du code voulu. On rapporte ce qui s'est produit, pas ce qu'on a demandé (règle 6).

VÉRIFICATION APRÈS COUP, depuis n'importe où :
    curl -s https://agendasabauda.eu/wp-json/cs/v1/version
Tant que ça répond 404, le correctif n'est pas passé.
*/

global $wpdb;
$table = $wpdb->prefix . 'snippets';
$avant = $wpdb->get_var("SELECT code FROM $table WHERE id = 6");

if ($avant === null) {
    return ['erreur' => 'Snippet 6 introuvable. Vérifier son identifiant avant tout.'];
}
if (strpos($avant, 'CS_PUBLISH_VERSION') !== false) {
    return ['deja_applique' => true,
            'note' => 'Le correctif est déjà en place. Rien touché.',
            'octets' => strlen($avant)];
}

// ── 1. Le filet ────────────────────────────────────────────────────────────────────
update_option('cs_publish_backup_20260812', $avant, false);
if (get_option('cs_publish_backup_20260812') !== $avant) {
    return ['erreur' => 'La sauvegarde ne se relit pas identique — on n\'écrit rien.'];
}

// ── 2. Les quatre remplacements ────────────────────────────────────────────────────
$ancre_entete = "if (!defined('ABSPATH')) { exit; }";

$entete = <<<'CSPATCH'
// UN FICHIER SUR LE DISQUE NE PROUVE RIEN SUR CE QUE WORDPRESS EXÉCUTE — c'est la règle 1
// appliquée au code plutôt qu'aux fiches. Le 2026-08-12, un correctif a été « déployé »
// sans jamais partir : push-wordpress.sh avait un fichier par défaut et personne ne
// pouvait le savoir depuis le VPS. D'où cette route, publique et en lecture seule, qui
// répond ce que la version EN LIGNE dit d'elle-même :
//     curl -s https://agendasabauda.eu/wp-json/cs/v1/version
// À incrémenter (la date suffit) quand ce fichier change de comportement.
define('CS_PUBLISH_VERSION', '2026-08-12 — fiche lieu retrouvée par titre ET ville');

add_action('rest_api_init', function () {
    register_rest_route('cs/v1', '/version', array(
        'methods'             => 'GET',
        'callback'            => function () {
            return array('cs_publish' => CS_PUBLISH_VERSION);
        },
        'permission_callback' => '__return_true',
    ));
});

/**
 * Retrouve une fiche lieu (tribe_venue) par son TITRE EXACT + une condition sur sa ville.
 *
 * WordPress n'offre pas de recherche « titre + méta » toute faite : get_page_by_title()
 * ignore les métas, et WP_Query['title'] ne comparait pas le titre exact avant WP 5.7.
 * D'où ce petit intermédiaire, écrit une fois plutôt que recopié deux.
 */
function cs_trouver_venue($titre, $meta_query) {
    $q = new WP_Query(array(
        'post_type'              => 'tribe_venue',
        'post_status'            => 'any',
        'posts_per_page'         => 1,
        'title'                  => $titre,
        'meta_query'             => $meta_query,
        'no_found_rows'          => true,
        'ignore_sticky_posts'    => true,
        'update_post_term_cache' => false,
    ));
    return !empty($q->posts) ? $q->posts[0] : null;
}
CSPATCH;

$ancien_init = "    \$venue_id = 0;\n    \$venue = \$b['venue'] ?? null;";
$nouveau_init = "    \$venue_id = 0;\n    \$venue_city_fixed = '';\n    \$venue = \$b['venue'] ?? null;";

$ancien_lieu = <<<'CSPATCH'
        $existing = get_page_by_title($venue['Venue'], OBJECT, 'tribe_venue');
        if ($existing) {
            $venue_id = (int) $existing->ID;
        } elseif (function_exists('tribe_create_venue')) {
CSPATCH;

$nouveau_lieu = <<<'CSPATCH'
        $existing = null;
        $ville_cherchee = isset($venue['City']) ? trim((string) $venue['City']) : '';
        if ($ville_cherchee !== '') {
            // 1) MÊME NOM, MÊME VILLE — c'est le même lieu, sans discussion.
            $existing = cs_trouver_venue($venue['Venue'], array(array(
                'key' => '_VenueCity', 'value' => $ville_cherchee, 'compare' => '=',
            )));
            // 2) sinon MÊME NOM, VILLE ABSENTE — les fiches lieu créées avant ce
            //    correctif n'ont souvent pas de ville. On les ADOPTE et le bloc ci-dessous
            //    les remplit, plutôt que d'en créer un double à côté. Sans cette étape, le
            //    premier `publisher_as --update` après déploiement aurait dupliqué chaque
            //    lieu du site : on aurait remplacé une fusion abusive par une
            //    prolifération, ce qui n'est pas un progrès.
            if (!$existing) {
                $existing = cs_trouver_venue($venue['Venue'], array(
                    'relation' => 'OR',
                    array('key' => '_VenueCity', 'value' => '', 'compare' => '='),
                    array('key' => '_VenueCity', 'compare' => 'NOT EXISTS'),
                ));
            }
            // 3) et RIEN D'AUTRE. Un lieu du même nom dans une AUTRE ville est un autre
            //    lieu : on en crée un nouveau. C'est tout l'objet du correctif — sans ce
            //    refus de se rabattre sur le titre seul, la salle des fêtes de Draillant
            //    continuerait de pointer sur celle de Margencel.
        } else {
            // Pas de ville de notre côté : on ne peut que retomber sur le titre. Créer une
            // fiche lieu de plus à chaque publication sans ville serait pire que la fusion.
            $existing = get_page_by_title($venue['Venue'], OBJECT, 'tribe_venue');
        }
        if ($existing) {
            $venue_id = (int) $existing->ID;
            // UNE FICHE LIEU CRÉÉE FAUSSE LE RESTAIT POUR TOUJOURS. On réutilisait le
            // post existant sans jamais regarder sa ville : chaque nouvel événement au
            // même endroit héritait de l'erreur, et rien dans la chaîne ne pouvait la
            // défaire. C'est un état terminal sans rouvreur (règle 3), et il a produit un
            // cas réel — fiche lieu 208, `_VenueCity = Aosta` pour le Forte di Bard, qui
            // est à Bard, cinquante kilomètres plus bas ; trois événements l'affichaient.
            //
            // DEUX CAS SEULEMENT, et la distinction est tout le sujet :
            //   • la ville du lieu est VIDE → on la remplit, on n'écrase rien ;
            //   • elle est renseignée et DIFFÈRE → on ne touche que si l'appelant nous
            //     dit tenir un fait qui fait autorité (`CityAuthoritative`, posé par
            //     publisher_as quand la ville vient du registre : note de savoir ou
            //     arbitrage consigné). Sans cette condition, deux événements en désaccord
            //     se réécriraient l'un l'autre à chaque publication — le dernier poussé
            //     gagnerait, ce qui n'est pas une règle, c'est un tirage au sort.
            $city = isset($venue['City']) ? trim((string) $venue['City']) : '';
            if ($city !== '') {
                $actuelle = trim((string) get_post_meta($venue_id, '_VenueCity', true));
                $autorite = !empty($venue['CityAuthoritative']);
                if ($actuelle === '' || ($autorite && strcasecmp($actuelle, $city) !== 0)) {
                    update_post_meta($venue_id, '_VenueCity', sanitize_text_field($city));
                    // Rendu dans la réponse : sans ça la correction serait muette, et on
                    // la découvrirait des semaines plus tard (règle 6).
                    $venue_city_fixed = ($actuelle === '' ? '(vide)' : $actuelle) . ' → ' . $city;
                }
            }
        } elseif (function_exists('tribe_create_venue')) {
CSPATCH;

$ancienne_reponse = "        'venue'   => \$venue_id ?: 0,\n    ), 200);";
$nouvelle_reponse = "        'venue'   => \$venue_id ?: 0,\n        'venue_city_fixed' => \$venue_city_fixed,\n    ), 200);";

$operations = array(
    array('quoi' => 'entete (version + helper)', 'de' => $ancre_entete,
          'vers' => $ancre_entete . "\n\n" . $entete),
    array('quoi' => 'init $venue_city_fixed',    'de' => $ancien_init,     'vers' => $nouveau_init),
    array('quoi' => 'recherche du lieu',         'de' => $ancien_lieu,     'vers' => $nouveau_lieu),
    array('quoi' => 'reponse REST',              'de' => $ancienne_reponse,'vers' => $nouvelle_reponse),
    // AJOUTÉ DANS LE MÊME CORRECTIF, pour ne pas refaire un aller-retour vers WordPress :
    // le méta qui porte le MOTIF du panel. Jusqu'ici le site affichait un verdict de
    // relecture sans jamais dire sur quoi il portait — au point qu'une session a conclu
    // de ce silence que les motifs n'existaient pas. Ils existaient, dans enrich_data ;
    // la liste $allowed ci-dessous ne les laissait simplement pas passer.
    array('quoi' => 'meta as_panel_motif',
          'de'   => "        'as_panel_revision', 'as_affiches', 'as_placement',",
          'vers' => "        'as_panel_revision', 'as_affiches', 'as_placement',\n"
                  . "        'as_panel_motif',"),
);

$code = $avant;
$journal = array();
foreach ($operations as $op) {
    // UNE ANCRE, EXACTEMENT UNE FOIS. Zéro = le fichier a changé sous nos pieds ; deux =
    // on ne sait pas laquelle on modifie. Dans les deux cas on renonce plutôt que de
    // deviner : c'est l'endpoint qui publie tout le site.
    $n = substr_count($code, $op['de']);
    $journal[$op['quoi']] = $n . ' occurrence(s)';
    if ($n !== 1) {
        return array('erreur' => 'Ancre « ' . $op['quoi'] . ' » trouvée ' . $n .
                                 ' fois au lieu de 1. RIEN n\'a été écrit.',
                     'journal' => $journal);
    }
    $code = str_replace($op['de'], $op['vers'], $code);
}

// ── 3. Le php -l du pauvre, et il est vrai ─────────────────────────────────────────
try {
    token_get_all('<?php ' . $code, TOKEN_PARSE);
} catch (ParseError $e) {
    return array('erreur' => 'Syntaxe PHP invalide : ' . $e->getMessage() .
                             ' — RIEN n\'a été écrit.',
                 'journal' => $journal);
}

// ── 4. Écrire, puis RELIRE ─────────────────────────────────────────────────────────
$wpdb->update($table, array('code' => $code), array('id' => 6));
$relu = $wpdb->get_var("SELECT code FROM $table WHERE id = 6");

return array(
    'journal'          => $journal,
    'ecrit'            => ($relu === $code),
    'octets_avant'     => strlen($avant),
    'octets_apres'     => strlen($relu),
    'sha1_apres'       => sha1($relu),
    'sauvegarde'       => 'option cs_publish_backup_20260812 (sha1 ' . sha1($avant) . ')',
    'a_verifier'       => 'curl -s https://agendasabauda.eu/wp-json/cs/v1/version',
);

/*
RETOUR ARRIÈRE — une requête, à coller dans novamira/execute-php :

    global $wpdb;
    $wpdb->update($wpdb->prefix . 'snippets',
                  array('code' => get_option('cs_publish_backup_20260812')),
                  array('id' => 6));
    return sha1(get_option('cs_publish_backup_20260812'));   // bfda649c28dc5d58871751d42f2c29fc48ff644d

La sauvegarde reste en base : on ne la supprime pas « pour faire propre ». Une option de
16 Ko ne coûte rien, et c'est la seule copie de ce qui tournait avant.
*/
