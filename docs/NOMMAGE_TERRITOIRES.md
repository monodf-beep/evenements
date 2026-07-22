# Convention de nommage : territoires, sous-divisions, exonymes FR/IT

*Référence unique pour nommer les lieux sur Agenda Sabauda (pages, fils d'Ariane, filtres,
libellés). Bilingue FR/IT. Deux niveaux : le **territoire** (les 4 de l'espace sabaudo) et,
sous lui, la **sous-division administrative** (département côté France, province côté Italie),
uniquement là où elle existe.*

**Version 2 (2026-07-21).** Corrections par rapport à la v1 :
1. « Haute-Savoie » / « Alta Savoia » abandonnés : la Savoie est **une**, distinguée au besoin
   par chef-lieu (Chambéry / Annecy).
2. Nice ramené à son identité (**Comté de Nice / Contea di Nizza**), sans le département des
   Alpes-Maritimes (trop large : il inclut Grasse, jamais niçoise). Pas de sous-division.
3. Exonymes traités comme **pédagogie** (aucun gain SEO), au format « Exonyme (nom actuel) »,
   et **uniquement quand attestés** par la nomenclature du Royaume de Sardaigne.

---

## 0. Principes

- Les 4 entités sont des **identités territoriales**, pas des unités administratives.
- **Jamais** « Haute-Savoie » ni « Alta Savoia ». **Jamais** « Savoie Mont Blanc ».
- Le territoire doit toujours être nommé : **ville, sous-division, territoire**.
- **Exonymes = pédagogie, pas SEO.** Forme « Exonyme (nom actuel) », par ex. « Ciamberì
  (Chambéry) ». On ne retient que les exonymes **attestés** (nomenclature sarde) ; sinon on
  garde le nom actuel seul. On n'invente jamais un toponyme (charte éditoriale).
- **Règle de langue croisée** : sur une page **FR**, exonyme français des villes italiennes
  (Turin, Coni, Alexandrie) ; sur une page **IT**, exonyme italien des villes françaises
  (Ciamberì, Mentone, Nizza Marittima).

---

## 1. Les 4 territoires (identité)

| Territoire | FR | IT | Slug taxo (FR / IT) |
|---|---|---|---|
| Savoie | **Savoie** | **Savoia** | `savoie` / `savoia` |
| Piémont | **Piémont** | **Piemonte** | `piemont` / `piemonte` |
| Vallée d'Aoste | **Vallée d'Aoste** | **Valle d'Aosta** | `vallee-d-aoste` / `valle-d-aosta` |
| Comté de Nice | **Comté de Nice** | **Contea di Nizza** | `comte-de-nice` / `contea-di-nizza` |

Slugs appliqués le 2026-07-22 : les anciens (`savoie-haute-savoie`, `nice-alpes-maritimes` et
leurs versions IT) ont été retirés, avec redirections 301 en place (voir § 5). Le sous-terme ville
« nice » conserve son slug, d'où `comte-de-nice` pour le territoire (évite la collision).

**Contea di Nizza** est le pendant italien exact de « Comté de Nice », au même niveau
d'identité que Savoie, Piémont et Vallée d'Aoste. On n'emploie **pas** « circondario di Nizza »
(échelon administratif) au niveau territoire.

---

## 2. Sous-divisions (seulement là où il y en a)

Motif : `FR = "Territoire (dept. X)"` · `IT = "Territoire (prov. X)"`. Seuls **« territoire »** et
**« dept./prov. »** se traduisent. Un sigle de province italien (2 lettres) peut être ajouté.

### Savoie : 2 départements, distingués par **chef-lieu** (jamais « Haute-Savoie »)

| FR (chef-lieu) | FR (numéro) | IT | Code court |
|---|---|---|---|
| Savoie (dept. Chambéry) | Savoie (dept. 73) | Savoia (prov. Ciamberì (Chambéry)) | **CM** |
| Savoie (dept. Annecy) | Savoie (dept. 74) | Savoia (prov. Annecy) | **AY** |

Les deux formes FR sont **équivalentes et acceptées** (chef-lieu ou numéro). On n'écrit jamais la
forme composée du 74. Annecy n'a pas d'exonyme italien attesté (voir § 3), on garde « Annecy ».

### Piémont : 8 provinces

Sur page FR, exonyme français attesté (Turin, Coni, Alexandrie, Novare, Verceil). Sur page IT,
nom italien + sigle officiel.

| FR | IT | Sigle |
|---|---|---|
| Piémont (prov. Turin) | Piemonte (prov. Torino) | TO |
| Piémont (prov. Coni (Cuneo)) | Piemonte (prov. Cuneo) | CN |
| Piémont (prov. Alexandrie (Alessandria)) | Piemonte (prov. Alessandria) | AL |
| Piémont (prov. Asti) | Piemonte (prov. Asti) | AT |
| Piémont (prov. Biella) | Piemonte (prov. Biella) | BI |
| Piémont (prov. Novare (Novara)) | Piemonte (prov. Novara) | NO |
| Piémont (prov. Verbano-Cusio-Ossola) | Piemonte (prov. Verbano-Cusio-Ossola) | VB |
| Piémont (prov. Verceil (Vercelli)) | Piemonte (prov. Vercelli) | VC |

**Sigles de province (libellé court).** Chaque province italienne a un sigle officiel de deux
lettres, utilisable en forme abrégée « **Torino (TO)** » (plaques, adresses) :

| Province | Sigle | Province | Sigle |
|---|---|---|---|
| Torino | **TO** | Novara | **NO** |
| Cuneo | **CN** | Verbano-Cusio-Ossola | **VB** |
| Alessandria | **AL** | Vercelli | **VC** |
| Asti | **AT** | Biella | **BI** |

Côté français, il n'existe **aucun code lettré officiel** : la France identifie ses départements
par numéro (Savoie 73, Savoie côté Annecy 74, Alpes-Maritimes 06). Pour garder la symétrie avec
les sigles italiens, Agenda Sabauda adopte une **convention construite** de 2 lettres pour les
chefs-lieux, vérifiées libres (aucune province italienne ne les porte) et lisibles dans les deux
langues :

| Ville | Code court | Logique |
|---|---|---|
| Nice / Nizza | **NI** | même amorce « Ni » en français et en italien |
| Annecy | **AY** | nom identique FR/IT (Anne-c**Y**) |
| Chambéry / Ciamberì | **CM** | initiale C commune + le **M** partagé (Cha**m**béry / Cia**m**berì) |

C'est une **convention propre à Agenda Sabauda**, pas un standard officiel : à présenter comme
telle. (Alternative libre pour Chambéry si l'on préfère : **CY**.)

### Vallée d'Aoste : région à collectivité unique
Pas de province, donc **pas de sous-division** : on reste au niveau territoire.

### Comté de Nice : pas de sous-division
Le Comté de Nice équivaut à peu près à **un arrondissement** (celui de Nice), contrairement au
Piémont et ses 8 provinces. On reste donc au niveau territoire. Code court de la ville (convention
construite, voir § 2) : **NI**.

*Note historique.* Sous le décret Rattazzi (Legge 23 ottobre 1859, n. 3702), la Contea di Nizza
est devenue la **Provincia di Nizza**, divisée en 3 circondari : Nizza, Porto Maurizio, San Remo.
L'échelon « circondario di Nizza » (l'arrondissement) reste disponible pour un découpage
administratif fin, non utilisé ici.

---

## 3. Exonymes de villes (attestés)

Base de référence : la nomenclature administrative du **Royaume de Sardaigne** (dictionnaire de
Casalis, décret Rattazzi). L'administration sarde italianisait les villes qui avaient un exonyme
réel et **gardait le français** quand il n'y en avait pas. On suit exactement cette logique.

### Sur page IT : exonyme italien des villes françaises

| FR | IT retenu |
|---|---|
| Chambéry | **Ciamberì (Chambéry)** |
| Nice (ville) | **Nizza Marittima** |
| Menton | **Mentone** |
| Annecy | **Annecy** (aucun exonyme attesté : les Sardes écrivaient « Annecy ») |

Autres italianisations sardes disponibles si besoin (niveau vallée / district) : Saint-Julien →
San Giuliano, Saint-Jean-de-Maurienne → San Giovanni in Moriana, Maurienne → Moriana, Tarentaise
→ Tarantasia, Chablais → Chiablese, Genevois → Genevese. Faucigny, Moûtiers et Bonneville
restaient en français.

### Sur page FR : exonyme français des villes italiennes

| IT | FR retenu |
|---|---|
| Torino | **Turin** |
| Cuneo | **Coni (Cuneo)** |
| Alessandria | **Alexandrie (Alessandria)** |
| Novara | **Novare (Novara)** |
| Vercelli | **Verceil (Vercelli)** |
| Asti | **Asti** (pas d'exonyme français) |
| Aosta | **Aoste** |
| Courmayeur | **Courmayeur** (Cormaiore = italianisation fasciste, non retenue) |

---

## 4. Nizza Marittima vs Nizza

« **Nizza Marittima** » est le nom sarde officiel de la ville de Nice, choisi pour la distinguer
de **Nizza Monferrato** (province d'Asti). En texte courant italien, « Nizza » suffit ;
« Nizza Marittima » s'emploie en libellé formel (fil d'Ariane, fiche, métadonnées).

---

## 5. Portée & mise en œuvre

- **État live (2026-07-22).** Nommage entièrement appliqué : termes « Savoia » et
  « **Contea di Nizza** », H2 des hubs, descriptions, snippets, mu-plugins (bandeau territoire,
  menus IT, choix de langue, filtre, requêtes), et contenu des fiches, guides, pages et extraits.
  « Alpes-Maritimes » n'est conservé que dans la prose factuelle des articles (vrai département,
  souvent pour des lieux ex-provençaux hors du Comté de Nice historique).
- **Slugs (fait, 2026-07-22).** Les 4 termes renommés : `savoie`, `savoia`, `comte-de-nice`,
  `contea-di-nizza`. **Redirections 301** en place (mu-plugin `cs-redirections-301.php`, FR + IT)
  et liens internes mis à jour.
- **Exonymes pédagogiques.** À appliquer sur les hubs quand on le souhaite (Ciamberì (Chambéry),
  Coni (Cuneo), etc.). Aucun gain SEO attendu : c'est de la transmission, pas du référencement.
- **Sous-division fine par événement** (prov./dept. dans le fil d'Ariane) : nécessite un mapping
  ville → province/département, absent en base (les événements portent `as_ville` et la taxo
  `territoire`, pas la province). À bâtir le jour venu ; ce document fige déjà le wording.

---

## Sources

- [Suddivisione amministrativa del Regno di Sardegna (Wikipedia)](https://it.wikipedia.org/wiki/Suddivisione_amministrativa_del_Regno_di_Sardegna)
- [Legge 23 ottobre 1859, n. 3702 (décret Rattazzi)](https://it.wikipedia.org/wiki/Legge_23_ottobre_1859,_n._3702) · [Provincia di Nizza (1859)](https://it.wikipedia.org/wiki/Provincia_di_Nizza_(1859))
- Goffredo Casalis, *Dizionario geografico-storico-statistico-commerciale degli Stati di S. M. il Re di Sardegna* (1833-1856)
- [Treccani, Chambéry (Ciamberì)](https://www.treccani.it/enciclopedia/chambery_(Enciclopedia-Italiana)/) · [Treccani, Annecy](https://www.treccani.it/enciclopedia/annecy_(Enciclopedia-Italiana)/)
- [Coni (Wikipédia FR)](https://fr.wikipedia.org/wiki/Coni) · [Sigles des provinces italiennes (Wikipedia)](https://it.wikipedia.org/wiki/Sigle_automobilistiche_italiane)
