<?php
/*
Plugin Name: Cultura Sabauda - Garde-fou structure du catalogue
Description: Widget de tableau de bord, lecture seule, qui detecte deux defauts
  structurels du pipeline de collecte, distincts des defauts de prose couverts
  par cs-garde-fou-langue.php.
  1) Taxonomies dans une langue differente de celle de la fiche : une fiche
     francaise etiquetee Contea di Nizza affiche un libelle italien sur les
     cartes et les hubs francais.
  2) Doublons de collecte : plusieurs fiches de MEME LANGUE partageant date de
     debut, date de fin et lieu. Les paires francais / italien sont exclues,
     ce sont des traductions legitimes.
  Ne 2026-08-03 apres correction de 38 fiches a taxonomie incoherente et fusion
  de 11 groupes de doublons.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : deposer dans wp-content/mu-plugins/cs-garde-fou-structure.php
  Actif automatiquement. Rien a activer, rien a configurer.

  LECTURE SEULE : ne modifie ni les posts, ni les termes, ni les langues.
  Seule ecriture : le transient de cache, qui expire seul au bout de 30 minutes.
  Le prefixe des tables n est jamais ecrit en dur, cf. agendasabauda-debug-pitfalls.

  IMPORTANT : le comptage passe par SQL direct et jamais par WP_Query ni
  get_posts, qui masquent silencieusement les tribe_events passes. Sur ce site
  l ecart constate etait de 324 fiches reelles contre 224 vues par l API.
*/

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'CS_GFS_CACHE_KEY', 'cs_gfs_rapport_v1' );
define( 'CS_GFS_CACHE_TTL', 30 * MINUTE_IN_SECONDS );
define( 'CS_GFS_MAX_AFFICHE', 25 );

/* ------------------------------------------------------------------ *
 * Famille 1 : taxonomies dans une langue etrangere a la fiche
 * ------------------------------------------------------------------ */

function cs_gfs_taxonomies_incoherentes() {
	global $wpdb;

	if ( ! function_exists( 'pll_get_post_language' ) || ! function_exists( 'pll_get_term_language' ) ) {
		return array();
	}

	$sql = "SELECT p.ID, p.post_title, tt.taxonomy, t.term_id, t.name
		FROM {$wpdb->posts} p
		JOIN {$wpdb->term_relationships} tr ON tr.object_id = p.ID
		JOIN {$wpdb->term_taxonomy} tt ON tt.term_taxonomy_id = tr.term_taxonomy_id
		JOIN {$wpdb->terms} t ON t.term_id = tt.term_id
		WHERE p.post_type = 'tribe_events'
		  AND p.post_status = 'publish'
		  AND tt.taxonomy IN ('territoire', 'tribe_events_cat')";

	$lignes = $wpdb->get_results( $sql, ARRAY_A );
	$fiches = array();

	foreach ( $lignes as $l ) {
		$langue_fiche = pll_get_post_language( $l['ID'] );
		$langue_terme = pll_get_term_language( $l['term_id'] );

		if ( ! $langue_fiche || ! $langue_terme || $langue_fiche === $langue_terme ) {
			continue;
		}

		$id = (int) $l['ID'];

		if ( ! isset( $fiches[ $id ] ) ) {
			$fiches[ $id ] = array(
				'titre'  => $l['post_title'],
				'langue' => $langue_fiche,
				'termes' => array(),
			);
		}

		// Une traduction existante rend la correction triviale. Son absence
		// demande un arbitrage humain : on le signale distinctement.
		$traduction = function_exists( 'pll_get_term' ) ? pll_get_term( $l['term_id'], $langue_fiche ) : 0;

		$fiches[ $id ]['termes'][] = array(
			'libelle'    => $l['name'],
			'langue'     => $langue_terme,
			'corrigeable' => ( $traduction && (int) $traduction !== (int) $l['term_id'] ),
		);
	}

	return $fiches;
}

/* ------------------------------------------------------------------ *
 * Famille 2 : doublons de collecte
 * ------------------------------------------------------------------ *
 * Meme date de debut, meme date de fin, meme lieu. Le regroupement par langue
 * intervient APRES la requete : deux fiches de langues differentes sont une
 * traduction, pas un doublon, et representaient 47 des 60 groupes bruts lors
 * du releve initial.
 */

