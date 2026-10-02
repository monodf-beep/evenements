<?php
/*
Plugin Name: Cultura Sabauda - Garde-fou nationalisation
Description: Widget de tableau de bord, lecture seule, qui repere dans les fiches
  evenement publiees les manquements au Lexique sabaud : mots proscrits (frontiere,
  versant, transalpin, de part et d autre...), designations de langue proscrites
  (francoprovencal, arpitan, patois), emplois de la nationalite pour une personne
  ou un lieu, et tournures d exotisation. Aucune ecriture sur le contenu, aucun
  affichage cote visiteur.
Author: Cultura Sabauda
Version: 2.0

  INSTALLATION : deposer dans  wp-content/mu-plugins/cs-garde-fou-nationalisation.php
  Actif automatiquement (must-use). Rien a activer, rien a configurer.

  LECTURE SEULE : le plugin ne modifie ni les posts, ni les termes, ni les options.
  La seule ecriture en base est le transient de cache (table des options), qui expire
  seul au bout de 30 minutes. Le prefixe des tables n est jamais ecrit en dur :
  tout passe par $wpdb->posts et $wpdb->prefix, qui valent ici wor4956_.

  VERSION 2, calibree sur les 89 occurrences reelles du premier scan.
  Trois nouveautes :
    1. Exclusions elargies (histoire, corpus artistiques, langue, institutions
       et competitions) et pluriels manquants corriges, notamment « textes ».
    2. Trois familles de detection nouvelles : mots proscrits par le Lexique,
       langue proscrite, exotisation.
    3. Affichage reorganise par GRAVITE et non plus par territoire.
*/

if ( ! defined( 'ABSPATH' ) ) { exit; }

/* ------------------------------------------------------------------ *
 * Constantes de reglage
 * ------------------------------------------------------------------ */

// Cle du transient de cache. Incrementer le suffixe si les motifs changent,
// cela invalide proprement les caches deja poses.
define( 'CS_GFN_CACHE_KEY', 'cs_gfn_rapport_v2' );

// Ancienne cle, conservee pour pouvoir la purger proprement.
define( 'CS_GFN_CACHE_KEY_V1', 'cs_gfn_rapport_v1' );

// Duree de vie du cache. Le scan ne doit pas repartir a chaque chargement
// du tableau de bord.
define( 'CS_GFN_CACHE_TTL', 30 * MINUTE_IN_SECONDS );

// Plafond de fiches analysees en une passe, garde-fou de performance.
define( 'CS_GFN_MAX_POSTS', 1500 );

// Nombre de fiches detaillees affichees par section dans le widget.
define( 'CS_GFN_MAX_AFFICHE', 25 );

/* ------------------------------------------------------------------ *
 * 1. Enregistrement du widget, administrateurs seulement
 * ------------------------------------------------------------------ */

add_action( 'wp_dashboard_setup', 'cs_gfn_enregistrer_widget' );

function cs_gfn_enregistrer_widget() {

    // Inerte pour tout le monde sauf les administrateurs.
    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    wp_add_dashboard_widget(
        'cs_gfn_widget',
        'Garde-fou Lexique sabaud (fiches evenement)',
        'cs_gfn_afficher_widget'
    );
}

/* ------------------------------------------------------------------ *
 * 2. Listes d exclusion de la famille NATIONALITE, documentees
 * ------------------------------------------------------------------ *
 *
 * Principe : on regarde les trois mots qui precedent l occurrence, en sautant
 * les determinants et prepositions. Si l un de ces mots figure dans une des
 * familles ci-dessous, l occurrence est ecartee, car l adjectif y qualifie
 * une institution, une norme, une langue, une periode historique ou un genre,
 * pas une personne ni un lieu.
 *
 * Ces exclusions ne valent QUE pour la famille nationalite. Les mots proscrits
 * par le Lexique (bloc rouge) n ont pas d exclusion contextuelle, sauf les trois
 * exceptions explicitement prevues plus bas.
 *
 * FAMILLE A - Etat, droit, institutions publiques
 *   « la loi italienne », « le ministere italien », « l Etat italien »,
 *   « la nationalite italienne », « le consulat francais ».
 *
 * FAMILLE B - Langue et version linguistique
 *   « textes en italien », « en italien uniquement », « catalogue bilingue
 *   italien/anglais », « sous-titres francais ».
 *   CORRECTION V2 : la liste v1 contenait « texte » au singulier mais pas
 *   « textes », d ou une famille entiere de faux positifs. Toute la liste a
 *   ete repassee au crible des pluriels.
 *
 * FAMILLE C - Traites, accords, cooperation bilaterale
 *
 * FAMILLE D - Competitions, selections, institutions sportives et prix
 *   AJOUT V2 : « Comite italien paralympique », « Comite paralympique italien »,
 *   « titres italiens senior », « prix musicaux italiens », « la grande
 *   competition italienne » (Sanremo).
 *
 * FAMILLE E - Genres, corpus artistiques et culinaires etablis
 *   AJOUT V2 : « l art italien », « la ceramique italienne », « les arts
 *   decoratifs italiens », « le cinema italien », « les auteurs-compositeurs
 *   italiens », « le design italien ».
 *
 * FAMILLE F - Noms propres d institutions
 *
 * FAMILLE H - Designations historiques
 *   AJOUT V2 : « l unification italienne », « l unite italienne »,
 *   « le Risorgimento italien », « le Royaume d Italie », « le Musee national
 *   du Risorgimento italien ».
 *
 * EXCLUSION G - Composes bilateraux dans la famille nationalite seulement.
 *   Attention : « franco-italien » reste signale en priorite MOYENNE par la
 *   famille des mots proscrits quand nos territoires sont le sujet.
 *
 * EXCLUSION I - Citations
 *   Tout passage entre guillemets francais, courbes ou droits est masque.
 *
 * EXCLUSION J - Balises et attributs
 *   Le HTML est retire avant analyse.
 */

