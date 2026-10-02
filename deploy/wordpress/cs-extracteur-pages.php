<?php
/*
Plugin Name: Cultura Sabauda - Extracteur des pages d entree
Description: Mesure quotidienne des dix pages d entree, sans aucun jugement, et
  production d une file de constats types. Le site se mesure LUI-MEME : c est la
  seule architecture ou la regle de cloture tient. Un agent qui corrige ne peut
  pas declarer sa propre victoire, le releve du lendemain tranche.
  Ne 2026-08-03. Cf. docs/PANEL_PERSONAS_HOMEPAGES.md.
Author: Cultura Sabauda
Version: 1.0

  INSTALLATION : deposer dans wp-content/mu-plugins/. Actif automatiquement.
  Le cron quotidien s enregistre seul au premier chargement.

  LECTURE SEULE sur le contenu : ne modifie ni post, ni meta, ni terme. Les
  seules ecritures sont les options de releve, prefixees cs_pex_.

  METHODE, ET SES TROIS PIEGES, tous rencontres en direct le 2026-08-03 :
   1. Les feuilles de style de ce site contiennent des libelles de section en
      clair. Une recherche dans le HTML brut tombe d abord dans un commentaire
      CSS. On retire style, script et commentaires AVANT toute analyse.
   2. L accueil rend les memes cartes DEUX FOIS : une serie mobile sans libelle,
      puis la serie desktop libellee. On dedoublonne sur le couple section+slug.
   3. Les h3 sont des titres de CARTES, pas de sections. Marqueurs de section :
      h1, h2, et class section-title__label.

  Le comptage passe par SQL direct et jamais par get_posts ni WP_Query, qui
  masquent silencieusement les tribe_events passes. Ecart constate sur ce site :
  324 fiches en SQL contre 224 vues par l API.
*/

if ( ! defined( 'ABSPATH' ) ) { exit; }

define( 'CS_PEX_OPT_DERNIER', 'cs_pex_dernier_releve' );
define( 'CS_PEX_OPT_HISTO',   'cs_pex_historique' );
define( 'CS_PEX_HISTO_MAX',   30 );
define( 'CS_PEX_HOOK',        'cs_pex_passe_quotidienne' );

/* ------------------------------------------------------------------ *
 * Perimetre : les dix pages, arbitre par Franck le 2026-08-03.
 * Ne PAS y ajouter les sous-territoires (Chablais, Monferrato, Cote
 * d Azur) ni les seize pages de province, bien qu ils portent le meme
 * cs_hub_type = territoire.
 * ------------------------------------------------------------------ */

function cs_pex_pages() {
	return array(
		array( 'id' => 928,  'role' => 'Accueil FR',            'lang' => 'fr', 'terr' => null ),
		array( 'id' => 1717, 'role' => 'Accueil IT',            'lang' => 'it', 'terr' => null ),
		array( 'id' => 2857, 'role' => 'Hub Savoie FR',         'lang' => 'fr', 'terr' => 'savoie' ),
		array( 'id' => 2858, 'role' => 'Hub Savoie IT',         'lang' => 'it', 'terr' => 'savoie' ),
		array( 'id' => 2859, 'role' => 'Hub Piemont FR',        'lang' => 'fr', 'terr' => 'piemont' ),
		array( 'id' => 2860, 'role' => 'Hub Piemont IT',        'lang' => 'it', 'terr' => 'piemont' ),
		array( 'id' => 2861, 'role' => 'Hub Vallee d Aoste FR', 'lang' => 'fr', 'terr' => 'vda' ),
		array( 'id' => 2862, 'role' => 'Hub Vallee d Aoste IT', 'lang' => 'it', 'terr' => 'vda' ),
		array( 'id' => 2863, 'role' => 'Hub Comte de Nice FR',  'lang' => 'fr', 'terr' => 'nice' ),
		array( 'id' => 2864, 'role' => 'Hub Comte de Nice IT',  'lang' => 'it', 'terr' => 'nice' ),
	);
}

/* ------------------------------------------------------------------ *
 * Etage 1 : extraction. Aucun avis, uniquement des faits.
 * ------------------------------------------------------------------ */

