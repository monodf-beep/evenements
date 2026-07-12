# État du build WordPress — agendasabauda.eu

*Dernière mise à jour : session du 2026-07-12 (4e passe — carte "à la une" + homepage mobile).*

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
