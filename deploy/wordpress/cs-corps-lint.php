<?php
/**
 * Plugin Name: CS - Lint doctrine des corps proposes
 * Description: Controle mecanique d un corps de fiche avant application : vocabulaire proscrit FR/IT, tirets cadratins, langue, longueur, balises. Aucun jugement editorial, seulement ce qui est verifiable.
 */
if (!defined('ABSPATH')) exit;

function cs_corps_lint($html, $lang = 'fr') {
    $err = array(); $avert = array();
    $txt = wp_strip_all_tags($html);
    $len = mb_strlen(trim($txt));

    // 1. tirets cadratins et demi-cadratins, interdit de forme absolu
    foreach (array("\xE2\x80\x94" => 'tiret cadratin', "\xE2\x80\x93" => 'tiret demi-cadratin') as $c => $nom) {
        $n = substr_count($html, $c);
        if ($n) { $err[] = "$nom present ($n fois)"; }
    }

    // 2. vocabulaire proscrit, le concept vaut dans les deux langues
    $interdits = array(
        'frontiere','frontière','frontalier','frontalière','transfrontalier','transfrontalière',
        'transalpin','transalpine','oltralpe','confine','confini','frontaliero','transfrontaliero',
        'transalpino','transalpina','espace alpin','spazio alpino','francoprovencal','francoprovençal',
        'francoprovenzale','arpitan','arpitano','patois','langues regionales','langues régionales',
        'lingue regionali','haut-savoyard','haut-savoyarde','altosavoiardo','alta savoia',
        'cote francais','côté français','cote italien','côté italien','lato francese','lato italiano',
        'de part et d\'autre','versant','crinale','ligne de crete','ligne de crête',
    );
    $bas = mb_strtolower($txt);
    foreach ($interdits as $t) {
        if (mb_strpos($bas, mb_strtolower($t)) !== false) {
            // exception attestee : le statut administratif
            if (in_array($t, array('frontalier','frontalière','frontaliero'), true)
                && preg_match('/(travailleu\w+|lavorat\w+)\s+frontali/iu', $txt)) { continue; }
            $err[] = 'terme proscrit : ' . $t;
        }
    }

    // 3. langue : detection grossiere par mots outils exclusifs
    $fr = preg_match_all('/\b(le|la|les|des|une|dans|avec|pour|est|sont|cette|aussi|entre)\b/iu', $txt);
    $it = preg_match_all('/\b(il|lo|gli|della|delle|nel|con|per|sono|questa|anche|tra)\b/iu', $txt);
    if ($lang === 'it' && $fr > $it) { $err[] = "etiquetee it mais le texte parait francais (fr=$fr, it=$it)"; }
    if ($lang === 'fr' && $it > $fr) { $err[] = "etiquetee fr mais le texte parait italien (fr=$fr, it=$it)"; }

    // 4. longueur
    if ($len < 400) { $err[] = "toujours indigent : $len caracteres"; }
    elseif ($len < 900) { $avert[] = "court : $len caracteres"; }
    elseif ($len > 2600) { $avert[] = "long : $len caracteres"; }

    // 5. balises hors liste blanche
    if (preg_match_all('/<\s*([a-z0-9]+)/i', $html, $m)) {
        $ok = array('p','h3','strong','em','ul','li','a','br');
        foreach (array_unique(array_map('strtolower', $m[1])) as $tag) {
            if (!in_array($tag, $ok, true)) { $err[] = 'balise non autorisee : <' . $tag . '>'; }
        }
    }

    // 6. anti-patterns IA les plus mecaniques
    $ia = array('incontournable','a couper le souffle','à couper le souffle','ecrin','écrin',
        'pittoresque','joyau','pepite','pépite','veritable','véritable','immanquable',
        'non seulement','imperdibile','gioiello','suggestivo','non solo');
    foreach ($ia as $t) { if (mb_strpos($bas, mb_strtolower($t)) !== false) { $avert[] = 'formule IA : ' . $t; } }

    return array('ok' => empty($err), 'longueur' => $len, 'erreurs' => $err, 'avertissements' => array_values(array_unique($avert)));
}