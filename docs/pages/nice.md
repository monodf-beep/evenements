# Page hub — Nice (ville · territoire Nice / Alpes-Maritimes)

*Package de contenu éditorial pour le hub ville Nice d'Agenda Sabauda (agendasabauda.eu),
édité par Cultura Sabauda. Le listing d'événements est **dynamique** (gabarit JetEngine) : aucun
événement n'est écrit en dur ici — seulement l'habillage éditorial autour du flux. Voix : sobre,
informative, géographie nommée, pas de superlatifs. Textes évergreen (aucune date, aucune édition).
Périmètre : espace sabaudo = **Comté de Nice** — on ne cite pas Cannes/Antibes/Grasse (hors zone).*

---

## Paramètres techniques

- **Slug (perpétuel, sans millésime)** : `nice/agenda`
  - URL FR : `/fr/nice/agenda/`
  - URL IT : `/it/nice/agenda/`
  - Jumelle « ce week-end » (page distincte, roulante) : `/fr/nice/ce-week-end/` — priorité prod.
- **Filtre de listing** : méta **`as_ville = "Nice"`** (JetEngine / JetSmartFilters),
  restreint à la taxonomie territoire `nice-alpes-maritimes`, tri `_EventStartDate` ASC, événements
  à venir uniquement, `lang = pll_current_language()`.
- **hreflang** : FR ↔ IT en paire + `x-default`. Canonical auto-référent.

---

## 🇫🇷 FR

### H1
Sortir à Nice : l'agenda des événements

### Meta title (~55 car.)
Sortir à Nice : agenda des sorties — Agenda Sabauda

### Meta description (~150 car.)
Que faire à Nice ? Concerts, expositions, spectacles, marchés et festivals : l'agenda des sorties de la capitale du comté de Nice, actualisé en continu.

### H2 en question (AEO — sous le H1)
Que faire à Nice ce week-end ?

### Intro éditoriale (au-dessus du flux)
Longtemps capitale du comté de Nice au sein des États de Savoie, la ville a gardé de cette histoire
son vieux Nice aux ruelles baroques, le cours Saleya et ses marchés, et une vie musicale portée par
l'Opéra Nice Côte d'Azur. Côté musées, Matisse, le MAMAC et le musée Chagall rythment la saison
d'expositions.

Au fil de l'année, l'agenda passe des concerts et des expositions aux fêtes populaires, spectacles
et festivals, du bord de mer aux collines de Cimiez. Retrouvez ici tout ce qu'il y a à faire à Nice
ce week-end et les jours qui viennent.

### Maillage interne suggéré
- **Hub territoire (parent)** : Agenda de Nice et des Alpes-Maritimes → `/fr/territoire/nice-alpes-maritimes/`
- **Croisements catégorie × ville** (au fil du volume d'événements) :
  - Concerts à Nice → `/fr/nice/concerts/`
  - Expositions & patrimoine à Nice → `/fr/nice/expositions/`
  - Spectacle vivant à Nice → `/fr/nice/spectacles/`
  - Festivals à Nice → `/fr/nice/festivals/`
- **Format roulant daté** : Que faire ce week-end à Nice → `/fr/nice/ce-week-end/`
- **Voisins du comté de Nice** : Menton → `/fr/menton/agenda/` · Vallée de la Roya →
  `/fr/roya/agenda/` · Vallée de la Vésubie → `/fr/vesubie/agenda/`
- **Breadcrumb** : Accueil › Nice / Alpes-Maritimes › Nice

---

## 🇮🇹 IT

### H1
Cosa fare a Nizza: l'agenda degli eventi

### Meta title (~55 car.)
Cosa fare a Nizza: agenda ed eventi — Agenda Sabauda

### Meta description (~150 car.)
Cosa fare a Nizza? Concerti, mostre, spettacoli, mercati e festival: l'agenda delle uscite della capitale della Contea di Nizza, aggiornato di continuo.

### H2 in forma di domanda (AEO — sotto l'H1)
Cosa fare a Nizza questo weekend?

### Intro editoriale (sopra il flusso)
A lungo capitale della Contea di Nizza in seno agli Stati sabaudi, la città conserva di quella
storia la Nizza vecchia dai vicoli barocchi, il cours Saleya con i suoi mercati e una vita musicale
sostenuta dall'Opéra Nice Côte d'Azur. Sul fronte dei musei, Matisse, il MAMAC e il museo Chagall
scandiscono la stagione espositiva.

Nel corso dell'anno l'agenda passa dai concerti e dalle mostre alle feste popolari, agli spettacoli
e ai festival, dal lungomare alle colline di Cimiez. Qui trovate tutto ciò che c'è da fare a Nizza
questo weekend e nei giorni a venire.

### Maglia interna suggerita
- **Hub territoriale (padre)** : Agenda di Nizza e delle Alpi Marittime → `/it/territoire/nice-alpes-maritimes/`
- **Incroci categoria × città** (in base al volume di eventi) :
  - Concerti a Nizza → `/it/nice/concerti/`
  - Mostre e patrimonio a Nizza → `/it/nice/mostre/`
  - Spettacolo dal vivo a Nizza → `/it/nice/spettacoli/`
  - Festival a Nizza → `/it/nice/festival/`
- **Formato aggiornato datato** : Cosa fare questo weekend a Nizza → `/it/nice/ce-week-end/`
- **Vicini della Contea di Nizza** : Mentone → `/it/menton/agenda/` · Val Roia →
  `/it/roya/agenda/` · Valle della Vésubie → `/it/vesubie/agenda/`
- **Breadcrumb** : Home › Nizza / Alpi Marittime › Nizza

---

*Note : les slugs de croisement catégorie × ville et des voisins ne graduent en pages indexables
qu'au-dessus du seuil (~8-12 événements à venir), sinon `noindex` — cf. INTENTIONS_RECHERCHE_SEO.md
et CATALOGUE_GEO_SEO.md. Aucun événement n'est cité en dur : le flux est rempli dynamiquement par le
filtre `as_ville = "Nice"`.*