function cs_pex_extraire( $url ) {
	$x = wp_remote_get( $url, array( 'timeout' => 45 ) );

	if ( is_wp_error( $x ) ) {
		return array( 'erreur' => $x->get_error_message(), 'cartes' => array(), 'promesses' => array() );
	}

	$h    = wp_remote_retrieve_body( $x );
	$code = wp_remote_retrieve_response_code( $x );

	// Piege 1 : indispensable, et avant tout le reste.
	$h = preg_replace( '#<style[^>]*>.*?</style>#is', '', $h );
	$h = preg_replace( '#<script[^>]*>.*?</script>#is', '', $h );
	$h = preg_replace( '#<!--.*?-->#s', '', $h );

	$marqueurs = array();

	if ( preg_match_all( '#<h([12])[^>]*>(.*?)</h\1>#is', $h, $m, PREG_OFFSET_CAPTURE ) ) {
		foreach ( $m[2] as $t ) {
			$marqueurs[] = array(
				'pos'   => $t[1],
				'label' => trim( preg_replace( '/\s+/', ' ', wp_strip_all_tags( $t[0] ) ) ),
				'src'   => 'titre',
			);
		}
	}

	if ( preg_match_all( '#class="[^"]*section-title__label[^"]*"[^>]*>(.*?)<#is', $h, $m2, PREG_OFFSET_CAPTURE ) ) {
		foreach ( $m2[1] as $t ) {
			$marqueurs[] = array( 'pos' => $t[1], 'label' => trim( wp_strip_all_tags( $t[0] ) ), 'src' => 'label' );
		}
	}

	usort( $marqueurs, function ( $a, $b ) { return $a['pos'] - $b['pos']; } );

	preg_match_all(
		'#href="https://agendasabauda\.eu/(?:it/)?evenement/([a-z0-9\-]+)/"#i',
		$h, $me, PREG_OFFSET_CAPTURE
	);

	$cartes = array();
	$vus    = array();

	foreach ( $me[1] as $t ) {
		$pos     = $t[1];
		$slug    = $t[0];
		$section = '(hors section)';
		$src     = 'titre';

		foreach ( $marqueurs as $k ) {
			if ( $k['pos'] < $pos ) { $section = $k['label']; $src = isset( $k['src'] ) ? $k['src'] : 'titre'; } else { break; }
		}

		$cle = $section . '|' . $slug;

		// Piege 2 : le gabarit rend deux fois, mobile puis desktop.
		if ( isset( $vus[ $cle ] ) ) { continue; }
		$vus[ $cle ] = 1;

		$cartes[] = array( 'section' => $section, 'src' => $src, 'slug' => $slug, 'rang' => count( $cartes ) );
	}

	// La PROMESSE de la page : ce que ses titres annoncent au lecteur. Sans ça,
	// impossible de reperer un ecart entre l annonce et le contenu, qui est
	// precisement ce que le panel de personas sait voir et pas une metrique.
	$promesses = array();
	foreach ( $marqueurs as $k ) {
		if ( $k['label'] !== '' ) { $promesses[] = $k['label']; }
	}

	return array( 'code' => $code, 'cartes' => $cartes, 'promesses' => array_slice( $promesses, 0, 40 ) );
}

function cs_pex_faits( $slug ) {
	global $wpdb;

	$id = $wpdb->get_var( $wpdb->prepare(
		"SELECT ID FROM {$wpdb->posts}
		 WHERE post_name = %s AND post_type = 'tribe_events' AND post_status = 'publish'
		 LIMIT 1",
		$slug
	) );

	if ( ! $id ) { return null; }
	$id = (int) $id;

	$sd  = get_post_meta( $id, '_EventStartDate', true );
	$ed  = get_post_meta( $id, '_EventEndDate', true );
	$now = current_time( 'timestamp' );
	$ts  = strtotime( $sd );
	$te  = strtotime( $ed );

	$vid   = (int) get_post_meta( $id, '_EventVenueID', true );
	$adr   = $vid ? trim( (string) get_post_meta( $vid, '_VenueAddress', true ) ) : '';
	$ville = $vid ? trim( (string) get_post_meta( $vid, '_VenueCity', true ) ) : '';
	$terr  = wp_get_object_terms( $id, 'territoire', array( 'fields' => 'names' ) );

	return array(
		'id'          => $id,
		'titre'       => html_entity_decode( get_the_title( $id ), ENT_QUOTES, 'UTF-8' ),
		'debut'       => substr( (string) $sd, 0, 10 ),
		'fin'         => substr( (string) $ed, 0, 10 ),
		'duree_j'     => ( $ts && $te ) ? (int) round( ( $te - $ts ) / 86400 ) : 0,
		'jours_avant' => $ts ? (int) floor( ( $ts - $now ) / 86400 ) : 0,
		'en_cours'    => ( $ts && $te && $ts <= $now && $te >= $now ),
		'passe'       => ( $te && $te < $now ),
		'ville'       => $ville,
		'adresse'     => ( $adr !== '' ),
		'territoire'  => ( $terr && ! is_wp_error( $terr ) ) ? $terr[0] : '',
		'lang'        => function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $id ) : '',
		'mots'        => str_word_count( wp_strip_all_tags( (string) get_post_field( 'post_content', $id ) ) ),
	);

	// NOTE VOLONTAIRE : la gratuite n est PAS relevee comme un manque.
	// Arbitrage de Franck du 2026-08-03 : le site ne publie qu une seule
	// information tarifaire, la gratuite. 44 fiches a oui, 544 a zero, et zero
	// signifie « on ne sait pas », pas « payant ». L absence est neutre, jamais
	// un defaut. Ne pas reintroduire cette colonne.
}

