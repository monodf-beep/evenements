# Page hub — Forte di Bard (lieu · commune de Bard · territoire Vallée d'Aoste)

*Package de contenu éditorial pour le hub LIEU « Forte di Bard » d'Agenda Sabauda
(agendasabauda.eu), édité par Cultura Sabauda. Le listing d'événements est **dynamique** (gabarit
JetEngine) : aucun événement n'est écrit en dur ici — seulement l'habillage éditorial autour du flux.
Voix : sobre, informative, pas de superlatifs. Textes évergreen. C'est un hub de LIEU (une
forteresse-musée qui programme expositions et concerts), pas une grande ville. Langue primaire IT +
version FR (VdA bilingue).*

---

## Paramètres techniques

- **Slug (perpétuel, sans millésime)** : `forte-di-bard`
  - URL IT : `/it/forte-di-bard/`
  - URL FR : `/fr/forte-di-bard/`
- **Filtre de listing** : méta **`as_ville = "Bard"`** (JetEngine / JetSmartFilters),
  restreint à la taxonomie territoire `vallee-aoste`, tri `_EventStartDate` ASC, événements à venir
  uniquement, `lang = pll_current_language()`. *(Repli possible : filtrer sur le lieu/venue
  « Forte di Bard » si `as_ville` varie.)*
- **hreflang** : IT ↔ FR en paire + `x-default`. Canonical auto-référent.

---

## 🇮🇹 IT

### H1
Forte di Bard: mostre, concerti ed eventi

### Meta title (~55 car.)
Forte di Bard: mostre ed eventi — Agenda Sabauda

### Meta description (~150 car.)
Cosa fare al Forte di Bard? Grandi mostre, concerti e appuntamenti nella fortezza-museo della Valle d'Aosta: l'agenda aggiornato di continuo.

### H2 in forma di domanda (AEO — sotto l'H1)
Quali mostre ed eventi al Forte di Bard?

### Intro editoriale (sopra il flusso)
All'imbocco della Valle d'Aosta, il Forte di Bard è una fortezza di primo Ottocento restaurata e
trasformata in polo culturale, con i suoi percorsi museali — a partire dal Museo delle Alpi — e i
suoi spazi espositivi. Il forte programma tutto l'anno grandi mostre e appuntamenti.

Qui trovate le mostre, i concerti e gli eventi in corso e in arrivo al Forte di Bard, aggiornati di
continuo — nel cuore dello spazio sabaudo, tra le vallate valdostane.

### Maglia interna suggerita
- **Hub territoriale (padre)** : Agenda della Valle d'Aosta → `/it/territoire/vallee-aoste/`
- **Incroci per categoria** (in base al volume) :
  - Mostre e patrimonio → `/it/forte-di-bard/mostre/`
  - Concerti → `/it/forte-di-bard/concerti/`
- **Vicini (stesso territorio)** : Aosta → `/it/aosta/agenda/`
- **Breadcrumb** : Home › Valle d'Aosta › Forte di Bard

---

## 🇫🇷 FR

### H1
Fort de Bard : expositions, concerts et événements

### Meta title (~55 car.)
Fort de Bard : expositions et événements — Agenda Sabauda

### Meta description (~150 car.)
Que voir au Fort de Bard ? Grandes expositions, concerts et rendez-vous dans la forteresse-musée de la Vallée d'Aoste : l'agenda actualisé en continu.

### H2 en question (AEO — sous le H1)
Quelles expositions et événements au Fort de Bard ?

### Intro éditoriale (au-dessus du flux)
À l'entrée de la Vallée d'Aoste, le Fort de Bard est une forteresse du début du XIXe siècle
restaurée et transformée en pôle culturel, avec ses parcours de musées — à commencer par le Musée
des Alpes — et ses espaces d'exposition. Le fort programme de grandes expositions et des rendez-vous
tout au long de l'année.

Retrouvez ici les expositions, concerts et événements en cours et à venir au Fort de Bard, actualisés
en continu — au cœur de l'espace sabaudo, entre les vallées valdôtaines.

### Maillage interne suggéré
- **Hub territoire (parent)** : Agenda de la Vallée d'Aoste → `/fr/territoire/vallee-aoste/`
- **Croisements par catégorie** (au fil du volume) :
  - Expositions & patrimoine → `/fr/forte-di-bard/expositions/`
  - Concerts → `/fr/forte-di-bard/concerts/`
- **Voisins (même territoire)** : Aoste → `/fr/aoste/agenda/`
- **Breadcrumb** : Accueil › Vallée d'Aoste › Fort de Bard

---

*Note : les slugs de croisement par catégorie ne graduent en pages indexables qu'au-dessus du seuil
(~8-12 événements à venir), sinon `noindex` — cf. INTENTIONS_RECHERCHE_SEO.md et CATALOGUE_GEO_SEO.md.
Aucun événement n'est cité en dur : le flux est rempli dynamiquement par le filtre `as_ville = "Bard"`.*
