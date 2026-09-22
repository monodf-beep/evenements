<?php
/*
Plugin Name: Agenda Sabauda — la strate « moment fort » sur les home
Description: Un gabarit, pas un encart. Un rendez-vous qui en regroupe beaucoup d'autres
  (journées du patrimoine, Nuit des musées, Noël, carnaval d'Ivrée, festivals d'été)
  mérite une strate qui ne ressemble à aucune autre de la page — et il faut pouvoir en
  poser une nouvelle sans redessiner quoi que ce soit.

  DEMANDE DE FRANCK, 22/09/2026, dans l'ordre où elle est venue :
  1. « un espèce d'encart qui montre quelques cartes d'événements » ;
  2. « je trouve que c'est pas très différenciant de ce qu'on a actuellement » ;
  3. « il faut peut-être une strate supplémentaire, mais une strate qui soit différente
     des autres » ;
  4. « ce type de strate, il faudra pouvoir la personnaliser […] imaginons qu'on veuille
     faire la même strate pour Noël, pour Pâques, pour les festivals d'été » ;
  5. « quand on est sur la partie Savoie et qu'on a les deux, Piémont et Vallée d'Aoste,
     les deux encarts que tu me montres, ça fait beaucoup » ;
  6. « ça serait quand même bien d'inclure une image pour personnaliser ».

  CE QUI REND CETTE STRATE DIFFÉRENTE DES AUTRES, ET POURQUOI C'EST MESURÉ

  La home empile « À la une », « Ce week-end » et « Événements du jour », qui sont le
  MÊME objet : un petit titre de section, puis trois cartes image. Une quatrième grille
  s'y fond — c'est le reproche n° 2 ci-dessus, et il était justifié. Trois choses
  changent donc ici, et elles changent ensemble :

  - LE FOND. `#18365E`, le bleu sabauda. Relevé dans le HTML servi par le site le
    22/09 : cette couleur est DÉCLARÉE dans la palette (`--bleu-sabauda`) et n'est
    utilisée nulle part sur la home. C'est une couleur de la charte, pas une invention,
    et elle n'entre en concurrence avec rien.
  - LES BORDS. Arrachés, jamais droits (tracés SVG remplis de la couleur de la page).
    C'est le seul élément de la home qui n'a pas de bord droit. Franck, 21/09 :
    « irrégulier, pas forcément droit ».
  - LA GRAMMAIRE. Un PROGRAMME en texte, pas une SÉLECTION en images. Le lecteur d'un
    événement-parapluie veut voir qu'il y en a beaucoup et où ; il n'a pas besoin de
    trois vignettes de plus.

  CONTRASTES MESURÉS sur `#18365E` (WCAG 2.1) : crème `#F7F1E8` 10,8:1 ; chapô
  `#D6CEC0` 7,8:1 ; saumon `#F0916F` 5,2:1 ; bleu clair `#9FB3CD` 5,7:1. Tous AA.
  Le rouge de la charte `#DC5D45` ne donne que 3,3:1 sur ce bleu : c'est pourquoi le
  kicker utilise le saumon, qui en est une teinte claire, et pas le rouge lui-même.
  `tests/test_moment_fort_palette.py` rejoue ces calculs sur la palette ci-dessous,
  avec une contre-épreuve — une paire délibérément mauvaise DOIT être refusée.

  LES CINQ GARDE-FOUS, chacun né d'une faute déjà commise dans ce dépôt

  1. UN SEUIL. La strate ne s'affiche que si elle a de quoi se remplir. Mesuré le 22/09
     avant d'écrire la première version : l'agenda n'avait que SEPT fiches sur le
     week-end des Giornate Europee del Patrimonio. Une strate posée ce jour-là aurait
     été vide — exactement ce qui est arrivé à /choisir/ la veille, découvert par une
     capture d'écran de Franck.
  2. UNE FENÊTRE, DONC UNE EXTINCTION AUTOMATIQUE. `affiche_du` / `affiche_au` : elle
     s'allume seule et s'éteint seule. Règle 3 du CLAUDE.md — « un humain qui pense à
     la retirer » n'est pas un rouvreur.
  3. UN ZÉRO QUI DIT D'OÙ IL VIENT. Quand rien ne s'affiche, la source de la page porte
     un commentaire disant lequel des cas s'est produit : hors fenêtre, pas de volet
     pour ce territoire, ou sous le seuil AVEC le nombre trouvé.
  4. UNE SEULE STRATE PAR PAGE, JAMAIS DEUX. Reproche n° 5 ci-dessus. Quand le
     territoire actif n'a pas de volet à lui mais que deux voisins en ont un, ce n'est
     pas deux bandes empilées : c'est UNE bande à deux colonnes. Hauteurs mesurées sur
     la home réelle le 22/09 — bande complète 523 px au bureau / 951 px en mobile,
     bande « voisins » 344 / 690. Deux bandes complètes auraient fait 1 900 px de
     défilement en mobile, plus que « Ce week-end », déjà la plus longue strate.
  5. LA PRIORITÉ EST DÉCLARÉE, JAMAIS DEVINÉE. On aurait pu réutiliser la table de
     proximité `cs_a_lire_proximite()` pour choisir quel voisin montrer. On ne le fait
     PAS : pour un lecteur savoyard elle met le Piémont avant la Vallée d'Aoste, alors
     que Plaisirs de Culture se tient en français, dure neuf jours et compte soixante-dix
     rendez-vous. Deux détecteurs pour la même chose, un seul juste (ERREURS 2026-09-08).
     L'ordre des volets dans la configuration fait foi.

  CE QUI SE RÈGLE SANS TOUCHER AU CODE — c'est ça, le gabarit
     `couleur`  bleu | encre | rouge | vert        (liste FERMÉE, contrastes testés)
     `photo`    aucune | epinglee | large
     `mise`     programme-jours | voisins          (choisie seule selon le territoire)
     les textes, par langue ; la fenêtre ; le seuil ; l'ordre des volets.

  TEXTES ÉDITORIAUX. Les titres et chapôs ci-dessous sont du texte destiné au site : ils
  doivent passer la doctrine de rédaction (voix + vocabulaire interdit + charte) AVANT
  déploiement. Tant que ce n'est pas fait, ne pas pousser ce fichier en ligne.

  Rollback : supprimer ce fichier. Rien n'est écrit en base, aucun réglage à défaire.
*/
if (!defined('ABSPATH')) { exit; }

/* -------------------------------------------------------------------------
 * 1. LA PALETTE — liste fermée, contrastes mesurés, testés en fixture.
 * ---------------------------------------------------------------------- */
