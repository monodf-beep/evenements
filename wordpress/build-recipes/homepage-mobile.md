# Recette de build — Homepage mobile (source RÉELLE, enfin trouvée)

*Source : `Agenda Sabaudo - Mobile.dc.html`, projet Claude Design **« Brief design
agenda Sabaudo »** (projectId `4b44f3d4-eac1-424a-aecf-c70fa2606fd2` — DIFFÉRENT du
projet "Cultura Sabauda Design System" lu précédemment). Lu le 2026-07-12.
Confirme mot pour mot les captures montrées par Franck. Remplace toute home
précédemment "fabriquée" dans `build-recipes/homepage.md`.*

**Le projet contient TOUS les gabarits du plan**, pas que la home :
`Agenda Sabaudo - Mobile.dc.html`, `Fiche Evenement.dc.html`, `Hub Categorie.dc.html`,
`Page Lieu.dc.html`, `Recherche.dc.html`, `Liste Evenements.dc.html`, `Le Fil.dc.html`,
`Article.dc.html`, `Proposer un evenement.dc.html`, `Annoncer.dc.html`,
`Explorations.dc.html` — **à lire un par un, dans cet ordre de priorité, avant de
construire chaque gabarit suivant.** Ne pas re-fabriquer, toujours relire la source.

## Tokens confirmés (identiques à `colors_and_type.css` déjà appliqués)
`{{ink}}` = `#1D1D1B` (noir encre) · fond carte = `#F7F1E8` (beige) / `#fff` ·
rouge accent = `#DC5D45` · éditorial = `'La Semplicita','Saira Condensed'` ·
corps = `'Nunito Sans'`. Rien de nouveau ici — les tokens déjà en snippet #11 sont bons.

## Structure mobile (ordre exact, de haut en bas)

| # | Section | Statique / Dynamique | Note |
|---|---|---|---|
| 0 | Interstitiel pub plein écran | Statique (contenu pub) | `sc-if popupVisible` — fermable, cf. §Publicité de `Specificites Agenda.html` |
| 1 | Masthead illustré (skyline Turin recoloré) + tagline | Statique (image + texte) | asset `masthead-full-sketch-v6.png`, masque CSS recoloré par territoire |
| 2 | Barre FR\|IT + burger menu | Statique | |
| 3 | Menu overlay (plein écran) | Statique | Liens : Home, Ce week-end, À la une, Événements d'aujourd'hui, Nouvelles expositions, Aux alentours, Musées, Curiosités, Météo, Rechercher, **Proposer un événement** (rouge, lien réel vers `Agenda Sabaudo - Proposer un evenement.dc.html` → future page WP) |
| 4 | Bandeau territoire actif + sélecteur (4 territoires) | Dynamique léger | "Vous regardez **{territoire}**" + dropdown des 4 |
| 5 | **Hero** — image pleine largeur + titre + dots carrousel | Dynamique (événement à la une) | ratio 1/1.05, dégradé sombre en bas, titre en Semplicita 28px |
| 6 | Pub inline (5:3) | Statique (emplacement pub) | |
| 7 | Recherche + bouton Chercher | Statique (form) | |
| 8 | **6 tuiles** (grid 2 col) : Ce week-end, Gastronomie, Concerts, Tout l'agenda (rang 1) | Statique (liens) | icônes dessinées à la main, légère rotation aléatoire (mode carnet) |
| 9 | Newsletter (cadre dessiné, rotation légère) | Statique (form) | "Chaque vendredi matin" |
| 10 | Pub inline | Statique | |
| 11 | **À LA UNE** — grid 2×2 cartes avec image | **Dynamique — vraies données TEC** | `as_score` élevé / mise en avant. Voir mapping ci-dessous |
| 12 | **ÇA VAUT LE DÉPLACEMENT** — 2 cartes verticales, module transfrontalier | **Dynamique — vraies données TEC** | Le fameux "Y aller →" ; icône jour/week-end selon `card.isDay`/`isWeekend` |
| 13 | **Événements d'aujourd'hui** — rail horizontal scrollable | **Dynamique — vraies données TEC** | 4 cartes 150px, `overflow-x:auto` |
| 14 | Pub inline | Statique | |
| 15 | **Nouvelles expositions** — 2 articles verticaux (image + H2 + chapô) | Dynamique (articles Cultura Sabauda ou événements enrichis) | Format "Le Fil", pas la carte événement standard |
| 16 | Pub inline | Statique | |
| 17 | **Tuiles secondaires** (rang 2) : Aux alentours, Musées, Curiosités, En famille | Statique | |
| 18 | Pub inline | Statique | |
| 19 | Suivez-nous (Instagram, Facebook) | Statique | |
| 20 | Recherche (bis, bas de page) | Statique | |
| 21 | Newsletter (bis, bas de page) | Statique | |
| 22 | Faire de la publicité (encart contact) | Statique | |
| 23 | **Footer** — 3 rangées de liens + mentions + copyright | Statique | Nav complète / légal / territoires+langues |
| 24 | Barre pub sticky bas d'écran (mobile only, position fixed) | Statique | |