/* ------------------------------------------------------------------ *
 * La passe : dix pages, un instantane.
 * ------------------------------------------------------------------ */

function cs_pex_passe() {
	$releve = array( 'date' => current_time( 'mysql' ), 'pages' => array() );

	foreach ( cs_pex_pages() as $pg ) {
		$url = get_permalink( $pg['id'] );

		if ( ! $url ) { continue; }

		$ex     = cs_pex_extraire( $url );
		$lignes = array();

		foreach ( $ex['cartes'] as $c ) {
			$f = cs_pex_faits( $c['slug'] );
			if ( $f ) {
				$lignes[] = array_merge( array( 'section' => $c['section'], 'src' => $c['src'], 'rang' => $c['rang'] ), $f );
			}
		}

		$releve['pages'][ $pg['id'] ] = array(
			'role'      => $pg['role'],
			'lang'      => $pg['lang'],
			'terr'      => $pg['terr'],
			'url'       => $url,
			'http'      => isset( $ex['code'] ) ? $ex['code'] : 0,
			'promesses' => isset( $ex['promesses'] ) ? $ex['promesses'] : array(),
			'lignes'    => $lignes,
		);
	}

	$releve['constats'] = cs_pex_constats( $releve );

	update_option( CS_PEX_OPT_DERNIER, $releve, false );

	// Historique : on ne garde que le resume, sinon l option explose.
	$histo = get_option( CS_PEX_OPT_HISTO, array() );
	$histo[] = array(
		'date'     => $releve['date'],
		'constats' => count( $releve['constats'] ),
		'par_classe' => cs_pex_compte_classes( $releve['constats'] ),
	);
	if ( count( $histo ) > CS_PEX_HISTO_MAX ) {
		$histo = array_slice( $histo, -CS_PEX_HISTO_MAX );
	}
	update_option( CS_PEX_OPT_HISTO, $histo, false );

	return $releve;
}

function cs_pex_compte_classes( $constats ) {
	$c = array( 1 => 0, 2 => 0, 3 => 0, 4 => 0 );
	foreach ( $constats as $x ) { $c[ $x['classe'] ] = ( isset( $c[ $x['classe'] ] ) ? $c[ $x['classe'] ] : 0 ) + 1; }
	return $c;
}

/* ------------------------------------------------------------------ *
 * Etage 3 : la file de constats, classee MECANIQUEMENT.
 * ------------------------------------------------------------------ *
 * La classe se deduit du TYPE DE MESURE qui a declenche le constat, jamais
 * d un jugement. Sans cette contrainte, tout finit en classe 1, la plus
 * facile a traiter.
 *   1. affichage / tri / filtre     -> snippet, corrigeable en code
 *   2. donnee de fiche manquante    -> lot de metas
 *   3. contenu ou traduction absent -> pipeline, remonte a Franck
 *   4. arbitrage editorial          -> Franck
 */

function cs_pex_fenetre_promise( $section ) {
	// Une section dont le TITRE promet une fenetre de temps. C est la seule
	// famille ou une duree longue est un defaut : ailleurs, une exposition de
	// six mois est parfaitement a sa place.
	$s = mb_strtolower( $section );

	if ( strpos( $s, '7 prochains jours' ) !== false || strpos( $s, 'prossimi 7 giorni' ) !== false ) {
		return array( 'jours' => 7, 'libelle' => $section );
	}
	if ( strpos( $s, 'week-end' ) !== false || strpos( $s, 'weekend' ) !== false ) {
		return array( 'jours' => 3, 'libelle' => $section );
	}
	if ( strpos( $s, "aujourd" ) !== false || strpos( $s, 'oggi' ) !== false ) {
		return array( 'jours' => 1, 'libelle' => $section );
	}
	return null;
}