function cs_gfn_mots_exclus() {
    return array(

        // Famille A
        'loi', 'lois', 'legislation', 'legislations', 'decret', 'decrets',
        'reglement', 'reglements', 'ministere', 'ministeres', 'ministre',
        'ministres', 'etat', 'etats', 'gouvernement', 'gouvernements',
        'republique', 'republiques', 'constitution', 'constitutions',
        'parlement', 'parlements', 'senat', 'assemblee', 'assemblees',
        'prefecture', 'prefectures', 'administration', 'administrations',
        'douane', 'douanes', 'fisc', 'code', 'codes', 'droit', 'droits',
        'justice', 'tribunal', 'tribunaux', 'police', 'carabiniers',
        'gendarmerie', 'armee', 'armees', 'ambassade', 'ambassades',
        'ambassadeur', 'ambassadeurs', 'consulat', 'consulats',
        'nationalite', 'nationalites', 'passeport', 'passeports',
        'citoyennete', 'citoyen', 'citoyens', 'citoyenne', 'citoyennes',
        'frontiere', 'frontieres', 'territoire', 'territoires',
        'domaine', 'domaines', 'fonction', 'fonctions', 'service',
        'services', 'systeme', 'systemes', 'securite', 'sante',
        'education', 'universite', 'universites', 'academie', 'academies',
        'ordre', 'ordres', 'chambre', 'chambres', 'syndicat', 'syndicats',
        'conseil', 'conseils', 'commission', 'commissions',

        // Famille B, langue et version linguistique
        'langue', 'langues', 'version', 'versions', 'traduction',
        'traductions', 'traduit', 'traduite', 'traduits', 'traduites',
        'sous-titre', 'sous-titres', 'sous-titrage', 'sous-titree',
        'sous-titres', 'sous-titrees', 'doublage', 'doublages',
        'texte', 'textes', 'ecrit', 'ecrits', 'ecrite', 'ecrites',
        'parle', 'parlee', 'parles', 'parlees', 'surtitrage', 'surtitre',
        'surtitres', 'cours', 'apprentissage', 'grammaire', 'lexique',
        'lexiques', 'dictionnaire', 'dictionnaires', 'catalogue',
        'catalogues', 'bilingue', 'bilingues', 'trilingue', 'livret',
        'livrets', 'notice', 'notices', 'panneau', 'panneaux',
        'audioguide', 'audioguides', 'brochure', 'brochures',
        'sous-titrees', 'vocabulaire', 'prononciation',

        // Famille C
        'traite', 'traites', 'accord', 'accords', 'convention',
        'conventions', 'protocole', 'protocoles', 'sommet', 'sommets',
        'cooperation', 'cooperations', 'partenariat', 'partenariats',
        'jumelage', 'jumelages', 'union', 'unions', 'relation',
        'relations', 'diplomatie',

        // Famille D, competitions, selections, prix et institutions sportives
        'equipe', 'equipes', 'selection', 'selections', 'championnat',
        'championnats', 'coupe', 'coupes', 'federation', 'federations',
        'ligue', 'ligues', 'champion', 'championne', 'champions',
        'championnes', 'record', 'records', 'comite', 'comites',
        'paralympique', 'paralympiques', 'olympique', 'olympiques',
        'titre', 'titres', 'prix', 'competition', 'competitions',
        'tournoi', 'tournois', 'medaille', 'medailles', 'senior',
        'seniors', 'junior', 'juniors', 'club', 'clubs', 'podium',
        'podiums', 'classement', 'classements', 'concours',

        // Famille E, genres et corpus artistiques ou culinaires
        'cinema', 'cinemas', 'opera', 'operas', 'comedie', 'comedies',
        'chanson', 'chansons', 'variete', 'varietes', 'neorealisme',
        'baroque', 'renaissance', 'style', 'styles', 'ecole', 'ecoles',
        'courant', 'courants', 'repertoire', 'repertoires',
        'cuisine', 'cuisines', 'gastronomie', 'recette', 'recettes',
        'specialite', 'specialites', 'charcuterie', 'charcuteries',
        'fromage', 'fromages', 'vin', 'vins', 'litterature',
        'litteratures', 'poesie', 'poesies', 'peinture', 'peintures',
        'jardin', 'jardins', 'mode', 'art', 'arts', 'artistique',
        'artistiques', 'ceramique', 'ceramiques', 'decoratif',
        'decoratifs', 'decorative', 'decoratives', 'design', 'designs',
        'auteur', 'auteurs', 'compositeur', 'compositeurs',
        'auteur-compositeur', 'auteurs-compositeurs', 'sculpture',
        'sculptures', 'gravure', 'gravures', 'dessin', 'dessins',
        'photographie', 'photographies', 'musique', 'musiques',
        'musical', 'musicaux', 'musicale', 'musicales', 'danse',
        'danses', 'theatre', 'theatres', 'artisanat', 'orfevrerie',
        'mobilier', 'tableau', 'tableaux', 'oeuvre', 'oeuvres',
        'collection', 'collections', 'patrimoine', 'patrimoines',
        'musee', 'musees', 'galerie', 'galeries', 'exposition',
        'expositions', 'architecture', 'architectures', 'affiche',
        'affiches', 'estampe', 'estampes', 'verrerie', 'tapisserie',

        // Famille F, premier mot des noms propres d institutions
        'institut', 'instituts', 'alliance', 'alliances', 'radio',
        'radios', 'television', 'televisions', 'chaine', 'chaines',
        'air', 'banque', 'banques', 'tour', 'bibliotheque',
        'bibliotheques', 'fondation', 'fondations', 'maison', 'maisons',
        'lycee', 'lycees', 'agence', 'agences', 'poste', 'societe',
        'societes', 'compagnie', 'compagnies', 'association',
        'associations', 'centre', 'centres',

        // Famille H, designations historiques
        'unification', 'unifications', 'unite', 'unites', 'risorgimento',
        'royaume', 'royaumes', 'empire', 'empires', 'revolution',
        'revolutions', 'annexion', 'annexions', 'plebiscite',
        'plebiscites', 'histoire', 'histoires', 'historique',
        'historiques', 'independance', 'resistance', 'guerre', 'guerres',
        'national', 'nationale', 'nationaux', 'nationales', 'siecle',
        'siecles', 'medieval', 'medievale', 'antique', 'antiques',
    );
}