function cs_gfs_doublons() {
	global $wpdb;

	if ( ! function_exists( 'pll_get_post_language' ) ) {
		return array();
	}

	$sql = "SELECT GROUP_CONCAT(p.ID ORDER BY p.ID) AS ids
		FROM {$wpdb->posts} p
		JOIN {$wpdb->postmeta} m1 ON m1.post_id = p.ID AND m1.meta_key = '_EventStartDate'
		JOIN {$wpdb->postmeta} m2 ON m2.post_id = p.ID AND m2.meta_key = '_EventEndDate'
		LEFT JOIN {$wpdb->postmeta} m3 ON m3.post_id = p.ID AND m3.meta_key = '_EventVenueID'
		WHERE p.post_type = 'tribe_events'
		  AND p.post_status = 'publish'
		GROUP BY m1.meta_value, m2.meta_value, m3.meta_value
		HAVING COUNT(*) > 1";

	$bruts   = $wpdb->get_results( $sql, ARRAY_A );
	$groupes = array();

	foreach ( $bruts as $b ) {
		$ids        = array_map( 'intval', explode( ',', $b['ids'] ) );
		$par_langue = array();

		foreach ( $ids as $id ) {
			$langue = pll_get_post_language( $id );
			$par_langue[ $langue ? $langue : 'inconnue' ][] = $id;
		}

		foreach ( $par_langue as $langue => $membres ) {
			if ( count( $membres ) < 2 ) {
				continue;
			}

			$detail = array();

			foreach ( $membres as $id ) {
				$post = get_post( $id );

				if ( ! $post ) {
					continue;
				}

				$detail[] = array(
					'id'    => $id,
					'titre' => $post->post_title,
					'mots'  => str_word_count( wp_strip_all_tags( $post->post_content ) ),
					'lien'  => get_permalink( $id ),
				);
			}

			if ( count( $detail ) > 1 ) {
				$groupes[] = array( 'langue' => $langue, 'fiches' => $detail );
			}
		}
	}

	return $groupes;
}

/* ------------------------------------------------------------------ *
 * Famille 3 : unites militaires de montagne
 * ------------------------------------------------------------------ *
 * Franck, 2026-08-03 : ne jamais publier de contenu en relation avec le
 * 13e BCA cote francais, ni son equivalent italien. Une fiche identifiee
 * recoit as_exclu = 1, et le snippet 126 la retire de tout le front.
 *
 * CE DETECTEUR NE SUPPRIME RIEN, ET C EST DELIBERE. Le releve du jour meme,
 * sur dix correspondances textuelles :
 *   - 1 seule visait vraiment une unite (Velotour ouvrant les portes du
 *     13e BCA a Chambery) ;
 *   - 5 n etaient que l adjectif alpin / alpino / alpinismo, ou le nom d un
 *     Museo Civico Alpino ;
 *   - 1 etait le Festival des jardins alpestres, dont le seul tort est de se
 *     tenir sur l esplanade des Chasseurs Alpins, a Albertville.
 * Un filtre automatique aurait donc supprime un festival de jardins pour un
 * nom de place. On signale, un humain tranche.
 *
 * Les motifs evitent volontairement le mot « alpini » seul : en italien il
 * sert d adjectif courant (borgo alpino, territorio alpino, ambiente alpino).
 * On exige un contexte qui designe le corps ou l association.
 */

function cs_gfs_militaire_motifs() {
	return array(
		// Cote francais
		'(^|[^[:alnum:]])BCA([^[:alnum:]]|$)',
		'chasseurs?[[:space:]]+alpins?',
		'bataillon[[:space:]]+de[[:space:]]+chasseurs',
		// Cote italien : jamais « alpini » seul, toujours qualifie
		'associazione[[:space:]]+nazionale[[:space:]]+alpini',
		// Variante francaise : les fiches traduites ecrivent « Association
		// Nationale Alpini ». Trou repere le 2026-08-03 : la jumelle FR du
		// Trofeo della Mole passait au travers alors que l originale IT etait vue.
		'association[[:space:]]+nationale[[:space:]]+alpini',
		'sezione[[:space:]]+[[:alpha:]]{0,20}[[:space:]]*alpini',
		'gruppo[[:space:]]+alpini',
		'truppe[[:space:]]+alpine',
		'penne[[:space:]]+nere',
		'adunata',
	);
}

