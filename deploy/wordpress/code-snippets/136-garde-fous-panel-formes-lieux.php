if (!function_exists('cs_gf2_run')) {
function cs_gf2_run() {
    global $wpdb;
    $rev = $wpdb->get_col("SELECT p.ID FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} v ON v.post_id=p.ID AND v.meta_key='as_panel_verdict' AND v.meta_value='revise' WHERE p.post_type='tribe_events' AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} r WHERE r.post_id=p.ID AND r.meta_key='as_panel_revision' AND TRIM(r.meta_value)<>'')");
    $tir = $wpdb->get_col("SELECT ID FROM {$wpdb->posts} WHERE post_type IN ('tribe_events','tribe_venue') AND post_status IN ('publish','draft') AND post_title LIKE '% - %'");
    $rows = $wpdb->get_results("SELECT ID, post_content FROM {$wpdb->posts} WHERE post_type='tribe_events' AND post_status IN ('publish','draft')", ARRAY_A);
    $tro = array();
    foreach ($rows as $r) {
        $t = trim(html_entity_decode(wp_strip_all_tags($r['post_content']), ENT_QUOTES, 'UTF-8'));
        if ($t === '') { continue; }
        if (preg_match('/(Leggi di pi|Lire la suite|Read more|En savoir plus|,[.]{3}|[.]{3}$)/iu', $t)) { $tro[] = (int) $r['ID']; }
    }
    $vs = $wpdb->get_results("SELECT ID, post_title FROM {$wpdb->posts} WHERE post_type='tribe_venue' AND post_status='publish'", ARRAY_A);
    $stop = array('de','di','du','la','le','les','del','della','il','a','au','aux','of','and','et','e','d','l');
    $v = array();
    foreach ($vs as $r) {
        $k = mb_strtolower(html_entity_decode($r['post_title']));
        $k = preg_replace('/[^\p{L}\p{N} ]/u', ' ', $k);
        $w = array_values(array_unique(array_diff(array_filter(explode(' ', preg_replace('/\s+/', ' ', $k))), $stop)));
        if (count($w)) { $v[(int) $r['ID']] = $w; }
    }
    $ids = array_keys($v); $m = count($ids); $lieux = array();
    for ($i = 0; $i < $m; $i++) {
        for ($j = $i + 1; $j < $m; $j++) {
            $a = $v[$ids[$i]]; $b = $v[$ids[$j]];
            $x = count(array_intersect($a, $b));
            if ($x > 1 and ($x === count($a) or $x === count($b))) {
                $ca = (string) get_post_meta($ids[$i], '_VenueCity', true);
                $cb = (string) get_post_meta($ids[$j], '_VenueCity', true);
                if ($ca !== '' and $cb !== '' and mb_strtolower($ca) !== mb_strtolower($cb)) { $lieux[] = $ids[$i] . '/' . $ids[$j]; }
            }
        }
    }
    $res = array('last_run' => current_time('mysql'), 'revise_sans_motif' => $rev, 'titres_tiret' => $tir, 'troncature' => $tro, 'lieux_a_verifier' => $lieux);
    update_option('cs_gardefous2', $res, false);
    // PERIMETRE DU RAPPORT (2026-08-17) : voir cs-audit-perimetre.php. La base garde
    // tout (option ci-dessus), le message ne parle que de ce qui est encore devant
    // nous -- sur les 25 fiches signalees ce matin-la par les trois audits, 12 etaient
    // passees et 3 a la corbeille. Les paires de LIEUX se jugent autrement : un lieu
    // n'a pas de date, donc on garde la paire si au moins un des deux sert encore a un
    // evenement a venir ; sinon la ville fausse n'est plus affichee a personne.
    $ecartes = array();
    if (function_exists('cs_audit_devant_nous')) {
        $f1 = cs_audit_devant_nous($rev); $rev = $f1['gardes'];
        $f2 = cs_audit_devant_nous($tir); $tir = $f2['gardes'];
        $f3 = cs_audit_devant_nous($tro); $tro = $f3['gardes'];
        $ecartes = cs_audit_cumuler($f1, $f2, $f3);
        if (function_exists('cs_audit_lieux_actifs')) {
            $fl = cs_audit_lieux_actifs($lieux);
            $lieux = $fl['gardes'];
        }
    }
    $l = array();
    if ($rev) { $l[] = '*verdict revise sans motif* : ' . count($rev) . ' -> ' . implode(', ', array_slice($rev, 0, 8)); }
    if ($tir) { $l[] = '*titre avec espace tiret espace, rendu en demi-cadratin* : ' . count($tir) . ' -> ' . implode(', ', array_slice($tir, 0, 8)); }
    if ($tro) { $l[] = '*corps finissant par une troncature d agregateur* : ' . count($tro) . ' -> ' . implode(', ', array_slice($tro, 0, 8)); }
    if ($lieux) { $l[] = '*lieux a verifier, titres proches et villes differentes* : ' . count($lieux) . ' -> ' . implode(', ', array_slice($lieux, 0, 8)); }
    if ($l and function_exists('cs_slack_notify_form')) {
        $mention = function_exists('cs_audit_mention_ecartes') ? cs_audit_mention_ecartes($ecartes) : '';
        cs_slack_notify_form(":shield: *Garde-fous 2 : panel, formes, lieux*" . chr(10) . implode(chr(10), $l)
            . ($mention !== '' ? chr(10) . $mention : ''));
    }
    return $res;
}
}
add_action('cs_gf2_event', 'cs_gf2_run');
if (!wp_next_scheduled('cs_gf2_event')) { wp_schedule_event(time() + 1200, 'daily', 'cs_gf2_event'); }