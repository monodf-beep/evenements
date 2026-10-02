# Plan complet des pages HUB + gabarit + runbook — à exécuter côté WordPress

*Document autonome, à confier à une conversation qui a l'accès WordPress (Novamira / MCP
JetEngine). Il contient : la **logique** (pourquoi ces pages, dans cet ordre), le **plan
complet** (socle + vagues), le **gabarit** à construire une fois, et le **runbook** de
création. Le contenu éditorial des pages « prêtes » est dans `docs/pages/<lieu>.md`.*

---

## A. Le principe (à comprendre avant de créer)

- **Un gabarit unique** = une zone d'intro éditoriale (statique, par page) + un **listing
  d'événements dynamique** (JetEngine) filtré par **lieu**. Jamais de page vide.
- **Graduation** : on ne crée une page « lieu » **que si elle a ≥ 8 événements à venir**
  (sinon page à moitié vide = *thin content*, pénalisé). La page **`/couverture-geo`** du
  back-office dit **qui est prêt** et **qui attend**. Ce n'est pas une question d'importance
  mais de **matière disponible** : ex. Torino (48) ou Nice (17) sont prêts, mais Annecy (5) non
  — Annecy graduera dès qu'il sera mieux sourcé.
- **Bilingue Polylang** : chaque page a une version **FR** et une **IT**, liées (hreflang).
- **URL perpétuelle** : jamais d'année dans le slug (la page cumule son autorité).
- Le filtre par lieu s'appuie sur ce que le publisher pose déjà sur chaque `tribe_events` :
  **méta `as_ville`** (ville), **taxonomie `territoire`** (4 termes), **`tribe_events_cat`**
  (catégorie), dates `_EventStartDate` / `_EventEndDate` (borne « à venir »).

  > ⚠️ **Corrigé le 04/09, vérifié en base (Novamira)** : ce paragraphe décrit un mécanisme
  > JetEngine qui n'a jamais été construit. Les 24 pages ville/zone réellement en ligne
  > utilisent un shortcode maison, `[cs_hub_ville villes="…" territoire="…"]`
  > (Code Snippets #61 « CS · Hub ville »), qui filtre par **`_VenueCity`** (méta du CPT
  > `tribe_venue`, pas `as_ville` de l'événement) pour une liste de villes fixée EN DUR dans
  > le contenu de chaque page. Les 4 pages territoire (§B0) filtrent par la taxonomie
  > `territoire` seule, sans liste de villes. Encore la règle 1 : ce document décrivait un
  > plan, pas ce qui a fini par être construit — personne ne l'avait revérifié après coup.

- **04/09, décision de Franck sur les 19 pages ville/zone sous le seuil de 8** (dont 8 à zéro
  événement, trouvées le 31/08 : Aix-les-Bains, Chamonix, Cluses, Menton, Moûtiers,
  Saint-Jean-de-Maurienne, Sallanches, Thonon-les-Bains — toujours à zéro le 04/09, mesuré à
  nouveau via le shortcode réel) : **restent en `index`, choix assumé**, pari sur un
  remplissage rapide plutôt qu'un passage en `noindex` le temps de graduer. Pas d'action
  technique prise. Si le remplissage tarde, revenir sur ce choix plutôt que de le laisser
  dormir sans y repenser — ce n'est pas un état terminal, personne ne le rouvre tout seul.

---

## B. Le plan complet des pages (la feuille de route)

### B0. SOCLE — 4 pages « territoire » (parentes, à créer EN PREMIER)
Elles agrègent **tout** un territoire → **toujours pleines**, jamais de souci de seuil. Ce sont
les **parents** du maillage interne (chaque page lieu y renvoie). Filtre = **tax query
`territoire`**. Intro courte (modèle bilingue en **Annexe G**).

| Page territoire | Slug | Filtre listing | Langues |
|---|---|---|---|
| Savoie / Haute-Savoie | `territoire/savoie-haute-savoie` | `territoire = savoie-haute-savoie` | FR + IT |
| Piémont | `territoire/piemonte` | `territoire = piemonte` | IT + FR |
| Vallée d'Aoste | `territoire/vallee-aoste` | `territoire = vallee-aoste` | FR + IT (parité) |
| Nice / Alpes-Maritimes | `territoire/nice-alpes-maritimes` | `territoire = nice-alpes-maritimes` | FR + IT |

### B1. VAGUE 1 — 5 pages « lieu » PRÊTES (seuil franchi aujourd'hui)
Contenu éditorial rédigé, dans `docs/pages/`. *(Forte di Bard retiré : un lieu-musée sans
intention de recherche « ville » — ses événements restent publiés sous le territoire VdA.)*

| Page | Type | Filtre listing | Langues | Contenu |
|---|---|---|---|---|
| **Torino / Turin** (48 évts) | ville | `as_ville ∈ {Torino, Turin}` | IT + FR | `docs/pages/torino.md` |
| **Nice / Nizza Marittima** (17) | ville | `as_ville = Nice` | FR + IT | `docs/pages/nice.md` |
| **Aoste / Aosta** (9) | ville | `as_ville ∈ {Aoste, Aosta}` | FR + IT (parité) | `docs/pages/aoste-aosta.md` |
| **Chambéry** (8) | ville | `as_ville = Chambéry` | FR + IT | `docs/pages/chambery.md` |
| **Chablais** (8) | zone | `as_ville ∈ {Thonon-les-Bains, Évian-les-Bains, Morzine, Les Gets, Abondance, Châtel, Avoriaz}` | FR + IT | `docs/pages/chablais.md` |

### B2. VAGUE 2 — les prochaines à GRADUER (au fil du sourcing, PAS maintenant)
Dès qu'une entité passe **8 événements à venir** (surveiller `/couverture-geo`), on lui crée sa
page — le contenu éditorial sera rédigé **à ce moment-là** (même gabarit). Les plus proches :
- **Savoie/HS** : Thonon-les-Bains (6), Annecy (5), Lac d'Annecy (5), Tarentaise (5)
- **Piémont** : Cuneo (4) — puis, une fois sourcés : **Langhe, Monferrato, Alba**
- **Vallée d'Aoste** : Courmayeur, Cervinia (à sourcer)
- **Nice/06** : Menton (à sourcer)
> La **liste complète** des entités candidates (villes, massifs, vallées, lacs, stations) avec
> priorités P1/P2/P3 est dans **`docs/CATALOGUE_GEO_SEO.md`**. On ne crée jamais à l'aveugle :
> c'est la Couverture géo qui déclenche.

### B3. Formats complémentaires (PLUS TARD)
- **`/[ville]/ce-week-end/`** — pages datées, roulantes (même filtre ville + fenêtre week-end).
- **Croisements catégorie × ville** (« concerts à Chambéry »…) — graduent aussi au seuil.

---

## C. Le gabarit réutilisable (à construire UNE fois)

### C1. La « carte événement » (JetEngine Listing Grid item), si absente
Listing pour `tribe_events` : image à la une · titre (lien) · date (`_EventStartDate`, format
`j F`) · ville (`as_ville`) · catégorie. Sobre, réutilisable partout.

### C2. La Query MODÈLE (à cloner par page)
JetEngine **Query Builder**, type *Posts*, `post_type = tribe_events`, `post_status = publish` :
- **Meta query « à venir »** : `_EventEndDate` `>=` `%current_date%` (repli `_EventStartDate`).
- **Order by** : méta `_EventStartDate`, **ASC**.
- **Posts per page** : 24 (pagination ou « load more »).
- Le **filtre lieu** est ajouté À LA COPIE, par page.

### C3. Le gabarit de page
Page WordPress (Gutenberg natif de préférence, sinon Elementor) :
`[H1]` → `[intro éditoriale]` → `[Listing Grid = carte C1 + Query de la page]` → `[maillage
interne]`. C'est CE gabarit qu'on duplique.

## D. Runbook — créer chaque page (répéter par page ET par langue)
1. **Cloner la Query modèle** + ajouter le filtre : page territoire → `tax territoire` ; page
   ville → `meta as_ville IN (…)` ; page zone → `meta as_ville IN (liste de communes)`.
2. **Créer la page** : titre + **slug perpétuel** + coller **H1 + intro** + insérer le **Listing
   Grid** filtré + le **maillage interne**.
3. **Yoast** : *Meta title* + *Meta description* (du fichier / annexe), bonne langue.
   > ⚠️ Corrigé le 2026-08-03 : ce runbook disait « RankMath ». **RankMath n'est pas
   > installé.** Mesuré sur la page servie de agendasabauda.eu — trois occurrences de
   > `yoast`, zéro de `rank-math`. Chercher un panneau RankMath dans l'éditeur, c'est
   > chercher un plugin qui n'existe pas sur ce site. Les autres mentions de RankMath du
   > dépôt (`AGENT_SEO_DASHBOARD_SPEC.md`, `DECISIONS_ECARTEES.md`, plus bas dans ce
   > fichier) datent d'avant l'installation réelle et n'ont pas été revérifiées.
4. **Polylang** : définir la langue, puis **lier** les versions FR ↔ IT.
5. **Indexation** : pages du socle (B0) et vague 1 (B1) = **index, follow**. Toute page sous le
   seuil = `noindex` jusqu'à graduation.
6. **Vérifier qu'aucune page n'est vide** (le listing doit remonter des événements).

## E. Rappels
- URL perpétuelle (pas d'année). hreflang via la liaison Polylang. Ne jamais créer sous le seuil.
- Ordre conseillé : **B0 (socle territoire) → B1 (les 6) → B2 au fil de l'eau**.

---

## F. Prompt prêt à coller (pour la conversation WordPress / Novamira)

> Tu as l'accès WordPress (agendasabauda.eu : The Events Calendar + JetEngine + Polylang +
> RankMath). Objectif : bâtir les pages hub SEO selon `docs/GABARIT_PAGES_HUB.md`.
> 1) Construis **une fois** le gabarit réutilisable (carte événement + Query modèle « à venir »
> filtrable, §C). 2) Crée d'abord le **socle : 4 pages territoire** (§B0, filtre taxo
> `territoire`, intro de l'annexe §G), FR + IT liées Polylang. 3) Crée ensuite les **5 pages
> prêtes** (§B1) à partir du contenu de `docs/pages/<lieu>.md` (H1, slug perpétuel, intro, meta
> RankMath), avec le Listing Grid filtré par `as_ville`, FR + IT liées. Mets socle + vague 1 en
> **index, follow**. Respecte les noms FR/IT de `docs/NOMMAGE_TERRITOIRES.md`. Vérifie qu'aucune
> page n'est vide. Rends la liste des URLs créées.
> N'attaque PAS la vague 2 (§B2) : elle se fera plus tard, quand la Couverture géo l'indiquera.

