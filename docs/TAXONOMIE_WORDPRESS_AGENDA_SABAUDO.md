# Taxonomie & structure WordPress — Agenda Sabauda

*Proposition de construction du site public dans WordPress, à partir de la taxonomie observée sur
guidatorino.com. Complète le plan du site (arborescence/URLs) et le guide d'indexation (stack).*

---

## 1. La taxonomie de GuidaTorino (ce qu'on a observé)

GuidaTorino tourne sous WordPress avec le plugin **Events Manager (EM)** — confirmé par
inspection du DOM (CPT `event` + CPT `location`, classes `single-event`, `single-location`,
`em-location-map-container`).

**Structure réelle observée (vérifiée sur le site vivant, Claude-in-Chrome) :**

| Objet | Type WordPress RÉEL | URL exacte | Remarque |
|---|---|---|---|
| Fiche événement | **CPT `event`** (Events Manager) | `/eventi-torino/{slug}/` | Permalink personnalisé |
| **Lieu / salle** | **CPT `location`** (Events Manager) | `/luoghi/{slug}/` (ex. `/luoghi/museo-egizio/`) | **La seule vraie taxonomie EM exposée** : adresse + carte Google Maps + événements liés |
| **Catégories** (mostre, concerti, teatro, gastronomia, bambini, sport, **eventi-gratis**) | **Pages WP statiques** (enfants d'une page parent), **pas** des archives de taxonomie | `/eventi/torino/{slug}/` | Chaque page = un shortcode EM filtré par catégorie. La taxo native `/event-category/` n'est **pas** utilisée en front |
| Temps : Oggi, Domani | **Pages WP statiques** + shortcode filtré | `/eventi-torino-oggi/`, `/eventi-torino-domani/` | Pas une vue dynamique |
| Temps : Weekend | **Article de blog** (post) **édité à la main** chaque semaine | `/eventi-torino-week-end/` | La fameuse URL evergreen recyclée |
| Temps : mois | **12 pages WP statiques** | `/eventi-torino-{mese}/` | Une page par mois |
| **Organisateur** | ❌ **non exposé** (`/organizzatori/` → 404) | — | Fonction EM présente mais non utilisée |

**Ce que la vérification confirme dans notre plan :**
- Le **lieu** (`/luoghi/`) est bien l'objet de valeur : adresse + carte + événements liés. À
  reprendre tel quel.
- Le **temps n'est jamais une taxonomie** — chez eux ce sont des pages/articles. On garde le
  temps comme **requête sur les dates**.
- L'**organisateur** est accessoire (eux ne l'exposent même pas) → chez nous, optionnel/noindex.

**Ce que la vérification corrige / ce qu'on fera MIEUX qu'eux :**
- Leurs **catégories = pages statiques manuelles** (une page WP à créer/maintenir par catégorie).
  Ça ne passe pas à l'échelle pour nous (11 catégories × 4 territoires × 2 langues). **On
  utilisera de vraies archives de taxonomie** (auto-générées) — voir §2.
- Leur **weekend = un article édité à la main** chaque semaine. **Chez nous, hub dynamique** à
  URL fixe qui interroge les dates (zéro saisie manuelle).
- **Bon à prendre chez eux quand même** : le principe « **page éditoriale + liste d'événements
  filtrée** » (leur intro + shortcode). On le reproduit **proprement** : chaque hub = archive de
  taxonomie **avec un texte d'intro pérenne** au-dessus (nos textes FR/IT sont déjà écrits). On
  garde l'avantage SEO de leur intro éditoriale, sans la corvée de la page statique manuelle.

Différence structurelle avec eux : GuidaTorino est **mono-ville** (Turin). Notre **4ᵉ axe, le
territoire** (4 territoires transfrontaliers), n'existe pas chez eux — c'est notre identité, une
taxonomie à part entière.

---

## 2. Le modèle de données proposé pour Agenda Sabauda

### 2.1 Un type de contenu : l'événement

