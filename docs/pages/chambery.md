# Page hub — Chambéry (ville · territoire Savoie)

*Package de contenu éditorial pour le hub ville Chambéry d'Agenda Sabauda (agendasabauda.eu),
édité par Cultura Sabauda. Le listing d'événements est **dynamique** (gabarit JetEngine) : aucun
événement n'est écrit en dur ici — seulement l'habillage éditorial autour du flux. Voix : sobre,
informative, géographie nommée, pas de superlatifs. Textes évergreen (aucune date, aucune édition).*

---

## Paramètres techniques

- **Slug (perpétuel, sans millésime)** : `chambery/agenda`
  - URL FR : `/fr/chambery/agenda/`
  - URL IT : `/it/chambery/agenda/`
  - Jumelle « ce week-end » (page distincte, roulante) : `/fr/chambery/ce-week-end/` — priorité prod.
- **Filtre de listing** : méta **`as_ville = "Chambéry"`** (JetEngine / JetSmartFilters),
  restreint à la taxonomie territoire `savoie-haute-savoie`, tri `_EventStartDate` ASC, événements
  à venir uniquement, `lang = pll_current_language()`.
- **hreflang** : FR ↔ IT en paire + `x-default`. Canonical auto-référent.

---

## 🇫🇷 FR

### H1
Sortir à Chambéry : l'agenda des événements

### Meta title (~55 car.)
Sortir à Chambéry : agenda des sorties — Agenda Sabauda

### Meta description (~150 car.)
Que faire à Chambéry ? Concerts, expos, spectacles, marchés et festivals : l'agenda des sorties de la cité des ducs de Savoie, actualisé en continu.

### H2 en question (AEO — sous le H1)
Que faire à Chambéry ce week-end ?

### Intro éditoriale (au-dessus du flux)
Ancienne capitale des ducs de Savoie, Chambéry garde de ce passé son château, sa Sainte-Chapelle
et la vieille ville aux rues à arcades, autour de la fontaine des Éléphants. La vie culturelle s'y
concentre entre l'Espace Malraux, scène nationale, le théâtre Charles Dullin et les salles du
Carré Curial.

Au fil de l'année, l'agenda passe des concerts et des expositions aux marchés, spectacles et
festivals, en ville comme aux Charmettes, la maison de Jean-Jacques Rousseau. Retrouvez ici tout
ce qu'il y a à faire à Chambéry ce week-end et les jours qui viennent, entre lac du Bourget,
massif des Bauges et Chartreuse.

### Maillage interne suggéré
- **Hub territoire (parent)** : Agenda de la Savoie et Haute-Savoie → `/fr/territoire/savoie-haute-savoie/`
- **Croisements catégorie × ville** (au fil du volume d'événements) :
  - Concerts à Chambéry → `/fr/chambery/concerts/`
  - Expositions & patrimoine à Chambéry → `/fr/chambery/expositions/`
  - Spectacle vivant à Chambéry → `/fr/chambery/spectacles/`
  - Festivals à Chambéry → `/fr/chambery/festivals/`
- **Format roulant daté** : Que faire ce week-end à Chambéry → `/fr/chambery/ce-week-end/`
- **Villes voisines (même territoire)** : Aix-les-Bains → `/fr/aix-les-bains/agenda/` ·
  Albertville → `/fr/albertville/agenda/` · Annecy → `/fr/annecy/agenda/`
- **Breadcrumb** : Accueil › Savoie / Haute-Savoie › Chambéry

---

## 🇮🇹 IT

### H1
Cosa fare a Chambéry: l'agenda degli eventi

### Meta title (~55 car.)
Cosa fare a Chambéry: agenda ed eventi — Agenda Sabauda

### Meta description (~150 car.)
Cosa fare a Chambéry? Concerti, mostre, spettacoli, mercati e festival: l'agenda delle uscite dell'antica capitale dei duchi di Savoia, aggiornato di continuo.

### H2 in forma di domanda (AEO — sotto l'H1)
Cosa fare a Chambéry questo weekend?

### Intro editoriale (sopra il flusso)
Antica capitale dei duchi di Savoia, Chambéry conserva di quel passato il castello, la
Sainte-Chapelle e la città vecchia dalle vie porticate, attorno alla fontana degli Elefanti. La
vita culturale si concentra tra l'Espace Malraux, scène nationale, il teatro Charles Dullin e le
sale del Carré Curial.

Nel corso dell'anno l'agenda passa dai concerti e dalle mostre ai mercati, agli spettacoli e ai
festival, in città come alle Charmettes, la casa di Jean-Jacques Rousseau. Qui trovate tutto ciò
che c'è da fare a Chambéry questo weekend e nei giorni a venire, tra il lago del Bourget, il
massiccio dei Bauges e la Chartreuse.

### Maglia interna suggerita
- **Hub territoriale (padre)** : Agenda della Savoia e Alta Savoia → `/it/territoire/savoie-haute-savoie/`
- **Incroci categoria × città** (in base al volume di eventi) :
  - Concerti a Chambéry → `/it/chambery/concerti/`
  - Mostre e patrimonio a Chambéry → `/it/chambery/mostre/`
  - Spettacolo dal vivo a Chambéry → `/it/chambery/spettacoli/`
  - Festival a Chambéry → `/it/chambery/festival/`
- **Formato aggiornato datato** : Cosa fare questo weekend a Chambéry → `/it/chambery/ce-week-end/`
- **Città vicine (stesso territorio)** : Aix-les-Bains → `/it/aix-les-bains/agenda/` ·
  Albertville → `/it/albertville/agenda/` · Annecy → `/it/annecy/agenda/`
- **Breadcrumb** : Home › Savoia / Alta Savoia › Chambéry

---

*Note : les slugs de croisement catégorie × ville et des villes voisines ne graduent en pages
indexables qu'au-dessus du seuil (~8-12 événements à venir), sinon `noindex` — cf.
INTENTIONS_RECHERCHE_SEO.md et CATALOGUE_GEO_SEO.md. Aucun événement n'est cité en dur : le flux
est rempli dynamiquement par le filtre `as_ville = "Chambéry"`.*
