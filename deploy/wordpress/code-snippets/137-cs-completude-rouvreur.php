// CS · Complétude — LE ROUVREUR (2026-09-06)
//
// cs-completude.php (mu-plugin) dépublie une fiche incomplète et écrit
// as_completude_refus. Rien, nulle part, ne la réexaminait ensuite : ni le cron
// (cs_completude_passe ne requête que post_status='publish'), ni le garde-fou lui-même
// (il ne se déclenche que sur transition_post_status VERS publish, ce qui n'arrive plus
// jamais pour une fiche garée). La fiche sortait donc de TOUTES les files, y compris de
// celles censées signaler qu'il reste du travail.
//
// C'est la règle 3 du CLAUDE.md dans sa forme la plus pure : un état terminal sans
// personne pour le rouvrir.
//
// POURQUOI LE PROCHAIN PASSAGE DONNE UN AUTRE RÉSULTAT — l'exigence de la règle 3, à
// laquelle il faut répondre par une mesure et non par « le pipeline finira bien par ».
// Mesure du 2026-09-06 : la fiche #8088 (championnat d'Europe de canoë à Ivrea, le
// 23 septembre) a été refusée le 02/09 pour source_officielle manquante. Au 06/09 son
// as_source_officielle_url pointe sur turismotorino.org et as_verifie_le vaut le jour
// même. L'enrichissement a donc fait son travail APRÈS le refus, et la fiche est restée
// hors ligne pour rien pendant quatre jours. Le contrôle relit des données qui ont
// changé, pas les mêmes.
//
// PAS DE VA-ET-VIENT POSSIBLE : on republie uniquement quand cs_completude_controler ne
// renvoie plus aucun bloquant, donc quand le garde-fou lui-même n'aurait plus de raison
// de dépublier. C'est la MÊME fonction, pas une règle parallèle qui pourrait diverger.
// as_completude_rouvertures compte les allers-retours : une fiche qui y revient plusieurs
// fois signale un désaccord entre le portillon et le pipeline, pas un succès.
//
// RÈGLE 5 : on ne rouvre que ce qui est encore devant nous.
//
// POURQUOI UN SNIPPET ET PAS UN AJOUT AU MU-PLUGIN — le serveur n'a pas de binaire `php`
// en ligne de commande, donc pas de `php -l` sur place. Une faute de syntaxe dans un
// mu-plugin tue le site ET la porte qui permettrait de le réparer : c'est l'incident du
// 8 au 10 août. Code Snippets, lui, désactive tout seul un snippet fatal. Le code est
// versionné ici, contrôlé par tests/test_php_syntax.py.
//
// Rollback : désactiver ce snippet. Les fiches déjà remises en ligne y restent (le
// garde-fou les redescendrait si elles redevenaient incomplètes).

if (!function_exists('cs_completude_rouvrir')) {
function cs_completude_rouvrir() {
    global $wpdb;

    if (!function_exists('cs_completude_controler')) {
        // Le mu-plugin n'est pas chargé : on ne devine pas le contrat de complétude
        // à sa place, on ne fait rien et on le dit.
        update_option('cs_completude_rouvreur', array(
            'erreur' => 'cs_completude_controler absente', 'le' => current_time('mysql'),
        ), false);
        return false;
    }

    $ids = $wpdb->get_col(
        "SELECT e.ID FROM {$wpdb->posts} e
         JOIN {$wpdb->postmeta} r  ON r.post_id  = e.ID AND r.meta_key = 'as_completude_refus'
                                   AND r.meta_value <> ''
         JOIN {$wpdb->postmeta} sd ON sd.post_id = e.ID AND sd.meta_key = '_EventStartDate'
         LEFT JOIN {$wpdb->postmeta} ed ON ed.post_id = e.ID AND ed.meta_key = '_EventEndDate'
         WHERE e.post_type = 'tribe_events'
           AND e.post_status = 'draft'
           AND COALESCE(NULLIF(ed.meta_value, ''), sd.meta_value) >= NOW()"
    );

    $rouvertes = array();
    $bloquees  = array();
    foreach ($ids as $id) {
        $id = (int) $id;
        $r = cs_completude_controler($id);
        if (!empty($r['bloquants'])) {
            $bloquees[$id] = implode(',', $r['bloquants']);
            continue;
        }
        wp_update_post(array('ID' => $id, 'post_status' => 'publish'));
        delete_post_meta($id, 'as_completude_refus');
        $n = (int) get_post_meta($id, 'as_completude_rouvertures', true);
        update_post_meta($id, 'as_completude_rouvertures', $n + 1);
        update_post_meta($id, 'as_completude_rouvert_le', current_time('mysql'));
        $rouvertes[] = $id;
    }

    // Règle 6 : un zéro doit dire combien de cas se sont présentés. « 0 rouverte » sur
    // 12 garées et « 0 rouverte » sur 0 garée ne veulent pas dire la même chose.
    $releve = array(
        'garees'    => count($ids),
        'rouvertes' => $rouvertes,
        'bloquees'  => $bloquees,
        'le'        => current_time('mysql'),
    );
    update_option('cs_completude_rouvreur', $releve, false);

    if ($rouvertes && function_exists('cs_slack_notify_form')) {
        $lignes = array();
        foreach ($rouvertes as $id) { $lignes[] = '#' . $id . ' ' . get_the_title($id); }
        cs_slack_notify_form(
            ':recycle: *Fiches remises en ligne* — ' . count($rouvertes) . ' sur '
            . count($ids) . " garée(s) encore à venir\n" . implode("\n", $lignes)
            . "\nLeurs manques bloquants ont été comblés depuis le refus."
        );
    }

    return $releve;
}
}

// Même cron quotidien que la mesure : le refus et sa levée respirent au même rythme.
// Priorité 20 pour passer APRÈS cs_completude_passe, dont le relevé tient alors compte
// des fiches qui viennent d'être remises en ligne.
add_action('cs_completude_event', 'cs_completude_rouvrir', 20);

// Le nombre de fiches garées doit se VOIR quelque part (règle 3 : « où se voit le nombre
// de fiches garées ? »). On l'expose à côté de la file de complétude existante.
add_action('rest_api_init', function () {
    register_rest_route('cultura/v1', '/completude-rouvreur', array(
        'methods'  => 'GET',
        'permission_callback' => function () { return current_user_can('edit_posts'); },
        'callback' => function () {
            $releve = (array) get_option('cs_completude_rouvreur', array());
            $releve['dernier_passage'] = isset($releve['le']) ? $releve['le'] : 'jamais';
            return rest_ensure_response($releve);
        },
    ));
});