Un CPT `evenement` (la « fiche »). Chaque occurrence = **une URL unique** (règle Google + guide
d'indexation).

### 2.2 Les taxonomies (le cœur de la proposition)

| Taxonomie | Hiérarchique ? | Termes | URL | Rôle |
|---|---|---|---|---|
| **`categorie`** | oui | les **11** (Expositions & Patrimoine, Concerts & Musique, …) | `/fr/evenements/{cat}/` | Hub thématique |
| **`territoire`** | **oui (2 niveaux)** | 4 territoires **> villes** (Piémont > Turin, Cuneo…) | `/fr/territoire/{terr}/` et `/fr/territoire/{terr}/{ville}/` | Hub géographique + pages villes (v2) |
| **`lieu`** | non | les salles/lieux (Château de Chambéry, Museo Egizio…) + adresse & géo en *term meta* | `/fr/lieu/{lieu}/` | Archive par salle (SEO « [lieu] événements », événements récurrents) |
| **`organisateur`** | non | les organisateurs | `/fr/organisateur/{nom}/` (souvent noindex) | Regroupement, réciprocité backlinks |
| **`etiquette`** | non | Gratuit, En famille, Plein air, Transfrontalier… | filtre | Badges & filtres transverses |

**Pourquoi `territoire` hiérarchique (territoire > ville)** : une seule taxonomie géographique
gère les 4 hubs territoire **et** les pages villes (quand une ville dépasse le seuil de ~15
événements — cf. brief). Élégant, pas de doublon. La ville reste un **terme enfant** ; tant que
son volume est faible, on la laisse en `noindex` (anti-bloat).

**Pourquoi `lieu` en taxonomie (et pas un simple champ texte)** : ça crée une **archive par
salle** — précieux pour le SEO local (« Château des Ducs de Savoie événements ») et pour les
**lieux récurrents** (un même théâtre accumule ses événements sur une page stable qui gagne en
autorité). C'est exactement le `/luoghi/` de GuidaTorino. On lui attache adresse + géo en
*term meta* (pour le schema `Place`).

**« Gratuit »** : chez GuidaTorino c'est une pseudo-catégorie (« Gratis »). Chez nous, mieux vaut
un **champ booléen** (badge + filtre) doublé d'un **terme d'étiquette** « Gratuit » pour générer
une vue `/fr/evenements/gratuit/` — « que faire gratuitement ce week-end » est une requête forte.

### 2.3 Le temps = une requête sur les dates (jamais une taxonomie)

Les hubs temporels (`/fr/aujourdhui/`, `/fr/ce-week-end/`, `/fr/cette-semaine/`,
`/fr/agenda/{aaaa}/{mm}/`) sont des **gabarits de page** (ou endpoints de réécriture) qui
**interrogent `date_debut`/`date_fin`**. URL **fixes**, recyclées (le pattern evergreen prouvé).
On ne crée jamais de taxonomie « week-end » ni d'article hebdo jetable.

### 2.4 Les champs (meta) de l'événement

Repris du schéma `events_raw` du backoffice :

| Champ | Usage |
|---|---|
| `date_debut`, `date_fin` (datetime + fuseau) | **le socle** : requêtes temporelles, tri, schema, badges « en cours »/« dernier week-end » |
| `horaire`, `tarif`, `gratuit` (bool), `billetterie_url` | bloc pratique + schema `offers` |
| `lieu` (→ taxo), `adresse`, `cp`, `ville`, `lat`, `lng` | bloc pratique + schema `Place` |
| `organisateur` (→ taxo) | crédit + schema `organizer` |
| `source_officielle_url`, `verifie_le` | confiance (GEO) — jamais la source radar |
| `image`, `image_credit`, `image_source` | héro + crédit obligatoire |
| `score`, `statut`, `langue` | pilotage éditorial (dont la sélection « À la une ») |

---

## 3. Quel plugin ? — The Events Calendar vs Events Manager (GuidaTorino)

La vérification l'a montré : **GuidaTorino utilise Events Manager (EM)**. Faut-il copier ?
Analyse critique — les deux ont un CPT événement + un CPT lieu + du schema, mais :

| Critère | The Events Calendar (TEC) | Events Manager (EM, = GuidaTorino) |
|---|---|---|
| Archives de taxonomie (catégorie, territoire) | ✅ natives, auto | ⚠️ possibles mais **GuidaTorino les contourne** par des pages statiques manuelles |
| Lieu (Venue/Location + carte + événements liés) | ✅ | ✅ (leur `/luoghi/`) |
| Schema `Event` auto | ✅ | ✅ |
| Intégration **RankMath / Yoast** (IndexNow, hreflang, sitemaps) | ✅ documentée | ⚠️ moins outillée |
| Multilingue **FR/IT** (WPML/Polylang) | ✅ intégration WPML officielle | ⚠️ friction connue |
| Passage à l'échelle (11 cat × 4 terr × 2 langues) | ✅ (taxonomies) | ⚠️ (leur modèle « page par catégorie » ne scale pas) |

**Reco : The Events Calendar** — pas parce que GuidaTorino a tort, mais parce que **notre besoin
diffère** : bilingue, 4 territoires, indexation rapide (IndexNow via RankMath, cf. guide
d'indexation). On **reprend les bons patterns d'EM/GuidaTorino** (le lieu-objet avec carte, le
hub = intro éditoriale + liste filtrée) **sans** ses faiblesses (catégories manuelles, weekend
édité à la main, multilingue laborieux). *Si tu tiens à mirrorer GuidaTorino à l'identique, EM
reste viable — mais tu hériteras de ses limites multilingues et de la maintenance des pages
statiques.*

On part donc de **TEC**, qui **fournit nativement** une structure proche du modèle GuidaTorino
et **génère le schema `Event`** :

| Notre modèle | Fourni par TEC ? | Action |
|---|---|---|
| CPT `evenement` | ✅ `tribe_events` | Utiliser tel quel |
| Dates début/fin, récurrence, horaires | ✅ | Utiliser tel quel |
| Taxonomie `categorie` | ✅ « Catégories d'événements » | Y créer nos **11** catégories |
| Taxonomie `lieu` | ✅ **« Lieux » (Venues)** avec adresse + carte + géo | = le `/luoghi/` de GuidaTorino |
| Taxonomie `organisateur` | ✅ **« Organisateurs »** | Utiliser tel quel |
| `etiquette` (Gratuit…) | ✅ Étiquettes | Créer nos étiquettes |
| Schema `Event` JSON-LD | ✅ auto | Vérifier + **une seule source** (désactiver le schema du plugin SEO sur la fiche) |
| **Taxonomie `territoire`** (4 > villes) | ❌ | **À AJOUTER** : `register_taxonomy('territoire', 'tribe_events', hiérarchique)` |
| Champs backoffice (`score`, `verifie_le`, `source`, `image_credit`) | ❌ | **À AJOUTER** : meta custom (ACF ou natif) |
| Hubs evergreen `/ce-week-end/` | ⚠️ vues par défaut à noindexer | **Construire nos gabarits** (meilleur SEO que les vues TEC) |

**En clair :** TEC nous donne 80 % (événements + catégories + lieux + organisateurs + dates +
schema). On ajoute **le territoire** (notre identité) + **les champs du backoffice** + **nos
hubs evergreen**. On **noindexe** les vues techniques de TEC (mois/semaine/photo) — cf. guide
d'indexation §3.

---

## 4. URLs & réglage des « rewrite slugs »

Cible (plan du site) vs défaut TEC (à reconfigurer dans Réglages → Events → URLs) :

| Page | URL cible | Réglage |
|---|---|---|
| Fiche | `/fr/evenement/{slug}/` | slug singulier `evenement` |
| Catégorie | `/fr/evenements/{cat}/` | base d'archive `evenements` |
| Territoire | `/fr/territoire/{terr}/` | rewrite de la taxo custom |
| Ville | `/fr/territoire/{terr}/{ville}/` | terme enfant |
| Lieu | `/fr/lieu/{lieu}/` | slug venues |
| Hubs temporels | `/fr/ce-week-end/`, `/fr/aujourdhui/`… | pages/gabarits maison |

> ⚠️ TEC a des limites sur la personnalisation fine des URLs de taxonomie ; certaines
> combinaisons (catégorie×territoire) devront passer par des **règles de réécriture** custom ou
> un gabarit d'archive à double taxonomie. À arbitrer au dev (les croisements sont ~12-16 pages,
> gérable).

---

## 5. Bilinguisme (Polylang + TEC)

- **Polylang** (ou WPML) : traduire le CPT `tribe_events`, **les termes des taxonomies**
  (catégories, territoires, lieux) et les slugs. Chaque événement = **une paire FR↔IT** liée par
  hreflang ; jamais deux langues sur une URL.
- Point d'attention connu : TEC + Polylang demande un peu de réglage (traduction des termes, des
  vues). WPML a une intégration TEC officielle plus poussée — **à trancher** selon le budget
  (Polylang gratuit/Pro vs WPML payant).
