# Chablais — page hub territoire (zone / microrégion)

*Zone multi-communes du Chablais (rive sud du Léman, montagnes du Chablais, Portes du Soleil).
Territoire Savoie / Haute-Savoie. Page hub de listing DYNAMIQUE : aucun événement écrit en dur,
le flux est monté par le gabarit JetEngine. Contenu évergreen — aucune date, aucune édition.*

---

## Paramètres techniques

- **Slug FR (perpétuel)** : `/fr/chablais/` — jamais de millésime.
- **Slug IT (perpétuel)** : `/it/chablais/`
- **hreflang** : `fr` ↔ `it` en paire + `x-default`.
- **Type** : hub ZONE (microrégion), enfant du hub département `/haute-savoie/` (et rattaché au
  hub agrégateur `/savoie/`).
- **Filtre de listing** (méta `as_ville`) — le flux affiche les événements dont la ville ∈ :
  `Thonon-les-Bains` · `Évian-les-Bains` · `Morzine` · `Les Gets` · `Abondance` · `Châtel` ·
  `Avoriaz`.
  *(À maintenir : ajouter une commune du Chablais à cette liste la fait remonter automatiquement,
  sans toucher au texte.)*

> Rappel de graduation (INTENTIONS_RECHERCHE_SEO / CATALOGUE_GEO_SEO) : le Chablais est une zone
> **P2**. Elle ne s'indexe que si les deux conditions sont réunies — intention réelle + stock
> suffisant (~8-12 événements à venir sur l'ensemble des communes du filtre). En dessous du seuil,
> laisser la page en `noindex` et la promouvoir quand la Couverture géo le justifie.

---

## 🇫🇷 FR

### H1
Chablais : tous les événements — agenda des sorties

### H2 (formulation AEO, sous le H1)
Que faire dans le Chablais ce week-end ?

### Meta title (~60 car.)
Que faire dans le Chablais ? Agenda des sorties — Agenda Sabauda

### Meta description (~150-155 car.)
Que faire dans le Chablais : concerts, expositions, festivals et fêtes, de Thonon au Léman jusqu'aux Portes du Soleil. L'agenda des sorties, mis à jour en continu.

### Intro éditoriale (au-dessus du flux)
Entre la rive sud du Léman et les montagnes du Chablais, le territoire réunit les villes du bord
du lac — Thonon-les-Bains et Évian-les-Bains, ports, jardins et villes d'eaux du thermalisme — et
les hautes vallées de l'Abondance et de la Dranse, du val d'Abondance aux stations des Portes du
Soleil : Morzine, Avoriaz, Les Gets, Châtel. Un même pays, du plan d'eau aux alpages, où la
saison culturelle suit le rythme des lieux, du lac l'été à la montagne l'hiver.

L'agenda y couvre l'année entière : concerts et festivals au bord du Léman, expositions et
patrimoine à Thonon et Évian, marchés et fêtes de village, spectacles et rendez-vous de station.
Terre de Savoie tournée vers la Suisse voisine, le Chablais partage avec le reste de l'espace
sabaudo un même goût de la fête et du partage. Agenda Sabauda rassemble ici, semaine après
semaine, tout ce qu'il y a à faire dans le Chablais — de Thonon-les-Bains à Châtel, d'Évian aux
Portes du Soleil.

### Maillage interne suggéré
- **Remontée (territoire parent)** : hub département `/haute-savoie/` et hub agrégateur
  `/savoie/` (fil d'Ariane : Savoie › Haute-Savoie › Chablais).
- **Descente (villes de la zone, quand leur page existe)** : `Thonon-les-Bains`,
  `Évian-les-Bains`, `Morzine`, `Les Gets`, `Châtel`, `Avoriaz`, `Abondance`.
  *(Sous le seuil, ces communes restent des filtres `noindex` — ne lier que les pages réellement
  publiées.)*
- **Zones voisines (liens latéraux)** : `Faucigny`, `Pays du Mont-Blanc`, `Léman [rive
  française]` — pour capter la circulation entre microrégions du 74.
- **Croisements catégorie × Chablais** (au fil du volume) : Concerts & Musique · Festivals ·
  Gastronomie & Sagre · Marchés & Foires · Jeune public & Famille · Fêtes & Traditions populaires.
- **Filet footer** : lien vers l'accueil, « Ce week-end », À propos (éditeur Cultura Sabauda).

---

## 🇮🇹 IT

### H1
Chablais: tutti gli eventi — agenda e cosa fare

### H2 (formulazione AEO, sotto l'H1)
Cosa fare nello Chablais questo weekend?

### Meta title (~60 car.)
Cosa fare nello Chablais? Eventi e agenda — Agenda Sabauda

### Meta description (~150-155 car.)
Cosa fare nello Chablais: concerti, mostre, festival e feste, da Thonon al Lemano fino alle Portes du Soleil. L'agenda degli eventi, aggiornato di continuo.

### Intro editoriale (sopra il flusso)
Tra la sponda meridionale del Lemano e le montagne dello Chablais, il territorio riunisce le città
in riva al lago — Thonon-les-Bains ed Évian-les-Bains, porti, giardini e città termali — e le alte
valli dell'Abondance e della Dranse, dalla val d'Abondance alle stazioni delle Portes du Soleil:
Morzine, Avoriaz, Les Gets, Châtel. Un unico paese, dallo specchio d'acqua agli alpeggi, dove la
stagione culturale segue il ritmo dei luoghi: il lago d'estate, la montagna d'inverno.

L'agenda copre tutto l'anno: concerti e festival in riva al Lemano, mostre e patrimonio a Thonon
ed Évian, mercati e feste di paese, spettacoli e appuntamenti di stazione. Terra di Savoia rivolta
alla vicina Svizzera, lo Chablais condivide con il resto dello spazio sabaudo lo stesso gusto per
la festa. Agenda Sabauda raccoglie qui, settimana dopo settimana, tutto ciò che c'è da fare nello
Chablais — da Thonon-les-Bains a Châtel, da Évian alle Portes du Soleil.

### Maglia interna suggerita
- **Risalita (territorio padre)** : hub `/it/haute-savoie/` e hub aggregatore `/it/savoie/`
  (briciole: Savoia › Alta Savoia › Chablais).
- **Discesa (città della zona, quando la pagina esiste)** : `Thonon-les-Bains`,
  `Évian-les-Bains`, `Morzine`, `Les Gets`, `Châtel`, `Avoriaz`, `Abondance`.
- **Zone limitrofe** : `Faucigny`, `Pays du Mont-Blanc`, `Lemano [sponda francese]`.
- **Incroci categoria × Chablais** (secondo il volume) : Concerti & Musica · Festival ·
  Gastronomia & Sagre · Mercati & Fiere · Bambini & Famiglia · Feste & Tradizioni popolari.
- **Rete footer** : home, « Questo weekend », Chi siamo (editore Cultura Sabauda).
