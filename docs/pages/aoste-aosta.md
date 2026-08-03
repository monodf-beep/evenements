# Page hub — Aoste / Aosta (ville · territoire Vallée d'Aoste)

> Package de contenu SEO pour Agenda Sabauda (agendasabauda.eu), édité par Cultura Sabauda.
> La Vallée d'Aoste est **officiellement bilingue** : la version **FR** et la version **IT** sont
> **toutes deux primaires** (pas de langue « traduction »). Elles sont **liées en Polylang** (paire
> hreflang FR ↔ IT + `x-default`). Textes évergreen : aucune édition datée, aucun fait périssable.
> Le listing d'événements est **dynamique** (gabarit JetEngine) — **aucun événement écrit en dur**.

---

## Slug & URL (perpétuels — jamais de millésime)

| Langue | Slug | URL |
|---|---|---|
| FR | `aoste` | `https://agendasabauda.eu/fr/vallee-d-aoste/aoste/` |
| IT | `aosta` | `https://agendasabauda.eu/it/valle-d-aosta/aosta/` |

- Les deux URL s'auto-référencent en canonical et pointent leur jumelle en hreflang (`fr-FR` ↔ `it-IT` + `x-default`).
- URL **perpétuelle** : la page cumule son autorité au fil des éditions (aucune année dans le chemin). Les sous-pages roulantes se greffent dessus : `…/aoste/ce-week-end/` · `…/aosta/nel-weekend/`.

## Filtre de listing (dynamique, JetEngine)

- **Méta** : `as_ville` ∈ { `Aoste`, `Aosta` } (les deux graphies de la commune, bilingue).
- **Taxonomie** : territoire = `Vallée d'Aoste` / `Valle d'Aosta`.
- Tri par date croissante, événements **à venir** uniquement ; pagination crawlable (`/page/2/`).
- Balisage `ItemList` sur la liste ; `Event` sur chaque fiche (généré par le gabarit fiche, hors de cette page).

---

# 🇫🇷 VERSION FR

## H1
Aoste : que faire et tous les événements — agenda des sorties

## Meta title (~58 car.)
Que faire à Aoste ? Événements et sorties — Agenda Sabauda

## Meta description (~152 car.)
Que faire à Aoste : expositions, concerts, marchés, fêtes et rendez-vous valdôtains. Au pied de l'arc d'Auguste, l'agenda de la ville mis à jour en continu.

## Intro éditoriale (sous le H1, au-dessus du flux)
Capitale de la Vallée d'Aoste, Aoste porte encore le plan de la ville romaine : l'arc d'Auguste, la porte Prétorienne et le théâtre antique en marquent le centre, à deux pas des rues où l'on parle italien, français et franco-provençal. Cette identité de carrefour alpin — entre le Mont-Blanc, le Grand-Saint-Bernard et les vallées latérales — donne le ton de sa vie culturelle.

L'agenda y suit le rythme de la montagne et des traditions valdôtaines : expositions et patrimoine, concerts, spectacles, marchés et grands rendez-vous identitaires, au premier rang desquels la Foire de Saint-Ours (Sant'Orso), la fête de l'artisanat qui remplit les rues de la ville. Agenda Sabauda rassemble ici, au fil des semaines, tout ce qu'il y a à faire à Aoste — le seul agenda à couvrir d'un même geste les quatre territoires de l'ancien espace de Savoie, de part et d'autre des Alpes.

## H2 en question (AEO — à placer avant ou dans le flux)
Que faire à Aoste ce week-end ?

