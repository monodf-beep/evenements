# Recette de build — Carte-événement (JetEngine Listing Item)

*Composant central du site agendasabauda.eu : la carte qui liste un `tribe_events`.
Stack réelle : GeneratePress + The Events Calendar + Crocoblock JetEngine/JetSmartFilters +
Elementor + Polylang. On NE crée PAS de CPT `evenement` : la carte habille un `tribe_events`.*

**Sources de vérité de ce fichier**
- Tokens live : `wordpress/design-system/tokens.css` (appliqués sur le site via Code Snippets).
- Contrat méta FIGÉ : `docs/CONTRAT_META_AS.md` (8 clés `as_*`, immuables).
- Brief design : `docs/BRIEF_DESIGN_AGENDA_SABAUDO.md` §8.1 (carte, 4 variantes) + §7.1 (dates).
- Build Crocoblock : `docs/BUILD_WORDPRESS_CROCOBLOCK.md` §2–3.

**Règles design VERROUILLÉES (rappel, non négociable)**
- (a) **Statut = typographie, jamais couleur.** Classes `.cs-ev--{statut}`.
- (b) **Catégorie = monochrome**, signalée par le LIBELLÉ en La Semplicita (`.cs-ev-cat`), sans teinte.
- (c) **Densité compacte** via tokens `--sc-*` (agenda uniquement).
- (d) **Radius 2px** (`--r-1`), ombre `--shadow-paper`.
- (e) **Pastille date** : jour + mois, fond rouge (`--cs-rouge`), La Semplicita 700.

---

## 1. Aperçu visuel — structure EventRow (variante compacte/liste, primaire)

Rangée horizontale dense, entièrement cliquable → permalien de l'événement.

```
┌───────────────────────────────────────────────────────────────────────┐
│ ┌──────┐  ┌────────┐  CONCERTS & MUSIQUE        ● Piémont              │  ← kicker cat (La Semplicita) + puce territoire (mono)
│ │ SAM  │  │        │  Titre de l'événement sur deux lignes maximum      │  ← H titre (La Semplicita 600)
│ │  4   │  │ image  │  📍 Turin · Teatro Regio      · 21h00              │  ← lieu (ville · venue) · heure
│ │ JUIL │  │ 3:2    │  ⏹ Annulé          [Gratuit]                       │  ← statut typographique + badge Gratuit
│ └──────┘  └────────┘                                                    │
└───────────────────────────────────────────────────────────────────────┘
  pastille    couverture
  date        (ratio 3:2)
```

**Ordre / hiérarchie de lecture** (le scan doit donner *quand → quoi → où* sans clic ni survol) :

1. **Pastille date** (à gauche, ancre visuelle) — jour de semaine abrégé + n° + mois, fond rouge.
2. **Kicker catégorie** — libellé en La Semplicita, monochrome, cliquable (petites capitales).
3. **Puce territoire** — pastille monochrome (point + libellé), alignée à droite du kicker.
4. **Titre** — La Semplicita 600, 2 lignes max (ellipsis), poids visuel principal.
5. **Lieu** — `ville · nom du lieu`, corps Nunito Sans, gris `--fg-2`.
6. **Heure** — dans la même ligne meta que le lieu, séparateur `·`.
7. **Statut** (si ≠ à venir) — typographique (`.cs-ev--{statut}`), jamais coloré.
8. **Badge « Gratuit »** (si applicable) — seul badge coloré toléré sur la carte.
9. **Image de couverture** — ratio **3:2** (invariant du site), vignette à gauche de la vignette
   compacte OU bandeau haut pour la variante verticale (voir §6).

> **Pas d'extrait sur la carte** (règle GuidaTorino) : date + lieu + heure suffisent.
> **Max 2 badges d'état** par carte (`Annulé`/`Reporté` écrasent tout ; `Gratuit` ; `Dernier week-end`).

---

## 2. Mapping DONNÉE — chaque élément → sa source exacte

