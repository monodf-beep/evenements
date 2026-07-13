# État du build WordPress — agendasabauda.eu

*Dernière mise à jour : session du 2026-07-13 (9e passe — vraie grammaire de carte, Hub territoire/catégorie, « Ce week-end »/« Tout l'agenda » et Recherche reconstruits en gabarits PHP dédiés).*

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