/**
 * Noms propres composes a ecarter tels quels, testes sur la fenetre de texte
 * qui entoure l occurrence (famille F, cas ou le mot declencheur est loin).
 */
function cs_gfn_expressions_exclues() {
    return array(
        'institut francais', 'alliance francaise', 'academie de france',
        'institut culturel italien', 'istituto italiano', 'radio france',
        'air france', 'banque de france', 'tour de france', 'coupe de france',
        'france bleu', 'france inter', 'france culture', 'france 2', 'france 3',
        'france 5', 'france televisions', 'bibliotheque nationale de france',
        'campus france', 'business france', 'atout france', 'miss france',
        'italia nostra', 'touring club italiano', 'rai italia',
        'a la francaise', 'a l italienne', 'a la italienne',
        'franco-italien', 'franco-italienne', 'italo-francais',
        'italo-francaise', 'franco-suisse', 'franco-italiennes',
        // Ajouts v2, designations historiques et corpus figes.
        'royaume d italie', 'royaume d’italie', 'unite italienne',
        'unification italienne', 'risorgimento italien',
        'musee national du risorgimento', 'jeunes italiens',
        'comite italien paralympique', 'comite paralympique italien',
        'banque d italie', 'tour d italie', 'giro d italia',
    );
}

/* ------------------------------------------------------------------ *
 * 3. Regles de detection, classees par bloc de gravite
 * ------------------------------------------------------------------ *
 *
 * Chaque regle porte :
 *   cle        identifiant court, affiche en tete d occurrence
 *   bloc       1 rouge, 2 orange, 3 gris
 *   famille    proscrit | langue | nationalite | exotisation | toponyme
 *   gravite    haute | moyenne | basse
 *   motif      expression reguliere, /iu, accents tolerants
 *   avant      mots declencheurs qui ANNULENT la detection (exception)
 *   sauf_si    expressions qui, presentes dans la fenetre, annulent la detection
 *   requiert   expressions dont AU MOINS UNE doit etre dans la fenetre
 *
 * Les regles sont evaluees dans l ordre. Une occurrence qui chevauche une
 * occurrence deja retenue est abandonnee : « cote italien » (proscrit) l emporte
 * donc sur « italien » (nationalite), ce qui est le classement voulu.
 */

