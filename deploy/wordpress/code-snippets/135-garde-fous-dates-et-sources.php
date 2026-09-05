if (!function_exists('cs_gardefous_run')) {
function cs_gardefous_run() {
    global $wpdb;
    $rows = $wpdb->get_results("SELECT p.ID, p.post_date, d.meta_value AS deb FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} d ON d.post_id=p.ID AND d.meta_key='_EventStartDate' WHERE p.post_type='tribe_events' AND p.post_status IN ('publish','draft')", ARRAY_A);
    $ant = array(); $sans = array();
    foreach ($rows as $r) {
        if (trim((string) $r['deb']) === '') { $sans[] = (int) $r['ID']; continue; }
        $ec = (strtotime(substr($r['post_date'], 0, 10)) - strtotime(substr($r['deb'], 0, 10))) / 86400;
        if ($ec > 180) { $ant[] = (int) $r['ID']; }
    }
    $src = $wpdb->get_results("SELECT p.ID, m.meta_value AS url, d.meta_value AS deb FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID AND m.meta_key='as_source_officielle_url' AND m.meta_value<>'' JOIN {$wpdb->postmeta} d ON d.post_id=p.ID AND d.meta_key='_EventStartDate' WHERE p.post_type='tribe_events' AND p.post_status='publish'", ARRAY_A);
    $an = array();
    foreach ($src as $r) {
        if (preg_match('#/(19|20)[0-9]{2}/#', $r['url'], $m)) {
            if (trim($m[0], chr(47)) !== substr($r['deb'], 0, 4)) { $an[] = (int) $r['ID']; }
        }
    }
    $ig = (array) get_option('cs_gardefous_ignore', array());
    $ant = array_values(array_diff($ant, $ig));
    $sans = array_values(array_diff($sans, $ig));
    $an = array_values(array_diff($an, $ig));
    $res = array('last_run' => current_time('mysql'), 'debut_anterieur' => $ant, 'date_absente' => $sans, 'url_annee' => $an);
    update_option('cs_gardefous_dates', $res, false);
    // PERIMETRE DU RAPPORT (2026-08-17). Ce garde-fou balayait tout publish+draft
    // depuis toujours : sur les 25 fiches signalees ce matin-la par les trois audits,
    // 12 etaient PASSEES (six depuis juillet) et 3 a la corbeille. Une file ou la
    // moitie des lignes ne sert personne cache l'autre moitie -- c'est le "548 taches,
    // c'est ingerable" du 2026-08-11. La BASE garde tout (option ci-dessus) ; seul le
    // MESSAGE est reduit a ce sur quoi un geste est encore possible (regle 5).
    $ecartes = array();
    if (function_exists('cs_audit_devant_nous')) {
        $f1 = cs_audit_devant_nous($ant);  $ant  = $f1['gardes'];
        $f2 = cs_audit_devant_nous($sans); $sans = $f2['gardes'];
        $f3 = cs_audit_devant_nous($an);   $an   = $f3['gardes'];
        $ecartes = cs_audit_cumuler($f1, $f2, $f3);
    }
    $l = array();
    if ($ant) { $l[] = '*date de debut anterieure de plus de 6 mois a la collecte* : ' . count($ant) . ' -> ' . implode(', ', array_slice($ant, 0, 8)); }
    if ($sans) { $l[] = '*fiche sans aucune date* : ' . count($sans) . ' -> ' . implode(', ', array_slice($sans, 0, 8)); }
    if ($an) { $l[] = '*URL de source portant une autre annee que l evenement* : ' . count($an) . ' -> ' . implode(', ', array_slice($an, 0, 8)); }
    if ($l and function_exists('cs_slack_notify_form')) {
        $mention = function_exists('cs_audit_mention_ecartes') ? cs_audit_mention_ecartes($ecartes) : '';
        cs_slack_notify_form(":shield: *Garde-fous dates et sources*" . chr(10) . implode(chr(10), $l)
            . ($mention !== '' ? chr(10) . $mention : ''));
    }
    return $res;
}
}
add_action('cs_gardefous_event', 'cs_gardefous_run');
if (!wp_next_scheduled('cs_gardefous_event')) { wp_schedule_event(time() + 900, 'daily', 'cs_gardefous_event'); }