<?php
/*
Plugin Name: Cultura Sabauda - Garde-fou coherence de langue
Description: Widget de tableau de bord, lecture seule, qui detecte les fiches dont la
  langue declaree par Polylang ne correspond pas a la langue reellement ecrite.
  Ne 2026-08-03 apres le nettoyage de 56 fiches declarees italiennes et redigees
  en francais, soit 42 pour cent du catalogue italien de l epoque. Sans ce
  controle, le defaut revient au lot suivant du pipeline.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : deposer dans wp-content/mu-plugins/cs-garde-fou-langue.php
  Actif automatiquement. Rien a activer, rien a configurer.

  LECTURE SEULE : ne modifie ni les posts, ni les termes, ni les langues.
  Seule ecriture : le transient de cache, qui expire seul au bout de 30 minutes.
  Le prefixe des tables n est jamais ecrit en dur.

  METHODE : score bilingue sur des marqueurs choisis pour ne jamais dependre d un
  nom propre ni d un titre d oeuvre. Une fiche italienne qui cite
  « Riprendersi l anima » reste italienne. Le verdict porte sur le CORPS du texte,
  jamais sur le titre seul, precisement parce que les titres sont souvent dans
  l autre langue de facon legitime.
*/

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'CS_GFL_CACHE_KEY', 'cs_gfl_rapport_v1' );
define( 'CS_GFL_CACHE_TTL', 30 * MINUTE_IN_SECONDS );
define( 'CS_GFL_MIN_MOTS', 25 );
define( 'CS_GFL_MAX_AFFICHE', 30 );

/* ------------------------------------------------------------------ *
 * Marqueurs
 * ------------------------------------------------------------------ *
 * Uniquement des formes EXCLUSIVES a une langue. Les formes communes ou
 * ambigues sont volontairement absentes : la, il, un, e, a, come, per, in,
 * di, da, no. Un article defini pluriel comme « les » ou « gli » n apparait
 * jamais dans l autre langue et ne peut pas venir d un nom propre.
 */

function cs_gfl_marqueurs_fr() {
    return array(
        'les','des','du','aux','au','est','sont','etait','etaient','dans','avec',
        'cette','cet','ces','depuis','jusqu','chaque','plus','leur','leurs','une',
        'pour','qui','que','ainsi','entre','sous','vers','tout','toute','toutes',
        'tous','mais','donc','alors','aussi','encore','deja','apres','avant',
        'pendant','lors','cependant','neanmoins','sera','seront','peut','peuvent',
        'janvier','fevrier','mars','avril','juin','juillet','aout','septembre',
        'octobre','novembre','decembre','lundi','mardi','mercredi','jeudi',
        'vendredi','samedi','dimanche','gratuit','gratuite','entree','billet',
    );
}

function cs_gfl_marqueurs_it() {
    return array(
        'gli','degli','della','dello','delle','nella','nello','nelle','sul','sulla',
        'sui','che','non','sono','anche','piu','perche','ogni','ore','dal','dalla',
        'dai','alle','allo','agli','negli','questo','questa','questi','queste',
        'viene','vengono','sara','saranno','puo','possono','oppure','inoltre',
        'mentre','durante','presso','tra','fra','suo','sua','loro','molto',
        'gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto',
        'settembre','ottobre','novembre','dicembre','lunedi','martedi','mercoledi',
        'giovedi','venerdi','sabato','domenica','gratuito','gratuita','ingresso',
        'biglietto','mostra','evento','citta',
    );
}

/**
 * Minuscule, accents retires pour la comparaison de mots, MAIS on compte les
 * diacritiques exclusivement francais avant de les perdre.
 */
function cs_gfl_score( $texte ) {

    $brut = wp_strip_all_tags( (string) $texte );
    $brut = html_entity_decode( $brut, ENT_QUOTES, 'UTF-8' );

    $score = array( 'fr' => 0, 'it' => 0, 'mots' => 0 );

    // 1. Diacritiques qui n existent pas en italien. Un point plein chacun.
    $score['fr'] += preg_match_all( '/[\x{00E7}\x{00EA}\x{00E2}\x{00EE}\x{00FB}\x{00EB}\x{00EF}\x{0153}]/u', $brut );

    // 2. Elisions. Tres discriminantes.
    $score['it'] += preg_match_all( "/\b(dell|nell|all|sull|quest|dall|un)'/iu", $brut );
    $score['fr'] += preg_match_all( "/\b(d|l|qu|n|s|j|c|m|t)'/iu", $brut );

    // 3. Mots grammaticaux exclusifs.
    $plat = mb_strtolower( $brut, 'UTF-8' );
    $plat = strtr( $plat, array(
        "\x{00E0}"=>'a', "\x{00E2}"=>'a', "\x{00E4}"=>'a', "\x{00E9}"=>'e',
        "\x{00E8}"=>'e', "\x{00EA}"=>'e', "\x{00EB}"=>'e', "\x{00EE}"=>'i',
        "\x{00EF}"=>'i', "\x{00F4}"=>'o', "\x{00F6}"=>'o', "\x{00F9}"=>'u',
        "\x{00FB}"=>'u', "\x{00FC}"=>'u', "\x{00E7}"=>'c', "\x{00EC}"=>'i',
        "\x{00F2}"=>'o', "\x{00E1}"=>'a', "\x{00ED}"=>'i', "\x{00F3}"=>'o',
        "\x{00FA}"=>'u',
    ) );
    $mots = preg_split( '/[^a-z]+/', $plat, -1, PREG_SPLIT_NO_EMPTY );
    $score['mots'] = is_array( $mots ) ? count( $mots ) : 0;

    if ( $score['mots'] ) {
        $fr = array_flip( cs_gfl_marqueurs_fr() );
        $it = array_flip( cs_gfl_marqueurs_it() );
        foreach ( $mots as $mot ) {
            if ( isset( $fr[ $mot ] ) ) { $score['fr']++; }
            elseif ( isset( $it[ $mot ] ) ) { $score['it']++; }
        }
    }

    return $score;
}

