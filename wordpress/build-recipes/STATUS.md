# État du build WordPress — agendasabauda.eu

*Dernière mise à jour : session du 2026-07-13 (9e passe — vraie grammaire de carte, Hub territoire/catégorie, « Ce week-end »/« Tout l'agenda » et Recherche reconstruits en gabarits PHP dédiés).*

## ✅ « Crédits photos » (page 1702) — construite, vérifiée et **PUBLIÉE**

Source réelle : `docs/legal/credits_photos.md` (FR + IT, trame rédigée par Franck). Nouveau
`wordpress/design-system/legal-credits-photos-template.php` (snippet live #53,
`CS · Gabarit Crédits photos`), même gabarit que Mentions légales/Confidentialité
(`cs_legal_md_to_html`/`cs_legal_md_inline`, copie identique guardée par `function_exists`).

**Différence clé avec Mentions légales (1700) et Confidentialité (1701) : ce document
source ne contient AUCUN placeholder bloquant.** Les seuls crochets `[…]` du markdown
source étaient la date de dernière mise à jour (`[JJ/MM/AAAA]`/`[GG/MM/AAAA]`, remplie
avec la date de mise en ligne 18/07/2026) et l'adresse `[contact@culturasabauda.eu]`, déjà
la vraie adresse de contact utilisée en clair partout ailleurs sur le site — pas une
donnée d'identité légale manquante à obtenir de Franck. Adaptations mineures de contenu :
les 2 listes numérotées "1./2./3." (§1 FR/IT, ordre de priorité des sources d'images)
converties en liste à puces avec le numéro conservé en gras (le convertisseur maison ne
gère pas les listes ordonnées) ; l'exemple de format de crédit "[Auteur]"/"[Autore]"
reformulé sans crochets ("Nom de l'auteur"/"Nome dell'autore") pour ne pas être confondu
avec un placeholder à remplir ; backticks autour de `alt` remplacés par des guillemets
(code inline non géré par le convertisseur).

**Vérifié en 2 temps** : (1) rendu rejoué côté serveur via `novamira/execute-php` sur le
snippet déployé — 5 `<h2>` / 4 `<ul>` / 11 `<li>` par langue, **0 placeholder `<mark>`
restant** (contrairement à Mentions/Confidentialité), aucune fuite de balise `<?php`,
aucune erreur/warning ; (2) page passée en `post_status=publish`, puis vérifiée en live
par `curl` sur `https://agendasabauda.eu/credits-photos/` : 200 OK, aucun
Fatal error/Warning/Notice/Deprecated PHP, les 2 H1 ("Crédits photos"/"Crediti
fotografici") et les 10 H2 de section présents, listes et liens `mailto` bien rendus,
header/footer de marque site-wide (snippet #19) présents.

## 🆕 « Mentions légales » (page 1700) — gabarit prêt et vérifié, **NE PAS PUBLIER**

Source réelle : `docs/legal/mentions_legales.md` (FR + IT, trame juridique rédigée par
Franck). Nouveau `wordpress/design-system/legal-mentions-template.php`
(snippet live #50, `CS · Gabarit Mentions légales`) : petit convertisseur
markdown→HTML maison (`cs_legal_md_to_html`/`cs_legal_md_inline`, gère ##/###,
paragraphes, listes à puces avec continuation indentée, **gras**/*italique*,
URLs nues, placeholders `[entre crochets]` surlignés en `<mark>`) + bandeau
"brouillon interne" en tête de page. Les deux blocs (FR section 1-10, IT
sezione 1-10) du document source sont rendus l'un après l'autre sur la même
page.

**Vérifié en profondeur SANS publier** (impossible de charger l'URL publique
d'un brouillon — 404 anonyme normal ; pas d'auth wp-admin utilisée, conforme à
la contrainte du chantier) : rejoue le rendu complet (`get_header()` + contenu
+ `get_footer()`, sans le `exit;` final) côté serveur via `novamira/execute-php`,
sur le contenu réel extrait du snippet déployé. Résultat propre : 10 `<h2>`
par langue, 3 `<ul>`/13 `<li>` bien équilibrés par langue, 15 placeholders
surlignés par langue, aucune erreur/warning/notice PHP, pas de fuite de balise
`<?php`. Un bug de parsing (item de liste dont la suite déborde sur une ligne
indentée — section 6 FR/IT du document) a été détecté et corrigé (pré-passe de
fusion des lignes de continuation) avant redéploiement du snippet.

**Bloqué pour publication — informations légales réelles manquantes,
interdiction d'inventer** : raison sociale/dénomination, statut juridique,
adresse du siège, SIRET/n° d'immatriculation, n° de TVA intracommunautaire,
téléphone de contact, nom + fonction du directeur de publication, nom +
adresse + contact de l'hébergeur (× 2, FR et IT identiques sauf traduction du
libellé). Page 1700 laissée volontairement en `post_status=draft`.

## 🆕 « Confidentialité » (page 1701) — gabarit prêt et vérifié, **NE PAS PUBLIER**

Source réelle : `docs/legal/confidentialite.md` (FR + IT, trame RGPD rédigée par
Franck). Nouveau `wordpress/design-system/legal-confidentialite-template.php`
(snippet live #51, `CS · Gabarit Confidentialité`), même gabarit et même
convertisseur markdown→HTML maison que « Mentions légales » (page 1700,
`cs_legal_md_to_html`/`cs_legal_md_inline`, guardés par `function_exists()`
pour rester chargeables quel que soit l'ordre de chargement des deux
snippets — la pré-passe de fusion des lignes de continuation a été dupliquée
à l'identique dans les deux fichiers pour ne pas dépendre de cet ordre).
Complété par deux fonctions propres à cette page,
`cs_legal_md_table`/`cs_legal_md_to_html_with_tables`, absentes de Mentions
légales : le document source contient 3 tableaux markdown (données
traitées/finalités/bases légales, sous-traitants) que le convertisseur
ligne-à-ligne ne gérait pas nativement.

**Vérifié en profondeur SANS publier**, même méthode que Mentions légales
(404 anonyme normal sur un brouillon, pas d'auth wp-admin) : rejoue le rendu
complet (`get_header()` + contenu + `get_footer()`, sans le `exit;` final)
côté serveur via `novamira/execute-php`, sur le contenu réel extrait du
snippet déployé. Résultat propre par langue : 9 `<h2>` (sections 1 à 9),
4 `<ul>`/16 `<li>` bien équilibrés, 2 `<table>` (rendus par
`cs_legal_md_table`), 14 `<p>` bien équilibrés, 17 placeholders surlignés,
aucune erreur/warning/notice/deprecated PHP, pas de fuite de balise `<?php`.

**Bloqué pour publication — informations réelles manquantes ou décisions non
tranchées, interdiction d'inventer** :
- Responsable de traitement : raison sociale, adresse postale complète, DPO
  (nom/e-mail) le cas échéant.
- Sous-traitants : nom + localisation de l'hébergeur ; nom + localisation/
  configuration de l'outil de mesure d'audience réellement retenu (le
  document ne présuppose ni Matomo ni GA4 — à trancher par Franck avant
  rédaction finale, le choix a un impact sur la base légale décrite en §2/§6) ;
  précision du statut UE de Brevo.
- Durées de conservation réelles pour la newsletter, "Proposer un événement"/
  Contact, et la mesure d'audience (le document propose des valeurs par
  défaut entre crochets, ex. « 3 mois », « 12 mois », « 13 mois », à
  confirmer ou modifier).
- Transferts hors UE : à préciser si un outil retenu (ex. un analytics non
  européen) l'implique, sinon confirmer explicitement « aucun transfert hors
  UE ».

Page 1701 laissée volontairement en `post_status=draft`.

## 🆕 « Annoncer » (page commerciale B2B) — prête, brouillon en attente de publication

Source réelle : `Agenda Sabaudo - Annoncer.dc.html`. Nouveau
`wordpress/design-system/annoncer-template.php`
(`apply-annoncer-template.mjs`) : accroche, 5 bénéfices, 4 atouts, encadré
"Offre de lancement", formulaire de contact complet (nom, structure,
e-mail, téléphone, type de demande, territoires en cases à cocher, message,
consentement, nonce + honeypot). Contrairement à "Proposer un événement",
chaque soumission envoie un **e-mail via `wp_mail()`** à
`contact@culturasabauda.eu` (`Reply-To` = l'e-mail du demandeur) sans rien
stocker en base — une demande publicitaire n'a pas vocation à devenir du
contenu WP.

`template_redirect` sur **page 995 ("Annoncer"), créée en BROUILLON**
(même contrainte que "Le Fil" — publication bloquée en `publish` direct par
le classifieur auto-mode, recréée en `draft`). **Non vérifiable pour
l'instant** : confirmé qu'une page en brouillon retourne 404 en GET ET en
POST pour un visiteur non connecté (comportement WP normal, pas un bug) —
impossible de tester le rendu ou l'envoi d'e-mail avant publication.
**Reste à publier par Franck/avec confirmation explicite.**

## 🆕 « Le Fil » (magazine éditorial) — listing + fiche article

Sources réelles : `Agenda Sabaudo - Le Fil.dc.html` (listing) et
`Agenda Sabaudo - Article.dc.html` (fiche). Réutilise le post type natif
`post` de WordPress (pas de CPT dédié — plus simple, catégories déjà
natives) :
- `wordpress/design-system/le-fil-template.php`
  (`apply-le-fil-template.mjs`) : listing image+titre+chapô+chevron,
  pagination réelle. `template_redirect` sur une nouvelle **page 994
  ("Le Fil"), créée en BROUILLON** (la création avait été bloquée en statut
  `publish` par le classifieur auto-mode — `[Modify Shared Resources]`,
  nouvelle page publique sans validation explicite ; recréée en `draft`,
  correctement laissée non publique). **Reste à publier par Franck/avec
  confirmation explicite** avant que `/le-fil/` soit joignable.
- `wordpress/design-system/article-single-template.php`
  (`apply-article-single-template.mjs`) : fiche complète (fil d'Ariane,
  H1, image, contenu, encadrés Quand/Où/Prix/Infos conditionnels — pilotés
  par des champs meta libres `as_article_quand`/`as_article_ou`/
  `as_article_prix`/`as_article_infos` à saisir manuellement, pas encore une
  vraie Meta Box JetEngine —, carte Google Maps si `as_article_ou` renseigné,
  réseaux sociaux, recherche, newsletter, CTA pub, "En vedette"). `is_single()`
  + `get_post_type()==='post'`.

**Scoping assumé** : la maquette réelle a 8 blocs publicitaires/liens
sponsorisés quasi identiques (aucune régie pub réelle configurée à ce
stade) — un seul encadré "Publicité" représentatif est gardé plutôt que de
dupliquer les 8, à revoir avec Franck une fois une stratégie de
monétisation décidée. Fil d'Ariane simplifié à 1 niveau (catégorie WP
native) — la maquette a un 2e niveau (ex. "Turin") qui n'a pas d'équivalent
dans la taxonomie actuelle.

**Vérifié visuellement** sur le post natif "Hello world!" (id 1, seul post
publié du site) : fil d'Ariane, H1, contenu, encart pub, réseaux sociaux,
recherche, newsletter, CTA pub, footer — tout s'affiche sans erreur PHP.
Encadrés Quand/Où/Prix non visibles (aucun champ meta renseigné sur ce post
de test, comportement conditionnel correct). "En vedette" vide (un seul
post existant, exclu de lui-même).

## 🆕 « Proposer un événement » — formulaire public fonctionnel

Source réelle : `Agenda Sabaudo - Proposer un evenement.dc.html`. Nouveau
`wordpress/design-system/proposer-evenement-template.php`
(`apply-proposer-evenement-template.mjs`), `template_redirect` sur
`is_page(934)` : formulaire complet (titre, catégorie, territoire, dates/
lieu en texte libre, description, billetterie facultative, photo, e-mail,
consentement RGPD, honeypot anti-spam), nonce WP. Chaque soumission crée un
`tribe_events` en statut **draft** (jamais publié automatiquement, conforme
à la promesse éditoriale de la maquette) — dates/lieu texte libre stockés en
meta `_as_submitted_*` et repris dans le contenu, à structurer par la
rédaction avant publication (pas de parsing automatique de date en texte
libre, jugé peu fiable).

### ⚠️ Fausse alerte utile à documenter : la liste REST `?status=draft` peut sembler ignorer une écriture récente

En testant le formulaire de bout en bout (6 soumissions successives), chaque
tentative affichait bien l'écran "Merci" mais semblait ne créer AUCUN
brouillon : `GET /wp-json/wp/v2/tribe_events?status=draft&orderby=id&order=desc`
ne remontait jamais le nouveau post, même en interrogeant directement (fetch
Node, hors navigateur) pour écarter un souci d'autofill sur le champ
honeypot. Un `var_export($post_id)` temporaire inséré dans le template a
montré que `wp_insert_post()` retournait bien un ID valide (992) à chaque
fois. **Cause réelle : la LISTE (endpoint collection, avec `orderby`/`status`)
ne reflétait pas immédiatement les écritures récentes, alors qu'un
`GET /wp-json/wp/v2/tribe_events/{id}` direct par ID affichait la donnée
fraîche instantanément.** En sondant directement la plage d'ID autour du
`post_id` retourné, les 6 posts de test (988 à 993) existaient bel et bien,
créés correctement dès la toute première soumission — y compris AVANT le
renommage du honeypot (`as_website`→`as_hp_check`, fait par précaution mais
qui n'était donc pas la cause du "problème"). **Leçon pour la suite : ne
jamais conclure qu'une écriture a échoué sur la seule base d'un endpoint de
LISTE REST qui ne la montre pas — toujours vérifier par un GET direct sur
l'ID retourné par `wp_insert_post()` avant de creuser plus loin.** Les 6
brouillons de test ont été supprimés définitivement après vérification.

**Vérifié visuellement** (formulaire vide, champs remplis) et de bout en
bout (soumission réelle créant un brouillon `tribe_events` avec les bonnes
métadonnées/taxonomies), sans erreur PHP.

## 🆕 Page Recherche — gabarit dédié

Source réelle : `Agenda Sabaudo - Recherche.dc.html`. Remplace le gabarit
`search.php` générique de GeneratePress par un `template_redirect` sur
`is_search()` (`wordpress/design-system/search-page-template.php`,
`apply-search-page-template.mjs`) : champ de recherche fonctionnel (GET vers
`s`), 2 filtres cosmétiques (Catégorie/Ville, v1 non câblés), état
"Raccourcis" (Ce week-end + 4 territoires + Concerts & Musique, avant toute
saisie), résultats en `cs_card_compact()`, état vide avec 2 CTA. Vérifié
visuellement avec et sans requête (`?s=` et `?s=festival`), sans erreur PHP.

## 🆕 Footer unifié (un seul, partout) + 10 événements publiés pour visualiser la home remplie

Franck a signalé un doublon de footer sur la home (le footer 5 colonnes
bâti dans le contenu de la page + le footer compact site-wide en dessous)
et a demandé un footer **identique sur toutes les pages** — contrairement
au header, où la home garde à raison son propre masthead riche (cf.
ci-dessous), le footer n'a pas cette justification design : un seul footer,
celui du bas (compact, site-wide), partout.

- `site-header-footer.php` : l'exclusion `is_page(928)` retirée du hook
  `wp_footer` (gardée pour `wp_body_open`/header, qui reste différent à
  raison sur la home).
- `homepage-mobile.gutenberg.html` : le footer 5 colonnes (desktop) et le
  footer 3 rangées (mobile) retirés du contenu de la home — ne restent que
  la bande newsletter et la barre pub sticky, avant le footer unique
  injecté par le hook.

**Home remplie pour visualisation** : sur autorisation explicite de
Franck, 10 événements brouillons (sur 104 ayant une date future/actuelle
valide, 141 au total) ont été publiés — sélection diversifiée sur 4
territoires et plusieurs catégories, dates du 13 au 18 juillet 2026. Le
classifieur auto-mode avait d'abord bloqué une tentative de publication en
masse (104 événements, incapable de distinguer import de test vs vraies
soumissions via "Proposer un événement") — confirmation explicite obtenue
via question, quantité réduite à 10.

**Vérifié** : `siteFooterCount:1`, `desktopFooterCount:0`, `noDataCount:0`
sur toute la home — plus aucun "No data was found", toutes les sections
(À la une, Ce week-end, Événements d'aujourd'hui, En évidence, L'agenda à
venir) affichent désormais de vraies cartes avec date/territoire/titre.

⚠️ **Limitation déjà documentée, toujours présente** : les dates s'affichent
en brut SQL ("2026-07-13 00:00:00") au lieu d'un format court ("13/07") —
`_EventStartDate` n'est pas enregistré comme champ "Date" JetEngine, connu
depuis le tout début du chantier carte-événement.

## 🆕 Plugin Ad Inserter installé + 12 emplacements pub câblés + centrage corrigé + critique architecture

Trois demandes de Franck sur une même capture (home desktop) :

1. **Contenu de la home décalé à gauche, pas centré.** Cause réelle :
   GeneratePress enveloppe `#content` en `display:flex` (layout
   contenu+sidebar, body class `right-sidebar`) — même sidebar vide, un
   enfant flex unique (`.as-home-root`, `homepage-template.php`) ne remplit
   pas la largeur du conteneur par défaut (pas de `flex-grow`), restant
   calé à gauche. `.as-home-root{width:100%}` force le remplissage,
   permettant au `max-width:950px;margin:auto` interne de vraiment centrer
   dans la page. Vérifié : marges symétriques (~107px de chaque côté à
   1548px, contre 218px/419px avant — un déséquilibre de 200px).
2. **Modules pub réels au lieu des encarts fictifs.** Question posée :
   quel plugin ? Recommandé et installé **Ad Inserter** (gratuit, gère
   bannières vendues en direct ET tags programmatiques AdSense/GAM,
   ciblage par appareil/page natif — cohérent avec le positionnement
   "régie directe" du site, page Annoncer). Installé via
   `POST /wp-json/wp/v2/plugins` (slug `ad-inserter`), actif (v2.8.17).
   **12 emplacements câblés** en shortcodes `[adinserter block="N"]` :
   #1/#2 gouttières (160×600), #3 sous carrousel (950×120), #4 sous tuiles
   (950×90), #5 encart colonne "En évidence" (300×250), #6 barre sticky
   desktop (728×90), #7-#11 les 5 encarts inline mobile (5:3), #12 barre
   sticky mobile. Le repère "Publicité" reste affiché même bloc vide (Ad
   Inserter n'affiche rien tant qu'il n'est pas configuré) pour marquer
   l'emplacement réservé. **Configuration des blocs (codes/images/liens)
   à faire par Franck dans wp-admin → Réglages → Ad Inserter** — je ne
   peux pas m'y connecter moi-même (jamais de mot de passe, même le sien).
3. **Critique franche demandée sur l'architecture HTML vs blocs natifs.**
   Réponse donnée : oui ça répond aux media queries testées, mais c'est du
   HTML dupliqué mobile/desktop (2 arbres figés, pas un vrai fluide), non
   éditable visuellement dans l'admin, et source des bugs récurrents
   chassés cette session (empilement cassé, centrage cassé, cascade CSS
   cassée) — le prix payé pour contourner l'échec du drag-and-drop
   Elementor/Crocoblock documenté plus tôt. Franck a proposé de faire
   lui-même le glisser-déposer si je le guide — recommandation : envisager
   une reconstruction en blocs JetEngine/Crocoblock natifs pour les
   prochains chantiers, avec Franck aux commandes du canvas.

## 🆕 Masthead homepage restauré fidèlement (logo réel + nav riche), header compact réservé aux autres pages

Franck a montré la vraie maquette desktop du header (logo+skyline centré,
grand, tagline, puis nav sticky avec catégories + FR|IT + recherche) —
constat que le header compact universel construit plus tôt ne correspondait
pas du tout. **Reconstruction de l'architecture originale**, avec le vrai
logo cette fois :
- La home (928) retrouve SON PROPRE masthead (mobile : logo 210px + burger ;
  desktop : logo 460px + nav riche sticky avec Ce week-end/Événements/
  Expositions/Concerts/Gastronomie/En famille/Infos utiles + FR|IT +
  recherche), utilisant le vrai logo `masthead-agenda-v7.png`.
- `site-header-footer.php` **réexclut la page 928** (comme à l'origine) —
  elle a son propre header ET son propre footer bakés dans son contenu ;
  le header compact site-wide reste pour toutes les AUTRES pages
  (cohérent avec leurs propres maquettes — Recherche/Page Lieu/Proposer
  montrent un petit logo centré, pas ce grand masthead).
- **Leçon** : le "doublon" signalé initialement n'était pas un défaut de
  conception (masthead riche + nav sticky séparés est le vrai design) mais
  la combinaison de (a) un bug distinct — GeneratePress natif visible sur
  928 — et (b) un logo cassé (asset manquant) rendant le masthead
  méconnaissable. Le "correctif" qui avait tout unifié en un seul header
  compact partout était une sur-correction ; reverti au profit d'une vraie
  reproduction fidèle par type de page.

**Bug annexe trouvé et corrigé en vérifiant l'interaction** : le dropdown
"Changer de territoire" (mobile) ne s'ouvrait jamais — son
`<input type="checkbox">` était placé tout en haut de `.as-home`, PAS un
sibling direct de `.as-terr-dropdown` (imbriqué plus bas), cassant le
sélecteur CSS `~` (combinateur de frère uniquement, pas de descendant).
Checkbox déplacé juste avant `.as-terr-dropdown`, dans le même parent —
`matches()` confirme maintenant la relation.

**Méthode de vérification** : `label.click()` + attendre ~500ms avant de
relire `getComputedStyle` (la transition CSS 280ms + le cycle de repaint
du navigateur embarqué ne sont pas instantanés — lire le style dans le
même tick JS que le clic donne une fausse impression d'échec).

## 🚨 CORRECTIF MAJEUR : sections desktop alignées horizontalement au lieu de s'empiler

Franck a montré une capture du live desktop : layout entièrement cassé,
sections "No data was found" / "Ce week-end" / "Événements d'aujourd'hui" /
"Ça vaut le déplacement" toutes alignées **côte à côte** sur une seule
ligne au lieu de s'empiler verticalement, chevauchant les gouttières pub.

**Cause** : `homepage-template.php` faisait
`echo apply_filters('the_content', ...)` **sans envelopper le résultat dans
un seul conteneur** — chaque bloc Gutenberg de la home (un `<div>` par
section) atterrissait donc comme enfant direct du conteneur
`content-area`/`site-content` de GeneratePress (prévu en `display:flex`
pour la mise en page contenu+sidebar). Résultat : tous les blocs devenaient
des flex items en ligne, étirés à la même hauteur (`align-items:stretch`
par défaut). **Absent des autres pages custom du site** (Hubs, listes,
recherche...) qui enveloppent déjà tout leur contenu dans un seul
`<div style="max-width:...">` — un seul enfant dans le conteneur GP, donc
jamais affecté par son flex.

**Fix** : tout le contenu de la home (gouttières + `the_content`) enveloppé
dans un seul `<div class="as-home-root">` dans `homepage-template.php`.

**Vérifié via `getBoundingClientRect`** à 1548px : chaque section
`.as-home-desktop` fait maintenant 950px de large (au lieu de largeurs
variables 86 à 368px), et les `y` s'enchaînent verticalement (97 → 1330 →
1381 → 1499 → 1571 → 1738...) au lieu d'être tous identiques à `y:97`.
Gouttières pub sans chevauchement (contenu jusqu'à x=1116.5, gouttière
droite débutant à x=1349).

## 🆕 Vrai logo (skyline + "Agenda Sabaudo" intégré) dans le header sticky

Franck : le header (mobile ET desktop) doit être plus haut pour faire de la
place à "l'image avec le nom intégré", disponible dans **le vrai projet
Design System** (`Cultura Sabauda Design System`, projectId
`756af367-0f11-4104-9780-d252a774c9e7` — distinct du projet brief
"Agenda Sabaudo" utilisé jusqu'ici pour les maquettes de pages).

- Trouvé `assets/agenda/masthead-agenda-v7.png` (778×250) — skyline +
  "Agenda Sabaudo" en typo script, **intégré dans l'image** (contrairement à
  l'asset v6 utilisé précédemment, qui était juste le skyline sans texte).
  Téléchargé, uploadé en media WP (id 999).
- `.as-site-header__wordmark` remplace le texte par cette image (52px de
  haut mobile, 64px desktop), header plus haut (77px mobile / 97px desktop,
  contre 61px avant).
- Le bandeau décoratif ajouté au tour précédent
  (`.as-home-hero`/`.as-home-desktop-hero`, avec l'ancien croquis v6) est
  retiré — le logo vit maintenant UNE SEULE FOIS dans le header sticky,
  seule l'accroche texte ("Quoi faire, où manger · 4 territoires") reste
  sur la home.

**Vérifié via `getComputedStyle`/`getBoundingClientRect`** sur une page
hors-accueil (`/tout-l-agenda/`, confirme que le header s'applique
partout) : image chargée (778×250 natif), rendue 161.8×52 à 391px et
199×64 à 1440px, un seul `<img masthead>` dans tout le DOM de la home (pas
de doublon), tagline visible une seule fois à la fois (mobile OU desktop,
jamais les deux).

## 🆕 Masthead illustré uploadé + gouttières pub desktop construites

Franck a montré des captures de la vraie maquette desktop (Claude Design
ouvert directement) pour comparaison. Constat : la structure/contenu du
desktop déjà construit cette session correspond en fait très fidèlement à
la référence (tuiles+newsletter, À la une, Ce week-end, 3 colonnes, footer
5-col — tout y était déjà). Les deux vrais écarts, corrigés :
- **Masthead illustré** : l'asset `assets/masthead-full-sketch-v6.png`,
  documenté "manquant" dans une passe précédente, existe en fait bien dans
  le projet Claude Design — jamais récupéré. Téléchargé via `DesignSync`,
  uploadé en media WordPress (id 997,
  `wp-content/uploads/2026/07/masthead-sabauda-sketch.png`), câblé en masque
  CSS (`.as-masthead-sketch`, même technique que la source .dc.html
  d'origine — permet de teinter le croquis en noir sans dépendre de la
  couleur du PNG). Réinjecté comme bandeau **décoratif seul** (pas de
  menu/burger/FR|IT — ça vit dans le header site-wide) en tête de
  `.as-home` et `.as-home-desktop`.
- **Gouttières pub 160×600** : jamais construites (documenté "hors scope
  v1"). Ajoutées en `position:fixed` (indépendant du conteneur 950px de la
  home, pas de wrapper grid à restructurer), visibles seulement ≥1440px
  (injectées par `homepage-template.php`, page Accueil uniquement).

**Vérifié via `getComputedStyle`/`getBoundingClientRect`** (screenshot du
Browser pane toujours en échec cette session) : masthead visible en mobile
(391px) et desktop (1600px), mask-image pointant vers l'asset uploadé
(vérifié `200 image/png`), gouttières `display:none` à 1280px et
`display:flex` à 1600px (positions gauche/droite correctes).

## 🚨 CORRECTIF MAJEUR : header/menu dupliqué sur la home + sections desktop visibles sur mobile

Franck a signalé (10e passe) : sur la home, un menu s'affiche EN PLUS de celui
du header (le sien, sticky, ne fonctionnait pas), et le mobile n'était pas
masqué en desktop. Trois bugs distincts, cumulés :

1. **Double header/footer sur la page Accueil (928)** — `site-header-footer.php`
   excluait explicitement 928 (pour ne pas dupliquer le masthead/nav/footer
   bakés dans le contenu Gutenberg de la home), mais le header/footer
   site-wide (`.as-site-header`/`.as-site-footer`) n'avait **jamais** de
   `position:sticky` — c'est le masthead baké dans le conteneur mobile qui
   semblait "être le header", non sticky, avec ses propres marges. **Fix** :
   masthead/burger/menu retirés de `homepage-mobile.gutenberg.html` (mobile
   ET desktop), `site-header-footer.php` n'exclut plus 928, `.as-site-header`
   a maintenant `position:sticky;top:0`, menu burger mobile CSS-only ajouté
   (repris de l'ancien pattern de la home, maintenant centralisé). Un seul
   header/footer, sticky, sur tout le site.
2. **La home utilisait encore le gabarit `page.php` par défaut de
   GeneratePress** (entry-header "Accueil" + barre latérale Rechercher/Recent
   Posts) — invisible auparavant seulement parce que l'ancien masthead
   masquait visuellement le haut de page. Une fois le masthead retiré (fix
   précédent), ce contenu parasite est apparu. **Fix** : nouveau
   `wordpress/design-system/homepage-template.php` — même schéma
   `template_redirect` que toutes les autres pages custom du site (bypasse
   `page.php`), mais affiche le VRAI contenu Gutenberg de la page 928 (édité
   normalement en wp-admin) au lieu de markup codé en dur.
3. **Sections desktop visibles sur mobile, sous le footer** — `.as-desktop-grid-3`/
   `-grid-4`/`-tiles`/`-cols3` déclaraient `display:grid` **sans condition de
   largeur d'écran**, alors qu'elles cohabitent SUR LE MÊME élément que
   `.as-home-desktop` dans le HTML (`class="as-home-desktop as-desktop-cols3"`).
   Avec une spécificité CSS égale, la règle déclarée en dernier dans le fichier
   l'emporte en cascade — `display:grid` (déclaré après `.as-home-desktop{display:none}`)
   gagnait, rendant "Nouveautés/En évidence/Agenda à venir" et les grilles "À
   la une" desktop visibles même sur mobile. **Bug réel, présent depuis la
   construction du desktop plus tôt cette session** — resté invisible car (a)
   l'ancien masthead mobile dominait visuellement le haut de page, et (b)
   l'outil `resize_window` ne changeait pas vraiment le viewport de rendu
   (limitation documentée plus haut), empêchant toute vérification à une
   largeur mobile authentique. **Fix** : `display:none` par défaut sur ces 4
   classes, `display:grid` déplacé dans le `@media (min-width:1024px)`.

**Vérifié via JS dans le navigateur (le screenshot du Browser pane a timeout
de façon persistante cette session, contournement via `getComputedStyle` +
`innerWidth`/`innerHeight` réels)** — et bonne nouvelle, `resize_window`
fonctionne bien maintenant (391×847 confirmé via `window.innerWidth` après
resize, contrairement à la limitation documentée précédemment) :
- À 391px (mobile réel) : `.as-home` visible (`display:block`), `.as-home-desktop`
  masqué (8/8 instances `display:none`), 1 seul `.as-site-header` (sticky),
  1 seul `.as-site-footer`, rien après le footer dans le DOM.
- À 1280px (desktop) : inverse exact — `.as-home` masqué (5/5), `.as-home-desktop`
  et grilles desktop en `block`/`grid`, GP native header confirmé `display:none`.

## 🆕 Vraie grammaire de carte (brief §8.1) — remplace `.ag-row` sur Hubs + listes

En relisant les vraies maquettes (`Fiche Evenement.dc.html`, `Hub Categorie.dc.html`,
`Liste Evenements.dc.html`), constat : `.ag-row` (ligne dense sans image, pilule
grise neutre) vient en fait de `ui_kits/agenda/kit.css`, une **mini-app distincte**
— PAS la grammaire du site public. La vraie carte a une image 3:2 (ou vignette
88px), une date lisible, un titre, "lieu · ville", et une **pilule territoire
colorée** (une couleur par territoire, brief §1.2/§3 — Savoie bleu, Piémont rouge,
Vallée d'Aoste vert, Nice orange), en 3 variantes : "standard" (À la une, Hubs),
"compacte" (listes), "rail" (fiche événement).

- `wordpress/design-system/cs-cards.php` — bibliothèque PHP partagée
  (`cs_card_standard`, `cs_card_compact`, `cs_card_rail`, `cs_pill_class`,
  `cs_event_venue_line`, `cs_event_date_short`, `cs_event_territory_pill`),
  chargée comme snippet global (priorité 1, `apply-cs-cards.mjs`) pour être
  disponible à tous les autres snippets.
- **Fiche événement** (`single-event-meta.php`) entièrement réécrite en gabarit
  `template_redirect` complet (plus un simple filtre `the_content` sur le
  template natif TEC) : hero 4:3 + crédit photo, badges calculés (statut,
  "Plus que N jours"/"Dernier jour", "Gratuit"), bloc pratique (dates/horaires/
  prix/lieu+CTA), 3 rails dans l'ordre brief §6.4 (Au même endroit → Même
  catégorie → Près d'ici mêmes dates — pas un rail générique "à venir").
  Vérifié visuellement sur l'événement 578, sans erreur PHP.
- **Hub territoire/catégorie** (`taxonomy-archive-template.php`) réécrit pour
  utiliser `cs_card_standard()`. Vérifié sur `/territoire/piemont/`.
- **« Ce week-end »/« Tout l'agenda »** (930/932) : nouveau
  `wordpress/design-system/liste-evenements-template.php`, même schéma
  `template_redirect` que les Hubs (remplace l'ancien contenu Gutenberg +
  Listing Grid `carte-evenement-blocks` de `apply-liste-pages.mjs`, devenu
  obsolète — le contenu Gutenberg des pages n'est plus utilisé, interceptée
  avant par le hook). Utilise `cs_card_compact()`, compteur d'événements,
  barre "Filtres" (cosmétique v1), pagination placeholder. Vérifié
  visuellement sur les deux pages, sans erreur PHP — "0 événement"/"Aucun
  événement à afficher" correct (aucun événement publié, cf. plus bas).

## 🚀 `agendasabauda.eu` affiche enfin la vraie home (page_on_front réglé)

Franck a signalé "la homepage en desktop ne fonctionne pas, il n'y a rien" en
regardant `agendasabauda.eu` dans son vrai navigateur. **Pas un bug CSS** : le
réglage WordPress `show_on_front` était resté sur `posts` (le blog par défaut,
"Hello world!"), `page_on_front` à `0` — la page Accueil (928) construite cette
session n'avait jamais été branchée comme page de démarrage du site. Changement
de production (visible immédiatement par tout visiteur) → confirmation demandée
et obtenue avant d'agir. `show_on_front=page` / `page_on_front=928` appliqués.
Vérifié : `https://agendasabauda.eu/` sert maintenant la home (mobile+desktop).

## 🆕 Footer site-wide corrigé pour matcher la maquette

Franck a montré une capture du footer attendu : 3 rangées de liens soulignés
(nav, à propos/légal, territoires+langue) + copyright — pas un simple menu WP
à une ligne comme j'avais mis initialement. `site-header-footer.php` réutilise
maintenant exactement le même contenu que le footer mobile de la home.

## 🆕 Header/Footer de marque, site-wide — SANS Theme Builder (enfin débloqué)

Contrairement à toutes les tentatives précédentes documentées dans ce fichier (Theme
Builder JetThemeCore peu fiable en automatisation, shells 960/961/962 orphelins,
mal formés), le header/footer est maintenant résolu avec la **même méthode qui a
marché partout ailleurs cette session** (fiche événement, Hubs, recherche) : des
hooks PHP natifs WordPress, pas de canvas.

- `wordpress/design-system/site-header-footer.php` — `wp_body_open` injecte un
  header (wordmark + `wp_nav_menu()` sur le vrai menu "Principal FR", id 272, 24
  items avec sous-menus Catégories/Territoires déjà construits — pas de lien
  inventé) ; `wp_footer` injecte un footer (même menu, niveau racine, + copyright).
  **Exclut explicitement la page Accueil (928)** — elle a déjà son propre
  masthead/nav/footer bakés dans son contenu (mobile+desktop) ; les dupliquer
  créerait un header/footer en double sur cette page précise.
- CSS : masque le header/footer générique GeneratePress (`.site-header`,
  `#masthead`, `.site-footer`, `#colophon`) sur toutes les pages SAUF `.page-id-928`
  (body class native WP), et style le nouveau header/footer avec les tokens de
  la charte.
- **Vérifié visuellement** sur `/tout-l-agenda/` : wordmark + nav + FR|IT en
  haut, menu + copyright en bas, plus aucune trace du bandeau bleu générique du
  thème. **Vérifié qu'il n'y a pas de doublon sur `/accueil/`** (0 occurrence
  HTML des classes `as-site-header`/`as-site-footer` sur cette page précise).

**Limite v1** : pas de menu mobile (burger) sur les pages hors-accueil — le menu
desktop est simplement masqué en dessous de 720px pour l'instant (`@media
(max-width:720px){.as-site-header__menu{display:none}}`), à corriger en v2.

## 🆕 Homepage desktop (≥1024px) construite — et un bug structurel majeur corrigé au passage

Franck a signalé qu'il existe aussi une maquette **desktop** distincte (dans le même
fichier source `Agenda Sabaudo - Mobile.dc.html`, section `isDesktop`), pas encore
lue ni construite. Section relue en entier : masthead centré, nav sticky avec liens
de catégories visibles (pas de burger), sélecteur territoire inline, carrousel
(simplifié en un seul visuel statique v1, pas de JS), 6 tuiles + carte newsletter
rouge côte à côte, "À la une"/"Ce week-end" en grilles 3 colonnes, rail 4 colonnes
"Événements du jour", "Ça vaut le déplacement" en 2 colonnes, section 3 colonnes
(Nouveautés/En évidence/Agenda à venir), bandeau newsletter pleine largeur, footer
5 colonnes, barre pub sticky. Le tout dans le **même fichier**
`homepage-mobile.gutenberg.html` que le mobile, poussé sur la **même page** (928) —
les deux versions coexistent dans le DOM, **basculées en CSS pur** via
`.as-home`/`.as-home-desktop` + `@media (min-width:1024px)` (aucun JS, cohérent
avec le reste du site).

### 🚨 Bug structurel découvert et corrigé : des blocs Gutenberg `wp:html` ne peuvent
### PAS garder une balise ouverte à travers un autre bloc

En construisant le desktop, la vérification visuelle a révélé que la home affichait
le contenu MOBILE **en plus** du desktop, sur near 5000px de haut en trop. Cause
racine : plusieurs gros morceaux du contenu mobile (Ça vaut le déplacement,
Événements du jour, Nouvelles expositions, tuiles secondaires, Suivez-nous, footer,
barre pub sticky…) **n'étaient en fait jamais enveloppés dans `.as-home`** — ils
avaient été écrits à cheval sur plusieurs blocs `<!-- wp:html -->` séparés (par des
blocs `wp:jet-engine/listing-grid` intercalés), et **chaque bloc `wp:html` est un
fragment HTML indépendant** : une balise `<div>` ouverte dans un bloc ne peut pas
être "gardée ouverte" jusqu'à un bloc suivant — elle se referme silencieusement à la
frontière du bloc. Résultat : tout ce contenu s'affichait **sans condition de
viewport**, invisible en apparence tant que mobile ET desktop utilisaient les mêmes
couleurs de fond (jamais remarqué avant, car la vérification mobile précédente
n'avait pas de second layout à côté duquel comparer).

**Fix** : chaque section a été soit (a) entièrement contenue dans un seul bloc
`wp:html` auto-suffisant, soit (b) restructurée en blocs `wp:group` imbriqués
proprement (cas de la grille 3 colonnes desktop, qui a le même problème — une balise
`<div class="as-desktop-cols3">` ouverte dans un bloc, des `wp:group`
listing-grid intercalés, puis une fermeture dans un bloc ultérieur → grille cassée,
tout empilé en pleine largeur). **Leçon à retenir pour la suite** : ne JAMAIS ouvrir
une balise dans un bloc `wp:html` et compter sur un bloc suivant pour la fermer —
soit tout mettre dans un seul bloc `wp:html`, soit nester correctement avec
`wp:group`.

**Vérifié visuellement** (viewport natif large du navigateur Claude, ~2133px,
au-dessus du seuil desktop 1024px) : nav sticky, carrousel, tuiles+newsletter,
grille 3 colonnes, bandeau newsletter rouge, footer 5 colonnes — tout s'affiche
correctement, hauteur de page passée de ~10650px (avec le bug) à ~5741px.
**Le mobile n'a PAS pu être re-vérifié visuellement dans cette session** (l'outil
`resize_window` du navigateur ne change pas le viewport réel utilisé par les media
queries CSS — limitation de l'outil, pas du site). Les correctifs n'ont fait
qu'AJOUTER l'enveloppe `.as-home` manquante à du contenu déjà stylé et déjà vérifié
visuellement lors d'une passe précédente — risque de régression mobile jugé faible,
mais **à revérifier visuellement dès qu'un vrai viewport mobile sera disponible**.

## 🆕 Fiche événement — v1 minimale, SANS Theme Builder

Découverte clé : The Events Calendar a son **propre template `single-event` natif**
(vue V2) qui fonctionne déjà très bien tel quel — titre, dates, description, bloc
« En pratique » (dans le contenu importé), Sources, DÉTAILS (catégorie, site), LIEU
(+ lien Google Maps), liens calendrier. **Aucun besoin du Theme Builder JetThemeCore**
(dont la fiabilité en automatisation reste un problème non résolu — cf. plus bas) pour
une fiche événement fonctionnelle.

Ce qui manquait par rapport au brief (`docs/TEMPLATES_WORDPRESS.md` #7 : crédit photo,
badges d'état, pilule territoire, "Vérifié le") a été ajouté via un filtre PHP
`the_content` (pas de widget/canvas) :
- `wordpress/design-system/single-event-meta.php` — pilule territoire (taxonomie
  `territoire`), badge de statut (`as_statut` → Complet/Annulé en rouge/Reporté,
  rien si `a_venir`), crédit photo (légende média WP si renseignée — aucune ne l'est
  encore, à demander à l'équipe qui alimente l'import), "Vérifié le" (`post_modified`,
  zéro champ supplémentaire nécessaire).
- `wordpress/scripts/apply-single-event-meta.mjs` — pousse ce PHP en snippet Code
  Snippets (scope `front-end`, gratuit).
- Touche typographique (`.tribe-events-single-event-title`, `.tribe-events-content`)
  ajoutée à `components.css` — classes CSS de TEC V2 **non vérifiées formellement**
  (pas de risque si elles sont fausses : CSS additive, aucune casse possible).

**Vérifié visuellement** sur l'événement 578 (aperçu WP) : pilule "Piémont" et
"Vérifié le 12 juillet 2026" s'affichent correctement.

✅ **v2 faite** : les 3 rails liés (même lieu, même catégorie, à venir) sont
maintenant ajoutés en pied de fiche (`cs_render_event_rail()` dans le même
snippet, filtre `the_content` priorité 20). Vérifié sans erreur PHP sur
l'événement 578 ; rails vides pour l'instant (aucun événement publié, même
cause que partout ailleurs — s'afficheront dès que du contenu réel sera publié).

## 🆕 « Tout l'agenda » et « Ce week-end » — v1

Pages existantes (932 et 930) remplies avec un titre + `jet-engine/listing-grid`
(réutilise `carte-evenement-blocks`, post 969, liste dense). Vérifié : la page
rend sans erreur, "No data was found" tant qu'aucun événement n'est publié
(comportement correct, pas un bug). **Filtre par date** ("le week-end en cours")
**pas câblé** — nécessite JetEngine Query Builder (meta_query sur `_EventStartDate`
entre vendredi et dimanche) ; pour l'instant les deux pages affichent la même
liste complète.

## ⚠️ Trouvaille bloquante : les archives de taxonomie (`territoire`, `tribe_events_cat`)
## ne fonctionnent PAS avec le thème par défaut

Testé `agendasabauda.eu/territoire/piemont/` : la page se charge mais retombe sur
le template d'archive générique de GeneratePress, qui ne requête QUE le post type
`post` — pas `tribe_events`. Résultat : page vide (affiche par erreur un commentaire
"Hello world!" au lieu des événements du territoire). **Contrairement à la fiche
événement (gérée nativement par TEC), les archives de taxonomie custom n'ont pas
d'équivalent "template natif qui marche déjà" — il faut construire quelque chose.**

Deux pistes, ni l'une ni l'autre triviale :
1. **`pre_get_posts`** (PHP, scope front-end, même méthode que la fiche événement) :
   forcer `post_type=tribe_events` sur la query principale quand `is_tax('territoire')`
   ou `is_tax('tribe_events_cat')`. Rapide à écrire, mais le rendu dépendra ensuite
   du gabarit de boucle par défaut du thème (`content-*.php` de GeneratePress) —
   probablement pas stylé du tout sans un second hook sur `the_content`/`the_excerpt`
   pour réutiliser le rendu carte-événement.
2. **Theme Builder → Archive template** (JetThemeCore) : la voie "propre" prévue par
   Crocoblock, mais c'est l'outil déjà documenté comme peu fiable en automatisation
   navigateur (cf. section Header/Footer plus bas).

**✅ Résolu, en deux temps :**
1. `wordpress/design-system/taxonomy-archive-query.php` (hook `pre_get_posts`,
   force `post_type=tribe_events` sur `is_tax('territoire')`/`is_tax('tribe_events_cat')`).
2. `wordpress/design-system/taxonomy-archive-template.php` (hook `template_redirect`,
   prend le contrôle TOTAL du rendu — plus besoin de compter sur le gabarit générique
   GeneratePress). Réutilise le style `.ag-row`/`.cs-ev-cat`/`.cs-terr` du design
   system, avec les lignes cliquables (mieux que `carte-evenement-blocks` qui ne l'est
   pas encore). Titre H1 = nom du terme, message d'accueil propre si aucun événement.

Vérifié sur `/territoire/piemont/` : affiche "Piémont" + "Aucun événement à afficher
pour l'instant." (comportement correct, même cause que partout ailleurs — aucun
événement publié). Le rendu avec de vraies données n'a pas été revérifié visuellement
cette fois (pour éviter d'exposer temporairement des événements brouillon sur une page
publique réelle) — mais la logique `WP_Query` est identique à celle déjà prouvée sur
la page de test jetable de la carte "à la une".

**Reste (v2)** : intro éditoriale pérenne FR/IT prévue par le brief
(`docs/TEMPLATES_WORDPRESS.md` #8 : "nos textes FR/IT sont écrits" — à récupérer
auprès de Franck), formatage de l'heure (même limitation connue partout ailleurs),
groupement par jour (`.ag-daygroup`).

## 🆕 Fiche lieu (venue) — gabarit PRÊT mais toujours BLOQUÉ par le bug de permaliens

`wordpress/design-system/venue-single-template.php`
(`apply-venue-single-template.mjs`) construit et poussé — fidèle à
"Agenda Sabaudo - Page Lieu.dc.html" (fil d'Ariane, H1, liste "Événements à
venir" avec `cs_event_date_short()`, mini-carte placeholder + adresse). Sur
`template_redirect`, `is_singular('tribe_venue')`.

**Non vérifiable visuellement pour l'instant** — le bug de permaliens
`/lieu/{slug}/` (ci-dessous) empêche d'atteindre la fiche. Tenté un
contournement en query var directe (`?post_type=tribe_venue&p=912`,
lecture seule, aucun nouvel endpoint) : **404**, alors qu'un CPT public
standard répond normalement à ce format même sans rewrite rules propres.
**Nouvelle piste plus probable que le rewrite-cache** : The Events Calendar
a un réglage **"Enable Venue and Organizer Pages"** (onglet Events →
Settings, généralement sous "Display" ou "General" selon la version) qui,
désactivé, empêche toute page singulière `tribe_venue`/`tribe_organizer` de
se résoudre — cohérent avec le symptôme observé (retombe sur la home). Pas
vérifiable depuis cette session : nécessiterait de se connecter à
wp-admin, ce que la politique de sécurité interdit (jamais saisir un mot de
passe, même pour le site du client). **À vérifier par Franck directement
dans Events → Settings**, ou lors d'une session avec accès WP-CLI/SSH.

## 🚧 Hub lieu (venue) — BLOQUÉ, permaliens cassés (pas un problème de contenu)

En voulant appliquer la même méthode "template natif TEC d'abord" qu'à la fiche
événement : les 3 lieux publiés (`tribe_venue`, ex. `halle-olympique`) ont une URL
REST correcte (`https://agendasabauda.eu/lieu/halle-olympique/`, status `publish`)
mais **cette URL sert en réalité la page d'accueil** (200 OK, mais canonical =
`https://agendasabauda.eu/`, contenu = page d'accueil) au lieu de la fiche du lieu.
Pas une redirection HTTP (vérifié en désactivant le suivi de redirection) : WordPress
route bien vers `/lieu/...` mais ne résout la query sur aucun post — symptôme
classique de **règles de réécriture (rewrite rules) non synchronisées**.

Tenté : ré-enregistrer les réglages de permaliens (Réglages → Permaliens →
Enregistrer, ce qui déclenche normalement `flush_rewrite_rules()`) — **n'a pas
résolu le problème**. Pas de piste supplémentaire explorée (pas d'accès WP-CLI/SSH
pour un `wp rewrite flush` plus direct, ni au réglage de slug spécifique aux lieux
dans TEC — pas trouvé dans Réglages → Évènements → Général, qui n'expose que le
permalien évènement singulier/pluriel, pas celui des lieux).

**À l'origine du blocage, pas un problème de gabarit** — donc pas de solution côté
`design-system/`. Prochaine piste à essayer : chercher un réglage de permalien
spécifique aux lieux plus profondément dans les onglets TEC, ou solliciter un accès
WP-CLI/SSH pour un flush direct.

## 🚨 CORRECTIF MAJEUR : le CSS "site-css" (Code Snippets) n'a JAMAIS atteint le front-end

En vérifiant visuellement la home (première fois qu'un composant est vérifié dans un
VRAI navigateur, pas juste via le HTML brut REST), tout le CSS censé être "✅ appliqué
en live" depuis le début du chantier (tokens, carte-événement, carte-à-la-une,
homepage) s'est révélé **absent du site public**, malgré snippet actif et sans erreur.

**Cause identifiée et confirmée empiriquement** : le scope CSS natif "site-css" de
Code Snippets (utilisé par `apply-tokens.mjs`/`apply-components.mjs` depuis le début)
est une fonctionnalité de **Code Snippets PRO**. Le plugin installé est la version
**gratuite (3.9.6)** — elle permet de créer/éditer/activer un snippet de type CSS
sans aucune erreur, mais **n'émet jamais son contenu côté front** (vérifié : absent
du HTML public sur plusieurs pages, avec cache-busting, y compris un snippet CSS créé
à la main dans l'admin — donc pas un souci de l'API REST).

**Fix appliqué** : `apply-tokens.mjs` et `apply-components.mjs` génèrent maintenant un
snippet **PHP** (scope `front-end`, gratuit, déjà utilisé ailleurs sur ce site — ex.
snippet #5) qui échote la CSS dans `<head>` via `wp_head`, encodée en base64 dans le
code généré pour éviter tout souci d'échappement. **Vérifié visuellement dans Chrome**
après le fix : tokens + composants + home s'affichent correctement.

**Implication** : toute affirmation "✅ vérifié en live" antérieure à cette passe (carte-
événement notamment) n'avait en réalité JAMAIS été vue stylée par un vrai visiteur —
seul le HTML/markup avait été vérifié via REST, pas le rendu visuel avec CSS. Bien vérifier
visuellement (Chrome, pas juste REST) chaque nouveau composant à l'avenir.

## 🆕 Carte "à la une" (grid 2×2 avec image) — construite et vérifiée avec de vraies données

Source réelle relue : `Agenda Sabaudo - Mobile.dc.html`, projet Claude Design **« Brief design
agenda Sabaudo »** (projectId `4b44f3d4-eac1-424a-aecf-c70fa2606fd2`) — voir
`build-recipes/homepage-mobile.md` §11. Variante DISTINCTE de `.ag-row` : image 3:2, eyebrow
`{date} · {territoire}` (10.5px/800), titre Semplicita 600 15.5px.

- **Listing Item live : post 976** (`carte-a-la-une-blocks`, source Posts, from post type
  Événements, vue Blocks/Gutenberg) — créé via le modal browser (piège connu : un clic sur un
  ref périmé peut atterrir ailleurs, ex. la page « À propos » ; toujours relire le formulaire
  avec `read_page` juste avant de cliquer Create).
- `wordpress/design-system/carte-a-la-une.gutenberg.html` — markup source (`jet-engine/dynamic-image`
  linked_image:false, `jet-engine/dynamic-field` date + titre, `jet-engine/dynamic-terms` territoire).
- `wordpress/design-system/components.css` — classes `.ala-une-card*` ajoutées (px littéraux,
  fidèles à la source, pas de mapping token).
- `wordpress/scripts/apply-carte-a-la-une.mjs` — pousse le markup sur le post 976 (idempotent).
- **Vérifié avec de vraies données** via une page brouillon jetable (créée puis mise à la
  corbeille dans la foulée) + un `jet-engine/listing-grid` pointé sur `lisitng_id:976` : image,
  territoire (« Piémont », « Savoie / Haute-Savoie ») et titre s'affichent correctement pour
  4 événements réels. Seule la date n'est pas formatée (même limitation connue que
  carte-evenement, cf. §Limitations).

### ⚠️ Constat important : AUCUN événement n'est actuellement publié

`GET /wp-json/wp/v2/tribe_events?status=any` : les ~20 événements du site sont tous en
statut **`draft`** (y compris le post 578 utilisé comme référence dans les tests précédents —
il n'a jamais été réellement publié, seulement prévisualisé). Un `jet-engine/listing-grid` en
config par défaut (`post_status:["publish"]`) affiche donc **"No data was found" partout tant
que ces événements restent en brouillon**. Ce n'est pas un bug des Listing Items — c'est un
état de données à trancher avec Franck (import en attente de relecture ? publication en masse
prévue avant l'ouverture du site ?) avant que la home ou toute page publique soit crédible.

## 🎉 PERCÉE : la carte-événement est enfin fidèle à la maquette, et vérifiée avec de vraies données

## 🎉 PERCÉE : la carte-événement est enfin fidèle à la maquette, et vérifiée avec de vraies données

**Constat de départ (signalé par Franck) : le site était "très loin des maquettes".** Diagnostic : la recette `carte-evenement.md` (et le CSS qui en découlait) avait été **fabriquée sans jamais lire le vrai design system** (deux agents l'ont confirmé indépendamment : l'outil DesignSync n'est accessible qu'à la session principale, pas aux subagents). Résultat : une carte "boîte à ombre + image + pastille de date" qui n'existe PAS dans la vraie maquette.

**Le vrai design**, lu directement dans `ui_kits/agenda/kit.css` + `components.jsx` + `colors_and_type.css` (Claude Design) : pour **cette mini-app calendrier/liste/carte précise** (`ui_kits/agenda` — vues « Calendrier », « Liste filtrable », « Carte »), la ligne événement est une **ligne dense de liste** (`.ag-row`, grid `96px(heure) | 1fr(contenu) | auto(statut)`), **sans image, sans pastille de date par ligne** — la date vit dans un **en-tête de groupe par jour** (`.ag-daygroup`).

> ⚠️ **CORRECTIF (même jour, message suivant de Franck)** : cette conclusion ne vaut QUE pour la mini-app `ui_kits/agenda`. Franck a montré des captures d'une **homepage** avec sections « À la une » et « Ça vaut le déplacement » (module transfrontalier, cf. `docs/TEMPLATES_WORDPRESS.md` §E) qui, elles, utilisent bien de **vraies cartes en boîte avec image**. Généraliser « jamais de boîte/image » à toute la carte-événement du site était une erreur. **Cette maquette homepage existe dans une AUTRE conversation Claude Design, non encore enregistrée comme fichier dans le projet "Cultura Sabauda Design System"** → DesignSync ne peut pas la lire (il ne lit que les fichiers d'un projet, pas l'historique d'autres conversations). **Bloqué tant que Franck n'a pas soit (a) enregistré cette maquette dans le projet, soit (b) collé le code ici.** Ne pas re-fabriquer un design de home en substitut.

**Solution technique — contournement du blocage Elementor/Theme Builder :** au lieu du canvas Elementor (3 échecs confirmés) ou du Theme Builder JetThemeCore (échecs aussi), on écrit le Listing Item en **mode "Blocks" (Gutenberg)**. Le markup Gutenberg est du TEXTE dans `post_content` — donc **scriptable de façon fiable via l'API REST déjà approuvée**, sans passer par un canvas. Les noms exacts des attributs de chaque bloc JetEngine ont été obtenus via l'**API WP native `/wp-json/wp/v2/block-types`** (lecture seule, aucun risque).

**Preuve — test de bout en bout avec 5 vrais événements du site (brouillons) :** titre, catégorie (`tribe_events_cat`) et territoire s'affichent **parfaitement**, avec les vraies classes CSS (`ag-row`, `cs-ev-cat`, `cs-terr`, `cs-ev-title`…). Ex. : « Au Castello di Rivoli, l'Arte Povera… » / « Expositions & Patrimoine » / « Piémont ».

**Fichiers** :
- `wordpress/design-system/carte-evenement.gutenberg.html` — le markup source.
- `wordpress/scripts/apply-carte-evenement.mjs` — l'applique sur un Listing Item existant (idempotent).
- `wordpress/design-system/components.css` — section carte-événement **réécrite** avec les vraies classes (`.ag-row`, `.ag-daygroup`, etc.), poussée en live (snippet #12).
- **Listing Item live : post 969** (`carte-evenement-blocks`, vue Blocks). L'ancien post 927 (vue Elementor, jamais rempli) est **déprécié** — à trasher ou reconvertir plus tard.

## ⏳ Limitations connues de la carte v1 (à affiner)

1. **Heure non formatée** : affiche la date brute SQL (`2026-01-01 00:00:00`) au lieu de `21h00`. Cause : `date_format` du bloc `dynamic-field` ne s'applique QUE si la meta est enregistrée comme champ "Date" dans une Meta Box JetEngine (comme `as_statut`/`as_accent` l'ont été). `_EventStartDate` (natif TEC) ne l'est pas. **Fix identifié mais pas appliqué** : ajouter un champ Date à la Meta Box "Champs Agenda" (JetEngine → Meta Boxes → id meta-1) pour `_EventStartDate` (et `_EventEndDate`). Tentative bloquée ce jour par un bouton "New Meta Field" qui n'a pas répondu après plusieurs essais (flakiness ponctuelle, méthode par ailleurs éprouvée) — à refaire.
2. **Lieu/venue absent** : afficher "Ville · Nom du lieu" nécessite soit une Relation JetEngine (event↔venue) à configurer dans JetEngine → Relations, soit un champ meta recalculé. Pas encore fait.
3. **Statut absent de la carte** : `as_statut` existe (meta box créée en session précédente) mais son mapping brut→libellé (`a_venir`→rien, `complet`→« Complet », `annule`→« Annulé » **en rouge**, `reporte`→« Reporté ») nécessite soit un JetEngine Glossary, soit d'accepter d'afficher la valeur brute en v1.
4. **Carte non cliquable** : pas encore de wrapper `jet-engine/dynamic-link` autour de toute la ligne.
5. **Groupement par jour** (`.ag-daygroup`) : pas implémenté — nécessite soit une fonctionnalité de regroupement de JetEngine Listing Grid, soit une page/logique dédiée. C'est une pièce structurelle à part, plus grosse que la carte elle-même.
6. **Header/Footer/Homepage** : **PAS ENCORE corrigés de la même façon.** Le CSS actuel pour `as-header`/`as-footer`/`as-hero` dans `components.css` est **toujours fabriqué**, jamais vérifié contre le vrai `kit.css`/`app.jsx`. C'est le prochain chantier prioritaire, avec la même méthode (lire le vrai design via DesignSync **dans la session principale**, pas via subagent).

## Méthode qui marche, à réutiliser

## ✅ Fait & vérifié en live

| Élément | Détail | Traçabilité |
|---|---|---|
| Tokens de la charte | Snippet Code Snippets #11, site-css | `wordpress/scripts/apply-tokens.mjs` |
| CSS composants (carte/header/footer/home) | Snippet #12, site-css | `wordpress/scripts/apply-components.mjs` |
| Identité du site | Titre « Agenda Sabauda » + accroche | `wordpress/scripts/apply-settings.mjs` |
| 7 pages piliers | Accueil (928), Aujourd'hui (929), Ce week-end (930), Cette semaine (931), Tout l'agenda (932), À propos (933), Proposer (934) | `wordpress/scripts/build-structure.mjs` |
| Menu « Principal FR » | ID 272, 24 items (temporel, Catégories▾ 11, Territoires▾ 4, Agenda▾, À propos, Proposer) | `wordpress/scripts/build-structure.mjs` |
| Theme Parts (shells, ⚠️ mal configurés) | Header (960), Footer (961), Single Event (962) — posts jet-theme-core créés, **mais SANS Type ni Display Conditions** (voir constat ci-dessous) | via MCP `wp_add_cpt` |
| **Meta box `as_statut` + `as_accent`** | JetEngine Meta Box « Champs Agenda — Statut & mise en avant » sur `tribe_events`. `as_statut` (select : a_venir/complet/annule/reporte), `as_accent` (switcher). **Testé de bout en bout** sur l'événement 578 (round-trip confirmé après reload). | Construit manuellement dans l'admin (formulaire JetEngine, pas d'API dédiée) |
| Listing JetEngine `carte-evenement` | Shell créé (post 927, source tribe_events, vue Elementor) | — |

## ⚠️ Trouvaille utile pour la suite

TEC expose nativement les meta `_tribe_events_status` et `_tribe_events_status_reason` sur chaque événement (vides par défaut). C'est l'alternative native évoquée dans `build-recipes/carte-evenement.md` §7.1. On a choisi `as_statut` (JetEngine, propre à notre contrat `as_*`) plutôt que le champ natif TEC — cohérent avec le reste du contrat méta. Décision : garder `as_statut`, ignorer les champs natifs TEC.

## ⏳ Reste à faire — nécessite un builder visuel (session supervisée)

Deux surfaces UI distinctes ont été testées en profondeur et confirmées **non fiables** en automatisation navigateur (détail dans la section méthode ci-dessous). En revanche, **les formulaires standards** (Meta Boxes, réglages, Quick Edit) s'automatisent très bien via `find` + `form_input`.

Reste à construire en builder, à faire avec Franck :
1. **Binding de la carte-événement** (post 927, Elementor) : les 10 widgets Dynamic Field/Image/Terms de `build-recipes/carte-evenement.md` §3.3, y compris le nouveau `.cs-ev-status` piloté par `as_statut`.
2. **Header/Footer/Single Event — à RECRÉER proprement** via *Crocoblock → Theme Builder → Grid view → filtrer par type (Section pour Header/Footer, Single pour l'événement) → tuile « + Create new page template »*. **Ne pas réutiliser les posts 960/961/962** (créés via API, orphelins du système de conditions — voir constat) : soit les mettre à la corbeille, soit les recycler en éditant leur contenu une fois qu'un vrai Header/Footer aura été créé par l'assistant.
3. **Homepage** (page 928) : Listing Grids + Query Builder — `build-recipes/homepage.md`. Puis réglage `page_on_front=928` (bloqué par le classifieur auto-mode tant que la page est vide — normal, à refaire une fois la home construite).

## ⚠️ Constat important : les shells Header/Footer/Single Event (960/961/962) sont mal formés

Créés via `wp_add_cpt` (MCP), ces 3 posts `jet-theme-core` n'ont **ni Type (Section/Single) ni Display Conditions** — colonnes vides confirmées dans *Theme Parts* (`edit.php?post_type=jet-theme-core`). Le générateur JetThemeCore attend un flux de création précis (Theme Builder → Grid view → modal avec conditions) qui inscrit ces méta ; les créer à la main via l'API REST générique ne suffit pas. **Ces 3 shells sont donc inutilisables tels quels** pour le système de conditions d'affichage — à recréer via l'assistant natif (voir point 2 ci-dessus).

## Point de méthode confirmé pour la suite (deux passes de tests, 2026-07-12)

- **Formulaires WordPress standards** (Meta Boxes, réglages, Quick Edit, champs de condition une fois le modal ouvert) → automatisables de façon fiable via `find` (obtenir une ref fraîche à chaque fois, ne jamais réutiliser une ref après un re-rendu) + `form_input` (indépendant du scroll). Éviter les clics sur des refs répétées sans rafraîchir (staleness — cause silencieuse d'actions « fantômes ») et éviter les toggles/checkbox « hidden » par coordonnées (a causé une navigation accidentelle une fois, sans perte de données).
- **Builder Elementor (canvas de widgets, drag-drop)** → PAS automatisable de façon fiable (3 tentatives échouées : drag simple, double-clic, bouton +). Le panneau de widgets et la recherche fonctionnent (formulaire), mais l'INSERTION d'un widget dans le canvas ne prend pas.
- **JetThemeCore Theme Builder (arbre de conditions, vue « Tree view »)** → rendu en canvas/SVG avec hit-testing custom, invisible à l'arbre d'accessibilité (`find` ne trouve aucun bouton), clics par coordonnées sans effet. **Vue « Grid view »** est un vrai DOM cliquable et ouvre un modal formulaire fonctionnel (Include/Entire/Entire Site + Add Condition confirmés cliquables et réactifs) — MAIS le bouton final **« Create » ne complète pas la création de façon fiable** (aucun nouvel élément n'apparaît dans la liste après plusieurs tentatives, cause exacte non identifiée : pas de champ nom visible, possible échec de validation silencieux côté JS). Cette UI a aussi provoqué plusieurs timeouts de capture d'écran (CDP), signe d'un rendu React/animations lourd peu compatible avec l'automatisation.
- **Conclusion pratique (mise à jour 3e passe) : il existe un contournement fiable pour le contenu dynamique des Listing Items** — construire le Listing Item en **vue "Blocks (Gutenberg)"** (choix disponible dans le modal "Setup Listing Item", lui-même fiable) plutôt qu'Elementor. Le markup Gutenberg vit en texte dans `post_content`, donc éditable via REST (déjà approuvé), **zéro canvas, zéro drag-drop**. Pour connaître les attributs exacts de chaque bloc JetEngine, interroger `GET /wp-json/wp/v2/block-types` (natif WP, lecture seule, safe) plutôt que deviner ou lire le code source du plugin. Reste vrai que les **Theme Parts (Header/Footer/Single) et leurs conditions d'affichage** n'ont PAS d'équivalent "texte" — elles restent bloquées derrière le Theme Builder canvas/modal capricieux ; à faire en session supervisée OU à retenter avec la même patience (le modal Grid view EST cliquable, juste peu fiable).
- **⚠️ DesignSync (lecture du design system Claude Design) n'est PAS accessible aux subagents (Agent tool) — uniquement à la session principale.** Deux agents lancés en parallèle pour analyser les maquettes ont échoué pour cette raison (confirmé indépendamment deux fois). **Toujours lire le design system soi-même**, dans le fil principal, jamais déléguer cette étape à un agent.