if (!function_exists('cs_mf_palette')) {
/**
 * `fond` porte la surface ; `texte` le corps ; `accent` le kicker et les mentions ;
 * `attenue` les phrases secondaires ; `discret` les sur-titres de lignes.
 *
 * Toute paire fond/couleur ici doit passer AA (4,5:1). Une couleur qu'on voudrait
 * ajouter se mesure D'ABORD : `tests/test_moment_fort_palette.py`.
 */
function cs_mf_palette($nom) {
    $p = array(
        // Bleu sabauda : déclaré dans la palette du site, inutilisé sur la home.
        'bleu'  => array('fond' => '#18365E', 'texte' => '#F7F1E8', 'accent' => '#F0916F',
                         'attenue' => '#D6CEC0', 'discret' => '#9FB3CD', 'filet' => 'rgba(247,241,232,.28)',
                         'filet_fin' => 'rgba(247,241,232,.13)'),
        // Encre : le noir des bordures de cartes, en aplat.
        'encre' => array('fond' => '#1D1D1B', 'texte' => '#F7F1E8', 'accent' => '#F0916F',
                         'attenue' => '#D6CEC0', 'discret' => '#B9B2A6', 'filet' => 'rgba(247,241,232,.30)',
                         'filet_fin' => 'rgba(247,241,232,.15)'),
        // Rouge de la charte, ASSOMBRI. Le `#DC5D45` de la charte, et même un `#B8402A`,
        // ne tiennent pas en aplat : la fixture a refusé trois de leurs quatre couleurs
        // de texte (22/09). `#99321F` les fait toutes passer avec de la marge.
        'rouge' => array('fond' => '#99321F', 'texte' => '#F7F1E8', 'accent' => '#F7D9CE',
                         'attenue' => '#F2DED6', 'discret' => '#EFCFC4', 'filet' => 'rgba(247,241,232,.34)',
                         'filet_fin' => 'rgba(247,241,232,.17)'),
        // Vert Vallée d'Aoste, assombri pour le contraste (le #1e7d34 des cartes ne passe
        // pas, et le #14562A laissait le saumon du kicker à 3,75:1 — refusé en fixture).
        'vert'  => array('fond' => '#104623', 'texte' => '#F7F1E8', 'accent' => '#F4A98C',
                         'attenue' => '#D6CEC0', 'discret' => '#A9C6B2', 'filet' => 'rgba(247,241,232,.28)',
                         'filet_fin' => 'rgba(247,241,232,.13)'),
    );
    return isset($p[$nom]) ? $p[$nom] : $p['bleu'];
}
}

/* -------------------------------------------------------------------------
 * 2. LES MOMENTS FORTS — la seule chose à éditer pour en poser un nouveau.
 * ---------------------------------------------------------------------- */
