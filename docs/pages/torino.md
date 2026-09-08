# Page hub — Torino / Turin (ville · territoire Piémont)

*Package de contenu éditorial pour le hub ville Torino d'Agenda Sabauda (agendasabauda.eu),
édité par Cultura Sabauda. Le listing d'événements est **dynamique** (gabarit JetEngine) : aucun
événement n'est écrit en dur ici — seulement l'habillage éditorial autour du flux. Voix : sobre,
informative, géographie nommée, pas de superlatifs. Textes évergreen (aucune date, aucune édition).
Langue primaire IT (ville italophone) + version FR. Ancrage sabaudo : Turin, capitale historique
des États de Savoie.*

---

## Paramètres techniques

- **Slug (perpétuel, sans millésime)** : `torino/agenda`
  - URL IT : `/it/torino/agenda/`
  - URL FR : `/fr/torino/agenda/`
  - Jumelle « ce week-end » (page distincte, roulante) : `/it/torino/questo-weekend/` — priorité prod.
- **Filtre de listing** : méta **`as_ville ∈ {"Torino", "Turin"}`** (JetEngine / JetSmartFilters),
  restreint à la taxonomie territoire `piemonte`, tri `_EventStartDate` ASC, événements à venir
  uniquement, `lang = pll_current_language()`.
- **hreflang** : IT ↔ FR en paire + `x-default`. Canonical auto-référent.

---

## 🇮🇹 IT

### H1
Cosa fare a Torino: l'agenda degli eventi

### Meta title (~55 car.)
Cosa fare a Torino: agenda ed eventi — Agenda Sabauda

### Meta description (~150 car.)
Cosa fare a Torino? Concerti, mostre, spettacoli, mercati e festival: l'agenda delle uscite della capitale sabauda, aggiornato di continuo.

### H2 in forma di domanda (AEO — sotto l'H1)
Cosa fare a Torino questo weekend?

### Intro editoriale (sopra il flusso)
Prima capitale degli Stati sabaudi, Torino ne conserva l'impianto barocco, le piazze porticate e le
residenze reali, dalla Mole Antonelliana ai Musei Reali. La città vive tutto l'anno tra il Museo
Nazionale del Cinema, il Museo Egizio, i teatri e le grandi istituzioni musicali.

Nel corso della stagione l'agenda passa dai concerti e dalle mostre ai mercati, agli spettacoli e ai
festival, dal centro alle sponde del Po. Qui trovate tutto ciò che c'è da fare a Torino questo
weekend e nei giorni a venire.

### Maglia interna suggerita
- **Hub territoriale (padre)** : Agenda del Piemonte → `/it/territoire/piemonte/`
- **Incroci categoria × città** (in base al volume di eventi) :
  - Concerti a Torino → `/it/torino/concerti/`
  - Mostre e patrimonio a Torino → `/it/torino/mostre/`
  - Spettacolo dal vivo a Torino → `/it/torino/spettacoli/`
  - Festival a Torino → `/it/torino/festival/`
- **Formato aggiornato datato** : Cosa fare questo weekend a Torino → `/it/torino/questo-weekend/`
- **Aree vicine (stesso territorio)** : Langhe → `/it/langhe/agenda/` · Monferrato →
  `/it/monferrato/agenda/` · Alba → `/it/alba/agenda/`
- **Breadcrumb** : Home › Piemonte › Torino

---

## 🇫🇷 FR

### H1
Que faire à Turin : l'agenda des événements

### Meta title (~55 car.)
Que faire à Turin : agenda des sorties — Agenda Sabauda

### Meta description (~150 car.)
Que faire à Turin ? Concerts, expositions, spectacles, marchés et festivals : l'agenda des sorties de l'ancienne capitale des États de Savoie, actualisé en continu.

### H2 en question (AEO — sous le H1)
Que faire à Turin ce week-end ?

### Intro éditoriale (au-dessus du flux)
Première capitale des États de Savoie, Turin en garde le tracé baroque, les places à arcades et les
résidences royales, de la Mole Antonelliana aux Musei Reali. La ville vit toute l'année entre le
Musée national du cinéma, le Musée égyptien, les théâtres et les grandes institutions musicales.

Au fil de la saison, l'agenda passe des concerts et des expositions aux marchés, spectacles et
festivals, du centre aux bords du Pô. Retrouvez ici tout ce qu'il y a à faire à Turin ce week-end et
les jours qui viennent.

### Maillage interne suggéré
- **Hub territoire (parent)** : Agenda du Piémont → `/fr/territoire/piemonte/`
- **Croisements catégorie × ville** (au fil du volume d'événements) :
  - Concerts à Turin → `/fr/torino/concerts/`
  - Expositions & patrimoine à Turin → `/fr/torino/expositions/`
  - Spectacle vivant à Turin → `/fr/torino/spectacles/`
  - Festivals à Turin → `/fr/torino/festivals/`
- **Format roulant daté** : Que faire ce week-end à Turin → `/fr/torino/ce-week-end/`
- **Zones voisines (même territoire)** : Langhe → `/fr/langhe/agenda/` · Monferrato →
  `/fr/monferrato/agenda/` · Alba → `/fr/alba/agenda/`
- **Breadcrumb** : Accueil › Piémont › Turin

---

*Note : les slugs de croisement catégorie × ville et des zones voisines ne graduent en pages
indexables qu'au-dessus du seuil (~8-12 événements à venir), sinon `noindex` — cf.
INTENTIONS_RECHERCHE_SEO.md et CATALOGUE_GEO_SEO.md. Aucun événement n'est cité en dur : le flux est
rempli dynamiquement par le filtre `as_ville ∈ {"Torino","Turin"}`.*