function cs_gfn_regles() {

    // Mots de personne ou d emploi qui rendent « frontalier » licite.
    // « travailleur frontalier » est un statut administratif atteste.
    $personnes_emploi = array(
        'travailleur', 'travailleurs', 'travailleuse', 'travailleuses',
        'salarie', 'salaries', 'salariee', 'salariees',
        'actif', 'actifs', 'active', 'actives',
        'resident', 'residents', 'residente', 'residentes',
        'statut', 'statuts', 'permis', 'emploi', 'emplois',
        'main-d oeuvre', 'navetteur', 'navetteurs',
    );

    // Noms propres d institutions ou d evenements qui rendent licite
    // la mention d une langue autrement proscrite.
    $noms_propres_langue = array(
        'centre d etudes francoprovencales', 'centre d etudes',
        'fete internationale du francoprovencal', 'fete internationale',
        'fete valdotaine et internationale des patois', 'fete valdotaine',
        'concours cerlogne', 'bureau regional pour l ethnologie',
        'assessorat', 'guichet linguistique', 'sportello linguistico',
    );

    $mots_nom_propre_langue = array(
        'centre', 'centres', 'fete', 'fetes', 'festival', 'festivals',
        'concours', 'association', 'associations', 'musee', 'musees',
        'institut', 'instituts', 'bureau', 'bureaux', 'prix', 'journee',
        'journees', 'semaine', 'semaines', 'guichet', 'sportello',
        'assessorat', 'etudes', 'colloque', 'colloques',
    );

    return array(

        /* ---------- BLOC 1, ROUGE : mots proscrits par le Lexique ---------- */

        array(
            'cle' => 'frontiere', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:zone\s+fronti[eè]re|fronti[eè]res?)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'frontalier', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:zone\s+)?frontali(?:er|ers|[eè]re|[eè]res)(?![\p{L}])/iu',
            // EXCEPTION : autorise colle a un mot de personne ou d emploi.
            'avant' => $personnes_emploi,
        ),
        array(
            'cle' => 'versant', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])versants?(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'transalpin', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:transalpin(?:e|s|es)?|transalpino|transalpini|oltralpe)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'de-part-et-d-autre', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])de\s+part\s+et\s+d\s*[’\']?\s*autre(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'cote-national', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])c[oô]t[eé]\s+(?:fran[cç]ais(?:e|es)?|italien(?:ne|s|nes)?)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'franchir-les-alpes', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:franchir|franchit|franchissent|traverser|traverse|traversent)\s+les\s+Alpes(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'ligne-de-crete', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:lignes?\s+de\s+cr[eê]tes?|partage\s+des\s+eaux|seuil\s+alpin)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'neo-gentile', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:haute?-savoyard(?:e|s|es)?|n[eé]o-savoyard(?:e|s|es)?|n[eé]o-vald[oô]tain(?:e|s|es)?)(?![\p{L}])/iu',
        ),

        // Langue proscrite, priorite haute, exception nom propre.
        array(
            'cle' => 'langue-proscrite', 'bloc' => 1, 'famille' => 'langue',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(?:francoproven[cç]a(?:l|le|les|ux)|arpitan(?:e|s|es)?|patois(?:ant|ants|ante|antes)?|langues?\s+r[eé]gionales?)(?![\p{L}])/iu',
            'avant'   => $mots_nom_propre_langue,
            'sauf_si' => $noms_propres_langue,
        ),

        // Priorite moyenne, tolerances explicites.
        array(
            'cle' => 'franco-italien', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'moyenne',
            'motif' => '/(?<![\p{L}])franco-italien(?:ne|s|nes)?(?![\p{L}])/iu',
            // Tolere quand le sujet est Lyon-Milan ou Paris-Rome, pas nos territoires.
            'sauf_si' => array( 'lyon', 'milan', 'milano', 'paris', 'rome', 'roma' ),
        ),
        array(
            'cle' => 'transfrontalier', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'moyenne',
            'motif' => '/(?<![\p{L}])transfrontali(?:er|ers|[eè]re|[eè]res)(?![\p{L}])/iu',
            // Tolere dans le nom d un programme officiel, proscrit en prose.
            'sauf_si' => array( 'interreg', 'alcotra', 'gect', 'espace mont-blanc',
                                'programme europeen', 'feder' ),
        ),
        array(
            'cle' => 'espace-alpin', 'bloc' => 1, 'famille' => 'proscrit',
            'gravite' => 'moyenne',
            'motif' => '/(?<![\p{L}])espace\s+alpin(?![\p{L}])/iu',
            // Proscrit seulement quand il recouvre Savoie plus Piemont.
            'requiert' => array( 'savoie', 'savoia', 'savoyard', 'piemont',
                                 'piemonte', 'turin', 'torino' ),
        ),

        /* ---------- BLOC 2, ORANGE : nationalite pour personne ou lieu ---------- */

        array(
            'cle' => 'gentile', 'bloc' => 2, 'famille' => 'nationalite',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(italien|italienne|italiens|italiennes|francais|francaise|francaises|français|française|françaises)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'origine', 'bloc' => 2, 'famille' => 'nationalite',
            'gravite' => 'haute',
            'motif' => '/(?<![\p{L}])(originaire|natif|native|ne|nee|né|née|nes|nees|venu|venue|venus|venues|issu|issue|issus|issues)\s+(?:de|d|du|des|en|dans)[\s\'’]*(?:l[\s\'’]*)?(France|Italie)(?![\p{L}])/iu',
        ),

        /* ---------- BLOC 3, GRIS : exotisation et toponymes nus ---------- */

        array(
            'cle' => 'exotisation', 'bloc' => 3, 'famille' => 'exotisation',
            'gravite' => 'basse',
            'motif' => '/(?<![\p{L}])(?:[eé]crins?|pittoresques?|joyaux?|perles?|village\s+hors\s+du\s+temps|bon\s+plan\s+m[eé]connu|authentiques?|ancestral(?:e|es)?|ancestraux|nos\s+voisins\s+transalpins|escapade\s+transalpine|magie\s+des\s+Alpes)(?![\p{L}])/iu',
        ),
        array(
            'cle' => 'toponyme', 'bloc' => 3, 'famille' => 'toponyme',
            'gravite' => 'basse',
            'motif' => '/(?<![\p{L}])(France|Italie)(?![\p{L}])/u',
        ),
    );
}

/* ------------------------------------------------------------------ *
 * 4. Outils de texte
 * ------------------------------------------------------------------ */

/**
 * Minuscule sans accent, pour comparer aux listes d exclusion.
 */
function cs_gfn_normaliser( $texte ) {
    $texte = function_exists( 'mb_strtolower' )
        ? mb_strtolower( $texte, 'UTF-8' )
        : strtolower( $texte );

    $accents = array(
        'à' => 'a', 'â' => 'a', 'ä' => 'a', 'á' => 'a', 'ã' => 'a', 'å' => 'a',
        'ç' => 'c',
        'è' => 'e', 'é' => 'e', 'ê' => 'e', 'ë' => 'e',
        'ì' => 'i', 'í' => 'i', 'î' => 'i', 'ï' => 'i',
        'ò' => 'o', 'ó' => 'o', 'ô' => 'o', 'ö' => 'o', 'õ' => 'o',
        'ù' => 'u', 'ú' => 'u', 'û' => 'u', 'ü' => 'u',
        'ý' => 'y', 'ÿ' => 'y', 'ñ' => 'n',
        '’' => ' ', "'" => ' ', '‘' => ' ',
    );

    return strtr( $texte, $accents );
}

/**
 * Prepare le texte a analyser : HTML retire, entites decodees,
 * passages cites masques par des espaces de meme longueur en octets
 * afin de preserver les decalages de position.
 */
function cs_gfn_preparer_texte( $brut ) {

    $texte = wp_strip_all_tags( (string) $brut );
    $texte = html_entity_decode( $texte, ENT_QUOTES, 'UTF-8' );

    // EXCLUSION I : masquage des citations.
    $motifs_citation = array(
        '/«.*?»/us',
        '/“.*?”/us',
        '/"[^"]{0,600}"/us',
    );

    foreach ( $motifs_citation as $motif ) {
        $texte = preg_replace_callback(
            $motif,
            function ( $m ) { return str_repeat( ' ', strlen( $m[0] ) ); },
            $texte
        );
    }

    return $texte;
}