if (!function_exists('cs_moments_forts')) {
/**
 * POURQUOI PAS UN FICHIER DE CONFIG DU DÉPÔT : ce mu-plugin s'exécute sur
 * l'hébergement WordPress (OVH), qui n'a aucun accès au dépôt ni au VPS.
 * `config/*.json` vit côté pipeline ; ici, la liste doit être dans le fichier.
 *
 * Dates au format Y-m-d, bornes INCLUSES.
 *
 * `volets` : un par territoire couvert, DANS L'ORDRE DE PRIORITÉ (garde-fou 5).
 * Chaque volet porte sa propre fenêtre d'événements, parce qu'un même moment
 * n'a pas forcément les mêmes dates de part et d'autre — mesuré : les Giornate
 * tiennent en deux jours en Piémont, Plaisirs de Culture en neuf en Vallée d'Aoste.
 */
function cs_moments_forts() {
    return array(
        array(
            'slug'       => 'patrimoine',   // SANS millésime : la même strate revient chaque année.
            // L'ÉTIQUETTE, par langue. Posée par le pipeline depuis config/moments_forts.json
            // (utils/moments_forts.py), jamais par un modèle. Deux slugs et non un seul
            // parce que `post_tag` est une taxonomie TRADUITE par Polylang sur ce site :
            // mesuré le 22/09, six paires `-it` existent déjà en ligne (bard / bard-it,
            // conference / conference-it). Un libellé français envoyé à une fiche italienne
            // aurait fabriqué un terme suffixé, introuvable ici.
            // PLUSIEURS SLUGS PAR LANGUE, et ce n'est pas de la prudence gratuite.
            // Mesuré en ligne le 22/09, après la première pose des étiquettes : Polylang
            // a créé le terme italien avec un suffixe `-it` (`giornate-europee-del-
            // patrimonio-it`) BIEN QUE le libellé italien soit distinct du français. Le
            // suffixe est sa manière de séparer deux termes de langues différentes ; on
            // ne peut pas le prédire, on peut seulement accepter les deux formes.
            'etiquette'  => array('fr' => array('journees-europeennes-du-patrimoine'),
                                  'it' => array('giornate-europee-del-patrimonio',
                                                'giornate-europee-del-patrimonio-it')),
            'affiche_du' => '2026-09-22',
            'affiche_au' => '2026-09-27',
            'couleur'    => 'bleu',
            'photo'      => 'large',
            'seuil'      => 3,
            'image'      => array(
                'url'     => 'https://agendasabauda.eu/wp-content/uploads/2026/09/apertura-straordinaria-del-primo-piano-nobile-carte-123504ae8d.webp',
                'legende' => array('fr' => "Racconigi, le salon d'Hercule",
                                   'it' => "Racconigi, il salone d'Ercole"),
            ),
            // Textes quand le lecteur EST dans le territoire du volet.
            'chez_soi'   => array(
                'kicker' => array('fr' => 'Le rendez-vous du week-end',
                                  'it' => "L'appuntamento del fine settimana"),
                'cta'    => array('fr' => 'Voir le programme', 'it' => 'Vedi il programma'),
            ),
            // Textes quand il est à côté (mise « voisins »).
            'ailleurs'   => array(
                'kicker' => array('fr' => "De l'autre côté du col",
                                  'it' => "Dall'altra parte del colle"),
                'titre'  => array('fr' => "Les journées du patrimoine, ce week-end, en Italie",
                                  'it' => "Le giornate del patrimonio, questo fine settimana, in Italia"),
                'chapo'  => array('fr' => "En France, c'était le week-end dernier. À moins de deux heures de route, ça commence seulement.",
                                  'it' => "In Francia è stato il fine settimana scorso. A meno di due ore di strada, comincia adesso."),
            ),
            'volets'     => array(
                array(
                    'canon' => 'piemont',   // cle de cs_territoire_actif(), cf. cs_mf_volet_du_territoire
                    'terr'  => array('fr' => 'piemont', 'it' => 'piemonte'),
                    'debut' => '2026-09-26', 'fin' => '2026-09-27',
                    'nom'   => array('fr' => 'Piémont', 'it' => 'Piemonte'),
                    'quand' => array('fr' => '26 et 27 septembre', 'it' => '26 e 27 settembre'),
                    'dates' => array('26', '27', array('fr' => 'sept.', 'it' => 'set.')),
                    'titre' => array('fr' => "Journées européennes du patrimoine en Piémont",
                                     'it' => "Giornate Europee del Patrimonio in Piemonte"),
                    'chapo' => array('fr' => "Samedi soir, neuf lieux d'État ouvrent en nocturne pour un euro. En France, c'était le week-end dernier ; de ce côté du col, c'est maintenant.",
                                     'it' => "Sabato sera nove luoghi statali aprono in notturna a un euro. In Francia è stato il fine settimana scorso; da questa parte del colle, è adesso."),
                    'phrase'=> array('fr' => "Cinquante-deux lieux d'État ouvrent, dont neuf en nocturne à un euro le samedi soir.",
                                     'it' => "Cinquantadue luoghi statali aprono, nove dei quali in notturna a un euro il sabato sera."),
                    'pied'  => array('fr' => "Le programme officiel compte 52 rendez-vous en Piémont.",
                                     'it' => "Il programma ufficiale conta 52 appuntamenti in Piemonte."),
                    'lien'  => array('fr' => 'Le programme piémontais', 'it' => 'Il programma piemontese'),
                    'page'  => array('fr' => 'https://agendasabauda.eu/journees-europeennes-du-patrimoine-piemont/',
                                     'it' => 'https://agendasabauda.eu/it/giornate-europee-del-patrimonio-piemonte/'),
                    // Libellés des colonnes de la mise « programme-jours ».
                    'jours' => array(
                        array('date' => '2026-09-26',
                              'titre' => array('fr' => 'Samedi 26', 'it' => 'Sabato 26'),
                              'mention' => array('fr' => 'en soirée, 1 €', 'it' => 'di sera, 1 €')),
                        array('date' => '2026-09-27',
                              'titre' => array('fr' => 'Dimanche 27', 'it' => 'Domenica 27'),
                              'mention' => array('fr' => 'en journée', 'it' => 'di giorno')),
                    ),
                ),
                array(
                    'canon' => 'vda',
                    'terr'  => array('fr' => 'vallee-d-aoste', 'it' => 'valle-d-aosta'),
                    'debut' => '2026-09-19', 'fin' => '2026-09-27',
                    'nom'   => array('fr' => "Vallée d'Aoste", 'it' => "Valle d'Aosta"),
                    'quand' => array('fr' => "jusqu'au 27 septembre", 'it' => 'fino al 27 settembre'),
                    'dates' => array('19', '27', array('fr' => 'sept.', 'it' => 'set.')),
                    'titre' => array('fr' => "Plaisirs de Culture en Vallée d'Aoste",
                                     'it' => "Plaisirs de Culture in Valle d'Aosta"),
                    'chapo' => array('fr' => "Neuf jours de châteaux, de musées et de sites ouverts, dans la seule région italienne où le programme se lit en français.",
                                     'it' => "Nove giorni di castelli, musei e siti aperti, nella sola regione italiana dove il programma si legge in francese."),
                    'phrase'=> array('fr' => "Plaisirs de Culture ouvre châteaux, musées et sites pendant neuf jours, en français.",
                                     'it' => "Plaisirs de Culture apre castelli, musei e siti per nove giorni, in francese."),
                    'pied'  => array('fr' => "Le programme régional compte une soixantaine de rendez-vous.",
                                     'it' => "Il programma regionale conta una sessantina di appuntamenti."),
                    'lien'  => array('fr' => 'Le programme valdôtain', 'it' => 'Il programma valdostano'),
                    'page'  => array('fr' => 'https://agendasabauda.eu/plaisirs-de-culture-vallee-d-aoste/',
                                     'it' => 'https://agendasabauda.eu/it/plaisirs-de-culture-valle-d-aosta/'),
                    'jours' => array(),   // Neuf jours : pas de découpage par jour, la liste suffit.
                ),
            ),
        ),
    );
}
}

if (!function_exists('cs_moment_fort_actif')) {
/** Le moment dont la fenêtre couvre aujourd'hui, ou null. Le premier trouvé gagne. */
function cs_moment_fort_actif($aujourdhui = null) {
    $aujourdhui = $aujourdhui ?: current_time('Y-m-d');
    foreach (cs_moments_forts() as $m) {
        if ($aujourdhui >= $m['affiche_du'] && $aujourdhui <= $m['affiche_au']) {
            return $m;
        }
    }
    return null;
}
}

if (!function_exists('cs_mf_volet_du_territoire')) {
/**
 * Le volet qui correspond au territoire actif, ou null.
 *
 * C'est ce qui décide de la mise : un volet trouvé => « programme-jours » (le lecteur
 * est chez lui) ; aucun => « voisins » (il regarde à côté). JAMAIS les deux.
 *
 * DEUX IDENTIFIANTS POUR UN MÊME TERRITOIRE, et ils ne se ressemblent que par hasard.
 * `cs_territoire_actif()` rend une clé CANONIQUE — 'savoie', 'piemont', 'vda', 'nice'
 * (cf. cs_terr_canon_data) — tandis que `terr[$lang]` porte le slug du TERME de la
 * taxonomie, qui change de langue : 'piemont'/'piemonte', 'vallee-d-aoste'/'valle-d-aosta'.
 * La comparaison se faisait sur le second. Mesuré en ligne le 22/09, sur les trois cas :
 *   ?as_territoire=piemont        en fr => mise programme  (juste, PAR COÏNCIDENCE :
 *                                          la clé canonique du Piémont s'écrit
 *                                          exactement comme son slug français) ;
 *   ?as_territoire=piemonte       en it => mise voisins    (faux) ;
 *   ?as_territoire=vallee-d-aoste en fr => mise voisins    (faux).
 * Soit un cas juste sur trois, et c'est le seul que la fixture regardait — elle se
 * donnait raison sur la coïncidence. La comparaison porte donc désormais sur `canon`,
 * et `terr[$lang]` reste ce pour quoi il est fait : interroger la taxonomie.
 */
function cs_mf_volet_du_territoire($moment, $terr_canon, $lang) {
    if (!$terr_canon) { return null; }
    foreach ($moment['volets'] as $i => $v) {
        if (!empty($v['canon']) && $v['canon'] === $terr_canon) {
            return array($i, $v);
        }
    }
    return null;
}
}