- Les **noms de lieux** ne se traduisent pas (Château de Chambéry reste Château de Chambéry) ;
  seuls les **libellés de catégories/territoires** et les **contenus** se traduisent.

---

## 6. Le pont backoffice → WordPress

Le backoffice pousse déjà des **brouillons** (`publisher.py`). Pour le site public, l'export
devra, en plus du titre/corps/image :
- créer/rattacher les **termes** : `categorie` (depuis `llm_categorie`), `territoire` (depuis
  `territoire` + `ville`), `lieu` (depuis `lieu`+adresse), `organisateur` ;
- écrire les **meta** : `date_debut`/`date_fin`, `tarif`/`gratuit`, `billetterie_url`,
  `source_officielle_url`, `verifie_le`, `image_credit`, `score` ;
- rester en **`draft`** (règle inchangée : rien n'est publié sans toi).

Mapping direct depuis `events_raw` — aucun champ à réinventer, tout existe déjà en base.

---

## 7. Schéma récapitulatif

```
CPT  evenement (TEC: tribe_events)
│
├─ TAXONOMIES
│   ├─ categorie        (11, hiérarchique)          /fr/evenements/{cat}/
│   ├─ territoire       (4 > villes, hiérarchique)  /fr/territoire/{terr}[/{ville}]/
│   ├─ lieu / venue     (+ adresse, géo)            /fr/lieu/{lieu}/
│   ├─ organisateur                                  /fr/organisateur/{nom}/  (souvent noindex)
│   └─ etiquette        (Gratuit, En famille…)       filtre + /fr/evenements/gratuit/
│
├─ META  date_debut/fin · horaire · tarif · gratuit · billetterie_url
│        · adresse/cp/ville/lat/lng · source_officielle_url · verifie_le
│        · image_credit/source · score · statut · langue
│
└─ TEMPS = requête sur date_debut/fin (JAMAIS une taxonomie)
     /fr/aujourdhui/ · /fr/ce-week-end/ · /fr/cette-semaine/ · /fr/agenda/{aaaa}/{mm}/
     → gabarits maison, URLs fixes recyclées (evergreen)
```

---

## 8. Anatomie du contenu & maillage interne (vérifié sur GuidaTorino)

Reconnaissance live du **corps** des pages (Claude-in-Chrome) — les règles concrètes à coder :

**Maillage « centripète » (la règle qui répond au reproche Yoast « aucun lien interne ») :**
- Une **fiche événement** ne lie, dans son corps, que vers **2 pages internes** : sa page
  **lieu** (`/luoghi/…`) et sa page **catégorie** (+ 1-2 liens externes billetterie). **Jamais
  vers d'autres fiches.** Le reste des liens de la page vient du gabarit (nav, tuiles catégories,
  sidebar) : ~33 liens internes au total sur la page, mais **~3 seulement dans le corps**.