function cs_pex_constats( $releve ) {
	$out = array();

	foreach ( $releve['pages'] as $pid => $pg ) {

		if ( (int) $pg['http'] !== 200 ) {
			$out[] = array(
				'classe' => 1, 'page' => $pg['role'], 'url' => $pg['url'],
				'mesure' => 'http', 'valeur' => $pg['http'],
				'constat' => 'La page ne repond pas en 200.',
			);
			continue;
		}

		foreach ( $pg['lignes'] as $l ) {

			// Mesure : date de fin passee, fiche encore affichee. Toujours un
			// defaut d affichage, jamais de contenu.
			if ( $l['passe'] ) {
				$out[] = array(
					'classe' => 1, 'page' => $pg['role'], 'url' => $pg['url'],
					'mesure' => 'fiche_passee', 'fiche' => $l['id'],
					'constat' => 'Fiche terminee le ' . $l['fin'] . ' encore affichee : ' . $l['titre'],
				);
			}

			// Mesure : la section PROMET une fenetre et la fiche a demarre avant.
			$fen = cs_pex_fenetre_promise( $l['section'] );
			// Deux corrections du 2026-08-03, apres verification de la premiere passe :
			// 1) comparaison de DATES et non d horodatages. Un evenement commencant
			//    aujourd hui a minuit etait signale des lors que la passe tournait
			//    dans la journee. Il est pourtant en plein dans la fenetre.
			// 2) la regle ne vaut que pour un VRAI libelle de section. Sur les hubs,
			//    le seul marqueur est un h2 rhetorique, « Que faire en Savoie ce
			//    week-end ? », qui n etiquette aucun bloc : les 47 cartes du
			//    territoire s y trouvaient rattachees et declenchaient 63 constats.
			if ( $fen && isset( $l['src'] ) && $l['src'] === 'label'
			     && $l['debut'] !== '' && $l['debut'] < current_time( 'Y-m-d' ) ) {
				$out[] = array(
					'classe' => 1, 'page' => $pg['role'], 'url' => $pg['url'],
					'mesure' => 'hors_fenetre_promise', 'fiche' => $l['id'],
					'constat' => 'Section « ' . $fen['libelle'] . ' » : fiche commencee le '
						. $l['debut'] . ', soit ' . abs( $l['jours_avant'] ) . ' jours avant, duree '
						. $l['duree_j'] . ' j. ' . $l['titre'],
				);
			}

			// Mesure : localisation introuvable. Drapeau rouge de Manuela et de
			// Karine, toutes deux sans voiture.
			// Corrige le 2026-08-03 : la premiere version signalait l absence de
			// RUE, et remontait 134 constats. Or aucun des 247 lieux du site n a de
			// rue : c est un seul fait systemique, pas 134 defauts. Toutes les
			// fiches avaient donc le meme constat, ce qui noyait la file sans rien
			// apprendre. On ne signale desormais que l absence TOTALE de repere :
			// ni rue, ni ville de lieu, ni as_ville. Un evenement itinerant qui
			// nomme sa ville n est pas un defaut.
			$repere = $l['adresse'] || $l['ville'] !== ''
			          || trim( (string) get_post_meta( $l['id'], 'as_ville', true ) ) !== '';
			if ( ! $repere ) {
				$out[] = array(
					'classe' => 2, 'page' => $pg['role'], 'url' => $pg['url'],
					'mesure' => 'localisation_absente', 'fiche' => $l['id'],
					'constat' => 'Ni rue, ni ville : ' . $l['titre'],
				);
			}

			// Mesure : langue de la fiche differente de celle de la page.
			if ( $l['lang'] && $pg['lang'] && $l['lang'] !== $pg['lang'] ) {
				$out[] = array(
					'classe' => 2, 'page' => $pg['role'], 'url' => $pg['url'],
					'mesure' => 'langue_fiche', 'fiche' => $l['id'],
					'constat' => 'Fiche en ' . $l['lang'] . ' sur une page en ' . $pg['lang'] . ' : ' . $l['titre'],
				);
			}

			// Mesure : contenu trop court. Drapeau rouge de Chantal, qui repart
			// sans rien avoir appris.
			if ( $l['mots'] > 0 && $l['mots'] < 150 ) {
				$out[] = array(
					'classe' => 3, 'page' => $pg['role'], 'url' => $pg['url'],
					'mesure' => 'contenu_court', 'fiche' => $l['id'],
					'constat' => $l['mots'] . ' mots seulement : ' . $l['titre'],
				);
			}
		}
	}

	// Mesure croisee : asymetrie entre les deux versions d un meme hub. Ce n est
	// jamais un defaut d affichage, toujours un manque de contenu ou de
	// traduction, donc classe 3.
	$par_terr = array();
	foreach ( $releve['pages'] as $pg ) {
		if ( ! $pg['terr'] ) { continue; }
		$par_terr[ $pg['terr'] ][ $pg['lang'] ] = count( $pg['lignes'] );
	}

	foreach ( $par_terr as $terr => $n ) {
		if ( ! isset( $n['fr'], $n['it'] ) ) { continue; }
		$fort = max( $n['fr'], $n['it'] );
		$faible = min( $n['fr'], $n['it'] );
		if ( $fort >= 10 && $faible < $fort * 0.5 ) {
			$out[] = array(
				'classe' => 3, 'page' => 'Hub ' . $terr, 'url' => '',
				'mesure' => 'asymetrie_langue',
				'constat' => 'Hub ' . $terr . ' : ' . $n['fr'] . ' fiches en FR contre '
					. $n['it'] . ' en IT.',
			);
		}
	}

	return $out;
}

