# Intentions de recherche → pages à créer (SEO local)

*Cartographie des requêtes réelles (SERP françaises 2025-2026) et des pages qui les captent.
Pilote le WordPress ET le sourcing (quelles villes remplir d'abord). Le trafic local se gagne
avec des PAGES DE HUB dont le titre colle à la requête — pas avec les fiches.*

---

## 1. DEUX intentions, traitées différemment par Google

| | **A — Touriste / intemporel** | **B — Habitant / daté** |
|---|---|---|
| Requêtes | « que faire à Annecy », « visiter Chambéry », « que faire dans les Bauges » | « **sortir à** Annecy », « **agenda** Chambéry », « **événements** Annecy », « **que faire ce week-end à** Annecy », « concert Annecy » |
| Attente Google | Listicle intemporel « 10 incontournables » | Liste d'événements **datés**, fraîche |
| Qui rank | TripAdvisor, Petit Futé, Routard, Generation Voyage, OT | agendaculturel.fr, jds.fr, alentoor.fr, OT « agenda », Le Dauphiné |
| Gagnable par un site NEUF ? | ❌ **Non** (autorité verrouillée) | ✅ **Oui — notre terrain** |

**Règle d'or : ne pas se battre sur l'intention A** (« que faire à [ville] » = listicle touristique
tenu par les géants). **Tout miser sur l'intention B datée**, surtout **« que faire ce week-end à
[ville] »** — le seul créneau où un site neuf bat les géants (par la fraîcheur).

## 2. Échelle géographique : VILLE d'abord (pas le massif)

| Échelle | Requête | Verdict SEO événementiel |
|---|---|---|
| **Ville** | « sortir à Chambéry », « agenda Annecy » | ✅ **le pivot** — volume régulier toute l'année, concurrence battable |
| **Département** | « agenda Savoie » | ⚠️ navigationnel/faible → **hub agrégateur**, pas captation fine |
| **Massif / zone** | « que faire dans les Bauges / Aravis / Tarentaise » | ❌ **touristique + saisonnier + verrouillé** (Routard, Lonely Planet, OT) — PAS de l'événementiel daté |

**Le massif n'est PAS une page événementielle.** « quels événements dans les Bauges ce week-end »
n'a quasi pas de volume ; sur l'événementiel on retombe sur la **ville-porte** (Annecy, Chambéry,
Albertville). Les OT eux-mêmes agrègent l'agenda des massifs dans la ville-centre.
→ **Massifs = ÉTIQUETTES transversales** (taxonomie `etiquette` existante), **`noindex` au
départ**, filtrables ; promouvables en page **le jour où le stock + la demande existent** (ex.
Tarentaise l'hiver). Jamais une catégorie ni un niveau de territoire.

## 3. Le format prioritaire : « ce week-end à [ville] », daté, hebdomadaire

C'est le meilleur ratio effort/gain de tout le projet. Modèle sortiraparis/jds.fr :
- URL : `/[ville]/ce-week-end/` (roulante, réécrite chaque semaine).
- **`<title>` = H1** : **« Que faire ce week-end à [Ville] ? [N] idées de sorties (du [date] au [date] 2026) »**
  (la date + le nombre = leviers de fraîcheur et de CTR).

## 4. Gabarits de titre à copier (levier gratuit n°1)

| Page | `<title>` / H1 |
|---|---|
| Hub ville | **« [Ville] : tous les événements — agenda des sorties »** |
| Ce week-end (ville) | **« Que faire ce week-end à [Ville] ? [N] idées de sorties (du [d1] au [d2]) »** |
| Catégorie × ville | **« Concerts à [Ville] — l'agenda des concerts et spectacles »** |
| Hub département | **« Agenda de la [Savoie] — sorties, concerts, événements »** |

## 5. Architecture recommandée (site neuf, solo)

**Priorité 1 — villes-ancres**, dans l'ordre de demande :
`Annecy → Chambéry → Aix-les-Bains → Thonon-les-Bains → Annemasse → Albertville → Cluses/Sallanches`.
Par ville : **hub** `/[ville]/agenda/` + **`/[ville]/ce-week-end/`** (roulant, priorité de prod
absolue) + sous-pages catégorie au fil du volume.

**Seuil de création** : **pas de page géo sous ~8-12 événements** à venir + une source qui la
maintient. Mieux vaut **3-5 villes bien remplies** que 20 coquilles (thin content = pénalité).
En dessous du seuil → `noindex`.

**Départements** `/savoie/` `/haute-savoie/` = **hubs agrégateurs** (maillage descendant vers
villes, remontée des événements).

**Massifs** = étiquettes `#bauges #aravis #tarentaise #maurienne #chablais #beaufortain` — filtres,
`noindex` au départ.

**Transfrontalier (Aoste, Nice, Piémont)** = **phase 2**, après consolidation du cœur savoyard
(concurrence plus faible mais volume dispersé + bilingue).

```
/ (accueil)
├── /savoie/                     ← hub agrégateur (parent)
│   ├── /chambery/agenda/        ← PAGE PRIORITAIRE (ville)
│   │   └── /chambery/ce-week-end/  ← FORMAT ROULANT (priorité #1)
│   ├── /aix-les-bains/agenda/
│   └── /albertville/agenda/
├── /haute-savoie/
│   ├── /annecy/agenda/  +  /annecy/ce-week-end/
│   └── /thonon-les-bains/agenda/  …
└── étiquettes transversales (noindex au départ) : #bauges #aravis #tarentaise …
```

## 6. Cohérence avec les décisions déjà prises
- ✅ Confirme **temps primaire** + hub « ce week-end » — mais à **décliner par ville**, pas seulement global.
- ✅ Confirme `noindex` « Aujourd'hui »/« Cette semaine » (infreshables par ville en solo).
- ➕ **Ajoute** : gabarit `/[ville]/ce-week-end/` daté ; les patterns de titres §4 ; les massifs en
  **étiquettes `noindex`** (pas une nouvelle taxonomie — on réutilise `etiquette`).
- Impact **sourcing** : remplir **Annecy + Chambéry d'abord** (au-dessus du seuil) avant d'ouvrir d'autres villes.

## 7. À confirmer (non bloquant)
Volumes chiffrés par mot-clé (l'outil de recherche est indexé US) → un passage Google Keyword
Planner / Ahrefs « France » sur les patterns du §1 affinera l'ordre exact des villes. L'ossature,
elle, est solide (structure réelle des SERP + qui rank observés).