| Élément carte | Source | Clé / objet exact | Lecture JetEngine |
|---|---|---|---|
| **Date (pastille)** | TEC (meta) | `_EventStartDate` (datetime local `Y-m-d H:i:s`) | Dynamic Field, source *Post Meta* → `_EventStartDate`, filtre de format date |
| Date de fin (badges « en cours », « dernier week-end ») | TEC (meta) | `_EventEndDate` | Dynamic Field / logique conditionnelle |
| **Titre** | TEC (Post) | `post_title` | Dynamic Field, source *Post* → Title |
| **Image de couverture** | TEC (Post) | image à la une (`_thumbnail_id`) | Dynamic Image, source *Featured image* |
| **Kicker catégorie** | Taxonomie TEC | `tribe_events_cat` | Dynamic Terms → taxonomie `tribe_events_cat` |
| **Puce territoire** | Taxonomie maison | `territoire` (hiérarchique) | Dynamic Terms → taxonomie `territoire` |
| **Lieu — nom** | TEC (relation Venue) | Venue `post_title` via `_EventVenueID` | Dynamic Field, source *Post* + « Get value from related item » → `_EventVenueID` |
| **Lieu — ville** | TEC (Venue meta) | `_VenueCity` (sur le post Venue) | Dynamic Field / macro sur le Venue lié |
| **Heure** | TEC (meta) | dérivée de `_EventStartDate` (format `H\hi`) | Dynamic Field → `_EventStartDate`, format heure ; masquer si `_EventAllDay = yes` |
| **Statut** | *(à créer, voir ⚠)* + natif | voir « statut » ci-dessous | Classe CSS conditionnelle sur le wrapper |
| **Badge Gratuit** | Méta `as_*` | `as_gratuit` (`0`/`1`) | Dynamic Field / conditional visibility si `as_gratuit = 1` |
| **Lien (carte cliquable)** | TEC (Post) | permalien | Listing Item → « Links settings » = permalink, OU wrapper `.cs-ev` en Dynamic Link |

### Méta `as_*` du contrat FIGÉ (`docs/CONTRAT_META_AS.md`) utilisées PAR LA CARTE
Sur la **carte**, une seule méta `as_*` entre en jeu : **`as_gratuit`** (badge + filtre).
`as_score` sert à la *requête* « À la une » (≥ 8) mais **ne s'affiche jamais**.
Les 6 autres (`as_tarif`, `as_horaire`, `as_billetterie_url`, `as_source_officielle_url`,
`as_verifie_le`, `as_image_credit`) sont réservées à la **fiche**, pas à la carte.

### Clés méta TEC connues (référence)
- Événement : `_EventStartDate`, `_EventEndDate`, `_EventStartDateUTC`, `_EventEndDateUTC`,
  `_EventAllDay` (`yes`), `_EventDuration`, `_EventVenueID`, `_EventOrganizerID`,
  `_EventCost`, `_EventURL`.
- Venue (post `tribe_venue`) : `_VenueAddress`, `_VenueCity`, `_VenueProvince`, `_VenueZip`,
  `_VenueCountry`, `_VenueLat`, `_VenueLng`, `_VenuePhone`.

> ⚠ **On n'utilise PAS `_EventCost` pour le badge Gratuit** : la source d'autorité du prix est
> `as_gratuit` (booléen écrit par le publisher). `_EventCost` reste optionnel/secondaire.