/* ------------------------------------------------------------------ *
 * Cron quotidien
 * ------------------------------------------------------------------ */

add_action( CS_PEX_HOOK, 'cs_pex_passe' );

add_action( 'init', function () {
	if ( ! wp_next_scheduled( CS_PEX_HOOK ) ) {
		wp_schedule_event( time() + 300, 'daily', CS_PEX_HOOK );
	}
} );

/* ------------------------------------------------------------------ *
 * Widget de tableau de bord
 * ------------------------------------------------------------------ */

function cs_pex_afficher() {
	$r = get_option( CS_PEX_OPT_DERNIER, array() );

	if ( empty( $r ) || empty( $r['date'] ) ) {
		echo '<p style="margin:0">Aucun releve pour le moment. La premiere passe ';
		echo 'se declenchera automatiquement.</p>';
		return;
	}

	$constats = isset( $r['constats'] ) ? $r['constats'] : array();
	$classes  = cs_pex_compte_classes( $constats );

	$libelles = array(
		1 => 'Affichage / tri (corrigeable en code)',
		2 => 'Donnee de fiche manquante (lot)',
		3 => 'Contenu ou traduction absent (pipeline)',
		4 => 'Arbitrage editorial',
	);

	echo '<p style="margin:0 0 10px"><strong>' . count( $constats ) . ' constat(s)</strong> ';
	echo '<span style="color:#6F6B62">sur ' . count( $r['pages'] ) . ' pages, releve du ';
	echo esc_html( $r['date'] ) . '</span></p>';

	if ( empty( $constats ) ) {
		echo '<p style="margin:0;color:#1a7f37"><strong>Rien a signaler.</strong></p>';
		return;
	}

	foreach ( $libelles as $cl => $lib ) {
		if ( empty( $classes[ $cl ] ) ) { continue; }

		echo '<p style="margin:12px 0 4px"><strong>Classe ' . $cl . ' &middot; ' . esc_html( $lib );
		echo ' : ' . (int) $classes[ $cl ] . '</strong></p><ul style="margin:0;padding-left:18px">';

		$n = 0;
		foreach ( $constats as $c ) {
			if ( $c['classe'] !== $cl ) { continue; }
			if ( $n++ >= 8 ) {
				echo '<li style="color:#6F6B62">... et ' . ( $classes[ $cl ] - 8 ) . ' autre(s).</li>';
				break;
			}
			echo '<li style="margin-bottom:3px"><span style="color:#6F6B62">[' . esc_html( $c['mesure'] );
			echo '] ' . esc_html( $c['page'] ) . '</span> — ' . esc_html( $c['constat'] ) . '</li>';
		}
		echo '</ul>';
	}

	$histo = get_option( CS_PEX_OPT_HISTO, array() );
	if ( count( $histo ) > 1 ) {
		$prec = $histo[ count( $histo ) - 2 ];
		$delta = count( $constats ) - (int) $prec['constats'];
		echo '<p style="margin:12px 0 0;color:#6F6B62;font-size:12px">Passe precedente : ';
		echo (int) $prec['constats'] . ' constats (' . ( $delta >= 0 ? '+' : '' ) . $delta . ').</p>';
	}

	echo '<p style="margin:8px 0 0;color:#6F6B62;font-size:12px">La cloture d un constat ';
	echo 'ne se declare pas : elle se constate a la passe suivante.</p>';
}

add_action( 'wp_dashboard_setup', function () {
	if ( ! current_user_can( 'edit_posts' ) ) { return; }
	wp_add_dashboard_widget( 'cs_pex_widget', 'Pages d entree : file de constats', 'cs_pex_afficher' );
} );
