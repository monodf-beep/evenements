<?php
/*
Plugin Name: Agenda Sabauda — Régie (skin + gouttières)
Description: Pose les emplacements publicitaires HORS FLUX que Ad Inserter/[cs_slot]
  gèrent mal : l'HABILLAGE / SKIN (bloc 4, la créative entière posée derrière la page,
  desktop) et les GOUTTIÈRES (blocs 5/6, skyscrapers latéraux sticky, desktop).
  Contrairement aux blocs 1-3, ces emplacements ne vivent pas dans le flux normal du
  thème — impossible de les envelopper avec le shortcode [cs_slot] de cs-regie-serve.php
  — donc ce fichier lit directement le backoffice et les pose lui-même via wp_footer, le
  contenu du site passant par-dessus. L'habillage tient en DEUX créatives : un FOND fixe
  dans la fenêtre et un BANDEAU en flux normal qui défile avec la page (cf. v2.0) ; les
  gouttières des blocs 5/6 restent collées.

  RÉUTILISE les fonctions déjà définies par cs-regie-serve.php (même mu-plugin folder,
  chargé avant celui-ci par ordre alphabétique : "cs-regie-serve.php" < "cs-regie.php") :
  cs_regie_serve_fetch() [fetch + cache 5 min de {backoffice}/api/active-ads] et
  cs_regie_host_ok() [allowlist de domaine https-only]. Pas de duplication de cette
  logique ; function_exists() en repli défensif si ce fichier tournait seul.

  Historique : v0.1 (scaffold, jamais déployé) pilotait ses créatives par une option WP
  statique (cs_regie), jamais remplie. v0.2/v0.3 (2026-08-04) : lit le backoffice comme
  cs-regie-serve.php, avec les VRAIS blocs 4/5/6 de app.py AD_BLOCKS (campagnes avec
  dates, pas de simple ON/OFF WP) — pas de kill-switch WP séparé, le statut de la
  campagne backoffice (active/ended, fenêtre de dates) fait déjà foi, comme pour les
  blocs 1-3.

  v0.4 (2026-08-05) : le bloc 4 n'était qu'un fond plein écran en position:fixed — ni
  bandeau haut, ni décalage du contenu, ni arrêt au pied de page (constat Franck en
  test réel : le bandeau chevauchait le menu du site au lieu de passer dessous, et les
  bandes latérales continuaient sous le footer). Remplacé par le format « habillage »
  validé sur maquette : un bandeau plein écran (bloc de flux normal, réinjecté en JS
  juste APRÈS la pile d'en-têtes sticky du thème — jamais avant, jamais par-dessus le
  menu — pour que le corps du site se décale sous lui) qui défile et disparaît avec la
  page, plus deux bandes latérales (position:fixed) qui prennent le relais pendant le
  défilement et s'arrêtent au-dessus du pied de page — même principe de calage que les
  gouttières des blocs 5/6, dupliqué plutôt que factorisé pour ne pas risquer de casser
  leur logique déjà éprouvée (cf. les nombreux correctifs commentés plus bas).

  v0.5 (2026-08-05) : $cs_skin_bp masquait le BANDEAU en même temps que les colonnes
  latérales, alors que lui seul (position fixed) a besoin de cette largeur pour ne pas
  chevaucher le contenu — le bandeau est en flux normal pleine largeur, sans ce risque.
  Constat Franck en test réel : sur un écran 1920×1080 à 175% d'échelle Windows + 80%
  de zoom navigateur (~1370px effectifs), le bandeau — visible dès 1280px avec l'ancien
  fond plein écran — avait disparu avec les colonnes alors qu'il tenait très bien à
  cette largeur. Le bandeau retombe désormais sur le seuil générique de .cs-regie
  (1280px) ; seules les colonnes restent réservées aux écrans ≥$cs_skin_bp.

  v0.6 (2026-08-05) : les colonnes latérales étaient ancrées aux BORDS DE L'ÉCRAN
  (left:0/right:0) alors que le bandeau est centré dans un conteneur de largeur FIXE
  ($cs_skin_container). Ça ne coïncide qu'à la largeur exacte $cs_skin_bp — sur tout
  écran plus large (le cas normal), un vide grandissant s'ouvrait entre bandeau et
  colonnes au lieu de se refermer. Capture Franck à l'appui (grand écran, vide béant de
  chaque côté du bandeau). Corrigé en calant les colonnes sur le bord du CONTENU
  (calc(50% + $cs_skin_container/2)) plutôt que sur le bord de la fenêtre : elles
  suivent désormais le conteneur quelle que soit la largeur d'écran, zéro vide.

  v0.7 (2026-08-05) : colonnes 320px -> 160px. Constat Franck sur son propre poste : meme
  a 130% de mise a l'echelle Windows (confort d'usage courant, pas un cas extreme —
  100% jugé « trop petit » par lui), les colonnes restaient masquées sous $cs_skin_bp
  (1590/1840px avec 320px de large) : « je ne vois pas assez ». Repris a l'identique la
  largeur des gouttieres des blocs 5/6 (deja en prod, deja eprouvee) plutot qu'une valeur
  choisie a vue : abaisse $cs_skin_bp a 1270/1520px, visible sur une part beaucoup plus
  large des ecrans reels sans changer le principe de calage (v0.6 ci-dessus inchangé).

  v0.8 (2026-08-05) — RETOUR A UNE IMAGE UNIQUE, et fin des v0.4 a v0.7. Celles-ci
  découpaient la créative en trois éléments (bandeau haut + deux bandes latérales) qui
  affichaient chacun une ZONE DIFFÉRENTE du même fichier via background-position : le
  bandeau son centre, les bandes ses bords extrêmes. Des pans entiers de l'image
  n'étaient donc affichés nulle part, et le raccord ne pouvait pas tomber juste : « on a
  des trous de partout, ça ne fait pas une skin, c'est n'importe quoi » (Franck, captures
  à l'appui). Les v0.5/v0.6/v0.7 ont chacune corrigé un symptôme de ce découpage (seuil
  du bandeau, ancrage des colonnes, largeur des colonnes) sans voir que le découpage
  LUI-MÊME était le défaut — trois correctifs pour une cause jamais traitée.
  Une skin, c'est l'image entière posée derrière la page, le contenu par-dessus. C'est
  redevenu ça : UN élément position:fixed portant toute la créative, `.site` (sans fond
  propre) au-dessus en z-index, et un décalage du contenu de 12.5vw pour dégager la bande
  haute. Plus aucun raccord à calculer, donc plus aucun trou possible — c'était d'ailleurs
  le principe de la v0.3, abandonné à tort en v0.4.

  v0.9 (2026-08-05) : le décalage du contenu de la v0.8 était un padding-top sur `.site`,
  qui plaçait la bande haute AU-DESSUS du menu sur l'accueil au lieu de dessous. Motif :
  sur l'accueil le menu n'est pas dans l'en-tête injecté (`.as-site-header` y est masqué,
  cf. snippet 62) mais bakè dans le CONTENU de la page, donc à l'intérieur de `.site` —
  un padding sur `.site` poussait donc le menu vers le bas lui aussi. Remplacé par une
  cale insérée en JS juste après la pile menu + barre territoire : elle tombe au bon
  endroit sur l'accueil comme sur les pages intérieures, sans distinguer les deux cas.
  « Le bandeau doit être en dessous du menu. Le corps du site doit se décaler
  suffisamment vers le bas pour que le bandeau ait la place » (Franck).

  v1.0 (2026-08-05) : la skin passe de position:fixed à position:ABSOLUE — elle défile
  donc avec la page et s'efface vers le haut sous le menu et la frise, au lieu de rester
  figée dans la fenêtre. « Le bandeau doit aussi scroller quand on scrolle vers le bas
  [...] on a uniquement les gouttières qui sont sticky, le haut des gouttières correspond
  au bas du menu » (Franck). Corrige du même coup le défaut constaté juste avant — « le
  fond de beige ne suit pas le corps du site » : figée pendant que le contenu défilait, la
  zone crème de la créative se désolidarisait du corps du site et le recouvrait de
  travers. Ancrée dans la page, elle ne peut plus se décaler : les deux bougent ensemble.
  Le bornage au pied de page et le plancher sous la barre collante disparaissent avec le
  position:fixed — la créative a désormais sa hauteur naturelle (56.25vw = 1080/1920).
  Les gouttières des blocs 5/6, elles, restent collées (cs-regie-clamp-js, inchangé).

  v1.1 (2026-08-05) : la v1.0 repositionnait la skin à chaque événement de défilement.
  Inutile — un élément en position:absolute est ancré dans la page et défile tout seul,
  à la vitesse exacte du contenu — et nuisible : le navigateur peint le défilement en
  continu tandis que l'événement JS arrive après coup, si bien que la skin rattrapait sa
  position avec un temps de retard visible. « Un effet de parallaxe entre le corps du site
  et le bandeau », « trop saccadé » (Franck). L'écouteur 'scroll' est donc supprimé : la
  position ne dépend plus que de la mise en page et ne se recalcule que quand celle-ci
  change. Corrigé au passage, même cause : la sélection de l'ancre de la cale testait la
  HAUTEUR des en-têtes, or sur l'accueil `.as-site-header` est un en-tête compact qui
  apparaît en cours de défilement — il entrait et sortait donc de la sélection au fil du
  défilement, déplaçant la cale sous la skin. Remplacé par un test sur `offsetParent`,
  qui ne bouge pas quand on défile.

  v1.2 (2026-08-05) : correctif de la v1.1 immédiatement repris — `offsetParent === null`
  ne signale pas seulement un élément `display:none`, il vaut AUSSI null pour tout élément
  en `position:fixed`. Les barres d'en-tête du site en font partie : toutes écartées, plus
  aucun repère trouvé, la cale retombait sur son repli « en tête de `.site` » et la
  créative repassait au-dessus du menu. Remplacé par `getClientRects().length === 0`, qui
  ne répond vide que si l'élément n'est vraiment pas rendu.

  v1.3 (2026-08-05) : les côtés disparaissaient dès qu'on descendait — « c'est pas sticky,
  les gouttières ne sont plus présentes quand on scroll » (Franck). Normal : depuis la v1.0
  la créative entière défilait, et elle ne fait que 56.25vw de haut. Or la demande porte
  sur DEUX comportements distincts — bandeau qui défile, bandes latérales collées sous le
  menu — et un seul élément ne peut pas faire les deux. La créative est donc à nouveau
  portée par trois éléments.
  ⚠️ Ce n'est PAS le découpage des v0.4-v0.7. Le défaut de celui-là n'était pas d'avoir
  plusieurs éléments, mais que chacun affichait une zone NON JOINTIVE du fichier : le
  bandeau en `background-size:1920px auto` centré montrait le MILIEU de l'image pendant que
  les bandes en montraient les bords extrêmes, laissant ~220px de créative de chaque côté
  affichés nulle part. Ici les trois partagent la même mise à l'échelle
  (`background-size:100vw auto` partout, « l'image fait exactement la largeur de l'écran »)
  et se partagent ses colonnes sans trou ni recouvrement : bandeau sur toute la largeur pour
  les lignes 0-240 (12.5vw de haut), bandes de 18.75vw (= 360/1920, la largeur exacte du
  décor latéral) alignées sur les bords de l'image. Les bandes partent de la ligne 0 et non
  de la ligne 240 : leur haut est masqué par le bandeau tant qu'on est en haut de page, donc
  le raccord tombe juste au pixel, puis le bandeau s'en va et elles prennent le relais.
  Le bandeau garde le placement sans JS au défilement de la v1.1 (pas de parallaxe) ; les
  bandes sont suivies en JS comme les gouttières, mais leur position ne change qu'aux rares
  moments où l'en-tête compact apparaît, jamais à chaque pixel.

  v1.4 (2026-08-05) — RETOUR A UN SEUL ELEMENT, et fin du découpage de la v1.3. Celui-ci
  faisait démarrer les bandes latérales à la ligne 0 de la créative pour que le raccord
  tombe juste en haut de page ; mais dès qu'on défilait, le bandeau glissait par-dessus des
  bandes qui affichaient toujours ce même haut d'image, si bien que le titre de l'annonceur
  apparaissait DEUX FOIS : « c'est comme si tu avais superposé deux gifs, ce n'est pas ça
  que je veux » (Franck, captures à l'appui).
  Version simplifiée demandée, et bien meilleure : un seul élément portant toute la
  créative, qui défile puis se FIGE quand le bas du bandeau atteint le menu — « tu mets le
  gif, tu as le bandeau, les gouttières, quand on scrolle il faut que ce soit sticky en haut
  des gouttières, en bas du bandeau ». Deux états (position:absolute puis position:fixed
  à `bas du menu − hauteur du bandeau`) qui coïncident au point de bascule, donc sans saut ;
  dans chacun la position est constante, donc le JS ne fait que choisir l'état et ne suit
  jamais le défilement pixel par pixel — pas de retour de la parallaxe de la v1.0.
  Une seule image affichée une seule fois : ni trou (v0.8) ni doublon (v1.3) possible.

  Conforme, au passage, à la spécification du format Page Skin (IQD/IAB, techspecs
  iqd-ao.de) : créative de fond 1920×1080 qui « reste visible en permanence dans la zone
  visible de l'utilisateur ». À noter — cette même spécification déconseille de placer du
  TEXTE dans le motif de fond et d'y ménager des zones creuses ou blanches, la visibilité
  dépendant de la résolution et de la mise en page ; la créative de test fait les deux (le
  titre « L'atmosfera sabauda » et la fenêtre crème centrale). À signaler aux annonceurs
  plutôt qu'à compenser en code.

  v1.5 (2026-08-05) : le point d'accrochage de la v1.4 valait « bas du menu − hauteur du
  bandeau ». Or le bas du menu n'est pas un repère stable : sur l'accueil la barre
  territoire s'en va en défilant pendant que l'en-tête compact apparaît, donc la valeur
  change en cours de route — le point d'accrochage bougeait sous une skin qui y était déjà
  accrochée, et elle sautait d'un cran de défilement à l'autre (« d'un cran de scroll à
  l'autre ça saute », Franck, captures à l'appui). Remplacé par une CONSTANTE : la skin
  s'accroche au haut de la fenêtre, bandeau juste au-dessus du bord. Le menu, opaque et
  au-dessus, recouvre le haut des gouttières : le rendu est celui demandé sans dépendre
  d'un repère mouvant. Supprimé au passage les fonctions footerTop()/headBottom() du script
  de la skin, devenues sans emploi (celles du clamp des gouttières sont intactes).

  v1.6 (2026-08-05) — LE SAUT N'ÉTAIT PAS DANS LES VALEURS, IL ÉTAIT DANS LE FAIT DE
  CALCULER. Les v1.4 et v1.5 basculaient la skin de position:absolute à position:fixed en
  JavaScript, sur l'événement de défilement. Or le navigateur PEINT le défilement avant
  d'exécuter le moindre script : à chaque cran de molette — une centaine de pixels d'un
  coup — la skin était donc d'abord peinte trop haut, puis remise en place au tour suivant.
  D'où un saut d'exactement un cran, que Franck a constaté sur trois versions de suite
  (« d'un cran de scroll à l'autre ça saute »). Aucun réglage de valeur ne pouvait le
  corriger — j'ai cherché deux fois du côté du point d'accrochage (v1.5) au lieu de voir que
  le défaut tenait à l'instant du calcul.
  Remplacé par `position:sticky` : le moteur de rendu fait le même travail, mais au moment
  où il peint. La skin est logée dans un rail (`#cs-skin-track`, position:absolute, de la
  cale au bas du document) parce qu'un élément sticky ne peut pas sortir de son parent, et
  colle à `top:-12.5vw`, soit la hauteur du bandeau. Il ne reste plus AUCUN écouteur de
  défilement dans le script de la skin : les seules bornes calculées sont celles du rail, et
  elles ne dépendent que de la mise en page.

  v1.7 (2026-08-05) : le rail de la v1.6 descendait jusqu'au bas du document, si bien que la
  skin restait collée derrière le pied de page — « les gouttières ne s'arrêtent pas au
  footer » (Franck, capture à l'appui). Le rail s'arrête désormais au haut du footer : comme
  un élément sticky ne peut pas sortir de son parent, la skin se décolle et remonte d'elle-
  même à l'arrivée du pied de page, toujours sans aucun calcul au défilement. Le repérage du
  footer reprend la liste de candidats et le garde-fou « 40 % hauts du document » du clamp
  des gouttières, qui évite qu'un <footer> de carte d'événement en milieu de page ne fasse
  passer le rail pour fini dès le premier tiers.

  v1.8 (2026-08-05) : « il reste un petit défaut en dessous des gouttières, on a une marge »
  (Franck). La créative est en 16/9 : mise à la largeur de l'écran elle fait 56.25vw de
  haut, et une fois collée son bandeau rangé au-dessus du bord il n'en restait que 43.75vw
  de visible — un peu moins que la hauteur d'une fenêtre courante, d'où une bande vide en
  bas. La hauteur est désormais calculée pour couvrir : au moins 9/7 de la fenêtre, puisque
  ce qui reste visible vaut 7/9 de la hauteur totale. `background-size:cover` remplace
  `100vw auto` pour remplir cette boîte plus haute que le ratio de l'image, quitte à rogner
  un peu les bords latéraux — ce que la spec du format prévoit explicitement (« le contenu
  peut dépasser les bords visibles du navigateur lors de la mise à l'échelle »).
  La hauteur du bandeau devient une variable CSS partagée avec la cale, qui doit dégager
  exactement cette hauteur-là : les deux ne peuvent plus diverger.

  v1.9 (2026-08-05) : « quand on scrolle de nouveau vers le haut, on n'arrive pas à avoir
  l'entièreté du bandeau, il faut recharger » (Franck). Le rail était calé une fois pour
  toutes, or sur l'accueil la mise en page CHANGE en cours de défilement (l'en-tête compact
  apparaît), ce qui déplace la cale et donc l'ancrage du rail. Celui-ci gardait son ancienne
  valeur : en remontant, la skin se retrouvait trop haute et son bandeau arrivait tronqué
  sous la barre territoire.
  Le rail est donc revérifié au défilement — mais l'écriture n'a lieu QUE si la valeur a
  changé, et le calcul passe par requestAnimationFrame. C'est toute la différence avec la
  parallaxe des v1.0/v1.4-v1.5 : on ne repositionne pas la skin à chaque pixel (c'est
  position:sticky qui la place, dans le moteur de rendu), on constate un changement de mise
  en page et on recale le rail quand il y en a un — donc quasi jamais. Un ResizeObserver sur
  le corps de page couvre en plus les changements de hauteur qui ne déclenchent aucun
  événement (gabarits JetEngine, images tardives).

  v2.0 (2026-08-05) — FIN DES v0.4 À v1.9, ET DE LEUR DÉFAUT COMMUN. Toutes ancraient
  l'habillage dans la PAGE. Or la page raccourcit de 89 px en cours de défilement : sur
  l'accueil, `.as-home-sticky-panel` passe en `position:fixed` entre y=250 et y=300, sort du
  flux, et tout ce qui est ancré en dessous remonte d'un coup (mesuré au navigateur depuis
  une session locale — méthode et chiffres dans docs/REGIE_SKIN_PASSATION.md). C'est une
  propriété du thème, pas un réglage à trouver : une skin ancrée dans la page ne peut que
  sauter (si elle suit) ou se décaler (si elle ne suit pas). Il n'y a pas de troisième
  comportement, et c'est pourquoi neuf corrections successives ont échoué.

  D'où la séparation en deux créatives, qui est aussi celle du format Page Skin (IQD/IAB) :
    - le FOND est `position:fixed`, ancré à la FENÊTRE et non à la page : rien de ce qui
      remue dans la page ne peut le décaler. Insensible aux 89 px par construction ;
    - le BANDEAU est un bloc de FLUX NORMAL : il pousse le contenu et défile avec lui
      jusqu'à sortir de l'écran, ce qui est le comportement natif d'un bloc — donc sans une
      ligne de JavaScript, donc sans retard ni saut possibles. C'est le format « pushdown ».

  Disparaissent avec cette version : le rail, la cale, le sticky, les deux écouteurs de
  défilement et le ResizeObserver. Le seul JS restant insère le bandeau au bon endroit, une
  fois — et ce point d'insertion est le seul vrai piège restant, cf. sa note dans
  cs-regie-skin-js : sur l'accueil il faut se poser APRÈS `.as-home-sticky-panel` et jamais
  dedans, sous peine de quitter le flux avec lui.

  Le bandeau est FACULTATIF (`image2` absente de l'API tant qu'il n'est pas renseigné) :
  sans lui, le fond seul reste un habillage valable.

  v2.1 (2026-08-05) : la v2.0 avait le fond en z-index:0 — un fixed à 0 peint AU-DESSUS de
  tout le contenu non positionné, d'où masthead et footer transparents sur la photo et
  bandeau invisible (captures Franck). C'était déjà, mot pour mot, le symptôme de la v0.3
  (« le fond chevauchait le menu ») : trois montages ont buté sur la même règle de peinture
  sans la nommer. Fond passé à z-index:-1 (sous tout le flux, par construction), béquille
  « .site z-index:1 » supprimée (sur ce site .site est la classe du bloc de widgets du
  FOOTER, elle ne remontait rien), et ajout de .cs-skin-mid : la colonne de lecture crème
  en CSS, à la largeur exacte du conteneur (950/1200) — le rôle que la fenêtre crème de
  l'ancienne créative jouait en dur dans l'image, raccord au pixel non garanti en moins.

  v2.2 (2026-08-05) : le bandeau restait invisible — mesuré au navigateur (headless via
  relais proxy) : présent dans le DOM, image chargée, mais rect 0×0. Cause : poser()
  l'ancrait sur `.as-home-sticky-panel` sans tester s'il est rendu ; c'est l'en-tête de la
  version MOBILE de l'accueil, masquée sur desktop — le bandeau était donc inséré dans un
  sous-arbre invisible. L'ancre devient le dernier en-tête VISIBLE, toutes constructions
  confondues (mêmes sélecteurs que le clamp des gouttières, même filtre getClientRects).
  Garde-fous : desktop uniquement (skin et gouttières sous leurs seuils respectifs —
  1280px générique pour la skin, $cs_bp pour les gouttières) ; consent-gated Complianz
  (cmplz_marketing=allow) ; coupé sur pages sensibles (légales, « annoncer », 404) ;
  libellé « Publicité » sur chaque emplacement.

  INSTALLATION : déposer dans wp-content/mu-plugins/cs-regie.php. Rollback : supprimer.
Author: Cultura Sabauda
Version: 2.2
*/

