# Build WordPress — Crocoblock / JetEngine (de la maquette au site)

*Spec de construction : comment passer des maquettes Claude Design au site WordPress, avec la stack
Crocoblock (déjà achetée). Principe directeur : **TEC est la donnée, JetEngine est la mise en forme**.
On NE recrée PAS le type de contenu ; on habille les événements TEC avec des templates JetEngine.
Objectif transverse : **rester rapide** (Core Web Vitals = SEO), donc builder léger + garde-fous perf.*

---

## 0. Décision de stack (à trancher avant de commencer)

| Brique | Choix | Note |
|---|---|---|
| Données événements | **The Events Calendar** (déjà en place) | CPT `tribe_events`, dates, lieux, catégories, schema. **On ne double pas avec un CPT JetEngine.** |
| Taxonomies | `tribe_events_cat` (11 cat) · **`territoire`** (4>villes) · étiquettes | déjà seedées (Code Snippets) |
| Mise en forme dynamique | **JetEngine** (Listing Grid + Query Builder) | cartes, grilles, hubs, module transfrontalier |
| Filtres | **JetSmartFilters** | sur les hubs (date/ville/catégorie) |
| **Builder** | **Bricks** (reco perf) *ou* **Gutenberg** (gratuit, léger) — **PAS Elementor** | Elementor + Jet = le combo le plus lourd → mauvais CWV. Bricks = contrôle + rapidité. Gutenberg = gratuit mais moins pixel-précis. |
| Thème | **Bricks** (si Bricks) *ou* thème bloc léger **Blocksy/GeneratePress** (si Gutenberg) | éviter les thèmes lourds |
| Bilingue | Polylang (déjà en place) | JetEngine + Polylang : traduire les Listings/templates par langue |