/* -------------------------------------------------------------------------
 * 3. LES DONNÉES — les fiches de la période, par volet.
 * ---------------------------------------------------------------------- */
if (!function_exists('cs_mf_evenements')) {
/**
 * Renvoie array('total' => int, 'lignes' => array).
 *
 * TROIS FILTRES : territoire, fenêtre de dates, ÉTIQUETTE. Le troisième est le seul
 * qui sépare vraiment un événement-parapluie du reste du week-end. Mesuré le 22/09
 * sans lui : 41 fiches en ligne les 26-27 septembre sur ces deux territoires, dont
 * BeerCult, le Biella Sport Festival et une exposition Kusama — une strate qui promet
 * « patrimoine » et montre une fête de la bière.
 *
 * POURQUOI PAS UN AUTRE MARQUEUR. L'URL de source ne tient pas : l'enrichissement la
 * remplace par le site officiel (fiche 10403 a gardé `cultura.gov.it`, la 10456 a reçu
 * `museireali.beniculturali.it`). L'étiquette, elle, est posée à CHAQUE publication par
 * `scripts/publisher_as.py` depuis `config/moments_forts.json` : elle survit aux
 * `--update`, et elle suit la traduction, qui recopie territoire, source et dates.
 *
 * `etiquette` ABSENTE => on retombe sur date + territoire, et la strate ne doit PAS
 * être déployée sur un moment dont la fenêtre attrape n'importe quoi.
 */
function cs_mf_evenements($moment, $volet, $lang, $max = 40) {
    $terme = isset($volet['terr'][$lang]) ? $volet['terr'][$lang] : '';
    if (!$terme) { return array('total' => 0, 'lignes' => array()); }

    $cle = 'cs_mf_' . $moment['slug'] . '_' . $terme . '_' . $lang;
    $cache = get_transient($cle);
    if (is_array($cache)) { return $cache; }

    $args = array(
        'post_type'           => 'tribe_events',
        'post_status'         => 'publish',
        'posts_per_page'      => 60,
        'ignore_sticky_posts' => true,
        'lang'                => $lang,
        'tax_query'           => array(array('taxonomy' => 'territoire', 'field' => 'slug', 'terms' => $terme)),
        'meta_query'          => array('debut' => array(
            'key'     => '_EventStartDate',
            'value'   => array($volet['debut'] . ' 00:00:00', $volet['fin'] . ' 23:59:59'),
            'compare' => 'BETWEEN',
            'type'    => 'DATETIME',
        )),
        'orderby'             => array('debut' => 'ASC'),
    );
    $etiq = array();
    if (!empty($moment['etiquette'])) {
        $e = is_array($moment['etiquette'])
            ? (isset($moment['etiquette'][$lang]) ? $moment['etiquette'][$lang] : '')
            : $moment['etiquette'];
        $etiq = array_filter((array) $e);
    }
    if ($etiq) {
        $args['tax_query']['relation'] = 'AND';
        $args['tax_query'][] = array('taxonomy' => 'post_tag', 'field' => 'slug', 'terms' => $etiq);
    }
    $q = new WP_Query($args);

    $lignes = array();
    $vus = array();
    foreach ($q->posts as $p) {
        $debut = get_post_meta($p->ID, '_EventStartDate', true);
        $lieu  = get_post_meta($p->ID, 'as_lieu', true);
        $ville = get_post_meta($p->ID, 'as_ville', true);
        // Un même lieu qui ouvre deux fois le même jour n'occupe qu'une ligne : la
        // strate montre des LIEUX, pas des créneaux. Sinon Turin mange la colonne.
        $cle_ligne = substr($debut, 0, 10) . '|' . $lieu;
        if (isset($vus[$cle_ligne])) { continue; }
        $vus[$cle_ligne] = true;
        $lignes[] = array(
            'jour'  => substr($debut, 0, 10),
            'titre' => get_the_title($p),
            'url'   => get_permalink($p),
            'ou'    => trim($ville . ($ville && $lieu ? ' · ' : '') . $lieu),
        );
        // LE PLAFOND NE DOIT PAS AFFAMER UN JOUR. Il était à huit, et le tri est par
        // date croissante : les huit premières lignes étaient toutes du samedi, si
        // bien que le dimanche n'arrivait jamais jusqu'au découpage par jour. Constaté
        // par Franck sur la bande en ligne le 22/09 — « où est le dimanche ? » — et
        // mesuré ensuite sur le code déployé : lignes_par_jour = { 2026-09-26 : 8 }.
        // Le plafond sert à borner la requête, pas à choisir ce qu'on montre : c'est
        // le découpage par jour (quatre lignes chacun) qui décide.
        if (count($lignes) >= $max) { break; }
    }
    wp_reset_postdata();

    // Le total compte les FICHES de la période, pas les lignes montrées : règle 6,
    // un compteur doit dire ce qu'il compte.
    $out = array('total' => count($q->posts), 'lignes' => $lignes);
    set_transient($cle, $out, $out['total'] ? HOUR_IN_SECONDS : 10 * MINUTE_IN_SECONDS);
    return $out;
}
}

/* -------------------------------------------------------------------------
 * 4. LE RENDU.
 * ---------------------------------------------------------------------- */
if (!function_exists('cs_mf_fleche')) {
function cs_mf_fleche() {
    return '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"'
         . ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
         . '<path d="M3.4 12.3c4.6-.5 11.5-.7 17.1-.6"/>'
         . '<path d="M14.6 6.1c1.9 2.1 4 4.1 5.9 5.6c-2 1.6-4.1 3.6-5.8 5.9"/></svg>';
}
}

if (!function_exists('cs_mf_bords')) {
/** Les deux bords arrachés. Remplis de la couleur de la PAGE, pas de la bande. */
function cs_mf_bords($ou) {
    $d = $ou === 'haut'
        ? 'M0,0 H1200 V8 C1118,14 1049,3 972,9 C889,15 835,4 742,10 C664,15 600,5 518,11 '
          . 'C441,16 379,4 297,10 C223,15 163,5 84,11 C56,13 28,10 0,7 Z'
        : 'M0,22 H1200 V11 C1130,5 1058,17 978,12 C902,7 842,18 756,13 C676,8 618,19 534,13 '
          . 'C460,8 396,18 312,12 C238,7 170,16 90,11 C60,9 30,12 0,15 Z';
    return '<svg class="cs-mf__bord cs-mf__bord--' . $ou . '" viewBox="0 0 1200 22" preserveAspectRatio="none"'
         . ' aria-hidden="true" focusable="false"><path d="' . $d . '" fill="#F7F1E8"/></svg>';
}
}

