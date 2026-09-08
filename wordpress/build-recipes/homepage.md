# Recette de build — Homepage (agendasabauda.eu)

*Recette de construction de la page d'accueil. Ne modifie rien sur le site : c'est le plan
d'exécution. Stack : GeneratePress + The Events Calendar (`tribe_events`) + Crocoblock JetEngine
(Listing Grid + Query Builder) + JetSmartFilters + Elementor + Polylang (FR/IT).*

**Principe directeur (hérité de `BUILD_WORDPRESS_CROCOBLOCK.md`) : TEC est la donnée, JetEngine
la mise en forme. On garde `tribe_events`, aucun CPT `evenement`.**

Sources : `docs/PLAN_DU_SITE_AGENDA_SABAUDO.md` §2 (3 modules), `docs/BRIEF_DESIGN_AGENDA_SABAUDO.md`
§6.1 + H1 (~l.243), `docs/TEMPLATES_WORDPRESS.md` (ordre des strates), `docs/BUILD_WORDPRESS_CROCOBLOCK.md`
(contrat de données + requêtes), `wordpress/design-system/tokens.css` (variables `--cs-*`).

> ⚠️ **Rôle de la home (décision produit figée, brief §6.1)** : la home **oriente**, elle ne
> **browse pas**. Ce n'est PAS un flux de tous les événements. Pas de géoloc, pas de sélecteur de
> territoire imposé. Elle **assume les 4 territoires**, **prouve** que l'espace Sabaudo vit, et
> distribue vers les portes (hubs). Best-of **équilibré** : au moins 1-2 temps forts par territoire,
> pour n'apparaître ni « site savoyard » ni « site turinois ».

---

## 1. Plan de la home, section par section (ordre mobile-first `TEMPLATES_WORDPRESS`)

Ordre canonique de `front-page` : **carrousel → recherche → 6 tuiles → à la une → ce week-end →
le fil → tuiles secondaires → newsletter → footer**. Détail avec rôle et nature (statique `S` /
dynamique `D`) :