## Maillage interne suggéré (4-6 liens sortants)
- **Hub territoire** ↑ : Vallée d'Aoste (parent) — `/fr/vallee-d-aoste/`
- **Villes voisines / stations** : Courmayeur · Cervinia · Cogne · Saint-Vincent (au fil de la graduation) — `/fr/vallee-d-aoste/courmayeur/`, `…/cogne/`
- **Vallées & sommets** : Val de Cogne · Grand-Paradis · Mont-Blanc / Cervin — `/fr/vallee-d-aoste/`
- **Lieu patrimonial** : Forte di Bard (fort de Bard) — `/fr/vallee-d-aoste/bard/` ou page lieu dédiée
- **Catégories** (croisement × Aoste) : Expositions & Patrimoine · Concerts & Musique · Marchés & Foires · Fêtes & Traditions populaires — ex. `/fr/aoste/marches/`
- **Roulant** : « Que faire ce week-end à Aoste » — `/fr/vallee-d-aoste/aoste/ce-week-end/`

---

# 🇮🇹 VERSION IT

## H1
Aosta: cosa fare e tutti gli eventi — agenda degli appuntamenti

## Meta title (~57 car.)
Cosa fare ad Aosta? Eventi e appuntamenti — Agenda Sabauda

## Meta description (~151 car.)
Cosa fare ad Aosta: mostre, concerti, mercati, feste e appuntamenti valdostani. Ai piedi dell'Arco d'Augusto, l'agenda della città aggiornato di continuo.

## Intro editoriale (sotto l'H1, sopra il flusso)
Capoluogo della Valle d'Aosta, Aosta conserva ancora l'impianto della città romana: l'Arco d'Augusto, la Porta Pretoria e il teatro antico ne segnano il centro, a due passi dalle vie dove si parlano italiano, francese e lingua savoiarda. Questa identità di crocevia alpino (tra il Monte Bianco, il Gran San Bernardo e le vallate laterali) dà il tono alla sua vita culturale.

L'agenda segue il ritmo della montagna e delle tradizioni valdostane: mostre e patrimonio, concerti, spettacoli, mercati e grandi appuntamenti identitari, primo fra tutti la Fiera di Sant'Orso, la festa dell'artigianato che riempie le vie della città. Agenda Sabauda raccoglie qui, settimana dopo settimana, tutto ciò che c'è da fare ad Aosta — l'unico agenda che copre in un solo luogo i quattro territori dell'antico spazio sabaudo, da una parte e dall'altra delle Alpi.

## H2 in forma di domanda (AEO)
Cosa fare ad Aosta nel weekend?

## Maglia interna suggerita (4-6 link in uscita)
- **Hub territorio** ↑ : Valle d'Aosta (genitore) — `/it/valle-d-aosta/`
- **Località vicine / stazioni** : Courmayeur · Cervinia · Cogne · Saint-Vincent (secondo la graduazione) — `/it/valle-d-aosta/courmayeur/`, `…/cogne/`
- **Vallate & cime** : Valle di Cogne · Gran Paradiso · Monte Bianco / Cervino — `/it/valle-d-aosta/`
- **Luogo del patrimonio** : Forte di Bard — `/it/valle-d-aosta/bard/` o pagina luogo dedicata
- **Categorie** (incrocio × Aosta) : Mostre & Patrimonio · Concerti & Musica · Mercati & Fiere · Feste & Tradizioni popolari — es. `/it/aosta/mercati/`
- **Rotante** : « Cosa fare ad Aosta nel weekend » — `/it/valle-d-aosta/aosta/nel-weekend/`

---

## Notes de conformité (rappel, ne pas publier ces notes)
- ✅ Bilingue à parts égales : FR et IT primaires, non traductions littérales, liées Polylang + hreflang.
- ✅ Slug/URL perpétuels (aucune année). Marque « Agenda Sabauda » en suffixe des titles.
- ✅ Aucun événement en dur : le flux est dynamique (`as_ville` = Aoste/Aosta).
- ✅ Ton sobre, géographie nommée (ville → territoire), pas de superlatifs creux, angle transfrontalier 4 territoires énoncé.
- ✅ Identité ancrée : Aoste romaine (arc d'Auguste, porte Prétorienne, théâtre romain), trilinguisme valdôtain, Foire de Saint-Ours / Sant'Orso.