### ⚠ Statut — champs à créer (NON présents dans le contrat figé)
Le contrat `as_*` **ne contient pas** de champ statut. Or le brief §8.3 exige les états
`Annulé` / `Reporté` / `Complet`. Deux briques à décider (voir §7, points d'incertitude) :

- **`as_statut`** *(à ajouter au contrat)* — enum `a_venir` | `complet` | `annule` | `reporte`.
  Pilote la classe `.cs-ev--{statut}`. Type Meta Box conseillé : *Select*.
- **`as_accent`** *(à ajouter au contrat)* — booléen `0`/`1`, mise en avant RARE (rouge signifiant).
  N.B. la sélection « À la une » passe déjà par `as_score ≥ 8` (Query Builder), donc `as_accent`
  n'est utile que pour un forçage manuel éditorial ponctuel — à confirmer s'il est vraiment nécessaire.
- **Statut « passé »** : n'est PAS une donnée — les événements terminés sont évincés des listes
  (brief §7.2). `.cs-ev--passe` ne sert que sur la fiche terminée, pas dans les listes.
- **Billetterie** : `as_billetterie_url` existe déjà (contrat) → **fiche uniquement**, pas la carte.

**Meta Box JetEngine à greffer sur `tribe_events`** (confort d'édition + rend les champs
« Dynamic-Field-ables ») : déclarer les 8 clés figées + `as_statut` (Select) + `as_accent`
(Switcher) une fois validées. Le publisher écrit la méta quoi qu'il arrive ; la Meta Box ne fait
que les exposer dans l'admin.

---

## 3. Recette JetEngine

### 3.1 Créer le Listing Item
- **JetEngine → Listings → Add New.**
- **Listing source** : `Posts`.
- **From post type** : `Events` (`tribe_events`).
- **Listing item name** : `carte-evenement`.
- **Listing view** : Elementor (builder de la stack). *(Si perf critique, Blocks/Gutenberg est
  plus léger — cf. note perf §7 ; mais la stack validée est Elementor.)*

### 3.2 Structure Elementor (conteneurs)
```
.cs-ev  (Section/Container, Dynamic Link = permalink, class cs-ev + cs-ev--{statut})
├── .cs-ev__date      (Container gauche)  → pastille date
├── .cs-ev__media     (Container)         → Dynamic Image 3:2
└── .cs-ev__body      (Container, flex column)
    ├── .cs-ev__topline (kicker cat + puce territoire)
    ├── .cs-ev__title   (titre)
    └── .cs-ev__meta    (lieu · heure + statut + badge)
```

### 3.3 Widgets à poser (et le réglage clé de chacun)

| # | Widget JetEngine | Rôle | Réglage clé |
|---|---|---|---|
| 1 | **Dynamic Field** | Pastille date | Source *Post Meta* → `_EventStartDate` · **Filter field output = Format date** · format `D j M` (donne « sam 4 juil »). Wrapper class `.cs-ev-date`. |
| 2 | **Dynamic Image** | Couverture | Source *Featured Image* · size `medium` (WebP) · ratio forcé 3:2 en CSS · `loading=lazy`. |
| 3 | **Dynamic Terms** | Kicker catégorie | Taxonomy `tribe_events_cat` · séparateur `·` · lien activé · class `.cs-ev-cat`. Limiter à 1 terme. |
| 4 | **Dynamic Terms** | Puce territoire | Taxonomy `territoire` · lien activé · class `.cs-ev-terr`. Limiter à 1 terme (le parent). |
| 5 | **Dynamic Field** | Titre | Source *Post Title* · HTML tag `h3` (ou `span` si déjà dans un lien) · class `.cs-ev-title`. |
| 6 | **Dynamic Field** | Lieu (nom) | Source *Post* → « Object field » `post_title`, **« Get value from related item »** via `_EventVenueID`. Class `.cs-ev-venue`. Préfixe icône 📍 en CSS (`::before`), pas en emoji-texte. |
| 7 | **Dynamic Field** | Ville | Venue meta `_VenueCity` (related item `_EventVenueID`). Affiché avant le nom du lieu : « Turin · Teatro Regio ». |
| 8 | **Dynamic Field** | Heure | Source *Post Meta* `_EventStartDate` · Filter = Format date · format `G\hi` → « 21h00 ». **Conditional visibility** : masquer si `_EventAllDay = yes`. Class `.cs-ev-time`. |
| 9 | **Dynamic Field** | Badge Gratuit | Texte statique « Gratuit » · **Conditional visibility** : afficher si `as_gratuit` = `1`. Class `.cs-ev-badge cs-ev-badge--free`. |
| 10 | **Dynamic Field** | Statut | Texte statique conditionnel (« Annulé », « Reporté », « Complet ») piloté par `as_statut` (conditions JetEngine). Class `.cs-ev-status`. Le style vient de `.cs-ev--{statut}` sur le wrapper. |

**Carte cliquable** : sur `.cs-ev`, activer *Settings → Link → Dynamic Tags → Permalink*.
Le kicker catégorie, la puce territoire et le lieu restent des liens internes propres (maillage) :
en HTML c'est un lien-dans-un-lien invalide → **préférer** rendre `.cs-ev` cliquable via un
`.cs-ev__overlay` (pseudo-lien plein-carte en `::after`) et laisser cat/territoire/lieu en vrais
`<a>` au-dessus (`position:relative; z-index:1`). *(Voir CSS §4.)*

### 3.4 Classe de statut sur le wrapper
Appliquer dynamiquement `cs-ev--{as_statut}` :
- via **JetEngine → « Dynamic tags » sur l'attribut class** du conteneur, OU
- via une **Listing Item macro** `%post_meta(as_statut)%` injectée dans un attribut `class`, OU
- fallback : un Dynamic Field masqué + un petit snippet CSS ciblant `[data-statut]`.

### 3.5 Où la carte est consommée (rappel)
Listing Grid (JetEngine) sur : Home (« À la une », « Ce week-end »), hubs catégorie/territoire,
« Tout l'agenda », recherche. Filtres via **JetSmartFilters** (date / territoire / catégorie /
`as_gratuit`). Voir requêtes Query Builder dans `BUILD_WORDPRESS_CROCOBLOCK.md` §4.