if (!function_exists('cs_mf_figure')) {
/** L'image, si le moment en déclare une et que le réglage n'est pas « aucune ». */
function cs_mf_figure($moment, $lang) {
    $mode = isset($moment['photo']) ? $moment['photo'] : 'aucune';
    if ($mode === 'aucune' || empty($moment['image']['url'])) { return ''; }
    $leg = isset($moment['image']['legende'][$lang]) ? $moment['image']['legende'][$lang] : '';
    return '<figure class="cs-mf__photo"><img src="' . esc_url($moment['image']['url']) . '" alt="" loading="lazy">'
         . ($leg ? '<figcaption>' . esc_html($leg) . '</figcaption>' : '') . '</figure>';
}
}

if (!function_exists('cs_mf_rendu_programme')) {
/**
 * Mise « programme-jours » : le lecteur est dans le territoire du volet.
 *
 * Un jour déclaré qui n'a AUCUNE ligne est masqué, et le jour restant prend toute la
 * largeur. Un jour qui n'en a qu'une est montré.
 *
 * LE SEUIL ÉTAIT À DEUX, ET C'ÉTAIT FAUX. Constaté par Franck sur la bande en ligne le
 * 22/09 : « où est le dimanche ? ». Le dimanche n'avait qu'une fiche publiée, il
 * disparaissait — pendant que le bloc de dates, trois lignes plus bas, annonçait
 * « 26 & 27 sept. ». La bande se contredisait elle-même. Une colonne maigre coûte
 * moins cher qu'une promesse démentie dans le même cadre.
 */
function cs_mf_rendu_programme($moment, $volet, $lang, $data) {
    $h  = '<div class="cs-mf__gauche">';
    $h .= '<span class="cs-mf__kicker">' . esc_html($moment['chez_soi']['kicker'][$lang]) . '</span>';
    $h .= '<h2 class="cs-mf__titre">' . esc_html($volet['titre'][$lang]) . '</h2>';
    $h .= '<p class="cs-mf__chapo">' . esc_html($volet['chapo'][$lang]) . '</p>';
    $h .= '<div class="cs-mf__bas">';
    if (!empty($volet['dates'])) {
        $h .= '<div class="cs-mf__dates"><b>' . esc_html($volet['dates'][0]) . '</b><i>&amp;</i><b>'
            . esc_html($volet['dates'][1]) . '</b><em>' . esc_html($volet['dates'][2][$lang]) . '</em></div>';
    }
    $h .= '<a class="cs-mf__cta" href="' . esc_url($volet['page'][$lang]) . '">'
        . esc_html($moment['chez_soi']['cta'][$lang]) . ' ' . cs_mf_fleche() . '</a>';
    $h .= '</div></div>';

    // Répartition des lignes par jour déclaré ; un jour sous deux lignes disparaît.
    $colonnes = '';
    $nb_colonnes = 0;
    $restantes = $data['lignes'];
    foreach ($volet['jours'] as $j) {
        $duj = array();
        foreach ($restantes as $l) { if ($l['jour'] === $j['date']) { $duj[] = $l; } }
        if (!$duj) { continue; }
        $li = '';
        foreach (array_slice($duj, 0, 4) as $l) {
            $li .= '<li><a href="' . esc_url($l['url']) . '"><span class="cs-mf__lieu">' . esc_html($l['ou'])
                 . '</span><span class="cs-mf__quoi">' . esc_html($l['titre']) . '</span></a></li>';
        }
        $nb_colonnes++;
        $colonnes .= '<div class="cs-mf__jour"><h3 class="cs-mf__jour-titre">' . esc_html($j['titre'][$lang])
                   . '<em>' . esc_html($j['mention'][$lang]) . '</em></h3><ul class="cs-mf__liste">' . $li . '</ul></div>';
    }
    // Aucun jour déclaré (ou aucun retenu) : une seule liste, sans découpage.
    if ($colonnes === '') {
        $li = '';
        foreach (array_slice($data['lignes'], 0, 6) as $l) {
            $li .= '<li><a href="' . esc_url($l['url']) . '"><span class="cs-mf__lieu">' . esc_html($l['ou'])
                 . '</span><span class="cs-mf__quoi">' . esc_html($l['titre']) . '</span></a></li>';
        }
        $colonnes = '<div class="cs-mf__jour cs-mf__jour--seul"><h3 class="cs-mf__jour-titre">'
                  . esc_html($volet['nom'][$lang]) . '<em>' . esc_html($volet['quand'][$lang])
                  . '</em></h3><ul class="cs-mf__liste">' . $li . '</ul></div>';
    }
    $pied = isset($volet['pied'][$lang]) ? '<p class="cs-mf__pied">' . esc_html($volet['pied'][$lang]) . '</p>' : '';

    // Une seule colonne retenue (un jour maigre écarté, ou un moment sans découpage) :
    // elle prend toute la largeur plutôt que de laisser la moitié droite vide — mesuré
    // sur le rendu réel du 22/09, où seul le samedi avait de quoi se montrer.
    $classe = 'cs-mf__droite' . ($nb_colonnes === 1 ? ' cs-mf__droite--une' : '');
    return $h . '<div class="' . $classe . '">' . $colonnes . $pied . '</div>';
}
}

if (!function_exists('cs_mf_rendu_voisins')) {
/**
 * Mise « voisins » : le territoire actif n'a pas de volet, un ou deux voisins en ont un.
 *
 * Pas de programme jour par jour ici. Un lecteur de Chambéry n'a pas besoin de la liste
 * des nocturnes de Turin, il a besoin de savoir que ça existe et où regarder — et c'est
 * ce qui garde la bande à la moitié de la hauteur de l'autre (mesuré : 344 px contre
 * 523 au bureau, 690 contre 951 en mobile).
 */
function cs_mf_rendu_voisins($moment, $volets, $lang) {
    $h  = '<div class="cs-mf__gauche">';
    $h .= '<span class="cs-mf__kicker">' . esc_html($moment['ailleurs']['kicker'][$lang]) . '</span>';
    $h .= '<h2 class="cs-mf__titre">' . esc_html($moment['ailleurs']['titre'][$lang]) . '</h2>';
    $h .= '<p class="cs-mf__chapo">' . esc_html($moment['ailleurs']['chapo'][$lang]) . '</p>';
    $h .= '</div><div class="cs-mf__droite">';
    foreach ($volets as $v) {
        $h .= '<div class="cs-mf__volet"><h3 class="cs-mf__jour-titre">' . esc_html($v['nom'][$lang])
            . '<em>' . esc_html($v['quand'][$lang]) . '</em></h3>'
            . '<p class="cs-mf__phrase">' . esc_html($v['phrase'][$lang]) . '</p>'
            . '<a class="cs-mf__lien" href="' . esc_url($v['page'][$lang]) . '">'
            . esc_html($v['lien'][$lang]) . ' ' . cs_mf_fleche() . '</a></div>';
    }
    return $h . '</div>';
}
}