> **Ma reco :** **Bricks + JetEngine** si tu acceptes un one-time (~80-130 €) → meilleur rapport
> contrôle/perf, la référence des sites Jet rapides. Sinon **Gutenberg + JetEngine + Blocksy**
> (100 % gratuit, plus léger qu'Elementor). **Dans les deux cas : n'installe pas Elementor.**

## 1. Garde-fous PERFORMANCE (non négociables — c'est ton SEO)
- **Pas Elementor.** Un seul builder.
- **Cache** : WP Rocket (payant) ou **LiteSpeed/W3TC/FlyingPress** ; + cache objet si dispo OVH.
- **Images** : formats réservés (ratios), lazy-load, WebP (plugin **ShortPixel/Imagify** free tier).
- **Limiter les Listing Grids par page** (chaque grille = une requête) ; **mise en cache** des requêtes JetEngine.
- **Désactiver les widgets Jet non utilisés** (JetElements/JetTabs… n'active que le nécessaire).
- Viser **LCP < 2,5 s mobile** ; tester chaque gabarit au **PageSpeed Insights** avant de généraliser.

## 2. Le CONTRAT de données (publisher ↔ JetEngine)

JetEngine affiche des **champs dynamiques**. Voici ce qu'il lit, et d'où ça vient :

**Fournis nativement par TEC** (JetEngine → « Dynamic Field » source *Post/TEC*) :
- image à la une, titre, contenu ; **date début/fin** (`_EventStartDate` / `_EventEndDate`) ;
- **lieu** (Venue : nom, adresse, ville, lat/lng) ; **catégorie** (`tribe_events_cat`).

**Taxonomie maison** : **`territoire`** (→ pilule couleur + filtre).

**Méta maison écrites par `publisher.py`** (clés canoniques — je ferai en sorte que le publisher
écrive EXACTEMENT celles-ci ; JetEngine les lit par « Meta Field » avec la clé) :

| Clé méta | Usage à l'affichage |
|---|---|
| `as_score` | tri « qualité » / sélection « À la une » (≥ 8) — jamais affiché |
| `as_gratuit` (0/1) | badge « Gratuit » + filtre |
| `as_tarif` | bloc pratique (prix) |
| `as_horaire` | bloc pratique (horaires) |
| `as_billetterie_url` | bouton « Réserver — site officiel » |
| `as_source_officielle_url` | lien source (jamais la source radar) |
| `as_verifie_le` | mention « Vérifié le JJ/MM » |
| `as_image_credit` | crédit photo sous l'image |

> ⚠️ **Point d'alignement** : ces clés sont le **contrat** entre mon `publisher.py`/`cs-seo-meta.php`
> et tes templates JetEngine. Je te livrerai la liste définitive figée quand on câblera le publisher
> (Lot 6) — mais construis les templates sur ces noms.

## 3. Composants réutilisables (JetEngine « Listing Items »)

À créer une fois, réutilisés partout :

- **`carte-evenement`** (gabarit constant) : image 3:2 → **DATE d'abord** (dynamic `_EventStartDate`,
  format `d/m`) → titre gras → lieu · ville → **pilule territoire** (couleur conditionnelle par terme)
  → badge « Gratuit » si `as_gratuit`. Toute la carte cliquable → permalien.
  - **variante `carte-compacte`** : vignette gauche + texte droite (pour les listes denses).
  - **variante `carte-hero`** : plein-largeur pour le carrousel.
- **`carte-article`** : vignette + titre (H2) + extrait + « » » (pour « Le fil » / listicles).
- **`carte-voisin`** (transfrontalier) : image + titre + **libellé trajet** (« Turin · 2 h · Fréjus ·
  🌙 week-end ») + bouton **« Y aller → »**.

## 4. Requêtes (JetEngine « Query Builder »)

- **À la une** : `tribe_events`, à venir, `as_score ≥ 8`, tri score desc, limite 4.
- **Ce week-end** : `tribe_events`, `_EventStartDate`/`_EventEndDate` chevauchant [ven, dim], limite 4 (+ compteur).
- **Aujourd'hui** : chevauchant aujourd'hui (module home ; hub en `noindex`).
- **Par catégorie** : filtré `tribe_events_cat = X`, à venir.
- **Par territoire** : filtré `territoire = X`, à venir.
- **Par ville** : `territoire = ville`, à venir (hub ville).
- **Transfrontalier** : `territoire IN {voisins de T}`, `as_score ≥ 8`, à venir, limite 3
  (table des voisins dans `PROXIMITE_TRANSFRONTALIERE.md`). **Masquer le bloc si 0 résultat.**
- **Tout l'agenda** : `tribe_events`, à venir, paginé.

## 5. Pages & templates (assemblage)

- **Home** : page construite au builder → carrousel (JetEngine Listing « hero » + query « à la une »/
  listicles) · recherche · **6 tuiles** (liens vers hubs) · Listing « À la une » · Listing « Ce week-end »
  (+ compteur + bouton noir « Voir tout l'agenda du week-end ») · « Le fil » (Listing articles) ·
  tuiles secondaires · newsletter · footer. *(Reprend l'ordre de `PROMPT_CLAUDE_DESIGN.md`.)*
- **Hub catégorie** (single template taxonomie, ou pages) : intro pérenne + Listing filtré + JetSmartFilters.
- **Hub territoire** : intro + « ce week-end en X » + Listing local filtrable + **module transfrontalier**.
- **`/[ville]/ce-week-end/`** : page/template daté (titre « Que faire ce week-end à [Ville] ? … ») — cf. `INTENTIONS_RECHERCHE_SEO.md`.
- **Fiche événement** : **single template** (TEC single override *ou* JetEngine Single) — mode minimal
  (image + crédit + badges + catégorie + titre + lieu + pilule + bloc pratique + « Vérifié le » + 3 rails Jet liés).
- **Recherche**, **404**, **Annoncer**, **légales**, **Proposer un événement** : cf. `TEMPLATES_WORDPRESS.md`.

## 6. Reprendre la maquette Claude Design
La maquette produit du HTML/CSS. On **ne réimporte pas le HTML** dans le builder — on **rebâtit**,
mais on **récupère les tokens** :
- **Couleurs** (charte Cultura Sabauda : `#18365E` bleu, `#F7F1E8` beige, `#DC5D45` rouge, `#1D1D1B` encre)
  → **réglages globaux** du builder (variables/couleurs globales).
- **Polices** (titres pinstripe *uniquement en display* · corps lisible) → typographies globales.
- **Espacements / ratios de carte** → styles globaux + le Listing Item `carte-evenement`.
- **Pilules territoire** (couleurs par territoire) → règle conditionnelle sur le terme.

## 7. Ordre de build conseillé
1. **Global styles** (couleurs, polices, conteneur) — la charte d'abord.
2. **Listing Item `carte-evenement`** (le composant central) → tester sur une requête.
3. **Home** (assembler les Listings + tuiles).
4. **Hub catégorie** + **hub territoire** (+ JetSmartFilters) + `/[ville]/ce-week-end/`.
5. **Single fiche** (mode minimal) + 3 rails liés.
6. Pages statiques (Annonce, légales, Proposer un événement).
7. **Perf pass** (cache, images, PageSpeed) avant d'ouvrir.

## 8. Ce qui reste chez MOI (indépendant de Crocoblock)
- Le **pont `publisher.py` → WordPress** (écrit les événements + méta `as_*` du §2) — Lot 6.
- Le **routage** score ≥7 (Cultura Sabauda) / <7 (Agenda Sabauda).
- La **liste définitive des clés méta** (contrat §2) au câblage du publisher.
- Le mu-plugin/filtre pour le **slug `luoghi`** des lieux si tu le veux.