function cs_gfs_militaires() {
	global $wpdb;

	$re = '(' . implode( '|', cs_gfs_militaire_motifs() ) . ')';

	$rows = $wpdb->get_results( $wpdb->prepare(
		"SELECT ID, post_title, post_content FROM {$wpdb->posts}
		 WHERE post_status = 'publish' AND post_type = 'tribe_events'
		   AND ( post_title REGEXP %s OR post_content REGEXP %s )",
		$re, $re
	), ARRAY_A );

	$out = array();

	foreach ( $rows as $r ) {
		$id = (int) $r['ID'];

		// Deja traitee : on ne la resignale pas.
		if ( get_post_meta( $id, 'as_exclu', true ) === '1' ) { continue; }

		$titre_txt = wp_strip_all_tags( $r['post_title'] );
		$corps_txt = wp_strip_all_tags( $r['post_content'] );

		// Le nom du LIEU ne compte pas : l esplanade des Chasseurs Alpins est
		// une place publique, pas une caserne. On mesure donc si la mention
		// existe ailleurs que dans le nom du lieu.
		$vid   = (int) get_post_meta( $id, '_EventVenueID', true );
		$lieu  = $vid ? wp_strip_all_tags( get_the_title( $vid ) ) : '';

		$motif_php = '/(' . str_replace(
			array( '[[:alnum:]]', '[[:space:]]', '[[:alpha:]]' ),
			array( '\w', '\s', '[a-zA-Z]' ),
			implode( '|', cs_gfs_militaire_motifs() )
		) . ')/iu';

		preg_match_all( $motif_php, $titre_txt . ' ' . $corps_txt, $m );
		$mentions = array_values( array_unique( array_map( 'trim', $m[0] ) ) );

		$dans_lieu_seul = false;
		if ( $lieu !== '' && preg_match( $motif_php, $lieu ) ) {
			$sans_lieu = str_ireplace( $lieu, '', $titre_txt . ' ' . $corps_txt );
			$dans_lieu_seul = ! preg_match( $motif_php, $sans_lieu );
		}

		$out[] = array(
			'id'             => $id,
			'titre'          => html_entity_decode( $r['post_title'], ENT_QUOTES, 'UTF-8' ),
			'lieu'           => $lieu,
			'mentions'       => array_slice( $mentions, 0, 4 ),
			'dans_lieu_seul' => $dans_lieu_seul,
		);
	}

	return $out;
}

/* ------------------------------------------------------------------ *
 * Rapport, cache et affichage
 * ------------------------------------------------------------------ */

function cs_gfs_rapport( $forcer = false ) {
	if ( ! $forcer ) {
		$cache = get_transient( CS_GFS_CACHE_KEY );

		if ( false !== $cache ) {
			return $cache;
		}
	}

	$rapport = array(
		'taxonomies' => cs_gfs_taxonomies_incoherentes(),
		'doublons'   => cs_gfs_doublons(),
		'militaires' => cs_gfs_militaires(),
		'date'       => current_time( 'mysql' ),
	);

	set_transient( CS_GFS_CACHE_KEY, $rapport, CS_GFS_CACHE_TTL );

	return $rapport;
}