if (!defined('ABSPATH')) { exit; }

if (!function_exists('cs_regie_serve_fetch')) {
    // Repli si ce fichier tournait sans cs-regie-serve.php (ne devrait pas arriver en
    // usage normal) : mini-fetch local, transient distinct pour ne pas interférer.
    if (!defined('CS_REGIE_BACKOFFICE')) {
        define('CS_REGIE_BACKOFFICE', 'https://backoffice.agendasabauda.eu');
    }
    function cs_regie_serve_fetch() {
        $cached = get_transient('cs_regie_hf_ads_fallback');
        if ($cached !== false) { return $cached; }
        $ads  = array();
        $resp = wp_remote_get(rtrim(CS_REGIE_BACKOFFICE, '/') . '/api/active-ads', array('timeout' => 4));
        if (!is_wp_error($resp) && (int) wp_remote_retrieve_response_code($resp) === 200) {
            $body = json_decode(wp_remote_retrieve_body($resp), true);
            if (!empty($body['ads']) && is_array($body['ads'])) { $ads = $body['ads']; }
        }
        set_transient('cs_regie_hf_ads_fallback', $ads, 5 * MINUTE_IN_SECONDS);
        return $ads;
    }
}
if (!function_exists('cs_regie_host_ok')) {
    if (!defined('CS_REGIE_IMG_HOST'))  { define('CS_REGIE_IMG_HOST',  'agendasabauda.eu'); }
    if (!defined('CS_REGIE_LINK_HOST')) { define('CS_REGIE_LINK_HOST', 'backoffice.agendasabauda.eu'); }
    function cs_regie_host_ok($url, $allowed) {
        if (wp_parse_url($url, PHP_URL_SCHEME) !== 'https') { return false; }
        $host = strtolower((string) wp_parse_url($url, PHP_URL_HOST));
        $allowed = strtolower($allowed);
        return ($host === $allowed) || (substr($host, -strlen('.' . $allowed)) === '.' . $allowed);
    }
}