/**
 * Renvoie les mots significatifs qui precedent l occurrence, liaisons sautees,
 * du plus proche au plus lointain.
 */
function cs_gfn_mots_avant( $texte, $offset, $combien = 3 ) {

    $liaison = array( 'de', 'du', 'des', 'la', 'le', 'les', 'l', 'd', 'un', 'une',
                      'et', 'ou', 'tres', 'plus', 'au', 'aux', 'a', 'en', 'ce',
                      'cette', 'son', 'sa', 'ses', 'leur', 'leurs', 'nos', 'notre',
                      'grand', 'grande', 'grands', 'grandes', 'petit', 'petite' );

    $debut  = max( 0, $offset - 110 );
    $avant  = cs_gfn_normaliser( substr( $texte, $debut, $offset - $debut ) );
    $tokens = preg_split( '/[^a-z0-9-]+/', $avant, -1, PREG_SPLIT_NO_EMPTY );

    $mots = array();
    if ( ! $tokens ) {
        return $mots;
    }

    for ( $i = count( $tokens ) - 1; $i >= 0 && count( $mots ) < $combien; $i-- ) {
        $mot = $tokens[ $i ];
        if ( in_array( $mot, $liaison, true ) ) {
            continue; // les liaisons ne consomment pas un pas
        }
        $mots[] = $mot;
    }

    return $mots;
}

/**
 * Fenetre normalisee autour de l occurrence, pour les expressions figees.
 */
function cs_gfn_fenetre( $texte, $offset, $longueur, $marge = 60 ) {
    return cs_gfn_normaliser(
        substr( $texte, max( 0, $offset - $marge ), $longueur + ( 2 * $marge ) )
    );
}

/**
 * Exceptions propres a une regle : mots declencheurs amont, expressions
 * tolerees, expressions requises. Renvoie true si l occurrence est ecartee.
 */
function cs_gfn_regle_ecartee( $regle, $texte, $offset, $longueur ) {

    $fenetre = cs_gfn_fenetre( $texte, $offset, $longueur );

    if ( ! empty( $regle['avant'] ) ) {
        // Deux mots amont suffisent : « travailleur frontalier », « salaries
        // frontaliers », « Fete internationale du francoprovencal ».
        $mots = cs_gfn_mots_avant( $texte, $offset, 3 );
        foreach ( $mots as $mot ) {
            if ( in_array( $mot, $regle['avant'], true ) ) {
                return true;
            }
        }
    }

    if ( ! empty( $regle['sauf_si'] ) ) {
        foreach ( $regle['sauf_si'] as $expression ) {
            if ( false !== strpos( $fenetre, $expression ) ) {
                return true;
            }
        }
    }

    if ( ! empty( $regle['requiert'] ) ) {
        $vu = false;
        foreach ( $regle['requiert'] as $expression ) {
            if ( false !== strpos( $fenetre, $expression ) ) {
                $vu = true;
                break;
            }
        }
        if ( ! $vu ) {
            return true;
        }
    }

    return false;
}

/**
 * Exclusions de la famille NATIONALITE seulement.
 * Regarde les trois mots precedents en sautant determinants et prepositions,
 * puis la fenetre large pour les noms propres composes, puis deux tests
 * de contexte immediat ajoutes en v2 (usage linguistique).
 */
function cs_gfn_est_exclue( $texte, $offset, $longueur ) {

    $exclus = cs_gfn_mots_exclus();

    foreach ( cs_gfn_mots_avant( $texte, $offset, 3 ) as $mot ) {
        if ( in_array( $mot, $exclus, true ) ) {
            return true;
        }
    }

    // EXCLUSION G et famille F : fenetre large, expressions figees.
    $fenetre = cs_gfn_fenetre( $texte, $offset, $longueur, 40 );
    foreach ( cs_gfn_expressions_exclues() as $expression ) {
        if ( false !== strpos( $fenetre, $expression ) ) {
            return true;
        }
    }

    // FAMILLE B, contexte immediat : « en italien », « en francais » designent
    // toujours la langue. Test colle a l occurrence, pas sur la fenetre large,
    // pour ne pas blanchir un « pianiste italien » voisin.
    $depart   = max( 0, $offset - 14 );
    $immediat = cs_gfn_normaliser( substr( $texte, $depart, $offset - $depart ) );
    if ( preg_match( '/(?:^|[^a-z0-9-])en\s+$/', $immediat ) ) {
        return true;
    }

    // FAMILLE B, couples de langues : « italien/anglais », « francais/italien ».
    $car_avant = ( $offset > 0 ) ? substr( $texte, $offset - 1, 1 ) : '';
    $car_apres = substr( $texte, $offset + $longueur, 1 );
    if ( '/' === $car_avant || '/' === $car_apres ) {
        return true;
    }

    return false;
}

/**
 * Extrait de 80 caracteres centre sur l occurrence, occurrence balisee.
 */
function cs_gfn_extrait( $texte, $offset, $longueur ) {

    $avant_car = mb_strlen( substr( $texte, 0, $offset ), 'UTF-8' );
    $terme     = substr( $texte, $offset, $longueur );
    $terme_car = mb_strlen( $terme, 'UTF-8' );

    // 80 caracteres au total, repartis de part et d autre de l occurrence.
    $marge = max( 0, (int) floor( ( 80 - $terme_car ) / 2 ) );
    $depart = max( 0, $avant_car - $marge );

    $extrait = mb_substr( $texte, $depart, $marge + $terme_car + $marge, 'UTF-8' );
    $extrait = trim( preg_replace( '/\s+/u', ' ', $extrait ) );

    $html = esc_html( $extrait );
    $mot  = esc_html( trim( preg_replace( '/\s+/u', ' ', $terme ) ) );

    // Mise en evidence du terme dans l extrait deja echappe.
    if ( '' !== $mot ) {
        $html = str_replace( $mot, '<mark>' . $mot . '</mark>', $html );
    }

    return $html;
}