---

## G. Annexe — intro des 4 pages territoire (socle)

*Gabarit court, à adapter légèrement par territoire. Aucun événement en dur (listing dynamique).*

- **Savoie / Haute-Savoie** — H1 FR « Que faire en Savoie et Haute-Savoie : l'agenda culturel » ·
  IT « Cosa fare in Savoia » · Intro FR : « Concerts, expositions, festivals,
  marchés et fêtes populaires des deux Savoie — d'Annecy à Chambéry, des lacs aux stations.
  Retrouvez ici tout l'agenda du territoire, actualisé en continu. »
- **Piémont** — H1 IT « Cosa fare in Piemonte: l'agenda degli eventi » · FR « Que faire en
  Piémont » · Intro IT : « Concerti, mostre, festival, sagre e mercati in tutto il Piemonte —
  da Torino alle Langhe e al Monferrato. Qui l'agenda del territorio, aggiornato di continuo. »
- **Vallée d'Aoste** — H1 (parité FR/IT) « Que faire en Vallée d'Aoste / Cosa fare in Valle
  d'Aosta » · Intro : agenda bilingue de la région — d'Aoste au Forte di Bard, des châteaux aux
  vallées et stations.
- **Nice / Alpes-Maritimes** — H1 FR « Que faire à Nice et dans les Alpes-Maritimes » · IT
  « Cosa fare a Nizza Marittima e nelle Alpi Marittime » · Intro : l'agenda du territoire niçois,
  de la ville aux vallées (Roya, Vésubie, Tinée) et à Menton.

*Meta title (~55 car.) : « Agenda [territoire] — sorties & événements | Agenda Sabauda ».
Meta description (~150 car.) : « Que faire en [territoire] ? Concerts, expos, festivals, marchés :
l'agenda culturel du territoire, actualisé en continu. » (traduire en IT).*