/** Un bloc backoffice → (image, lien) si actif ET conforme à l'allowlist, sinon null. */
function cs_regie_hf_slot($bloc) {
    $ads  = cs_regie_serve_fetch();
    $bloc = (string) $bloc;
    if (empty($ads[$bloc]['image']) || empty($ads[$bloc]['link'])) { return null; }
    $img  = $ads[$bloc]['image'];
    $link = $ads[$bloc]['link'];
    if (!cs_regie_host_ok($img, CS_REGIE_IMG_HOST) || !cs_regie_host_ok($link, CS_REGIE_LINK_HOST)) {
        return null;
    }
    $out = array('img' => esc_url($img), 'link' => esc_url($link));
    /* Seconde créative, facultative (bandeau de l'habillage — backoffice 2026-08-05).
       Soumise à la MÊME allowlist que la première : une image de campagne ne peut venir
       que du domaine des médias, sinon on la laisse tomber sans toucher au reste. La clé
       est absente de l'API tant que le bandeau n'est pas renseigné, et son absence ici
       signifie simplement « fond seul », ce qui reste un habillage valable. */
    if (!empty($ads[$bloc]['image2']) && cs_regie_host_ok($ads[$bloc]['image2'], CS_REGIE_IMG_HOST)) {
        $out['img2'] = esc_url($ads[$bloc]['image2']);
    }
    return $out;
}