if (!function_exists('cs_mf_page_existe')) {
/**
 * La page de destination existe-t-elle VRAIMENT ?
 *
 * POURQUOI CE GARDE-FOU. Une strate qui envoie sur un 404 est pire que pas de strate :
 * elle promet un programme et rend une page d'erreur, à la une de la home, le jour où
 * l'événement a lieu. Et la séquence qui y mène est facile — le mu-plugin déployé avant
 * que les pages dédiées soient écrites, puis l'étiquette posée sur les fiches, et la
 * bande s'allume toute seule sur une adresse vide.
 *
 * C'est la règle 3 du CLAUDE.md prise à l'envers : au lieu d'un état qui gare une fiche
 * sans personne pour la rouvrir, un état qui se ROUVRE tout seul. Le jour où la page est
 * publiée, la strate apparaît sans que personne touche à ce fichier.
 *
 * Une adresse d'un AUTRE domaine n'est pas vérifiable ici et passe : on ne bloque que ce
 * qu'on sait juger. Cache court : une page qu'on vient de publier doit s'allumer vite.
 */
function cs_mf_page_existe($url) {
    $url = trim((string) $url);
    if ($url === '') { return false; }
    $hote = parse_url($url, PHP_URL_HOST);
    $nous = parse_url(home_url('/'), PHP_URL_HOST);
    if ($hote && $nous && strtolower($hote) !== strtolower($nous)) {
        return true;   // hors du site : non vérifiable, donc non bloquant
    }
    $cle = 'cs_mf_page_' . md5($url);
    $cache = get_transient($cle);
    if ($cache !== false) { return $cache === '1'; }
    $id = url_to_postid($url);
    $ok = ($id > 0 && get_post_status($id) === 'publish');
    set_transient($cle, $ok ? '1' : '0', $ok ? HOUR_IN_SECONDS : 5 * MINUTE_IN_SECONDS);
    return $ok;
}
}

if (!function_exists('cs_mf_html')) {
/** La strate, ou un commentaire qui DIT pourquoi elle ne s'affiche pas. */
function cs_mf_html($moment, $lang, $terr_slug) {
    $seuil = isset($moment['seuil']) ? (int) $moment['seuil'] : 3;
    $trouve = cs_mf_volet_du_territoire($moment, $terr_slug, $lang);

    if ($trouve) {
        list($i, $volet) = $trouve;
        if (!cs_mf_page_existe(isset($volet['page'][$lang]) ? $volet['page'][$lang] : '')) {
            return '<!-- cs-moment-fort : ' . esc_html($moment['slug']) . '/' . esc_html($terr_slug)
                 . ' [' . esc_html($lang) . '] la page de destination n\'existe pas encore — strate masquée -->';
        }
        $data = cs_mf_evenements($moment, $volet, $lang);
        if ($data['total'] < $seuil) {
            return '<!-- cs-moment-fort : ' . esc_html($moment['slug']) . '/' . esc_html($terr_slug)
                 . ' [' . esc_html($lang) . '] ' . (int) $data['total'] . ' fiche(s) pour un seuil de '
                 . $seuil . ' — strate masquée -->';
        }
        $mise = 'programme';
        $corps = cs_mf_rendu_programme($moment, $volet, $lang, $data);
    } else {
        // Garde-fou 4 : une seule strate, à deux colonnes au plus — jamais deux bandes.
        $voisins = array();
        $traduits = 0;   // volets qui EXISTENT dans cette langue, page mise à part
        foreach ($moment['volets'] as $v) {
            if (!isset($v['nom'][$lang]) || !isset($v['page'][$lang])) { continue; }
            $traduits++;
            // Un volet dont la page n'existe pas encore n'est pas montré : mieux vaut
            // une bande à une colonne qu'un lien vers un 404.
            if (!cs_mf_page_existe($v['page'][$lang])) { continue; }
            $voisins[] = $v;
            if (count($voisins) >= 2) { break; }
        }
        if (!$voisins) {
            // Le zéro doit dire d'où il vient, et les deux causes ne se corrigent pas
            // de la même façon : traduire la configuration, ou publier la page.
            $cause = $traduits
                ? 'aucune page de destination publiée (' . $traduits . ' volet(s) traduits)'
                : 'aucun volet pour la langue ' . $lang;
            return '<!-- cs-moment-fort : ' . esc_html($moment['slug']) . ' — ' . esc_html($cause) . ' -->';
        }
        $mise = 'voisins';
        $corps = cs_mf_rendu_voisins($moment, $voisins, $lang);
    }

    $classes = 'cs-mf cs-mf--' . $mise;
    if (!empty($moment['photo']) && $moment['photo'] !== 'aucune') {
        $classes .= ' cs-mf--photo-' . $moment['photo'];
    }
    return '<section class="' . esc_attr($classes) . '" data-moment="' . esc_attr($moment['slug']) . '">'
         . cs_mf_bords('haut')
         . '<div class="cs-mf__in">' . $corps . '</div>'
         . cs_mf_figure($moment, $lang)
         . cs_mf_bords('bas')
         . '</section>';
}
}

