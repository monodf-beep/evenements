# Gabarit des pages HUB (lieu) + runbook de création — à exécuter côté WordPress

*But : créer les pages hub SEO hyperlocal (Torino, Nice, Aoste, Forte di Bard, Chambéry,
Chablais…) avec **UN seul gabarit réutilisable** et un **listing d'événements dynamique**
(jamais de page vide). Ce document est autonome : il peut être confié à une conversation
qui a l'accès WordPress (Novamira / MCP JetEngine). Le CONTENU de chaque page (H1, intro,
meta FR/IT) est dans `docs/pages/<lieu>.md`.*

---

## 0. Principe

- **Un gabarit unique** = une zone d'intro éditoriale (statique, par page) + un **listing
  d'événements dynamique** (JetEngine) filtré par **lieu**.
- Le filtre par lieu s'appuie sur ce que le publisher pose déjà sur chaque `tribe_events` :
  - **méta `as_ville`** (la ville de l'événement) → filtre VILLE (ex. « Chambéry »),
  - **taxonomie `territoire`** (4 termes) → filtre TERRITOIRE,
  - **`tribe_events_cat`** → filtre CATÉGORIE (pour les croisements ville×catégorie),
  - dates `_EventStartDate` / `_EventEndDate` → borne « à venir ».
- **Bilingue Polylang** : chaque page a une version **FR** et une **IT**, liées.
- **URL perpétuelle** : jamais d'année dans le slug.

## 1. Prérequis (à vérifier une fois)

- JetEngine actif (Query Builder + Listing Grid) ; The Events Calendar ; Polylang ; RankMath.
- La méta `as_ville` est bien renseignée sur les `tribe_events` (c'est le cas via
  `scripts/publisher_as.py`). Vérifier sur 2-3 fiches (champ personnalisé `as_ville`).

## 2. Étape 0 — construire le gabarit réutilisable (UNE fois)

### 2a. La « carte événement » (JetEngine Listing Grid item), si elle n'existe pas déjà
Listing pour `tribe_events` affichant : image à la une · titre (lien) · date (de
`_EventStartDate`, format `j F`) · ville (`as_ville`) · catégorie. Sobre, réutilisable partout.

### 2b. La Query MODÈLE (à cloner par page)
JetEngine **Query Builder**, type *Posts*, `post_type = tribe_events`, `post_status = publish` :
- **Meta query** « à venir » : `_EventEndDate` `>=` `%current_date%` (repli `_EventStartDate`
  si l'événement n'a pas de fin).
- **Order by** : méta `_EventStartDate`, **ASC** (le plus proche d'abord).
- **Posts per page** : 24 (avec pagination) ou « load more ».
- Le **filtre lieu** est ajouté À LA COPIE, par page (cf. étape 1).

### 2c. Le gabarit de page
Une page WordPress (Gutenberg natif de préférence, sinon Elementor) structurée ainsi :
`[H1]` → `[intro éditoriale]` → `[Listing Grid = carte 2a + Query de la page]` → (option)
`[maillage interne]`. C'est CE gabarit qu'on duplique.

## 3. Étape 1 — créer chaque page (runbook, à répéter par lieu et par langue)

Pour la page **FR** puis la page **IT** (contenu dans `docs/pages/<lieu>.md`) :
1. **Cloner la Query modèle** → y ajouter le filtre du lieu :
   - page VILLE : **meta query** `as_ville` `IN` (liste du fichier), ex. `Chambéry` ;
   - page ZONE (ex. Chablais) : `as_ville` `IN` (la liste de communes du fichier) ;
   - page TERRITOIRE : **tax query** `territoire` = le terme.
2. **Créer la page** : titre + **slug perpétuel** (du fichier) + coller l'**intro** (H1, texte),
   insérer le **Listing Grid** (carte 2a + la Query de l'étape 1) + le **maillage interne**.
3. **RankMath** : renseigner *Meta title* + *Meta description* (du fichier), langue correcte.
4. **Polylang** : définir la langue de la page, puis **lier** la version FR et la version IT
   (elles doivent pointer l'une vers l'autre → hreflang correct).
5. **Indexation** : ces 6 pages ont l'offre (seuil franchi) → **index, follow**. (Une future
   page sous le seuil = `noindex` jusqu'à graduation, cf. `docs/CATALOGUE_GEO_SEO.md`.)

## 4. Les 6 pages à créer maintenant (offre suffisante — cf. Couverture géo)

| Page | Type | Filtre listing | Langues | Contenu |
|---|---|---|---|---|
| **Torino / Turin** | ville | `as_ville ∈ {Torino, Turin}` | IT + FR | `docs/pages/torino.md` |
| **Nice** | ville | `as_ville = Nice` | FR + IT | `docs/pages/nice.md` |
| **Aoste / Aosta** | ville | `as_ville ∈ {Aoste, Aosta}` | FR + IT (à parité) | `docs/pages/aoste-aosta.md` |
| **Forte di Bard** | lieu | `as_ville = Bard` | IT + FR | `docs/pages/forte-di-bard.md` |
| **Chambéry** | ville | `as_ville = Chambéry` | FR + IT | `docs/pages/chambery.md` |
| **Chablais** | zone | `as_ville ∈ {Thonon-les-Bains, Évian-les-Bains, Morzine, Les Gets, Abondance, Châtel, Avoriaz}` | FR + IT | `docs/pages/chablais.md` |

## 5. Rappels

- **URL perpétuelle** (pas d'année) ; garder la même URL d'une saison à l'autre.
- **hreflang** via la liaison Polylang FR↔IT (indispensable).
- **Maillage interne** : chaque page renvoie vers son hub territoire, ses catégories, ses
  lieux/villes voisins (détaillé dans chaque fichier de contenu).
- Ne PAS créer de page pour un lieu sous le seuil (thin content) — attendre la graduation.

---

## 6. Prompt prêt à coller (pour la conversation WordPress / Novamira)

> Tu as l'accès WordPress (agendasabauda.eu : The Events Calendar + JetEngine + Polylang +
> RankMath). Crée les **6 pages hub** décrites dans `docs/GABARIT_PAGES_HUB.md` §4, en suivant
> le **runbook §2-§3** : construis (ou réutilise) le gabarit unique (carte événement + Query
> modèle « à venir » filtrée par `as_ville`/`territoire`), puis pour chaque page crée la version
> **FR** et la version **IT** à partir du contenu de `docs/pages/<lieu>.md` (H1, slug perpétuel,
> intro, meta RankMath), insère le Listing Grid filtré, **lie les deux langues en Polylang**, et
> mets les 6 pages en **index, follow**. Vérifie qu'aucune n'est vide (le listing doit remonter
> des événements). Rends la liste des URLs créées.