/* ------------------------------------------------------------------ *
 * 5. Territoires
 * ------------------------------------------------------------------ */

/**
 * Slugs racines des quatre territoires.
 *
 * RELEVES EN BASE le 2026-08-03, pas devines. Le site est bilingue et chaque
 * territoire porte DEUX termes racines, un par langue Polylang. Oublier les
 * slugs italiens rangerait toutes les fiches IT du mauvais cote du rapport.
 *
 *   comte-de-nice / contea-di-nizza
 *   piemont       / piemonte
 *   savoie        / savoia
 *   vallee-d-aoste / valle-d-aosta
 *
 * Les termes enfants (annecy, chambery, nice, aoste, turin, province-*,
 * provincia-*) remontent a leur parent par get_ancestors().
 */
function cs_gfn_slugs_territoires() {
    return array(
        'savoie', 'savoia',
        'piemont', 'piemonte',
        'vallee-d-aoste', 'valle-d-aosta',
        'comte-de-nice', 'contea-di-nizza',
    );
}

/**
 * Une fiche est « dans les quatre territoires » si un de ses termes territoire,
 * ou un de ses ancetres, porte un des slugs racines.
 */
function cs_gfn_est_en_territoire( $post_id, &$libelles ) {

    $libelles = array();
    $termes   = wp_get_object_terms( $post_id, 'territoire' );

    if ( is_wp_error( $termes ) || empty( $termes ) ) {
        return false;
    }

    $racines = cs_gfn_slugs_territoires();
    $trouve  = false;

    foreach ( $termes as $terme ) {

        $libelles[] = $terme->name;

        $chaine = array( $terme->slug );
        foreach ( get_ancestors( $terme->term_id, 'territoire' ) as $ancetre_id ) {
            $ancetre = get_term( $ancetre_id, 'territoire' );
            if ( $ancetre && ! is_wp_error( $ancetre ) ) {
                $chaine[] = $ancetre->slug;
            }
        }

        if ( array_intersect( $chaine, $racines ) ) {
            $trouve = true;
        }
    }

    $libelles = array_unique( $libelles );

    return $trouve;
}

/* ------------------------------------------------------------------ *
 * 6. Le scan
 * ------------------------------------------------------------------ */

/**
 * Parcourt les tribe_events publies et renvoie le rapport.
 *
 * SQL DIRECT VOULU. get_posts() et WP_Query masquent silencieusement les
 * evenements passes sur ce type de contenu : 324 fiches en SQL contre 224 par
 * l API. Ne pas remplacer cette requete par WP_Query.
 * Lecture seule, aucun prefixe de table en dur.
 */