/** Pages où la pub hors-flux est coupée (légales, tunnel annonceur, 404…). */
function cs_regie_suppressed() {
    if (is_404()) { return true; }
    if (is_page(array('mentions-legales', 'politique-confidentialite', 'cgv',
                      'cgu', 'annoncer', 'contact'))) { return true; }
    return false;
}

add_action('wp_footer', function () {
    if (is_admin() || cs_regie_suppressed()) { return; }

    $skin  = cs_regie_hf_slot('4');
    $left  = cs_regie_hf_slot('5');
    $right = cs_regie_hf_slot('6');
    if (!$skin && !$left && !$right) { return; }

    /* Seuil d'affichage calcule SELON LA PAGE : la colonne de contenu ne fait pas la
       meme largeur partout, donc un seuil unique est forcement faux quelque part.
         - accueil        : .as-home-desktop = 950px  -> 950  + 2*(160+24) = 1318
         - reste du site  : container GeneratePress = 1200px (verifie en direct via
                            generate_get_option) -> 1200 + 2*(160+24) = 1568
       L'ancien seuil unique de 1440px faisait les deux erreurs a la fois : il privait
       l'accueil de 120px d'ecran utile (gouttieres invisibles a 100% de zoom sur un
       portable ~1366px, constat Franck 2026-08-04) ET laissait les gouttieres mordre
       sur le contenu des fiches entre 1440 et 1568px. */
    $cs_bp = is_front_page() ? 1320 : 1570;

    /* Largeur de la colonne de lecture de la skin (bande creme .cs-skin-mid) : les memes
       conteneurs que le calcul des gouttieres ci-dessus, verifies en direct le 2026-08-04
       (.as-home-desktop = 950px ; container GeneratePress = 1200px). */
    $cs_skin_container = is_front_page() ? 950 : 1200;

    /* La SKIN (bloc 4) n'a plus ni largeur de bande ni seuil propre depuis la v0.8 :
       l'image entiere est posee derriere la page et le contenu passe dessus, donc il n'y
       a plus de bande a dimensionner ni de place a reserver a cote du contenu. Elle suit
       le seuil generique de .cs-regie (1280px) comme les autres emplacements.
       Les trois variables $cs_skin_container / $cs_skin_col_w / $cs_skin_bp qui vivaient
       ici pilotaient le decoupage en bandeau + bandes laterales : elles sont mortes avec
       lui. Leur histoire (320px puis 160px, seuils 1590/1840 puis 1270/1520) est dans les
       notes de version en tete de fichier — inutile de la rejouer ici. */

    // Rendu masqué par défaut ; révélé en JS si consentement marketing + viewport desktop.
    ?>
    <style id="cs-regie-css">
      .cs-regie{display:none}
      /* révélé uniquement quand <html> porte la classe de consentement + ≥1280px */
      .cs-consent-mkt .cs-regie{display:block}
      @media (max-width:1279px){ .cs-consent-mkt .cs-regie{display:none !important} }
      /* HABILLAGE (bloc 4) — DEUX ELEMENTS, DEUX COMPORTEMENTS, AUCUN CALCUL.

         C'est la refonte du 2026-08-05 qui met fin a dix versions ratees. Le format Page
         Skin (IQD/IAB) separe deux creatives, et il faut les separer ici aussi :

           LE FOND reste FIXE dans la fenetre. Il n'est ancre a rien dans la page, donc
           rien de ce qui remue dans la page ne peut le decaler. C'est le point capital :
           l'accueil RACCOURCIT de 89px en cours de defilement quand .as-home-sticky-panel
           passe en position:fixed (mesure au navigateur, cf. docs/REGIE_SKIN_PASSATION.md).
           Toutes les versions precedentes ancraient la skin dans la page et sautaient donc
           de 89px a ce moment-la. Un element fixe y est insensible PAR CONSTRUCTION.

           LE BANDEAU est un bloc de FLUX NORMAL. Il pousse le contenu vers le bas et
           defile avec lui jusqu'a sortir de l'ecran — sans une ligne de JavaScript, c'est
           le comportement natif d'un bloc. C'est aussi le format standard du "pushdown".

         Il n'y a plus ni sticky, ni rail, ni cale, ni ecouteur de defilement. Le seul JS
         restant sert a INSERER le bandeau au bon endroit, une fois. */
      /* z-index NEGATIF, et c'est le point qui a coute trois montages (v0.3, v0.4, v2.0) :
         un element position:fixed a z-index 0 peint AU-DESSUS de tout le contenu non
         positionne — fonds du masthead et du footer compris. C'est tres exactement le
         symptome de la v0.3 ("le fond chevauchait le menu") et celui du 2026-08-05 au soir
         (masthead et footer transparents, laissant voir la photo). A -1, le fond passe sous
         TOUT le flux, par construction ; le beige de body, propage au canvas (verifie en
         direct : html n'a aucun background), reste dessous et n'est jamais visible.
         ⚠️ L'ancienne beequille ".cs-consent-mkt.cs-skin-on .site{z-index:1}" ne remontait
         RIEN : sur ce site, ".site" est... la classe du bloc de widgets du FOOTER
         (<div id="footer-widgets" class="site footer-widgets">), pas une enveloppe du
         contenu. Supprimee. */
      .cs-skin-bg{position:fixed;inset:0;z-index:-1;cursor:pointer;
        background-repeat:no-repeat;background-position:center top;background-size:cover}
      /* La COLONNE DE LECTURE. Le site n'a pas de fond propre sur sa colonne centrale :
         tout repose sur le beige de body. Des que le fond photo couvre la fenetre, la
         colonne devient donc transparente sur la photo — illisible. L'ancienne creative
         "compensait" en peignant une fenetre creme EN DUR dans l'image, un raccord au
         pixel que le format ne garantit pas (et que la spec deconseille). Ici la bande
         creme est un element CSS : largeur exacte de la colonne (950 accueil / 1200
         ailleurs, memes valeurs que les gouttieres), toujours alignee, a toutes les
         largeurs d'ecran. Posee APRES le fond dans le DOM, au meme niveau -1 : elle peint
         au-dessus de lui et sous tout le flux. */
      .cs-skin-mid{position:fixed;top:0;bottom:0;left:50%;transform:translateX(-50%);
        width:<?php echo (int) $cs_skin_container; ?>px;z-index:-1;
        background:var(--beige,#F7F1E8)}
      /* 15.625vw = 300/1920 : la hauteur du bandeau une fois mis a la largeur de l'ecran,
         donc jamais deforme. position:relative + z-index pour passer devant le fond, le
         bandeau pouvant selon la page etre un enfant de body place avant .site. */
      .cs-skin-banner{position:relative;z-index:1;display:block;width:100%;
        height:15.625vw;cursor:pointer;
        background-repeat:no-repeat;background-position:center center;background-size:cover}
      /* 160×600 DES DEUX COTES, ancrees a 24px des bords — valeurs du design system
         maison (.as-desktop-gutter-ad, components.css), pas une invention locale.
         L'ancienne formule calait la gouttiere sur une colonne fantome de 1160px et
         soustrayait sa propre largeur : avec une 160 a gauche et une 300 a droite, les
         marges exterieures etaient forcement inegales (constat Franck 2026-08-04). */
      .cs-gutter{position:fixed;top:120px;z-index:2;width:160px}
      .cs-gutter--l{left:24px}
      .cs-gutter--r{right:24px}
      .cs-gutter a{display:block}
      .cs-lbl{font:800 8px/1 'Nunito Sans',system-ui,sans-serif;letter-spacing:.1em;
              text-transform:uppercase;color:#6F6B62;margin-bottom:3px}
      .cs-gutter img{display:block;max-width:100%;height:auto}
      /* Pas assez large pour loger la gouttiere sans chevaucher le contenu : on cache.
         ⚠️ Selecteur .cs-consent-mkt .cs-gutter et pas .cs-gutter seul : il doit BATTRE
         « .cs-consent-mkt .cs-regie{display:block} » (0,2,0). L'ancienne regle
         « .cs-gutter--l{display:none} » (0,1,0) perdait la cascade et ne masquait donc
         rien du tout sous 1440px — bug latent jamais vu, corrige ici. */
      @media (max-width:<?php echo (int) $cs_bp - 1; ?>px){ .cs-consent-mkt .cs-gutter{display:none !important} }
    </style>

    <?php if ($skin) : ?>
    <div class="cs-regie cs-skin-bg" id="cs-skin-bg" role="complementary" aria-label="Publicité"
         style="background-image:url('<?php echo $skin['img']; ?>')"
         onclick="window.open('<?php echo esc_js($skin['link']); ?>','_blank')">
      <span class="cs-lbl" style="position:absolute;left:12px;top:10px">Publicité</span>
    </div>
    <div class="cs-regie cs-skin-mid" aria-hidden="true"></div>
    <?php if (!empty($skin['img2'])) : ?>
    <a class="cs-regie cs-skin-banner" id="cs-skin-banner" aria-label="Publicité"
       href="<?php echo $skin['link']; ?>" target="_blank" rel="noopener sponsored"
       style="background-image:url('<?php echo $skin['img2']; ?>')"></a>
    <?php endif; ?>
    <?php endif; ?>

    <?php if ($left) : ?>
    <div class="cs-regie cs-gutter cs-gutter--l">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $left['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $left['img']; ?>" width="160" height="600" alt="Publicité">
      </a>
    </div>
    <?php endif; ?>

    <?php if ($right) : ?>
    <div class="cs-regie cs-gutter cs-gutter--r">
      <div class="cs-lbl">Publicité</div>
      <a href="<?php echo $right['link']; ?>" target="_blank" rel="noopener sponsored">
        <img src="<?php echo $right['img']; ?>" width="160" height="600" alt="Publicité">
      </a>
    </div>
    <?php endif; ?>

    <script id="cs-regie-js">
      (function(){
        var root = document.documentElement;
        function consented(){
          // Complianz : cookie cmplz_marketing=allow (adapter si CMP différent)
          return /(?:^|;)\s*cmplz_marketing=allow(?:;|$)/.test(document.cookie);
        }
        function apply(){
          if (consented()){
            root.classList.add('cs-consent-mkt');
            <?php if ($skin) : ?>root.classList.add('cs-skin-on');<?php endif; ?>
          } else {
            root.classList.remove('cs-consent-mkt','cs-skin-on');
          }
        }
        apply();
        // Complianz émet cet évènement au changement de consentement
        document.addEventListener('cmplz_status_change', apply);
        window.addEventListener('cmplz_cookie_warning', apply);
      })();
    </script>

    <script id="cs-regie-clamp-js">
      /* Cale verticalement les gouttieres entre le BAS des barres sticky et le HAUT du
         footer (demandes Franck 2026-08-04 : « elles passent en dessous du menu et
         depassent vers le haut », puis « quand on arrive au footer, le bas de la
         publicite doit s'arreter en haut du footer »).

         Pourquoi du JS et pas du CSS : en position:fixed l'element ignore le flux, donc
         aucune regle CSS ne peut lui faire connaitre la position du footer. position:
         sticky le ferait, mais exigerait d'injecter les gouttieres DANS la colonne de
         contenu — or elles vivent volontairement hors flux (wp_footer), justement parce
         que le gabarit ne leur offre aucun point d'ancrage lateral.

         Sélecteurs multiples et tolerants : .as-site-footer a ete retire le 2026-07-14
         au profit du footer natif GeneratePress, et plusieurs elements sont sticky en
         haut (.as-site-header, .as-terr-bar, .as-home-desktop__nav) — on prend le plus
         bas de tous plutot que d'en coder un seul en dur.
         .as-terr-bar-inline (ajoute 2026-08-05, constate en lisant le HTML servi) :
         sur la home DESKTOP, la barre territoire n'est PAS .as-terr-bar (masquee la,
         display:none !important, cf. components.css) mais un second element distinct
         .as-terr-bar-inline, place APRES .as-home-desktop__nav dans le DOM. Sans lui
         dans la liste, headBottom s'arretait au nav et ignorait la barre "Vous regardez
         X" qui le suit — gouttieres et skin auraient mordu dessus sur la home. */
      (function(){
        var ads = document.querySelectorAll('.cs-gutter');
        if (!ads.length) { return; }
        var GAP = 16;
        var heads = document.querySelectorAll('.as-site-header, .as-terr-bar, .as-home-desktop__nav, .as-terr-bar-inline');

        /* Le footer doit etre cherche a CHAQUE passage et VALIDE, pas resolu une fois
           pour toutes. Bug du 2026-08-04 (gouttieres invisibles partout, y compris en
           navigation normale) : querySelector('.site-footer, #colophon, …') renvoie le
           premier element dans l'ORDRE DU DOM correspondant a n'importe lequel des
           selecteurs — pas le premier selecteur de la liste. Il tombait donc sur le
           footer natif GeneratePress, masque par « display:none !important »
           (components.css). Un element display:none renvoie un rectangle a ZERO, d'ou
           footTop=0, maxTop negatif, et la branche « pas la place » masquait les deux
           gouttieres sur toutes les pages. */
        /* On veut le HAUT de la zone de pied de page, donc le repere le plus HAUT
           parmi les candidats — pas le plus bas. Erreur du premier jet : je gardais le
           plus bas, qui est #colophon (la barre de copyright, position 547062 dans le
           DOM), alors que .site-footer ouvre bien plus tot (415868) et ENGLOBE les
           colonnes. La pub s'arretait donc sur le copyright et recouvrait tout le bloc
           de liens — « elle ne s'arrete pas au debut du footer » (Franck, 2026-08-04).
           Le filtre « moitie basse du document » evite de confondre le pied de page
           avec un <footer> d'article place plus haut. */
        function footerTop(){
          var cands = document.querySelectorAll('.site-footer, #footer-widgets, .as-desktop-footer, .as-site-footer, #colophon, footer');
          var docH  = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, 1);
          var scrollY = window.pageYOffset || 0;
          var best = Infinity;
          for (var i = 0; i < cands.length; i++) {
            var el = cands[i];
            if (el.offsetParent === null) { continue; }        // display:none
            var r = el.getBoundingClientRect();
            if (r.height <= 0) { continue; }                   // pas rendu
            if ((r.top + scrollY) < docH * 0.4) { continue; }  // trop haut pour un pied de page
            if (r.top < best) { best = r.top; }
          }
          return best;   // Infinity si rien de fiable → pas de borne basse (fail-open)
        }

        function place(){
          var vh = window.innerHeight;

          /* Bas de la zone d'en-tete. On teste le bord SUPERIEUR pour decider si un
             element est ancre en haut, puis on retient son bord INFERIEUR.
             Erreur du premier jet : la condition « bottom < vh/2 » ecartait un en-tete
             des que sa BASE depassait la moitie de l'ecran. Or en haut de page la pile
             masthead + menu + barre territoire descend a ~470px sur ~800px de haut :
             les trois etaient donc ignores, headBottom restait a 0, et les gouttieres
             remontaient jusqu'en haut de l'ecran. Invisible en etat defile (l'en-tete
             collant est court), visible des qu'on revenait en haut — exactement ce que
             Franck a constate le 2026-08-04. */
          var headBottom = 0;
          for (var h = 0; h < heads.length; h++) {
            var hr = heads[h].getBoundingClientRect();
            if (hr.height <= 0) { continue; }             // pas rendu
            if (hr.top > vh * 0.6) { continue; }          // pas ancre en haut de l'ecran
            if (hr.bottom > headBottom) { headBottom = hr.bottom; }
          }
          var minTop  = headBottom + GAP;
          var footTop = footerTop();

          for (var i = 0; i < ads.length; i++) {
            var el = ads[i];
            // offsetHeight vaut 0 tant que le consentement n'a pas revele l'encart
            // (.cs-regie est display:none) : on retombe sur la hauteur nominale.
            var adH = el.offsetHeight || 614;
            var top = Math.round((vh - adH) / 2);              // centre par defaut
            if (top < minTop) { top = minTop; }
            var maxTop = footTop - adH - GAP;
            /* Le pied de page a la PRIORITE sur l'en-tete : quand les deux contraintes
               s'opposent, on laisse « top » passer sous minTop, voire devenir negatif.
               La pub sort alors de l'ecran par le haut en meme temps que le footer
               monte — comportement attendu d'un skyscraper.
               Erreur precedente : une ligne « si top < minTop alors top = minTop »
               suivait ce clamp au nom du fail-open, et le defaisait donc integralement.
               Elle se declenchait pile dans le cas qu'elle etait censee traiter, d'ou
               une pub qui continuait de recouvrir le pied de page (Franck, 2026-08-04).
               Le fail-open ne porte plus que sur une mesure IMPOSSIBLE (footTop non
               fini), jamais sur un resultat simplement serre. */
            if (isFinite(maxTop) && top > maxTop) { top = maxTop; }
            if (!isFinite(top)) { top = minTop; }
            el.style.top = top + 'px';
            el.style.visibility = '';
          }
        }

        place();
        addEventListener('scroll', place, { passive: true });
        addEventListener('resize', place, { passive: true });
        addEventListener('load',   place);
        // Le consentement revele l'encart APRES coup : sa hauteur n'est mesurable
        // qu'a ce moment-la, il faut donc recalculer.
        document.addEventListener('cmplz_status_change', function(){ setTimeout(place, 0); });
      })();
    </script>

    <?php if ($skin && !empty($skin['img2'])) : ?>
    <script id="cs-regie-skin-js">
      /* Le SEUL travail du JS : poser le bandeau au bon endroit du DOM, une fois.
         Son comportement au defilement, lui, est celui d'un bloc normal — le navigateur
         s'en charge, et c'est ce qui garantit qu'il ne peut plus ni sauter ni trainer.

         Point d'insertion, et c'est tout le sujet :
         - ACCUEIL : le menu est bake dans le contenu, dans .as-home-sticky-panel, lequel
           passe en position:fixed des qu'on defile. Tout ce qu'on poserait DEDANS quitterait
           donc le flux avec lui et cesserait de pousser quoi que ce soit — c'est exactement
           ce qui arrivait a la cale des versions precedentes. On se pose APRES le panneau,
           dans .as-home, qui reste en flux.
         - AUTRES PAGES : .as-site-header / .as-terr-bar sont en position:sticky, donc
           toujours dans le flux ; se poser apres la derniere d'entre elles suffit. */
      (function(){
        var b = document.getElementById('cs-skin-banner');
        if (!b) { return; }

        /* ⚠️ NE PAS ancrer sur .as-home-sticky-panel sans tester s'il est RENDU (v2.1,
           repris aussitot, mesure au navigateur : bandeau en rect 0x0). Ce panneau est
           l'en-tete de la version MOBILE de l'accueil — la page porte deux constructions
           (.as-home mobile / .as-home-desktop), et sur desktop la mobile est masquee :
           tout ce qu'on insere dedans devient invisible avec elle. L'ancre est donc le
           DERNIER en-tete visible, toutes constructions confondues — memes selecteurs que
           le clamp des gouttieres, meme filtre getClientRects (cf. piege offsetParent). */
        function ancre(){
          var heads = document.querySelectorAll(
            '.as-home-sticky-panel, .as-site-header, .as-terr-bar, .as-home-desktop__nav, .as-terr-bar-inline');
          var last = null;
          for (var i = 0; i < heads.length; i++) {
            if (heads[i].getClientRects().length === 0) { continue; }   // non rendu
            if (!last || (last.compareDocumentPosition(heads[i]) & Node.DOCUMENT_POSITION_FOLLOWING)) {
              last = heads[i];
            }
          }
          return last;
        }

        function poser(){
          var a = ancre();
          /* Aucun ancrage trouve (gabarit inattendu) : on MASQUE plutot que de laisser le
             bandeau la ou wp_footer l'a depose, c'est-a-dire tout en bas de la page. Une
             pub au mauvais endroit se remarque davantage qu'une pub absente, et l'absence
             se diagnostique, elle. */
          if (!a) { b.style.display = 'none'; return; }
          b.style.display = '';
          if (b.previousElementSibling !== a) { a.insertAdjacentElement('afterend', b); }
        }

        // Aucun ecouteur 'scroll' : rien ne depend du defilement. Les rappels differes ne
        // couvrent que les gabarits JetEngine qui reconstruisent des morceaux de page apres
        // coup, auquel cas le bandeau doit retrouver sa place.
        poser();
        addEventListener('load', poser);
        setTimeout(poser, 600);
        document.addEventListener('cmplz_status_change', function(){ setTimeout(poser, 0); });
      })();
    </script>
    <?php endif; ?>
    <?php
}, 40);