---

## 4. CSS — classes + règles (tokens `--cs-*` / `--sc-*`)

À poser dans le CSS du Listing (ou Code Snippets `site-css`). Tous les tokens existent déjà
dans `wordpress/design-system/tokens.css`.

```css
/* ---- Carte / EventRow (variante compacte dense) ---- */
.cs-ev{
  position: relative;
  display: grid;
  grid-template-columns: auto var(--sc-media, 88px) 1fr; /* date · image · corps */
  gap: var(--sc-5);                 /* 14px, densité agenda */
  align-items: start;
  padding: var(--sc-5);
  background: var(--bg-white);
  border: 1px solid var(--rule);
  border-radius: var(--r-1);        /* 2px */
  box-shadow: var(--shadow-paper);
  line-height: var(--lh-compact);   /* 1.35 */
  transition: box-shadow var(--dur-fast) var(--ease-std),
              transform var(--dur-fast) var(--ease-std);
}
.cs-ev:hover{ box-shadow: var(--shadow-lift); }
.cs-ev:focus-within{ outline: 2px solid var(--cs-bleu); outline-offset: 2px; }

/* Pseudo-lien plein-carte : garde cat/territoire/lieu cliquables au-dessus */
.cs-ev__overlay::after{ content:""; position:absolute; inset:0; z-index:0; }
.cs-ev a{ position: relative; z-index: 1; }

/* ---- Pastille date (jour + n° + mois, fond rouge, La Semplicita 700) ---- */
.cs-ev-date{
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 52px; padding: var(--sc-3) var(--sc-2);
  background: var(--cs-rouge); color: var(--fg-on-accent);
  border-radius: var(--r-1);
  font-family: var(--font-editorial); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  line-height: 1.05; text-align: center;
}
/* mise en forme du texte « sam 4 juil » : le jour n° en grand (via <strong> injecté ou nth) */
.cs-ev-date strong{ font-size: 1.5rem; display: block; }

/* ---- Image 3:2 ---- */
.cs-ev__media img{
  width: 100%; aspect-ratio: 3 / 2; object-fit: cover;
  border-radius: var(--r-1); display: block;
}

/* ---- Topline : kicker catégorie + puce territoire ---- */
.cs-ev__topline{ display:flex; align-items:center; gap: var(--sc-4); margin-bottom: var(--sc-2); }
.cs-ev-cat{                              /* CATÉGORIE = monochrome, La Semplicita */
  font-family: var(--font-editorial); font-weight: 600;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  font-size: var(--fs-eyebrow); color: var(--fg-2);
  text-decoration: none;
}
.cs-ev-cat:hover{ color: var(--fg-1); }
.cs-ev-terr{                             /* TERRITOIRE = puce MONOCHROME (pas de couleur) */
  display:inline-flex; align-items:center; gap: var(--sc-2);
  font-size: var(--fs-meta); color: var(--fg-3); text-decoration:none;
}
.cs-ev-terr::before{                     /* point neutre, jamais une teinte territoire */
  content:""; width:6px; height:6px; border-radius: var(--r-pill);
  background: currentColor; opacity:.6;
}

/* ---- Titre ---- */
.cs-ev-title{
  font-family: var(--font-editorial); font-weight: 600;
  font-size: var(--fs-h4); color: var(--fg-1); line-height: var(--lh-title);
  margin: 0 0 var(--sc-2);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cs-ev:hover .cs-ev-title{ color: var(--cs-bleu); }

/* ---- Meta : lieu · heure ---- */
.cs-ev__meta{
  display:flex; flex-wrap:wrap; align-items:center; gap: var(--sc-2) var(--sc-4);
  font-family: var(--font-body); font-size: var(--fs-body-sm); color: var(--fg-2);
}
.cs-ev-venue::before{ content:"\1F4CD"; margin-right: var(--sc-2); } /* 📍 décoratif; remplaçable par SVG mask */
.cs-ev-time{ color: var(--fg-3); }

/* ---- STATUT = TYPOGRAPHIE, jamais couleur ---- */
.cs-ev--a_venir  .cs-ev-status{ display:none; }                  /* à venir = normal */
.cs-ev--complet  .cs-ev-title,
.cs-ev--complet  .cs-ev__meta { color: var(--fg-3); }            /* complet = gris */
.cs-ev--annule   .cs-ev-title{ text-decoration: line-through; color: var(--fg-3); } /* annulé = barré + gris */
.cs-ev--reporte  .cs-ev-title{ font-style: italic; color: var(--fg-3); }
.cs-ev--passe{ opacity: .55; }                                   /* passé = opacité réduite (fiche only) */
.cs-ev-status{                                                   /* libellé statut, neutre */
  font-family: var(--font-body); font-size: var(--fs-meta);
  text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--fg-3);
}

/* ---- Badge Gratuit (seul badge coloré toléré) ---- */
.cs-ev-badge--free{
  display:inline-block; padding: 1px var(--sc-3);
  font-family: var(--font-body); font-weight:700; font-size: var(--fs-meta);
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--cs-bleu); background: transparent; border: 1px solid var(--cs-bleu);
  border-radius: var(--r-1);
}

/* ---- Accent RARE (mise en avant éditoriale, si as_accent=1) ---- */
.cs-ev--accent{ border-left: 3px solid var(--cs-rouge); }
```