- Le **listicle** est le **seul** gabarit à créer des **liens croisés entre fiches** (« en savoir
  plus → » vers chaque fiche) : ~11 liens internes dans le corps.
- **Pas** de bloc « événements liés » dynamique chez eux. **Nous, on peut faire mieux** : ajouter
  un rail « événements liés » (même lieu / catégorie / dates) — c'est un plus SEO qu'ils n'ont pas.

→ **Règle Agenda Sabauda** : dans le corps d'une fiche, lier le **nom du lieu** vers sa page
lieu et la **catégorie** vers son hub. Ces liens se posent à l'export (on connaît lieu + catégorie).

**Corps de l'article (fiche) :**
- GuidaTorino : **court et dense** (200-270 mots, 2 paragraphes, **zéro sous-titre**). Ils
  évitent le reproche Yoast « 300 mots sans sous-titres » **en restant courts**.
- Nous, nos articles enrichis font ~450-500 mots → il **faut des `##` sous-titres** (fait :
  `enrich.py` ajoute désormais des H2 au-delà de ~250 mots, phrases courtes, mots de liaison).
- **Gras** sur les faits : dates, noms propres (artistes), lieux, chiffres, titres d'œuvres +
  les labels du bloc pratique (Quand / Où / Prix). On applique le même patron.
- Pas de chapô typographique distinct chez eux ; nous gardons notre chapô en gras (c'est un plus).

**Page lieu (`/luoghi/`) — minimale, à reproduire :** fil d'Ariane → H1 (nom du lieu) → liste
**« Événements à venir »** (chaque événement daté + lié) → **carte** → **adresse**. **Aucune
description éditoriale.** Confirme le CPT `lieu` = agrégateur (événements + carte + adresse).

**Listicle « Les 10 du week-end » — 1 item = ** `## Nom` → image → paragraphe (~75 mots) →
lien **« En savoir plus → »** vers la fiche. 10 items. Pas de H3, pas de chapô de section.

**Note technique :** chez eux, le bloc pratique (Quand/Où/Prix/Carte) est du `<p>` avec
`<strong>` (pas des headings) ; les étoiles (WP-PostRatings) sont sur chaque fiche (engagement,
optionnel pour nous) ; **pas de boutons de partage** (mais on garde l'Open Graph pour l'aperçu
au partage de lien, qui est autre chose).

---

## 9. Décisions — FIGÉES

Ces choix sont **tranchés et verrouillés** dans `deploy/agenda-sabaudo/INSTALL_RUNBOOK.md` §0.0
(ne plus les ré-ouvrir pendant le build) :

1. **Plugin** : **The Events Calendar**. ✅
2. **Bilingue** : **Polylang** (gratuit) ; WPML seulement si la traduction des termes TEC coince. ✅
3. **`territoire`** : **hiérarchique** territoire > ville. ✅
4. **`lieu`** : **taxonomie TEC « Venues »** (slug `luoghi`). ✅
5. **« Gratuit »** : **champ booléen + étiquette** pour la vue `/fr/evenements/gratuit/`. ✅

Voir aussi la **politique d'indexation & routage par fiche** (un site par événement, masse en
`noindex`) : `INSTALL_RUNBOOK.md` §0.1.

*Rien ici n'est du dev : c'est le plan de structure. La construction WordPress (installer TEC,
enregistrer `territoire`, régler les URLs, brancher l'export backoffice) se fera quand tu
donneras le feu vert.*