| # | Section | Rôle | Contenu | S/D |
|---|---|---|---|---|
| 0 | **Header + barre chips temporelles** | Orientation « quand » | Logo `Agenda Sabauda.` · Aujourd'hui · Ce week-end · Catégories▾ · Territoires▾ · Agenda▾ · 🔍 · **FR\|IT texte** ; sous le header, chips scrollables : Aujourd'hui · Ce week-end · Cette semaine · Dates | S (partie de thème) |
| 1 | **Hero éditorial** (+ carrousel léger) | Marque + accroche | **H1 accroche pérenne** + sous-texte + **barre de recherche** ; 1-2 temps forts curés (sélection manuelle). Carrousel = **non auto**, flèches/points, texte HTML réel (jamais dans l'image) | D (source manuelle) + S (H1) |
| 2 | **Recherche** | Entrée directe | Champ + bouton (redondant avec la loupe header, assumé). Cible : archive « Tout l'agenda » filtrable | S (renvoie vers moteur) |
| 3 | **6 tuiles-raccourcis** | Distribution vers hubs | 6 tuiles illustrées « familles de sorties » → liens crawlables (voir §4) | S (liens fixes) |
| 4 | **À la une / « À ne pas manquer »** | Preuve + curation équilibrée | 4-6 cartes-héro **choisies** (best-of, ≥1-2 par territoire). Module « En évidence » du plan §2.2 | **D** (query À la une) |
| 5 | **Ce week-end** | Le réflexe agenda | Titre + **compteur** (« 34 événements ce week-end ») + 4-8 cartes standard + **bouton noir « Voir tout l'agenda du week-end → »** vers `/fr/ce-week-end/` | **D** (query Ce week-end) |
| 6 | **Tour des territoires (4 portes)** | Axe identitaire primaire | Les 4 territoires, chacun sa couleur : soit 4 tuiles-portes vers les hubs, soit 4 mini-rails « ce week-end en X » (2 cartes/territoire). C'est **l'axe « où ? »** | S (portes) *ou* **D** (mini-rails) |
| 7 | **Le fil** | Éditorial / listicles | Cartes-article (vignette + H2 + extrait) : « Les 10 du week-end » + dossiers. Renvoie vers les listicles | **D** (query articles) |
| 8 | **Dernière chance** *(option, brief §6.1.6)* | Urgence réelle | Expositions/événements se terminant ≤ 14 j, **badge rouge « Plus que X jours »** | **D** (query fin proche) |
| 9 | **Tuiles secondaires / nav thématique** | Relance + maillage SEO | Rail des 11 catégories + bloc « Retrouvez sur Agenda Sabauda… » (§4). **Liens crawlables vers TOUS les hubs** | S (liens fixes) |
| 10 | **Newsletter inline** | Conversion (actif n°1) | 1 champ email + promesse datée « Le vendredi matin » + RGPD. Pas de pop-up | S (form) |
| 11 | **Footer** | Accès complet + SEO | 4 colonnes (Explorer · Catégories 11 · Territoires 4 · Le projet) + nav thématique + « édité par Cultura Sabauda » + FR\|IT | S (partie de thème) |

**Note de réconciliation** : l'ordre TEMPLATES ci-dessus est le squelette de build. Le brief §6.1
insiste pour que **les 4 portes territoire (§6) soient un bloc majeur** (axe primaire) et place la
« dernière chance » (§8). Les deux sont compatibles : on garde l'ordre TEMPLATES, on donne juste
au bloc territoires un poids visuel fort.

---

## 2. Sections DYNAMIQUES — requêtes JetEngine Query Builder (sur `tribe_events`)

**Réglages communs à toutes les requêtes** (Query Builder → type **Posts Query**) :

- **Post Type** : `tribe_events` · **Post Status** : `publish` · **Post per page** : voir chaque section.
- **Meta clause « à venir »** (obligatoire, évite tout événement passé — règle non négociable) :
  clé `_EventEndDate`, `compare` **`>=`**, `type` **`DATETIME`**, `value` = macro JetEngine
  **`%current_datetime|Y-m-d H:i:s%`** (l'événement n'est pas encore terminé).
  *(On teste sur `_EventEndDate` plutôt que `_EventStartDate` pour garder visibles les expos « en cours ».)*
- **Order** : `orderby` = **Meta value** · Meta key = `_EventStartDate` · Meta type = **DATETIME** ·
  Order = **ASC** (le plus proche d'abord). *(La « À la une » trie par score, voir plus bas.)*
- **Listing réutilisé** : le Listing Item **`carte-evenement`** (voir §2.5), sauf « Le fil » qui
  utilise `carte-article`.

> ⚠️ **Garde-fou TEC/WP_Query** : TEC injecte ses propres filtres sur les requêtes de `tribe_events`
> (ordre, masquage). Dans JetEngine, cocher **« Manual Query » n'est pas nécessaire**, mais s'il y a
> conflit d'ordre/masquage, ajouter dans les args avancés `tribe_suppress_query_filters => true`
> (via le filtre `jet-engine/query-builder/query/args`). À valider au premier test (voir §5, incertitudes).

### 2.1 « À la une » / « À ne pas manquer » (best-of équilibré)

- **But** : 4-6 temps forts curés, ≥1-2 par territoire, distincts du flux daté.
- **Query** :
  - Post Type `tribe_events`, status `publish`, **Posts per page = 6**.
  - Meta « à venir » (`_EventEndDate >= %current_datetime%`).
  - **Sélection** : filtrer sur la méta **`as_score`** `>=` `8` (type `NUMERIC`) → n'affiche que
    ce que le publisher/choix manuel a marqué comme fort. *(Le contrat `as_score` est écrit par
    `publisher.py`, cf. BUILD §2.)*
  - **Order** : `orderby` = Meta value NUM `as_score` **DESC**, tie-break `_EventStartDate` ASC.
  - *(Équilibre territorial : ne se garantit pas par une seule requête SQL. Deux options — a) accepter
    l'ordre par score ; b) forcer l'équilibre via un champ « épingle home » manuel `as_home_pin`
    et 4 requêtes de 1-2 par `territoire`. Décision à confirmer §6.)*
- **Listing** : `carte-evenement` variante **`carte-hero`** (image dominante, date en gros, chapô 1 ligne).

### 2.2 « Ce week-end »

- **But** : événements qui **chevauchent** le prochain week-end (ven. soir → dim.).
- **Query** :
  - Post Type `tribe_events`, status `publish`, **Posts per page = 8**.
  - **Chevauchement de dates** (2 clauses meta, relation AND) :
    - `_EventStartDate` `<=` `%as_weekend_end%` (l'événement commence avant/le dim.),
    - `_EventEndDate` `>=` `%as_weekend_start%` (et n'est pas fini avant le ven.).
    - Type `DATETIME` pour les deux.
  - **Order** : `_EventStartDate` ASC.
- **Bornes `%as_weekend_start%` / `%as_weekend_end%`** : JetEngine n'a pas de macro « prochain
  week-end » native → **enregistrer 2 macros custom** (Code Snippets, hook
  `jet-engine/register-macros`) qui renvoient le vendredi 18:00 et le dimanche 23:59 de la semaine
  courante (`strtotime('friday this week')`…). *(Repli sans macro : JetSmartFilters « Date Range »
  avec preset week-end, mais la macro est plus propre pour un module home figé.)*
- **Compteur** : afficher le total via le champ dynamique JetEngine **« Query results count »** de
  cette même requête (« {count} événements ce week-end »).
- **Listing** : `carte-evenement` variante **standard** (datebloc « SAM 4 JUIL »).
- **CTA** : bouton noir → `/fr/ce-week-end/`.

### 2.3 « Le fil » (éditorial / listicles)

- **But** : articles rédigés (« Les 10 du week-end », dossiers) — **pas** des `tribe_events`.
- **Query** : Posts Query, Post Type **`post`**, status `publish`, orderby **date DESC**,
  Posts per page = 3-4. (Optionnel : filtrer sur une catégorie WP « Le fil » / « listicles ».)
- **Listing** : **`carte-article`** (vignette + titre H2 + extrait + « → »).

### 2.4 « Tour des territoires » (mini-rails, si version dynamique) & « Dernière chance »

- **Par territoire** (×4, un rail par terme) : même query « à venir » +
  **Tax Query** : taxonomie **`territoire`**, terme = `Savoie` / `Piemonte` / `Vallee-Aoste` /
  `Nice` (valeurs techniques, brief §1.2). Order `_EventStartDate` ASC, Posts per page = 2-3.
  *(4 Listing Grids = 4 requêtes → surveiller la perf, cf. §5. Alternative légère : 4 tuiles-portes
  statiques vers les hubs `/fr/territoire/{terr}/`, zéro requête.)*
- **Dernière chance** : query « à venir » + clause `_EventEndDate` **`<=`**
  `%current_datetime|Y-m-d H:i:s|+14 days%` (se termine dans ≤ 14 j), order `_EventEndDate` **ASC**,
  Posts per page = 4. Carte variante **« dernière chance »** (bandeau rouge « Plus que X jours »).

### 2.5 Le Listing réutilisé : `carte-evenement`

Composant central, **construit une seule fois** (Lot « carte-événement » du README wordpress),
réutilisé dans toutes les grilles de la home ET des hubs. Structure (BUILD §3) :

1. Image à la une **ratio 3:2** (repli = bannière territoire) + crédit `as_image_credit` en 10-11 px.
2. **DATE d'abord** : champ dynamique `_EventStartDate`, format humanisé (datebloc « SAM 4 JUIL »).
3. Titre gras (2 lignes max).
4. Lieu · ville (Venue TEC).
5. **Pilule territoire** : terme `territoire`, **couleur conditionnelle** (JetEngine Conditional /
   Dynamic Visibility) — Savoie bleu, Piémont rouge, Vallée d'Aoste vert, Nice orange (brief §1.2).
6. Badge **« Gratuit »** si méta `as_gratuit == 1` ; badges d'état = **typo, jamais couleur**
   (règle charte : statut = typo).
7. Carte **entièrement cliquable** → permalien.

Variantes : **`carte-hero`** (à la une / carrousel), **standard** (grilles), **compacte**
(listes denses), **dernière chance** (bandeau urgence).

---

## 3. Le hero

- **H1 (accroche pérenne, brief ~l.243)** :
  > **Que faire dans les Alpes, de Chambéry à Turin**

  IT : *Cosa fare sulle Alpi, da Chambéry a Torino* — **non** adapté par territoire (assumé transfrontalier).
- **Sous-texte** : *« L'agenda des sorties des 4 territoires alpins — Savoie & Haute-Savoie, Piémont,
  Vallée d'Aoste, Nice. Expositions, concerts, festivals, sagre, marchés, en famille. »*
- **Recherche** : champ + bouton sous le H1 (loupe aussi dans le header).
- **Carrousel** (optionnel, léger) : 1-2 temps forts curés, **non auto** (interdit brief §12.5),
  navigation manuelle, **tout le texte en HTML réel** (titre/date jamais dans l'image).
- **Tokens** : titre en **display CAPS** `--font-display` ('Alumni Sans Pinstripe', MAJUSCULES
  uniquement), taille `--fs-hero` (`clamp(3.5rem, 7vw, 6.5rem)`), `line-height: var(--lh-display)` (0.95),
  `letter-spacing: var(--tracking-display)` (0.05em). Sous-texte en `--font-body` ('Nunito Sans'),
  `--fs-lead`. Fond `--bg` (beige `#F7F1E8`) ou `--bg-deep` (bleu `#18365E`) avec `--fg-on-deep`.
  Accent rouge (`--cs-rouge`) **rare** : uniquement le point du logotype et le bouton de recherche.

---

## 4. Les « 6 tuiles » et la nav thématique

### 6 tuiles-raccourcis (plan §2.1 — « familles de sorties », ordre du plus cherché au plus identitaire)

| # | Tuile | Lien (crawlable) | Taxo cible |
|---|---|---|---|
| 1 | **Ce week-end** | `/fr/ce-week-end/` | hub temporel (query dates) |
| 2 | **Tout l'agenda** | `/fr/evenements/` | archive filtrable |
| 3 | **Expositions & Patrimoine** | `/fr/evenements/expositions-patrimoine/` | `tribe_events_cat` |
| 4 | **Concerts & Musique** | `/fr/evenements/concerts-musique/` | `tribe_events_cat` |
| 5 | **Festivals & Sagre** | `/fr/evenements/festivals/` (+ `gastronomie-sagre`) | `tribe_events_cat` |
| 6 | **En famille** | `/fr/evenements/jeune-public-famille/` | `tribe_events_cat` |

Icônes **trait simple** (façon guide), **jamais d'emoji** dans l'UI. Les 11 catégories restent
toutes accessibles via le menu Catégories▾ : les 6 tuiles ne sont que les raccourcis vedettes.
*(Alternative écartée : 6 tuiles = temporel + 4 territoires ; les territoires vivent dans le bloc
dédié §1.6 + le menu.)*

### Nav thématique (bas de home + footer, plan §2.3)

Bloc texte, liens crawlables vers tous les hubs :

> **Retrouvez sur Agenda Sabauda tout ce qu'il ne faut pas manquer :** Que faire ce week-end · les
> 4 territoires (Savoie & Haute-Savoie · Piémont · Vallée d'Aoste · Nice) · Expositions & patrimoine
> · Concerts, spectacles & festivals · Gastronomie, sagre & marchés · En famille & jeune public.

IT : *Ritrovate su Agenda Sabauda tutto ciò da non perdere: cosa fare questo weekend · i 4 territori
· mostre & patrimonio · concerti, spettacoli & festival · gastronomia, sagre & mercati · in famiglia.*

---

## 5. Recette de build (exécution)

**Ordre conseillé** (BUILD §7, adapté à la home) :

1. **Global styles d'abord** : injecter `wordpress/design-system/tokens.css` (déjà poussé via
   `scripts/apply-tokens.mjs`, Code Snippets scope site-css) ; mapper les couleurs `--cs-*` et les
   polices en **couleurs/typographies globales Elementor** (ou variables CSS globales). Cible finale :
   `theme.json` du child theme GeneratePress.
2. **Listing Item `carte-evenement`** (JetEngine → Listings), testé sur une requête « Ce week-end ».
3. **Créer la page « Accueil »** (Pages → Ajouter) puis **Réglages → Lecture → « Page d'accueil
   affiche : une page statique » → Accueil**. (Front-page statique, pas le blog.)
4. **Construire la page** en **Elementor** :
   - Hero (Elementor natif : Heading H1 + champ recherche) — voir §3.
   - 6 tuiles : grille Elementor de liens/images (statique) — §4.
   - « À la une » : **JetEngine Listing Grid** (widget) branché sur la query 2.1, Listing `carte-hero`.
   - « Ce week-end » : Listing Grid → query 2.2 + Dynamic « results count » + bouton CTA.
   - Tour des territoires : 4 tuiles statiques **ou** 4 Listing Grids (query 2.4) — trancher perf.
   - Le fil : Listing Grid → query 2.3, Listing `carte-article`.
   - Dernière chance (option) : Listing Grid → query 2.4.
   - Nav thématique + Newsletter : blocs Elementor statiques (form 1 champ).
   - Footer : template de thème GeneratePress (pas dans la page).

**Garde-fous perf / Core Web Vitals (BUILD §1 — c'est le SEO) :**

- **Un seul builder** (Elementor ici, imposé par le task) ; **ne pas** ajouter Bricks en parallèle.
  Elementor + Jet est le combo le plus lourd → **surveiller LCP mobile < 2,5 s** au PageSpeed sur la
  home avant d'ouvrir.
- **Limiter le nombre de Listing Grids** (chaque grille = 1 requête). La home en compte déjà 3-4 ;
  si on passe le « tour des territoires » en 4 grilles, on monte à 7-8 → préférer alors **4 tuiles
  statiques** pour les territoires.
- **Cache des requêtes JetEngine** activé ; cache page (LiteSpeed/W3TC/FlyingPress) ; **cache objet**
  si dispo OVH.
- **Images** : ratios réservés (pas de layout shift), lazy-load, WebP (ShortPixel/Imagify) ;
  **le hero LCP** (1ʳᵉ image / carte) chargé en priorité (pas lazy).
- **Désactiver les widgets Jet non utilisés** ; ne charger Elementor que sur les pages qui en ont besoin.
- Pas de carrousel auto, pas de scroll infini (pagination crawlable ailleurs, pas d'enjeu sur la home).

---

## 6. CSS clé (variables `--cs-*`)

Ces variables viennent de `wordpress/design-system/tokens.css` (déjà en prod via Code Snippets).
Classes utilitaires à poser sur la home :

```css
/* ---- HERO ---- */
.as-hero {
  background: var(--bg);            /* beige #F7F1E8 ; ou var(--bg-deep) pour hero bleu */
  color: var(--fg-1);
  padding: var(--s-9) var(--s-5);   /* 96px / 24px */
}
.as-hero__h1 {
  font-family: var(--font-display); /* Alumni Sans Pinstripe — CAPS only */
  text-transform: uppercase;
  font-size: var(--fs-hero);        /* clamp(3.5rem, 7vw, 6.5rem) */
  line-height: var(--lh-display);   /* 0.95 */
  letter-spacing: var(--tracking-display); /* 0.05em */
  color: var(--cs-bleu);            /* #18365E ; var(--fg-on-deep) sur fond bleu */
}
.as-hero__lead {
  font-family: var(--font-body);
  font-size: var(--fs-lead);        /* 1.25rem */
  line-height: var(--lh-body);
  color: var(--fg-2);
  max-width: var(--col-text);       /* 64ch */
}
.as-hero__dot { color: var(--cs-rouge); } /* le point rouge du logotype — accent RARE */

/* ---- GRILLES de cartes ---- */
.as-grid {
  display: grid;
  gap: var(--s-5);                                   /* 24px */
  grid-template-columns: 1fr;                        /* mobile-first : 1 colonne */
  max-width: var(--page-max);                        /* 1240px */
  margin-inline: auto;
}
@media (min-width: 768px)  { .as-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .as-grid { grid-template-columns: repeat(3, 1fr); } }
.as-grid--hero { gap: var(--s-6); }                  /* à la une : plus aéré */

/* ---- CARTE (rappel des tokens ; le rendu réel = Listing JetEngine) ---- */
.as-card              { background: var(--bg-white); box-shadow: var(--shadow-paper);
                        border-radius: var(--r-2); overflow: hidden; }
.as-card:hover        { box-shadow: var(--shadow-lift); }
.as-card__media       { aspect-ratio: 3 / 2; object-fit: cover; }        /* ratio unique partout */
.as-card__date        { font-family: var(--font-editorial); font-size: var(--fs-meta);
                        letter-spacing: var(--tracking-caps); text-transform: uppercase; }
.as-card__title       { font-family: var(--font-editorial); font-size: var(--fs-h4);
                        line-height: var(--lh-title); }

/* ---- Pilules territoire (couleur par terme) ---- */
.as-pill              { border-radius: var(--r-pill); padding: 2px 10px; font-size: var(--fs-eyebrow); }
.as-pill--savoie      { background:#e6effb; color:#1a56b0; }
.as-pill--piemonte    { background:#fdeaea; color:#b3261e; }
.as-pill--vallee-aoste{ background:#e7f6ea; color:#1e7d34; }
.as-pill--nice        { background:#fff1e0; color:#b25e00; }

/* ---- Bouton CTA noir « Voir tout l'agenda du week-end » ---- */
.as-cta { background: var(--cs-noir); color: var(--cs-blanc); border-radius: var(--r-pill);
          padding: var(--s-3) var(--s-5); font-family: var(--font-editorial); }
```

---

## 7. Polylang FR/IT & SEO

**Polylang** :

- **Une seule home traduite** (recommandé), pas deux pages séparées : page « Accueil » (FR) +
  sa traduction « Home » (IT), reliées dans Polylang. En Réglages → Lecture, définir la front-page ;
  Polylang sert la version selon la langue (`/fr/` ↔ `/it/`).
- **Listings JetEngine** : le même Listing `carte-evenement` sert dans les 2 langues ; les
  **libellés statiques** (titres de section « Ce week-end », boutons) se traduisent via **strings
  Polylang** (`pll_register_string` / interface Elementor traduisible) ou 2 versions du bloc.
- **Requêtes** : filtrer les Listing Grids par langue si les `tribe_events` sont eux-mêmes traduits
  (une fiche non traduite n'existe pas dans l'autre langue — brief §9). Vérifier que Polylang
  filtre bien les Query Builder par langue courante (sinon ajouter `lang` aux args).
- **FR|IT en texte, jamais de drapeaux** (piège du site transfrontalier).
- **hreflang** par paires + `x-default` (géré par Polylang) ; strings IT +10-15 % (badges, boutons).

**SEO** :

- **H1 unique et pérenne** : « Que faire dans les Alpes, de Chambéry à Turin » (jamais en image,
  texte HTML réel).
- **Intro pérenne** : la home n'a pas besoin d'un gros pavé, mais garder un paragraphe stable
  (accroche + les 4 territoires nommés) pour l'ancrage sémantique.
- **Liens crawlables vers TOUS les hubs** (6 tuiles + nav thématique + footer) → Google voit toute
  la structure depuis la home (brief §6.1 SEO).
- **JSON-LD** : `WebSite` + `SearchAction` (boîte de recherche) + `Organization` (éditeur : Cultura
  Sabauda) sur la home. Les cartes ne portent PAS de schema Event (le schema Event vit sur les fiches).
- **Title** type : « Agenda Sabauda — Que faire dans les Alpes, de Chambéry à Turin (expos, concerts,
  festivals) ».
- **Pas d'événement passé** visible (clause `_EventEndDate >= now` sur toutes les requêtes).

---

## 8. Incertitudes / décisions à confirmer

1. **Équilibre territorial du « À la une »** : tri par `as_score` seul (simple, 1 requête) **vs**
   forçage 1-2/territoire via champ `as_home_pin` + 4 requêtes (garantit l'équilibre voulu au brief,
   mais +3 requêtes). → **Décision Franck.**
2. **Tour des territoires** : 4 tuiles-portes **statiques** (perf ✅, mais pas de contenu vivant) vs
   4 mini-rails **dynamiques** (vivant, mais +4 requêtes → risque CWV sur home Elementor+Jet). →
   Trancher au test PageSpeed.
3. **Macros `%as_weekend_start/end%`** : à enregistrer en Code Snippets (hook
   `jet-engine/register-macros`). Sinon repli JetSmartFilters date-range. → À implémenter (Lot carte/queries).
4. **Filtre TEC sur `tribe_events`** : confirmer au 1ᵉʳ test si `tribe_suppress_query_filters` est
   nécessaire pour que l'ordre `_EventStartDate` ASC et le masquage des passés se comportent bien
   dans JetEngine.
5. **Contrat méta `as_*`** : les clés (`as_score`, `as_gratuit`, `as_image_credit`, `as_verifie_le`…)
   ne sont figées définitivement qu'au câblage de `publisher.py` (BUILD §2, Lot 6). Construire les
   Listings sur ces noms, mais prévoir un ajustement.
6. **Carrousel hero** : le garder ou hero fixe 1 temps fort ? (Brief §0 méfiant des carrousels ;
   §12.5 interdit seulement l'auto-défilement.) → Préférence design.
7. **Polylang + JetEngine Query Builder** : vérifier le filtrage par langue des requêtes (peut
   nécessiter un arg `lang` explicite selon la version).
8. **Auto-publication score 4-6** : impacte le **volume affiché** dès le lancement (donc le
   remplissage des grilles home). Question ouverte au backlog (plan §6.3).
```
