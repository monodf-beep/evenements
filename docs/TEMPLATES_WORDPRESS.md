# Templates de page WordPress — ce qui manque (Agenda Sabauda)

*Socle : The Events Calendar (TEC) + thème bloc + Polylang. TEC fournit déjà les fiches, lieux,
organisateurs et archives de catégories ; on n'ajoute que ce qui manque ou ce qu'on veut mieux.
Un même gabarit sert plusieurs pages (1 hub catégorie → 11 catégories ; 1 hub territoire → 4
territoires + villes). Ordre = priorité de lancement.*

---

## A. À CONSTRUIRE — gabarits maison (rien par défaut) · LANCEMENT

| # | Template | Fichier | Contenu clé |
|---|---|---|---|
| 1 | **Home** | `front-page.php` | Les strates mobiles : carrousel → recherche → 6 tuiles → à la une → ce week-end → le fil → tuiles secondaires → newsletter → footer. |
| 2 | **Hub « Ce week-end »** (clé SEO) | page + gabarit (requête dates) | Titre + dates + intro pérenne + **filtres date/ville/catégorie** + liste exhaustive. URL evergreen `/fr/ce-week-end/`. |
| 3 | **« Tout l'agenda »** | page + gabarit | La **seule** page exhaustive, filtrable date · ville · catégorie · territoire. |
| 4 | **Hub territoire** | `taxonomy-territoire.php` | Intro pérenne + « ce week-end en X » + flux local filtrable + encart **« De l'autre côté des Alpes »** (module transfrontalier). Sert les 4 territoires. |
| 5 | **« Proposer un événement »** | page + formulaire modéré | Levier organisateurs. Soumission → brouillon à modérer (jamais auto-publié). |
| 6 | **404** | `404.php` | Recherche + portes principales (pas un cul-de-sac). |

## B. À PERSONNALISER — TEC/WP donne une base, on l'override · LANCEMENT

| # | Template | Base | Ce qu'on change |
|---|---|---|---|
| 7 | **Fiche événement** | TEC `single-event` | **Mode minimal d'abord** + nos champs : crédit photo, badges d'état, **pilule territoire**, « Vérifié le », bloc pratique, **3 rails liés** (même lieu / catégorie / dates). Une seule source de schema (TEC). |
| 8 | **Hub catégorie** | archive catégorie TEC | **Intro éditoriale pérenne** au-dessus (nos textes FR/IT sont écrits) + cartes au **gabarit constant**. Sert les 11 catégories. |
| 9 | **Hub lieu** | TEC `single-venue` (`/luoghi/`) | Style GuidaTorino minimal : fil d'Ariane → H1 (lieu) → « Événements à venir » → carte → adresse. Aucune prose. |
| 10 | **Recherche** | `search.php` | Résultats orientés **événements** (date + lieu + pilule), pas des articles bruts. |

## C. À PERSONNALISER — APRÈS lancement

| # | Template | Base | Note |
|---|---|---|---|
| 11 | **Hub ville** | `taxonomy-territoire.php` (terme enfant) | Même gabarit que le territoire. **`noindex`** tant que < seuil de volume (anti-bloat). |
| 12 | **« Le fil » / archive articles** | `home.php` / `archive.php` | Liste verticale H2 + vignette + extrait + pagination (les listicles). |
| 13 | **Article / listicle** | `single.php` | Dossier « Les 10 du week-end » : `## Nom` → image → paragraphe → « En savoir plus → ». |
| 14 | **Hubs « Aujourd'hui » / « Cette semaine »** | gabarit dates | À construire **seulement si affichés** ; **`noindex`** (infreshables en solo). |
| 15 | **Hub étiquette « Gratuit »** | archive étiquette | `/fr/evenements/gratuit/` — quand la donnée prix sera fiable. |
| 16 | **Hub organisateur** | TEC `single-organizer` | Souvent **`noindex`** ; optionnel (GuidaTorino ne l'expose même pas). |

## D. CONTENU SEUL — gabarit page par défaut, juste remplir (LANCEMENT)

- **Mentions légales · Confidentialité · Crédits photos** — contenu FR/IT **déjà écrit** dans
  `docs/legal/`. → coller dans 3 pages WordPress standard.
- **À propos / le projet** — page standard.
- **Landing newsletter** (si page dédiée en plus du bloc home).

## E. PARTIES DE THÈME (pas des « pages », mais nécessaires au lancement)

- **Header** : logo · FR|IT · burger + **menu overlay** (4 territoires, catégories, Proposer un
  événement, à propos).
- **Footer** : 3 rangées (nav · légal/société · territoires + FR|IT + « édité par Cultura Sabauda »).
- **Composants réutilisables** : la **carte événement** (gabarit constant, 3 variantes), le
  **carrousel** de sélections, le **bloc newsletter**, les **emplacements pub**, le **module
  transfrontalier** (carte « Y aller → » avec trajet + tunnel + format journée/week-end).

---

## Récap — le strict minimum pour OUVRIR

**7 gabarits** couvrent tout le lancement :
1. Home · 2. Fiche événement · 3. Hub catégorie · 4. Hub territoire · 5. Hub lieu ·
6. « Ce week-end » + « Tout l'agenda » (gabarit liste filtrable, mutualisable) · 7. Recherche + 404.

\+ les pages **contenu seul** (légales, à propos) et les **parties de thème** (header/footer/
carte/carrousel). « Proposer un événement » peut suivre juste après si le temps manque.
