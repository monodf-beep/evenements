<?php
/**
 * Garde-fou : conformite des gabarits de carte.
 *
 * 2026-08-02 (Franck) : "on va toujours courir derriere la carte qui aura pas
 * respecte". Constat : le site a 7 gabarits de carte JetEngine, chacun avec son
 * propre jeu de classes (venir-row__title, evidence-card__title, ...). Le CSS
 * devait donc ENUMERER les classes gabarit par gabarit -- et il en manquait
 * toujours une (constate : .venir-row__image restee en 3:2 quand les autres
 * passaient en 4:3).
 *
 * Correction de fond : tous les gabarits portent desormais un vocabulaire commun
 * (cs-card-thumb / -meta / -terr / -date / -title / -commune). Une seule regle CSS
 * par role, et un nouveau gabarit herite du systeme du seul fait de porter les
 * classes. Ce fichier VERIFIE que c est bien le cas et le signale dans le tableau
 * de bord, pour que l oubli se voie au lieu de se decouvrir en production.
 */
if (!function_exists('cs_cards_conformite')) {
function cs_cards_conformite() {
    $attendus = array(
        "dynamic-image"                  => "cs-card-thumb",
        "dynamic_field_post_object"      => "cs-card-title",
        "_EventStartDate"                => "cs-card-date",
        "from_tax\":\"territoire"        => "cs-card-terr",
    );
    // Exemptions DOCUMENTEES : ces gabarits ne sont pas des cartes.
    //  1721/1722 = visuels plein cadre du carrousel d accueil (ratio propre,
    //              volontairement different des vignettes de carte).
    // Le champ 'time' du gabarit 969 (ag-row__time) reste hors systeme lui aussi :
    // c est une GOUTTIERE horaire de 96px en colonne, pas une date en ligne meta ;
    // l aligner sur cs-card-date casserait la grille de la liste agenda.
    $exempts = array(1721, 1722);
    $res = array();
    $gabarits = get_posts(array("post_type"=>"jet-engine","posts_per_page"=>-1,"post_status"=>"any"));
    foreach ($gabarits as $g) {
        $c = $g->post_content;
        if (trim($c) === "" || in_array($g->ID, $exempts, true)) { continue; }
        $manques = array();
        foreach ($attendus as $champ => $classe) {
            if ($classe === "cs-card-date" && (int) $g->ID === 969) { continue; }
            if (strpos($c, $champ) !== false && strpos($c, $classe) === false) { $manques[] = $classe; }
        }
        if ($manques) { $res[] = array("id"=>$g->ID, "nom"=>$g->post_title, "manques"=>$manques); }
    }
    return $res;
}
}

add_action('wp_dashboard_setup', function () {
    wp_add_dashboard_widget("cs_cards_conformite_widget", "Cartes evenement : conformite des gabarits", function () {
        $ko = cs_cards_conformite();
        if (empty($ko)) {
            echo "<p style=\"margin:0;color:#1E7D34;font-weight:600\">Les gabarits de carte utilisent tous le vocabulaire commun.</p>";
            echo "<p style=\"margin:8px 0 0;color:#6F6B62;font-size:12px\">Une seule regle CSS gouverne chaque role (vignette, ligne meta, territoire, date, titre, lieu). Un gabarit qui porte ces classes herite du systeme sans reglage supplementaire.</p>";
            return;
        }
        echo "<p style=\"margin:0 0 8px;color:#B3261E;font-weight:600\">" . count($ko) . " gabarit(s) hors systeme :</p><ul style=\"margin:0;padding-left:18px\">";
        foreach ($ko as $k) {
            echo "<li style=\"margin-bottom:5px\"><strong>" . esc_html($k["nom"]) . "</strong> (#" . (int) $k["id"] . ")<br><span style=\"color:#6F6B62;font-size:12px\">classe(s) manquante(s) : " . esc_html(implode(", ", $k["manques"])) . "</span></li>";
        }
        echo "</ul><p style=\"margin:8px 0 0;color:#6F6B62;font-size:12px\">Sans ces classes, la carte echappe au systeme et devra etre rattrapee au cas par cas.</p>";
    });
});