**Décisions de style tenues** : radius 2px (`--r-1`), ombre `--shadow-paper` par défaut,
densité via `--sc-*`, statut purement typographique, catégorie et territoire monochromes
(le seul rouge de la carte = la pastille date, plus le liseré `.cs-ev--accent` réservé au rare).

---

## 5. Notes FR/IT (Polylang) & responsive

### Bilinguisme
- **Un seul Listing Item** `carte-evenement` suffit : il rend les données de l'événement
  courant, donc déjà dans la bonne langue (chaque `tribe_events` FR↔IT est une paire Polylang).
- **Formats de date localisés** : ne pas coder « juil » en dur. Utiliser le format PHP TEC/JetEngine
  (`D j M`) qui suit la locale WordPress active (`fr_FR` / `it_IT`). En IT la pastille donnera
  « sab 4 lug ». Vérifier que la locale IT est bien installée côté serveur.
- **Libellés statiques traduisibles** : « Gratuit »/« Gratis », « Annulé »/« Annullato »,
  « Complet »/« Esaurito », « Reporté »/« Rinviato ». Les poser via chaînes Polylang
  (Strings translation) ou via `as_statut` mappé à un libellé traduit, **jamais en dur** dans le widget.
- **Longueur IT +10–15 %** : la pastille date et les badges doivent tolérer l'italien plus long
  (pas de largeur fixe rigide sur `.cs-ev-badge` ; `min-width` seulement sur la pastille).
- **Gabarit strictement identique** dans les deux langues (règle brief §9).

### Responsive (mobile-aware, dense)
- **Mobile (< 480px)** : garder la grille horizontale mais réduire l'image ou la masquer si
  l'espace manque. Suggestion : `grid-template-columns: auto 1fr;` et `.cs-ev__media{ display:none; }`
  en dessous de 380px, OU image en 64px. La pastille date reste toujours visible (ancre).
- **Zones tactiles** : toute la carte cliquable (overlay) → cible ≥ 44px de haut assurée par le padding.
- **Line-clamp titre** : 2 lignes mobile comme desktop (invariant brief).
- **Densité** : conserver `--sc-*` sur mobile ; ne pas repasser aux `--s-*` (agenda = dense partout).