/**
 * Verdict : 'fr', 'it', ou '' quand le texte ne tranche pas.
 * Seuil volontairement severe : la langue gagnante doit doubler l autre ET la
 * devancer d au moins 3 points, sur un minimum de 4 marqueurs. Mieux vaut un
 * faux negatif silencieux qu un faux positif qui decredibilise le tableau.
 */
function cs_gfl_verdict( $score ) {
    $fr = $score['fr'];
    $it = $score['it'];
    if ( ( $fr + $it ) < 4 ) { return ''; }
    if ( $fr >= ( $it * 2 ) && ( $fr - $it ) >= 3 ) { return 'fr'; }
    if ( $it >= ( $fr * 2 ) && ( $it - $fr ) >= 3 ) { return 'it'; }
    return '';
}

/* ------------------------------------------------------------------ *
 * Le scan
 * ------------------------------------------------------------------ */

function cs_gfl_scanner() {

    global $wpdb;

    $rapport = array(
        'date'      => current_time( 'mysql' ),
        'analysees' => 0,
        'ignorees'  => 0,
        'douteuses' => 0,
        'anomalies' => array(),
        'par_type'  => array(),
    );

    if ( ! function_exists( 'pll_get_post_language' ) ) {
        $rapport['erreur'] = 'Polylang absent';
        return $rapport;
    }

    // SQL direct : get_posts et WP_Query masquent les evenements passes sur
    // tribe_events, ce qui sous-estime le catalogue d un tiers.
    $lignes = $wpdb->get_results(
        "SELECT ID, post_title, post_content, post_type
           FROM {$wpdb->posts}
          WHERE post_status = 'publish'
            AND post_type IN ('tribe_events','post','page')
       ORDER BY post_date DESC"
    );

    if ( empty( $lignes ) ) { return $rapport; }

    foreach ( $lignes as $ligne ) {

        $declaree = pll_get_post_language( (int) $ligne->ID );
        if ( ! in_array( $declaree, array( 'fr', 'it' ), true ) ) {
            $rapport['ignorees']++;
            continue;
        }

        // Le CORPS seul decide. Le titre est souvent dans l autre langue de
        // facon legitime : « Riprendersi l anima », « Voglio tornare negli anni ».
        $score = cs_gfl_score( $ligne->post_content );

        if ( $score['mots'] < CS_GFL_MIN_MOTS ) {
            $rapport['ignorees']++;
            continue;
        }

        $rapport['analysees']++;
        $reelle = cs_gfl_verdict( $score );

        if ( '' === $reelle ) {
            $rapport['douteuses']++;
            continue;
        }

        if ( $reelle === $declaree ) { continue; }

        $extrait = wp_strip_all_tags( html_entity_decode( $ligne->post_content, ENT_QUOTES, 'UTF-8' ) );
        $extrait = trim( preg_replace( '/\s+/u', ' ', $extrait ) );

        $sens = $declaree . '>' . $reelle;
        if ( ! isset( $rapport['par_type'][ $sens ] ) ) { $rapport['par_type'][ $sens ] = 0; }
        $rapport['par_type'][ $sens ]++;

        $rapport['anomalies'][] = array(
            'id'       => (int) $ligne->ID,
            'titre'    => $ligne->post_title,
            'type'     => $ligne->post_type,
            'declaree' => $declaree,
            'reelle'   => $reelle,
            'fr'       => $score['fr'],
            'it'       => $score['it'],
            'extrait'  => mb_substr( $extrait, 0, 150, 'UTF-8' ),
        );
    }

    // Les ecarts les plus francs en tete.
    usort( $rapport['anomalies'], function ( $a, $b ) {
        $ea = abs( $a['fr'] - $a['it'] );
        $eb = abs( $b['fr'] - $b['it'] );
        return $eb - $ea;
    } );

    return $rapport;
}