function cs_gfn_scanner() {

    global $wpdb;

    $lignes = $wpdb->get_results(
        $wpdb->prepare(
            "SELECT ID, post_title, post_content
               FROM {$wpdb->posts}
              WHERE post_type = %s
                AND post_status = %s
           ORDER BY post_date DESC
              LIMIT %d",
            'tribe_events',
            'publish',
            CS_GFN_MAX_POSTS
        )
    );

    $rapport = array(
        'date'       => current_time( 'mysql' ),
        'analysees'  => is_array( $lignes ) ? count( $lignes ) : 0,
        'bloc1'      => array(), // mots proscrits et langue proscrite
        'bloc2_en'   => array(), // nationalite, fiche dans les quatre territoires
        'bloc2_hors' => array(), // nationalite, fiche hors des quatre territoires
        'bloc3'      => array(), // exotisation et toponymes nus
        'n_bloc1'    => 0,
        'n_bloc2'    => 0,
        'n_bloc3'    => 0,
        'occurrences' => 0,
        'tronque'    => ( is_array( $lignes ) && count( $lignes ) >= CS_GFN_MAX_POSTS ),
    );

    if ( empty( $lignes ) ) {
        return $rapport;
    }

    $regles = cs_gfn_regles();

    foreach ( $lignes as $ligne ) {

        $occurrences = array();

        // Le titre et le corps sont analyses separement, pour situer la faute.
        $sources = array(
            'titre' => cs_gfn_preparer_texte( $ligne->post_title ),
            'corps' => cs_gfn_preparer_texte( $ligne->post_content ),
        );

        foreach ( $sources as $ou => $texte ) {

            if ( '' === trim( $texte ) ) {
                continue;
            }

            foreach ( $regles as $regle ) {

                if ( ! preg_match_all( $regle['motif'], $texte, $trouvailles, PREG_OFFSET_CAPTURE ) ) {
                    continue;
                }

                foreach ( $trouvailles[0] as $trouvaille ) {

                    $brut     = $trouvaille[0];
                    $offset   = $trouvaille[1];
                    $longueur = strlen( $brut );

                    // Exceptions propres a la regle.
                    if ( cs_gfn_regle_ecartee( $regle, $texte, $offset, $longueur ) ) {
                        continue;
                    }

                    // Exclusions documentees, famille nationalite seulement.
                    if ( 'nationalite' === $regle['famille']
                        && cs_gfn_est_exclue( $texte, $offset, $longueur ) ) {
                        continue;
                    }

                    // Chevauchement : la regle la plus grave, evaluee en premier,
                    // l emporte. « cote italien » masque donc « italien ».
                    $doublon = false;
                    foreach ( $occurrences as $deja ) {

                        if ( $deja['ou'] !== $ou ) {
                            continue;
                        }

                        $chevauche = ( $offset < ( $deja['offset'] + $deja['longueur'] ) )
                                  && ( $deja['offset'] < ( $offset + $longueur ) );

                        // Le toponyme nu est absorbe par toute alerte voisine.
                        $voisin = ( 'toponyme' === $regle['famille']
                                    && abs( $deja['offset'] - $offset ) < 40 );

                        if ( $chevauche || $voisin ) {
                            $doublon = true;
                            break;
                        }
                    }
                    if ( $doublon ) {
                        continue;
                    }

                    $occurrences[] = array(
                        'ou'       => $ou,
                        'bloc'     => (int) $regle['bloc'],
                        'famille'  => $regle['famille'],
                        'gravite'  => $regle['gravite'],
                        'cle'      => $regle['cle'],
                        'terme'    => $brut,
                        'offset'   => $offset,
                        'longueur' => $longueur,
                        'extrait'  => cs_gfn_extrait( $texte, $offset, $longueur ),
                    );
                }
            }
        }

        if ( empty( $occurrences ) ) {
            continue;
        }

        $libelles = array();
        $en_terr  = cs_gfn_est_en_territoire( (int) $ligne->ID, $libelles );

        $rapport['occurrences'] += count( $occurrences );

        // Une meme fiche peut nourrir plusieurs blocs, avec ses seules
        // occurrences pertinentes dans chacun.
        $par_bloc = array( 1 => array(), 2 => array(), 3 => array() );
        foreach ( $occurrences as $occurrence ) {
            $par_bloc[ $occurrence['bloc'] ][] = $occurrence;
        }

        foreach ( $par_bloc as $bloc => $liste ) {

            if ( empty( $liste ) ) {
                continue;
            }

            // Les priorites hautes remontent en tete de fiche.
            usort( $liste, 'cs_gfn_trier_occurrences' );

            $fiche = array(
                'id'          => (int) $ligne->ID,
                'titre'       => $ligne->post_title,
                'territoires' => array_values( $libelles ),
                'en_terr'     => $en_terr,
                'occurrences' => $liste,
            );

            if ( 1 === $bloc ) {
                $rapport['bloc1'][] = $fiche;
                $rapport['n_bloc1'] += count( $liste );
            } elseif ( 2 === $bloc ) {
                if ( $en_terr ) {
                    $rapport['bloc2_en'][] = $fiche;
                } else {
                    $rapport['bloc2_hors'][] = $fiche;
                }
                $rapport['n_bloc2'] += count( $liste );
            } else {
                $rapport['bloc3'][] = $fiche;
                $rapport['n_bloc3'] += count( $liste );
            }
        }
    }

    // Les fiches les plus chargees en occurrences remontent en tete.
    $tri = function ( $a, $b ) {
        return count( $b['occurrences'] ) - count( $a['occurrences'] );
    };
    usort( $rapport['bloc1'], $tri );
    usort( $rapport['bloc2_en'], $tri );
    usort( $rapport['bloc2_hors'], $tri );
    usort( $rapport['bloc3'], $tri );

    return $rapport;
}

/**
 * Tri des occurrences dans une fiche : haute, puis moyenne, puis basse,
 * et a gravite egale, dans l ordre du texte.
 */
function cs_gfn_trier_occurrences( $a, $b ) {

    $rang = array( 'haute' => 0, 'moyenne' => 1, 'basse' => 2 );

    $ra = isset( $rang[ $a['gravite'] ] ) ? $rang[ $a['gravite'] ] : 3;
    $rb = isset( $rang[ $b['gravite'] ] ) ? $rang[ $b['gravite'] ] : 3;

    if ( $ra !== $rb ) {
        return $ra - $rb;
    }

    return $a['offset'] - $b['offset'];
}

/**
 * Renvoie le rapport, depuis le cache si possible.
 */
function cs_gfn_rapport( $forcer = false ) {

    if ( ! $forcer ) {
        $cache = get_transient( CS_GFN_CACHE_KEY );
        if ( is_array( $cache ) && isset( $cache['bloc1'] ) ) {
            $cache['cache'] = true;
            return $cache;
        }
    }

    $rapport = cs_gfn_scanner();
    set_transient( CS_GFN_CACHE_KEY, $rapport, CS_GFN_CACHE_TTL );
    $rapport['cache'] = false;

    return $rapport;
}

/* ------------------------------------------------------------------ *
 * 7. Affichage du widget, organise par GRAVITE
 * ------------------------------------------------------------------ */