if (!function_exists('cs_mf_css')) {
function cs_mf_css($moment) {
    $c = cs_mf_palette(isset($moment['couleur']) ? $moment['couleur'] : 'bleu');
    $v = '';
    foreach ($c as $k => $val) { $v .= '--mf-' . $k . ':' . $val . ';'; }
    return '<style id="cs-moment-fort">
.cs-mf{' . $v . 'position:relative;margin:34px 0 30px;width:100vw;margin-left:calc(50% - 50vw);
 background:var(--mf-fond);color:var(--mf-texte);font-family:\'Nunito Sans\',sans-serif;overflow:hidden;isolation:isolate}
/* `100vw` compte la gouttière de la barre de défilement (le site force overflow-y:scroll) :
   la bande dépasse donc de 7,5 px de CHAQUE côté, symétriquement. Mesuré le 22/09 :
   scrollWidth 375 pour une fenêtre de 390, 1273 pour 1280 — aucun défilement horizontal.
   Corriger par une variable `calc(100vw - 100%)` posée sur le body NE MARCHE PAS : une
   propriété personnalisée est substituée telle quelle, donc le 100 % se résout chez
   l\'enfant, et la bande tombait à 950 px de large au format bureau. */
/* UNE SEULE BANDE, TOUJOURS. Le marqueur « A LA UNE » figure deux fois dans le contenu
   de la home : une pour le gabarit mobile (.as-home), une pour le gabarit bureau
   (.as-home-desktop). Le thème les rend exclusifs à 900 px (relevé dans le CSS servi le
   22/09 : @media (min-width:900px){.as-home{display:none}.as-home-desktop{display:block}}),
   donc en principe une seule apparaît. Franck en a pourtant vu DEUX. On pose la même
   règle ici, au MÊME point de rupture : si un cache ou une extension neutralise celle
   du thème, celle-ci tient, et aucune largeur ne se retrouve sans bande.
   LE DÉBORDEMENT, aussi : 100vw compte la gouttière de défilement, donc la bande
   dépasse de 7,5 px de chaque côté (mesuré : scrollWidth 1273 pour une page de 1265).
   overflow-x:clip sur le conteneur de la home coupe ce débordement sans créer de
   conteneur de défilement, contrairement à hidden, qui casserait les éléments collés. */
.as-home-root{overflow-x:clip}
@media(min-width:900px){.as-home .cs-mf{display:none}}
@media(max-width:899px){.as-home-desktop .cs-mf{display:none}}
.cs-mf *{box-sizing:border-box}
.cs-mf__bord{position:absolute;left:0;width:100%;height:22px;display:block;z-index:3}
.cs-mf__bord--haut{top:-1px}
.cs-mf__bord--bas{bottom:-1px}
.cs-mf__in{max-width:1120px;margin:0 auto;padding:40px 20px 34px;display:grid;grid-template-columns:1fr;gap:26px}
.cs-mf__kicker{display:block;font-size:10px;font-weight:800;letter-spacing:.2em;text-transform:uppercase;color:var(--mf-accent);margin-bottom:9px}
.cs-mf__titre{font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:26px;line-height:1.03;
 letter-spacing:.01em;color:var(--mf-texte);margin:0 0 11px}
.cs-mf__chapo{margin:0 0 18px;font-size:14px;line-height:1.55;color:var(--mf-attenue);max-width:44ch}
.cs-mf__bas{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.cs-mf__dates{display:inline-flex;align-items:baseline;gap:5px;padding:7px 13px 8px;border:1.5px solid var(--mf-texte);
 border-radius:4px;transform:rotate(-1.6deg);font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;line-height:1}
.cs-mf__dates b{font-size:30px;font-weight:600}
.cs-mf__dates i{font-size:15px;font-style:normal;opacity:.7}
.cs-mf__dates em{font-size:13px;font-style:normal;letter-spacing:.04em;opacity:.85;margin-left:2px}
.cs-mf__cta{display:inline-flex;align-items:center;gap:7px;background:var(--mf-texte);color:var(--mf-fond);text-decoration:none;
 font-size:13.5px;font-weight:800;padding:11px 16px;border-radius:4px;transform:rotate(.8deg)}
.cs-mf__cta:hover{transform:rotate(0)}
.cs-mf__droite{display:grid;grid-template-columns:minmax(0,1fr);gap:18px}
/* `min-width:0` PARTOUT dans la chaîne. Une piste de grille `1fr` a une largeur
   minimale AUTOMATIQUE : elle s\'élargit pour contenir son plus long enfant. Le nom de
   lieu est en `nowrap` (« COMPLESSO MONUMENTALE DEL CASTELLO DUCALE, GIARDINO E PARCO
   DI AGLIÉ »), donc la colonne poussait la bande hors de l\'écran au lieu d\'écrêter.
   Invisible tant qu\'il n\'y avait qu\'une colonne, visible dès qu\'il y en a eu deux —
   constaté par Franck le 22/09, la colonne du dimanche sortait à droite. */
.cs-mf__jour,.cs-mf__volet,.cs-mf__liste li,.cs-mf__liste a{min-width:0}
.cs-mf__jour-titre{margin:0 0 9px;padding-bottom:7px;border-bottom:1px solid var(--mf-filet);
 font-family:\'La Semplicita\',\'Saira Condensed\',sans-serif;font-weight:600;font-size:17px;letter-spacing:.02em;
 display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.cs-mf__jour-titre em{font-family:\'Nunito Sans\',sans-serif;font-style:normal;font-size:10px;font-weight:800;
 letter-spacing:.14em;text-transform:uppercase;color:var(--mf-accent);white-space:nowrap}
.cs-mf__liste{list-style:none;margin:0;padding:0}
.cs-mf__liste li{padding:7px 0;border-bottom:1px solid var(--mf-filet-fin)}
.cs-mf__liste li:last-child{border-bottom:0}
.cs-mf__liste a{text-decoration:none;color:inherit;display:block}
.cs-mf__liste a:hover .cs-mf__quoi{text-decoration:underline;text-underline-offset:3px}
.cs-mf__lieu{display:block;font-size:10.5px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
 color:var(--mf-discret);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* Les vrais titres de fiches font deux à trois lignes (« Arte e naturalia : deux visites
   croisent art et nature au château d\'Agliè »), et certains noms de lieu en font autant
   (« Complesso monumentale del Castello Ducale, giardino e parco di Aglié »). Sans
   écrêtage, quatre lignes remplissent la bande. Mesuré sur le rendu réel du 22/09. */
.cs-mf__quoi{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
 font-size:13.5px;line-height:1.3;color:var(--mf-texte)}
.cs-mf__pied{grid-column:1/-1;margin:2px 0 0;font-size:12px;color:var(--mf-discret)}
.cs-mf__phrase{margin:0 0 9px;font-size:13.5px;line-height:1.45;color:var(--mf-attenue)}
.cs-mf__lien{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:800;color:var(--mf-texte);
 text-decoration:none;border-bottom:1.5px solid var(--mf-filet);padding-bottom:2px}
.cs-mf__lien:hover{border-bottom-color:var(--mf-texte)}
.cs-mf__photo{display:none}
@media(min-width:900px){
 .cs-mf__in{grid-template-columns:minmax(0,44%) minmax(0,1fr);gap:46px;padding:54px 20px 46px}
 .cs-mf__titre{font-size:40px;max-width:16ch}
 .cs-mf__chapo{font-size:15px}
 .cs-mf--programme .cs-mf__droite{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px 26px}
 .cs-mf--programme .cs-mf__droite--une{grid-template-columns:minmax(0,1fr)}
 /* Colonne unique au bureau : la liste se met sur deux colonnes en GRILLE, pas en
    `columns` — le multi-colonnes CSS laissait les lignes déborder à droite parce que
    le nom de lieu est en `nowrap` et fixait une largeur de colonne hors cadre.
    Constaté sur le rendu réel du 22/09. */
 .cs-mf--programme .cs-mf__droite--une .cs-mf__liste{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:0 26px}
 .cs-mf--programme .cs-mf__droite--une .cs-mf__liste li{min-width:0}
 .cs-mf--voisins .cs-mf__in{grid-template-columns:minmax(0,34%) minmax(0,1fr);gap:44px;padding:46px 20px 42px}
 .cs-mf--voisins .cs-mf__titre{font-size:32px;max-width:18ch}
 .cs-mf--voisins .cs-mf__droite{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:30px}
 /* photo « épinglée » : un tirage penché à cheval sur le bord haut */
 .cs-mf--photo-epinglee .cs-mf__photo{display:block;position:absolute;right:calc(50% - 560px + 4px);top:-30px;width:196px;
  margin:0;z-index:4;transform:rotate(-2.6deg);background:var(--mf-texte);padding:7px 7px 0;border-radius:3px;
  box-shadow:0 10px 24px rgba(0,0,0,.28)}
 .cs-mf--photo-epinglee .cs-mf__photo img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:2px}
 .cs-mf--photo-epinglee .cs-mf__photo figcaption{font-size:9px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:#1D1D1B;padding:5px 2px 6px;text-align:center}
 .cs-mf--photo-epinglee .cs-mf__droite{padding-top:92px}
 .cs-mf--photo-epinglee .cs-mf__in{padding-top:64px}
 /* photo « large » : l\'image tient toute la hauteur, les bords arrachés passent devant */
 .cs-mf--photo-large .cs-mf__in{padding-left:calc(27% + 30px);grid-template-columns:minmax(0,31%) minmax(0,1fr);gap:34px}
 .cs-mf--photo-large .cs-mf__titre{font-size:33px}
 .cs-mf--photo-large .cs-mf__jour-titre{display:block;font-size:16px}
 .cs-mf--photo-large .cs-mf__jour-titre em{display:block;margin-top:3px}
 .cs-mf--photo-large .cs-mf__quoi{font-size:13px}
 .cs-mf--photo-large .cs-mf__lieu{font-size:10px;letter-spacing:.04em}
 .cs-mf--voisins.cs-mf--photo-large .cs-mf__in{grid-template-columns:minmax(0,36%) minmax(0,1fr)}
}
.cs-mf--photo-large .cs-mf__photo{display:block;position:absolute;left:0;top:0;bottom:0;width:27%;margin:0;padding:0;z-index:1}
.cs-mf--photo-large .cs-mf__photo img{width:100%;height:100%;object-fit:cover;display:block}
.cs-mf--photo-large .cs-mf__photo figcaption{position:absolute;left:0;right:0;bottom:0;padding:26px 14px 12px;
 background:linear-gradient(transparent,var(--mf-fond));color:var(--mf-texte);font-size:9.5px;font-weight:700;
 letter-spacing:.09em;text-transform:uppercase}
@media(max-width:899px){
 .cs-mf__droite{grid-template-columns:minmax(0,1fr)}
 .cs-mf__titre{font-size:26px}
 .cs-mf__in{padding:32px 18px 28px;gap:20px}
 .cs-mf__cta{flex:1;justify-content:center}
 /* La bande doit tenir dans un pouce de défilement, pas devenir une page à elle seule. */
 .cs-mf__liste li:nth-child(n+4){display:none}
 .cs-mf__jour-titre{font-size:16px}
 /* La photo passe EN TÊTE : reléguée après le texte elle devenait une bande orpheline,
    et le lecteur découvrait l\'image après avoir décidé de passer (mesuré sur capture). */
 .cs-mf--photo-large{display:flex;flex-direction:column}
 .cs-mf--photo-large .cs-mf__photo{position:relative;order:-1;width:100%;height:auto}
 .cs-mf--photo-large .cs-mf__photo img{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}
 .cs-mf--photo-large .cs-mf__photo figcaption{padding:22px 16px 10px}
 .cs-mf--photo-large .cs-mf__in{order:1;padding-top:22px}
 /* Pas de place pour un timbre-poste : la photo épinglée disparaît en petit écran. */
 .cs-mf--photo-epinglee .cs-mf__photo{display:none}
}
</style>';
}
}

/* -------------------------------------------------------------------------
 * 5. L'INSERTION.
 * ---------------------------------------------------------------------- */
/**
 * Juste avant « À la une », sur les DEUX gabarits de la home.
 *
 * Le marqueur `<!-- A LA UNE -->` est dans le CONTENU Gutenberg des pages 928 (FR) et
 * 1717 (IT), et il y figure deux fois — une pour le gabarit mobile, une pour le bureau.
 * Les deux variantes cohabitent dans le DOM, masquées l'une ou l'autre par media query :
 * insérer aux deux endroits est donc correct, et c'est le seul moyen d'être vu dans les
 * deux cas. Vérifié le 22/09 sur le HTML servi par le site.
 */
add_filter('the_content', function ($content) {
    $home_ids = function_exists('cs_agenda_home_page_ids') ? cs_agenda_home_page_ids() : array(928, 1717);
    if (is_admin() || !is_page($home_ids) || strpos($content, '<!-- A LA UNE -->') === false) {
        return $content;
    }

    $moment = cs_moment_fort_actif();
    if (!$moment) {
        return str_replace('<!-- A LA UNE -->',
            '<!-- cs-moment-fort : aucun moment dans sa fenêtre aujourd\'hui --><!-- A LA UNE -->', $content);
    }

    $lang = function_exists('pll_current_language') ? pll_current_language() : 'fr';
    $terr = function_exists('cs_territoire_actif') ? cs_territoire_actif() : '';

    $strate = cs_mf_html($moment, $lang, $terr);
    if (strpos($strate, '<section') !== 0) {
        // Commentaire de diagnostic : on l'insère quand même, c'est lui qui dit d'où
        // vient le zéro quand Franck regarde la source de la page.
        return str_replace('<!-- A LA UNE -->', $strate . '<!-- A LA UNE -->', $content);
    }
    return str_replace('<!-- A LA UNE -->', cs_mf_css($moment) . $strate . '<!-- A LA UNE -->', $content);
}, 22);