---

## 6. Variantes (même donnée, layout différent)

Le brief §8.1 décrit 4 variantes. Cette recette détaille la **compacte/liste (EventRow)**.
Les autres se dérivent en **réutilisant les mêmes champs** :

| Variante | Usage | Différence de layout | Implémentation |
|---|---|---|---|
| **Compacte / liste** *(ce fichier)* | listes denses, mobile, recherche, hubs | horizontale, image 3:2 vignette gauche | `carte-evenement` |
| **Standard** | grilles de hub desktop | verticale : image 3:2 en tête, date en pastille surimposée | `.cs-ev--vertical` (même Listing, modificateur CSS `grid-template` + position pastille) OU 2ᵉ Listing Item |
| **Héro** | home, tête de hub | plein-largeur, image dominante, date en grand, chapô 1 ligne | Listing Item séparé `carte-hero` |
| **Dernière chance** | expos finissant ≤ 14 j | standard + bandeau urgence rouge « Plus que X jours » | `.cs-ev--urgent` (calcul sur `_EventEndDate`) |

Recommandation : **1 Listing Item + modificateurs CSS** pour compacte/standard (perf : moins de
requêtes/templates), **1 Listing Item dédié** pour héro. À arbitrer selon la précision voulue.

---

## 7. Points d'incertitude / décisions à confirmer

1. **`as_statut` et `as_accent` NE sont PAS dans le contrat figé** (`docs/CONTRAT_META_AS.md`
   = 8 clés, immuables). Le brief §8.3 exige pourtant `Annulé`/`Reporté`/`Complet`.
   → **Décision requise** : ajouter `as_statut` (Select) et éventuellement `as_accent` (bool) au
   contrat AVANT le premier événement publié, et confirmer que `publisher.py` les écrira.
   Sans ça, la carte ne peut pas rendre le statut. *(Alternative pour « Annulé/Reporté » : certains
   flux TEC utilisent `_tribe_events_status` / `_tribe_events_status_reason` — à vérifier sur
   l'install réelle ; si présent nativement, s'en servir plutôt que créer `as_statut`.)*

2. **Territoire monochrome vs. pilules colorées.** Ce fichier applique la règle VERROUILLÉE
   (puce territoire monochrome). Le brief §1.2 mentionne des **couleurs par territoire**
   (Savoie bleu, Piémont rouge, etc.) héritées de la newsletter. Les tokens live
   (`tokens.css`) **n'ont pas** de variables territoire → la règle monochrome est cohérente avec
   les tokens. → **Confirmer** que les pilules colorées sont bien abandonnées pour l'agenda.

3. **Builder : Elementor (stack déclarée) vs. reco perf.** `BUILD_WORDPRESS_CROCOBLOCK.md` §0–1
   déconseille Elementor (CWV). La stack réelle inclut Elementor. → Si le LCP mobile dépasse
   2,5 s sur les grilles, envisager le rendu Blocks/Gutenberg du Listing Item (JetEngine le
   permet) sans changer la recette de données. Décision perf, pas design.

4. **Ville : source exacte.** Le nom du lieu vient du post `tribe_venue` (`_EventVenueID`) ; la
   ville de `_VenueCity`. → Vérifier que le publisher renseigne bien `_VenueCity` sur chaque Venue
   (sinon la ligne « ville · lieu » n'affiche que le lieu). Fallback : masquer la ville si vide.

5. **Lien-dans-lien.** Carte entièrement cliquable + kicker/territoire/lieu cliquables =
   imbrication d'ancres invalide. La recette propose l'overlay `::after` + `z-index`. → Valider
   l'accessibilité (focus, lecteur d'écran) sur l'implémentation Elementor réelle.

6. **Pastille date « jour n° en grand ».** Le rendu « SAM / 4 / JUIL » avec le chiffre agrandi
   demande soit un `<strong>` injecté, soit deux Dynamic Fields (jour-nom + n°+mois) empilés.
   → Choisir : 2 Dynamic Fields empilés est le plus robuste (format `D` puis `j M`).

7. **Format date localisé IT** : dépend de l'installation de la locale `it_IT` côté serveur et de
   la traduction Polylang des libellés statiques. → À tester en recette bilingue.