function cs_gfn_afficher_widget() {

    if ( ! current_user_can( 'manage_options' ) ) {
        return;
    }

    // Relance manuelle du scan, protegee par nonce. Vide seulement le cache.
    $forcer = ( isset( $_GET['cs_gfn_refresh'] )
        && check_admin_referer( 'cs_gfn_refresh' ) );

    $rapport = cs_gfn_rapport( $forcer );

    $f1 = count( $rapport['bloc1'] );
    $f2 = count( $rapport['bloc2_en'] ) + count( $rapport['bloc2_hors'] );
    $f3 = count( $rapport['bloc3'] );

    echo '<p style="margin-top:0">';
    printf(
        '<strong>%d</strong> occurrence(s) au total, dans %d fiches publiees analysees. ' .
        'Interdits <strong>%d</strong> &middot; nationalite <strong>%d</strong> &middot; relecture <strong>%d</strong>.',
        (int) $rapport['occurrences'],
        (int) $rapport['analysees'],
        (int) $rapport['n_bloc1'],
        (int) $rapport['n_bloc2'],
        (int) $rapport['n_bloc3']
    );
    echo '</p>';

    if ( ! empty( $rapport['tronque'] ) ) {
        echo '<p><em>Analyse plafonnee a ' . (int) CS_GFN_MAX_POSTS . ' fiches, les plus recentes.</em></p>';
    }

    // BLOC 1, rouge. Interdits absolus du Lexique sabaud.
    cs_gfn_afficher_section(
        'Interdits du Lexique : mots proscrits et langue (' . $f1 . ' fiche(s), ' . (int) $rapport['n_bloc1'] . ' occurrence(s))',
        'Frontiere, versant, transalpin, de part et d autre, cote francais, francoprovencal, patois. A reecrire, sans discussion. La mention « moyenne » signale les cas tolerables (programme Interreg, axe Lyon-Milan).',
        $rapport['bloc1'],
        '#b32d2e'
    );

    // BLOC 2, orange. Nationalite pour une personne ou un lieu.
    cs_gfn_afficher_section(
        'Nationalite au lieu du gentile, fiches dans les quatre territoires (' . count( $rapport['bloc2_en'] ) . ')',
        'Le gentile du territoire est attendu : turinois, savoyard, valdotain, nicois.',
        $rapport['bloc2_en'],
        '#996800'
    );

    cs_gfn_afficher_section(
        'Nationalite, fiches hors des quatre territoires (' . count( $rapport['bloc2_hors'] ) . ')',
        'Hors perimetre sabaud, la mention nationale est souvent legitime. Les fiches sans terme territoire atterrissent ici : les lire quand meme.',
        $rapport['bloc2_hors'],
        '#996800'
    );

    // BLOC 3, gris. Relecture seulement.
    cs_gfn_afficher_section(
        'Pour relecture : exotisation et toponymes nus (' . $f3 . ')',
        'Ecrin, pittoresque, joyau, authentique, ancestral, et les mentions simples de France ou d Italie. Bruit attendu eleve, ce bloc n est pas une liste de fautes.',
        $rapport['bloc3'],
        '#8c8f94'
    );

    $lien = wp_nonce_url(
        add_query_arg( 'cs_gfn_refresh', '1', admin_url( 'index.php' ) ),
        'cs_gfn_refresh'
    );

    echo '<p style="margin-bottom:0;font-size:11px;color:#646970">';
    echo 'Scan du ' . esc_html( $rapport['date'] ) . ' ';
    echo empty( $rapport['cache'] ) ? '(frais)' : '(cache, 30 min)';
    echo ' &middot; <a href="' . esc_url( $lien ) . '">relancer le scan</a>';
    echo ' &middot; lecture seule, aucune fiche modifiee.';
    echo '</p>';
}

/**
 * Pastille de gravite affichee devant chaque occurrence.
 */
function cs_gfn_pastille( $occurrence ) {

    $couleurs = array(
        'haute'   => '#b32d2e',
        'moyenne' => '#996800',
        'basse'   => '#8c8f94',
    );

    $couleur = isset( $couleurs[ $occurrence['gravite'] ] )
        ? $couleurs[ $occurrence['gravite'] ]
        : '#8c8f94';

    $etiquette = $occurrence['cle'];
    if ( 'haute' !== $occurrence['gravite'] ) {
        $etiquette .= ' / ' . $occurrence['gravite'];
    }

    return '<code style="font-size:10px;color:#fff;background:' . esc_attr( $couleur ) .
        ';padding:0 4px;border-radius:2px">' . esc_html( $etiquette ) . '</code>';
}

function cs_gfn_afficher_section( $titre, $aide, $fiches, $couleur ) {

    echo '<h4 style="margin:12px 0 4px;border-left:4px solid ' . esc_attr( $couleur ) . ';padding-left:8px">';
    echo esc_html( $titre );
    echo '</h4>';

    if ( empty( $fiches ) ) {
        echo '<p style="margin:0 0 8px;color:#646970">Rien a signaler.</p>';
        return;
    }

    echo '<p style="margin:0 0 6px;font-size:11px;color:#646970">' . esc_html( $aide ) . '</p>';
    echo '<ul style="margin:0">';

    $i = 0;
    foreach ( $fiches as $fiche ) {

        if ( $i++ >= CS_GFN_MAX_AFFICHE ) {
            printf(
                '<li style="color:#646970">... et %d fiche(s) supplementaire(s).</li>',
                count( $fiches ) - CS_GFN_MAX_AFFICHE
            );
            break;
        }

        $edit = get_edit_post_link( $fiche['id'] );

        echo '<li style="margin-bottom:8px">';
        echo '<a href="' . esc_url( $edit ) . '"><strong>' . esc_html( $fiche['titre'] ) . '</strong></a>';

        if ( ! empty( $fiche['territoires'] ) ) {
            echo ' <span style="font-size:11px;color:#646970">[' .
                esc_html( implode( ', ', $fiche['territoires'] ) ) . ']</span>';
        }

        echo '<ul style="margin:2px 0 0 12px;font-size:12px">';
        foreach ( $fiche['occurrences'] as $occurrence ) {
            echo '<li style="color:#3c434a">';
            // Pastille et emplacement construits ici, deja echappes.
            echo cs_gfn_pastille( $occurrence ) . ' ';
            echo '<code style="font-size:11px">' . esc_html( $occurrence['ou'] ) . '</code> ';
            // Extrait deja echappe par cs_gfn_extrait().
            echo '&hellip; ' . $occurrence['extrait'] . ' &hellip;';
            echo '</li>';
        }
        echo '</ul>';

        echo '</li>';
    }

    echo '</ul>';
}