## Mapping données — cartes « À la une » / « Ça vaut le déplacement »

**À la une** (grid 2×2, `article`) — réutilise en fait presque exactement la
recette déjà écrite pour `carte-evenement` (titre + image + territoire + date),
mais en variante **image + eyebrow date·territoire** plutôt que ligne dense :
- Image 3:2 (`_thumbnail_id`)
- Eyebrow : `{date courte} · {territoire}` — ex. « 04–05/07 · Piémont » (à composer :
  format date TEC + nom territoire, PAS un champ unique)
- Titre : `post_title`, Semplicita 600 15.5px

→ Nécessite un **2ᵉ Listing Item JetEngine (Blocks)**, variante "à-la-une-carte",
distinct de `carte-evenement-blocks` (post 969, qui est la ligne dense liste).
Même technique (blocs `jet-engine/dynamic-*` + `core/group`), déjà prouvée.

**Ça vaut le déplacement** (module transfrontalier) — **pas mappable sur un champ
TEC natif**. Nécessite des données maison : route (« Turin · 2 h · Tunnel du Fréjus »),
icône jour/week-end, lien "Y aller". Champs à ajouter à la Meta Box JetEngine
existante (id meta-1, déjà sur `tribe_events`) : `as_route` (text), `as_duree_visite`
(select : jour/week-end). **Décision à prendre avec Franck** : est-ce un champ par
événement, ou une sélection éditoriale à part (2 événements "vedettes" hors-territoire
choisis à la main) ? Le design suggère plutôt une **sélection manuelle** (2 cartes
fixes), pas une requête automatique.

## Ce qui est purement statique (pas de canvas Elementor nécessaire)

Toutes les sections marquées "Statique" ci-dessus sont du **HTML sémantique avec
styles inline** dans le fichier source — PAS de widget Elementor/JetEngine
spécifique requis. Elles se traduisent directement en **blocs Gutenberg natifs**
(`core/group`, `core/image`, `core/heading`, `core/paragraph`, `core/buttons`,
`core/html` pour les SVG inline) avec les mêmes styles inline — donc **scriptables
à 100% via REST (MCP), sans passer par Chrome.**

## Prochaines étapes (ordre d'exécution)

1. ✅ **Fait** — 2ᵉ Listing Item "carte-à-la-une" (post 976, Blocks/Gutenberg), vérifié
   avec de vraies données. Détail : `build-recipes/STATUS.md` §Carte "à la une".
2. ✅ **Fait (v1 complet, 24/24 sections)** — page Accueil (928) construite de bout
   en bout via `wordpress/design-system/homepage-mobile.gutenberg.html` +
   `apply-homepage.mjs`, **vérifiée visuellement dans Chrome** (après le correctif
   CSS, voir STATUS.md) du masthead jusqu'au footer. Interactions menu/territoire
   en CSS pur (checkbox hack), pas de JS.

   **Sections dynamiques (vraies données TEC)** : À la une (post 976, grid 2×2),
   Événements d'aujourd'hui (rail horizontal, réutilise le même Listing Item —
   ⚠️ pas encore filtré par date du jour, affiche les 4 derniers événements ; un
   vrai filtre "aujourd'hui" nécessite JetEngine Query Builder, pas juste le
   Listing Grid). Toutes deux affichent "No data was found" tant qu'aucun
   événement n'est publié (Franck a choisi de continuer sans attendre).

   **Sections encore statiques/placeholder, à finaliser plus tard** :
   - *Ça vaut le déplacement* (transfrontalier) : structure/styles fidèles à la
     source, contenu factice ("Titre de l'événement transfrontalier"…) — le
     mécanisme de données (sélection manuelle vs champ auto) reste à trancher
     avec Franck avant de câbler du vrai contenu.
   - *Nouvelles expositions* : textes d'exemple repris mot pour mot de la
     source design (les 2 mêmes articles que la maquette) — format "Le Fil"/
     Article, gabarit pas encore construit (cf. `docs/TEMPLATES_WORDPRESS.md`).
   - *Suivez-nous* : liens Instagram/Facebook en `#` — vraies URLs à demander
     à Franck.
   - *Footer* : liens vers les 7 pages piliers existantes câblés en vrai ; les
     pages qui n'existent pas encore (Dove Mangiare, Infos utiles, Qui sommes-
     nous, Politique de confidentialité, Cookies, Plan du site, Publicité) sont
     en `#`, à créer.
   - *Masthead* : asset manquant (`assets/masthead-full-sketch-v6.png`, croquis
     Turin recoloré) jamais fourni — repli en wordmark texte
     (`.as-masthead-sketch` dans `components.css`), à remplacer une fois l'asset
     obtenu.
3. Trancher avec Franck le mécanisme du module transfrontalier (champ auto vs
   sélection manuelle).
4. Relire les autres fichiers du projet (Fiche Événement, Hub Catégorie, etc.) au
   fur et à mesure des gabarits suivants du plan (`docs/TEMPLATES_WORDPRESS.md`).