/**
 * Garde-fou : couverture des visuels de repli.
 *
 * 2026-08-02 (Franck) : "mettre une de NOS images fallback si pas d image, et
 * surtout que WordPress n invente pas une image par defaut".
 *
 * Le mecanisme existe (snippet 87) : il intercepte _thumbnail_id et renvoie le
 * visuel territoire x categorie de la mediatheque (48 fichiers). Mais il ABANDONNE
 * silencieusement si l evenement n a pas de territoire ou pas de categorie -- la
 * carte tombe alors sur le placeholder texte de JetEngine. Ce widget compte les cas
 * et donne la RAISON, pour que la brique manquante soit une donnee a corriger et
 * non un mystere visuel.
 */
if (!function_exists('cs_visuels_couverture')) {
function cs_visuels_couverture() {
    global $wpdb;
    $ids = $wpdb->get_col("SELECT p.ID FROM {$wpdb->posts} p WHERE p.post_type='tribe_events' AND p.post_status='publish' AND NOT EXISTS (SELECT 1 FROM {$wpdb->postmeta} m WHERE m.post_id=p.ID AND m.meta_key='_thumbnail_id')");
    $total = (int) $wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type='tribe_events' AND post_status='publish'");
    $r = array("total"=>$total, "sans_image"=>count($ids), "repli_ok"=>0, "sans_territoire"=>array(), "sans_categorie"=>array(), "fichier_absent"=>array());
    foreach ($ids as $id) {
        $fid = function_exists("cs_fallback_thumbnail_id") ? cs_fallback_thumbnail_id($id) : 0;
        if ($fid) { $r["repli_ok"]++; continue; }
        $tt = wp_get_post_terms($id, "territoire", array("fields"=>"ids"));
        $cc = get_the_terms($id, "tribe_events_cat");
        if (!$tt || is_wp_error($tt)) { $r["sans_territoire"][] = $id; }
        elseif (!$cc || is_wp_error($cc)) { $r["sans_categorie"][] = $id; }
        else { $r["fichier_absent"][] = $id; }
    }
    return $r;
}
}

add_action('wp_dashboard_setup', function () {
    wp_add_dashboard_widget("cs_visuels_repli_widget", "Visuels de repli : couverture", function () {
        $r = cs_visuels_couverture();
        $ko = count($r["sans_territoire"]) + count($r["sans_categorie"]) + count($r["fichier_absent"]);
        echo "<p style=\"margin:0 0 10px;font-size:13px\"><strong>" . (int) $r["total"] . "</strong> evenements publies, dont <strong>" . (int) $r["sans_image"] . "</strong> sans image propre.</p>";
        echo "<p style=\"margin:0 0 4px;color:#1E7D34;font-weight:700\">" . (int) $r["repli_ok"] . " recoivent un de nos visuels (territoire x categorie).</p>";
        if ($ko === 0) {
            echo "<p style=\"margin:0;color:#1E7D34;font-weight:700\">Aucun evenement ne tombe sur un placeholder.</p>";
        } else {
            echo "<p style=\"margin:0 0 6px;color:#B3261E;font-weight:700\">" . $ko . " tombent sur le placeholder faute de donnee :</p><ul style=\"margin:0;padding-left:18px;font-size:12.5px\">";
            if ($r["sans_territoire"]) { echo "<li><strong>" . count($r["sans_territoire"]) . "</strong> sans territoire " . cs_visuels_liens($r["sans_territoire"]) . "</li>"; }
            if ($r["sans_categorie"])  { echo "<li><strong>" . count($r["sans_categorie"]) . "</strong> sans categorie " . cs_visuels_liens($r["sans_categorie"]) . "</li>"; }
            if ($r["fichier_absent"])  { echo "<li><strong>" . count($r["fichier_absent"]) . "</strong> dont le fichier de repli manque en mediatheque " . cs_visuels_liens($r["fichier_absent"]) . "</li>"; }
            echo "</ul>";
        }
        echo "<p style=\"margin:10px 0 0;color:#6F6B62;font-size:12px\">Le repli passe par _thumbnail_id : tout le site en beneficie (cartes, fiches, partages sociaux). WordPress ne fournit jamais d image par defaut -- sans notre visuel, la carte reste vide.</p>";
    });
});

if (!function_exists('cs_visuels_liens')) {
function cs_visuels_liens($ids) {
    $out = array();
    foreach (array_slice($ids, 0, 4) as $id) {
        $out[] = "<a href=\"" . esc_url(get_edit_post_link($id)) . "\">" . esc_html(mb_substr(get_the_title($id), 0, 30)) . "</a>";
    }
    $s = "<br><span style=\"color:#6F6B62\">" . implode(", ", $out);
    if (count($ids) > 4) { $s .= " et " . (count($ids) - 4) . " autre(s)"; }
    return $s . "</span>";
}
}