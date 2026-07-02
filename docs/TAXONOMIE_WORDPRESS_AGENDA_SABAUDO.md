# Taxonomie & structure WordPress — Agenda Sabaudo

*Proposition de construction du site public dans WordPress, à partir de la taxonomie observée sur
guidatorino.com. Complète le plan du site (arborescence/URLs) et le guide d'indexation (stack).*

---

## 1. La taxonomie de GuidaTorino (ce qu'on a observé)

GuidaTorino tourne sous WordPress avec le plugin **Events Manager**. Sa structure repose sur
**trois axes** — et un principe clé.

| Objet | Type WordPress | URLs observées |
|---|---|---|
| Événement | CPT « event » | `/eventi-torino/{slug-evenement}/` |
| **Catégorie** d'événement | Taxonomie | `/eventi/torino/{categoria}/` → cinema, mostre, concerti, teatro, gastronomia, bambini, sport, **gratis** |
| **Lieu / salle** | Taxonomie « luoghi » | `/luoghi/{nom-lieu}/` (ex. `/luoghi/pista-500/`) — avec adresse + carte |
| **Temps** (oggi, domani, weekend, mois) | **PAS une taxonomie** | Vues filtrées / pages dédiées (`/eventi-torino-weekend/`, `/eventi-torino-luglio/`) |

**Le principe à retenir :** le temps n'est **jamais** une taxonomie. C'est une **requête sur les
dates**. Les sections « Cosa fare / Dove mangiare » de GuidaTorino sont, elles, du contenu de
guide de ville — **hors périmètre** pour nous (on est un agenda d'événements, pas un guide
touristique complet). On garde donc **3 axes : catégorie · lieu · (géographie)**, plus le temps
comme requête.

Différence importante avec nous : GuidaTorino est **mono-ville** (Turin). Nous avons un **4ᵉ axe
qu'il n'a pas : le territoire** (4 territoires transfrontaliers). C'est notre identité — il doit
être une taxonomie à part entière.

---

## 2. Le modèle de données proposé pour Agenda Sabaudo

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

## 3. Recommandation d'implémentation : **The Events Calendar** comme socle

Plutôt que tout recréer à la main, on part de **The Events Calendar (TEC)** — déjà recommandé
dans le guide d'indexation — qui **fournit nativement** une structure calquée sur le modèle
GuidaTorino, et **génère le schema `Event`**.

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

## 8. Décisions à trancher (pour toi)

1. **Socle** : The Events Calendar (ma reco) — ou un CPT 100 % maison (plus de contrôle, plus de
   dev) ? Reco : TEC, on ne réinvente pas les dates/lieux/schema.
2. **Bilingue** : Polylang (gratuit/Pro) ou WPML (payant, intégration TEC plus fluide) ?
3. **`territoire`** : hiérarchique territoire > ville (ma reco) — validé ?
4. **`lieu`** : taxonomie TEC « Venues » (ma reco) — ou simple champ texte au lancement, taxo
   plus tard ?
5. **« Gratuit »** : champ booléen + étiquette pour la vue `/evenements/gratuit/` — ok ?

*Rien ici n'est du dev : c'est le plan de structure. La construction WordPress (installer TEC,
enregistrer `territoire`, régler les URLs, brancher l'export backoffice) se fera quand tu
donneras le feu vert.*