function cs_gfl_rapport( $forcer = false ) {
    if ( ! $forcer ) {
        $cache = get_transient( CS_GFL_CACHE_KEY );
        if ( is_array( $cache ) ) { $cache['cache'] = true; return $cache; }
    }
    $rapport = cs_gfl_scanner();
    set_transient( CS_GFL_CACHE_KEY, $rapport, CS_GFL_CACHE_TTL );
    $rapport['cache'] = false;
    return $rapport;
}

/* ------------------------------------------------------------------ *
 * Widget
 * ------------------------------------------------------------------ */

add_action( 'wp_dashboard_setup', function () {
    if ( ! current_user_can( 'manage_options' ) ) { return; }
    wp_add_dashboard_widget( 'cs_gfl_widget', 'Garde-fou coherence de langue', 'cs_gfl_afficher' );
} );

function cs_gfl_afficher() {

    if ( ! current_user_can( 'manage_options' ) ) { return; }

    $forcer  = ( isset( $_GET['cs_gfl_refresh'] ) && check_admin_referer( 'cs_gfl_refresh' ) );
    $rapport = cs_gfl_rapport( $forcer );

    if ( ! empty( $rapport['erreur'] ) ) {
        echo '<p>' . esc_html( $rapport['erreur'] ) . '</p>';
        return;
    }

    $n = count( $rapport['anomalies'] );

    echo '<p style="margin-top:0">';
    if ( 0 === $n ) {
        echo '<strong style="color:#008a20">Aucune incoherence detectee</strong> sur ';
        echo (int) $rapport['analysees'] . ' contenus analyses.';
    } else {
        echo '<strong style="color:#b32d2e">' . (int) $n . ' contenu(s)</strong> dont la langue declaree ';
        echo 'ne correspond pas au texte, sur ' . (int) $rapport['analysees'] . ' analyses.';
    }
    echo '</p>';

    if ( ! empty( $rapport['par_type'] ) ) {
        echo '<p style="margin:0 0 10px;font-size:12px;color:#3c434a">';
        foreach ( $rapport['par_type'] as $sens => $c ) {
            $lib = ( 'it>fr' === $sens ) ? 'declare italien, ecrit en francais' : 'declare francais, ecrit en italien';
            echo '<span style="margin-right:14px"><strong>' . (int) $c . '</strong> ' . esc_html( $lib ) . '</span>';
        }
        echo '</p>';
    }

    if ( $n ) {
        echo '<ul style="margin:0">';
        $i = 0;
        foreach ( $rapport['anomalies'] as $a ) {
            if ( $i++ >= CS_GFL_MAX_AFFICHE ) {
                printf( '<li style="color:#646970">... et %d autre(s).</li>', $n - CS_GFL_MAX_AFFICHE );
                break;
            }
            $edit = get_edit_post_link( $a['id'] );
            $vue  = get_permalink( $a['id'] );
            echo '<li style="margin-bottom:9px">';
            echo '<a href="' . esc_url( $edit ) . '"><strong>' . esc_html( $a['titre'] ) . '</strong></a> ';
            echo '<span style="font-size:11px;color:#646970">[' . esc_html( $a['type'] ) . ' ' . (int) $a['id'] . ']</span><br>';
            echo '<span style="font-size:11px;color:#b32d2e">declare ' . esc_html( strtoupper( $a['declaree'] ) );
            echo ' mais ecrit en ' . esc_html( strtoupper( $a['reelle'] ) ) . '</span> ';
            echo '<span style="font-size:11px;color:#646970">(fr ' . (int) $a['fr'] . ' / it ' . (int) $a['it'] . ')</span> ';
            echo '<a href="' . esc_url( $vue ) . '" style="font-size:11px">voir</a>';
            echo '<div style="font-size:11px;color:#3c434a;margin-top:2px">' . esc_html( $a['extrait'] ) . '&hellip;</div>';
            echo '</li>';
        }
        echo '</ul>';
    }

    $lien = wp_nonce_url( add_query_arg( 'cs_gfl_refresh', '1', admin_url( 'index.php' ) ), 'cs_gfl_refresh' );

    echo '<p style="margin-bottom:0;font-size:11px;color:#646970">';
    echo 'Scan du ' . esc_html( $rapport['date'] ) . ' ';
    echo empty( $rapport['cache'] ) ? '(frais)' : '(cache, 30 min)';
    echo ' &middot; ' . (int) $rapport['ignorees'] . ' ignores (trop courts ou sans langue), ';
    echo (int) $rapport['douteuses'] . ' indecidables';
    echo ' &middot; <a href="' . esc_url( $lien ) . '">relancer</a>';
    echo ' &middot; lecture seule.';
    echo '</p>';
}