function cs_gfs_afficher() {
	$rapport = cs_gfs_rapport();
	$taxo    = $rapport['taxonomies'];
	$doub    = $rapport['doublons'];

	$mil_n = isset( $rapport['militaires'] ) ? count( $rapport['militaires'] ) : 0;
	if ( empty( $taxo ) && empty( $doub ) && $mil_n === 0 ) {
		echo '<p style="margin:0;color:#1a7f37"><strong>Rien a signaler.</strong> ';
		echo 'Aucune taxonomie en langue etrangere, aucun doublon de collecte.</p>';
		echo '<p style="margin:8px 0 0;color:#6F6B62;font-size:12px">Releve du ';
		echo esc_html( $rapport['date'] ) . '</p>';
		return;
	}

	/* Famille 1 */
	echo '<p style="margin:0 0 6px"><strong>Taxonomies en langue etrangere : ';
	echo count( $taxo ) . ' fiche(s)</strong></p>';

	if ( ! empty( $taxo ) ) {
		echo '<p style="margin:0 0 8px;color:#6F6B62;font-size:12px">';
		echo 'Une fiche francaise etiquetee avec un terme italien affiche ce libelle ';
		echo 'italien sur les cartes et les hubs francais.</p>';
		echo '<ul style="margin:0 0 14px;padding-left:18px">';

		$n = 0;

		foreach ( $taxo as $id => $f ) {
			if ( $n++ >= CS_GFS_MAX_AFFICHE ) {
				echo '<li style="color:#6F6B62">... et ' . ( count( $taxo ) - CS_GFS_MAX_AFFICHE );
				echo ' autre(s).</li>';
				break;
			}

			$libelles = array();

			foreach ( $f['termes'] as $t ) {
				$libelles[] = $t['libelle'] . ' [' . $t['langue'] . ']'
					. ( $t['corrigeable'] ? '' : ' SANS TRADUCTION' );
			}

			echo '<li style="margin-bottom:4px">';
			echo '<a href="' . esc_url( get_edit_post_link( $id ) ) . '">';
			echo esc_html( wp_html_excerpt( $f['titre'], 70, '...' ) ) . '</a> ';
			echo '<span style="color:#6F6B62">(' . esc_html( $f['langue'] ) . ') : ';
			echo esc_html( implode( ', ', $libelles ) ) . '</span></li>';
		}

		echo '</ul>';
	}

	/* Famille 2 */
	echo '<p style="margin:0 0 6px"><strong>Doublons de collecte : ';
	echo count( $doub ) . ' groupe(s)</strong></p>';

	if ( ! empty( $doub ) ) {
		echo '<p style="margin:0 0 8px;color:#6F6B62;font-size:12px">';
		echo 'Meme langue, meme date, meme lieu. Verifier avant de fusionner : ';
		echo 'deux evenements distincts peuvent legitimement partager une salle ';
		echo 'et une date.</p>';
		echo '<ul style="margin:0;padding-left:18px">';

		$n = 0;

		foreach ( $doub as $g ) {
			if ( $n++ >= CS_GFS_MAX_AFFICHE ) {
				echo '<li style="color:#6F6B62">... et ' . ( count( $doub ) - CS_GFS_MAX_AFFICHE );
				echo ' autre(s).</li>';
				break;
			}

			echo '<li style="margin-bottom:6px"><span style="color:#6F6B62">';
			echo esc_html( $g['langue'] ) . '</span><br>';

			foreach ( $g['fiches'] as $f ) {
				echo '<a href="' . esc_url( get_edit_post_link( $f['id'] ) ) . '">';
				echo esc_html( wp_html_excerpt( $f['titre'], 70, '...' ) ) . '</a> ';
				echo '<span style="color:#6F6B62">(' . (int) $f['mots'] . ' mots)</span><br>';
			}

			echo '</li>';
		}

		echo '</ul>';
	}

	/* Famille 3 : unites militaires de montagne */
	$mil = isset( $rapport['militaires'] ) ? $rapport['militaires'] : array();
	echo '<p style="margin:12px 0 6px"><strong>Unites militaires de montagne : ';
	echo count( $mil ) . ' fiche(s) a examiner</strong></p>';
	if ( ! empty( $mil ) ) {
		echo '<p style="margin:0 0 8px;color:#6F6B62;font-size:12px">';
		echo 'Signalement, pas verdict. Une mention peut venir du seul NOM DU LIEU : ';
		echo 'le Festival des jardins alpestres se tient sur l esplanade des Chasseurs ';
		echo 'Alpins, a Albertville, et n a rien de militaire. Poser as_exclu = 1 sur ';
		echo 'la fiche pour la retirer du site (snippet 126).</p>';
		echo '<ul style="margin:0;padding-left:18px">';
		foreach ( $mil as $x ) {
			echo '<li style="margin-bottom:4px">';
			echo '<a href="' . esc_url( get_edit_post_link( $x['id'] ) ) . '">';
			echo esc_html( wp_html_excerpt( $x['titre'], 70, '...' ) ) . '</a> ';
			echo '<span style="color:#6F6B62">' . esc_html( implode( ', ', $x['mentions'] ) );
			if ( $x['dans_lieu_seul'] ) {
				echo ' — <em>uniquement dans le nom du lieu (' . esc_html( $x['lieu'] ) . ')</em>';
			}
			echo '</span></li>';
		}
		echo '</ul>';
	}

	echo '<p style="margin:10px 0 0;color:#6F6B62;font-size:12px">Releve du ';
	echo esc_html( $rapport['date'] ) . ', recalcule toutes les 30 minutes.</p>';
}

add_action( 'wp_dashboard_setup', function () {
	if ( ! current_user_can( 'edit_posts' ) ) {
		return;
	}

	wp_add_dashboard_widget(
		'cs_gfs_widget',
		'Structure du catalogue : taxonomies et doublons',
		'cs_gfs_afficher'
	);
} );
