# Refonte de `/ou-manger/` — diagnostic mesuré, arbitrage SEO, contenu prêt

*05/09/2026. Franck : « cette page est d'un format qui n'est plus d'actualité, on n'a pas les
quatre territoires, il n'y a pas assez de liens internes. Faut-il une page générique avec
filtres, ou des boutons vers quatre articles « où manger » ? Sois critique. Quelle est la bonne
pratique SEO ? »*

**Réponse courte : ni l'un ni l'autre tout à fait. Le modèle « un article par territoire » est
le bon, il est DÉJÀ à moitié construit, et `/ou-manger/` doit devenir le hub qui y renvoie —
pas un concurrent qui les double avec des données périmées. Les filtres sont à écarter, pour
une raison technique précise (§3).**

---

## 1. Ce que j'ai mesuré (pas inféré)

| Fait | Mesure | Source |
|---|---|---|
| Audience de `/ou-manger/` | **0 impression sur 90 jours** | CrawlSEO / GSC — 88 pages ont ≥1 impression, celle-ci n'y est pas |
| Liens internes DANS le contenu | **0** — aucun lien, ni interne ni sortant | parsing de `entry-content` |
| Place dans le maillage | footer, colonne **« Infos & légal »**, entre *Plan du site* et *Mentions légales* | footer du site |
| Volume | **433 mots** pour 4 territoires et 44 adresses | idem |
| Gabarit | `page-template-default` + `right-sidebar` + widget **« Recent Posts »** (en anglais, non traduit, présent aussi sur `/it/dove-mangiare/`) | `<body class>` |
| Les 4 territoires | **ils y sont** (4 × H2), mais déséquilibrés : Nice 32 adresses, Piémont 5, VdA 4, **Savoie 3** | comptage |

Deux points que Franck n'avait pas en tête et qui changent l'arbitrage :

**(a) La page publie une note de travail interne.** Texte en ligne, visible du public :

> « […] mais les noms exacts n'ont pas pu être récupérés automatiquement (site de l'office de
> tourisme non accessible), **à vérifier auprès de l'office de tourisme métropolitain avant
> publication définitive**. »

Et juste au-dessus : « Liste 2022 ci-dessous ». La page se date elle-même de quatre ans.

**(b) Cette liste 2025/26 existe déjà sur le site, sur une page dédiée, et elle se classe.**

| Page | Mots | Liens internes | Impressions 90 j | Position |
|---|---|---|---|---|
| `/ou-manger/` | 433 | **0** | **0** | — |
| `/cuisine-nissarde-tables-labellisees/` (+ jumelle IT) | 1192 | **26** | 2 | **7,5** |
| `/sagre-piemont-2026/` (+ jumelle IT) | 630 | 14 | 0 | — |

Le titre de l'article niçois est *« Où manger niçois : les tables labellisées Cuisine Nissarde
**2025/26** »*. **La section Comté de Nice de `/ou-manger/` — sa seule section substantielle —
est un doublon périmé d'un article à jour qui, lui, existe et remonte.**

Et le seul lien entre les deux est un accident : le widget « Recent Posts » de la sidebar. Il
disparaîtra au prochain article publié.

**(c) La demande réelle du site n'est pas « restaurant ».** Sur les 40 premiers mots-clés :
**zéro** requête restaurant, zéro « où manger ». En revanche la demande gourmande existe, et
elle est **événementielle** : `sagra del riso jolanda di savoia 2026`, `festival del riso`,
`terra madre 2026`, `fiera di vicoforte 2026`, `agrisalumeria luiset`. C'est la catégorie
**Gastronomie & Sagre** — qui ne compte que **2 événements à venir publiés sur 86**. Il y a là
un gisement, et il n'est pas dans les listes de restaurants.

---

## 2. Pourquoi la page ne marche pas — la vraie cause

Ce n'est pas le gabarit. Le gabarit est un symptôme.

**`/ou-manger/` ne répond à aucune requête réelle.** Personne ne cherche « où manger en Savoie,
Piémont, Vallée d'Aoste et Comté de Nice ». On cherche « où manger à Turin », « restaurant
Aoste », « cuisine nissarde ». Une page qui vise quatre intentions à la fois n'en sert aucune :
Google ne sait pas pour quelle requête la proposer, et la classe pour rien. Les 0 impressions
sur 90 jours ne sont pas un accident de démarrage, c'est le résultat attendu.

Le classement en footer « Infos & légal » confirme le diagnostic de l'intérieur : **le site
lui-même traite cette page comme un utilitaire**, au même rang que les mentions légales. Google
lit ce signal.

---

## 3. Les trois options, jugées

### ❌ Option « page générique avec filtres »

**À écarter, et la raison est technique, pas esthétique.**

- Un filtre JavaScript ne crée **aucune URL indexable**. On garde une seule page pour quatre
  intentions — exactement le problème d'aujourd'hui, avec du JavaScript en plus.
- Un filtre qui génère des URL (`?territoire=piemont`) crée des pages fines, quasi dupliquées,
  qu'il faut ensuite canonicaliser ou passer en `noindex` : on paie la complexité sans gagner
  l'indexation.
- Et surtout : **un filtre sert à réduire un volume trop grand pour être parcouru.** Il y a
  **44 adresses**. Ça tient sur un écran et demi. Le filtre résoudrait un problème que cette
  page n'a pas.

### ⚠️ Option « 4 boutons → 4 articles » (l'intuition de Franck)

**C'est le bon modèle — c'est celui qui fonctionne déjà sur ce site.** Mais appliqué
brutalement aujourd'hui, il fabrique du *thin content* :

| Territoire | Matière disponible | Verdict |
|---|---|---|
| Comté de Nice | 32 adresses + article 2025/26 en ligne | ✅ l'article existe déjà |
| Piémont | 5 adresses (piole) + article sagre en ligne | ⚠️ article événementiel oui, restaurants non |
| Vallée d'Aoste | 4 adresses | ❌ trop peu |
| Savoie | **3 adresses**, la page dit elle-même « rubrique encore courte » | ❌ trop peu |

Publier « Où manger en Savoie » avec trois fermes-auberges, c'est créer une page qui ne
classera jamais et qui dilue le site. **Le dépôt a déjà tranché ce principe** :
`docs/GABARIT_PAGES_HUB.md` — *« on ne crée une page que si elle a ≥ 8 événements à venir
(sinon page à moitié vide = thin content) […] ce n'est pas une question d'importance mais de
matière disponible »*. La même règle vaut ici.

### ❌ Option « on ne touche à rien »

Non : la note de travail interne est publique, la liste est datée 2022 alors que la 2025/26 est
en ligne à côté, et la page double un article qui marche.

---

## 4. Recommandation

**Hub + rayons, construits au fur et à mesure. Un seul geste maintenant, les autres quand la
matière arrive.**

### 4.1 `/ou-manger/` devient un hub, pas un catalogue

- **Titre** : *Où manger dans les quatre territoires — Savoie, Piémont, Vallée d'Aoste, Comté
  de Nice*. Il assume l'intention **navigationnelle** (« montre-moi par où entrer ») au lieu de
  concourir sur l'intention transactionnelle (« trouve-moi une table »), qu'il perdra toujours
  face à TripAdvisor et TheFork.
- **Quatre blocs territoire**, chacun avec : 2–3 phrases de substance réelle + **les liens**
  vers l'article dédié quand il existe, vers le hub d'événements du territoire, et vers les
  pages ville.
- **La section Nice ne recopie plus la liste 2022.** Elle présente le label en trois phrases et
  **renvoie à `/cuisine-nissarde-tables-labellisees/`**, qui porte la liste 2025/26. Un doublon
  périmé de moins, un lien interne de plus vers la page qui remonte.
- **Piémont, Vallée d'Aoste, Savoie gardent leurs adresses en ligne dans le hub**, tant qu'ils
  n'ont pas assez de matière pour un article propre.

### 4.2 Les rayons, seuil à respecter

Un article « Où manger en <territoire> » se crée **à partir de ~8 adresses vérifiées**, jamais
avant — par analogie explicite avec le seuil de `GABARIT_PAGES_HUB.md`. Aujourd'hui : **Nice
seul est au-dessus, et son article existe.** Quand le Piémont passera 8 (il en faut 3 de plus),
son article se détache du hub, et le hub le remplace par un lien. Le hub ne rétrécit jamais :
il change de nature, de catalogue à carrefour.

**Ne pas renommer les slugs existants.** `/cuisine-nissarde-tables-labellisees/` et
`/sagre-piemont-2026/` collent à des requêtes réelles ; les basculer en `/ou-manger/<territoire>/`
coûterait des redirections pour un gain nul. Le hub s'adapte aux slugs, pas l'inverse.

### 4.3 Le vrai gisement, à ne pas rater

La demande gourmande mesurée sur ce site est **événementielle** (sagre, foires, salons), et la
catégorie Gastronomie & Sagre ne compte que **2 événements à venir sur 86**. Le hub doit fermer
sur un renvoi vers cette catégorie et vers `/sagre-piemont-2026/`. Mais le vrai chantier n'est
pas cette page : **c'est de sourcer les sagre.** Une ligne dans le hub ne remplacera pas
30 sagre publiées.

### 4.4 Correctifs techniques, indépendants de l'arbitrage éditorial

1. **Sortir « Où manger » de la colonne footer « Infos & légal »** → colonne « Catégories »,
   à côté de *Gastronomie*. Le classement actuel est un signal de dépréciation, gratuit à corriger.
2. **Supprimer le widget sidebar « Recent Posts »** — titre anglais non traduit, affiché sur FR
   et IT, et seule source (accidentelle) de lien vers le bon article.
3. **Passer la page au gabarit des autres pages éditoriales** (`no-sidebar`, comme
   `/plan-du-site/`) : c'est le « template plus d'actualité » que Franck a repéré.
4. **Retirer la note de travail interne** et la mention « Liste 2022 ».
5. **Renommer le H2 « Savoie » en « Savoie & Haute-Savoie »** : les trois adresses listées sont
   autour d'Annecy, donc en Haute-Savoie. Le territoire de la charte est bien « Savoie /
   Haute-Savoie ».

---

## 5. Deux anomalies trouvées en chemin, hors périmètre de cette page

À traiter séparément — je ne les corrige pas ici, mais elles pèsent plus lourd que `/ou-manger/`.

1. **Quatre familles d'URL pour les quatre mêmes territoires**, toutes présentes dans une seule
   page :

   | Famille | Statut | Canonique déclarée |
   |---|---|---|
   | `/que-faire-en-savoie/` … | 200 | elle-même ✅ |
   | `/territoire/savoie/` … | 200 | → `/que-faire-en-savoie/` ✅ |
   | `/choisir/<terr>/`, `/explore/<terr>/` | 200 | **→ la page d'accueil `/`** ⚠️ |

   Les deux dernières sont **les liens du menu de navigation**. Un lien de nav vers une URL dont
   la canonique est la home dilue le maillage de tout le site. `/explore/comte-de-nice/` a
   d'ailleurs 4 impressions en position 28 — donc Google les voit. Côté italien, même schéma :
   `/it/scopri/savoia/` déclare `/it/home-it/` comme canonique.

2. **Le footer de la version italienne est en français** (« Territoires », « Catégories »,
   « Le projet », « Infos & légal »). Site-wide, pas propre à cette page.

*Ce que j'ai cru trouver et qui est faux : un `hreflang` manquant sur
`/que-faire-en-vallee-d-aoste/`. La première récupération était tronquée ; trois essais de
contrôle montrent les 3 balises attendues. **Les quatre hubs territoire sont correctement
appairés FR↔IT.** Noté ici parce que c'est exactement le piège de `ERREURS_2026-08-18` —
conclure sur une lecture unique au lieu de mesurer deux fois.*

3. Mineur : `/sagre-piemont-2026/`, `/festivals-savoie-2026/`, `/concerts-nice-2026/`,
   `/expositions-turin-2026/` portent une année dans le slug, contre la règle « URL perpétuelle,
   jamais d'année dans le slug » de `GABARIT_PAGES_HUB.md`. Ne pas les renommer maintenant
   (redirections pour rien) ; appliquer la règle aux prochains.

---

## 6. Contenu prêt à poser — FR

> *Rien d'inventé : toutes les adresses et tous les faits viennent du contenu déjà en ligne.
> Seuls la structure, les liens et le cadrage changent. La liste niçoise 2022 est retirée au
> profit du lien vers l'article qui porte la 2025/26.*
>
> *Les **21 liens FR** ci-dessous ont été appelés un par un le 05/09 : **tous répondent 200**.
> Aucun n'est proposé sur la foi d'une supposition de slug.*

**Titre / H1** — `Où manger dans les quatre territoires`
**Title SEO** — `Où manger en Savoie, Piémont, Vallée d'Aoste et Comté de Nice`
**Meta description** — `Par où commencer pour bien manger sur les quatre territoires de
l'espace sabaudo : piole turinoises, tables valdôtaines, cuisine nissarde labellisée et
fermes-auberges de Haute-Savoie.`

---

**Chapô**

Agenda Sabauda est un agenda d'événements, pas un guide de restaurants — mais on nous demande
souvent par où commencer quand on descend d'un versant à l'autre. Voici les portes d'entrée,
territoire par territoire : des cuisines de terroir, des adresses tenues par ceux qui les font
vivre, et les fêtes gourmandes qui rythment l'année. Liste évolutive, complétée au fil du temps.

### Piémont & Turin

Les **piole**, bouchons populaires turinois nés au XIX<sup>e</sup> siècle autour des marchés,
servent la cuisine piémontaise dans sa version la plus directe : vin au verre, œufs durs, plats
mijotés.

- **Locanda San Giors** · Borgo Dora, à son adresse actuelle depuis 1904, près du marché de
  Porta Palazzo.
- **Tre Galline** · installée dans un bâtiment datant de 1592.
- **Madama Piola** · via Ormea 6 bis, cuisine piémontaise classique.
- **Antiche Sere** · via Cenischia 9, cadre familial simple.
- **La Piola di Alfredo** · via Sant'Ottavio 44.

Le Piémont se mange aussi debout, dans ses **sagre** : →&nbsp;[Sagre du Piémont 2026 :
calendrier des fêtes gourmandes](/sagre-piemont-2026/)
· →&nbsp;[Que faire dans le Piémont](/que-faire-dans-le-piemont/)
· →&nbsp;[Que faire dans le Monferrato](/que-faire-dans-le-monferrato/)
· →&nbsp;[Asti](/que-faire-a-asti/) · [Ivrea](/que-faire-a-ivrea/)

### Vallée d'Aoste

Certains restaurants portent le label régional **Saveurs du Val d'Aoste**, qui garantit l'usage
de produits locaux : fromages, charcuterie, polenta, châtaignes.

- **La Locanda** · labellisée Saveurs du Val d'Aoste, cuisine valdôtaine de saison.
- **Osteria La Vache Folle** · Piazza Cavalieri di Vittorio Veneto 14, Aoste. Fondue, salaisons
  et grillades dans un cadre rustique.
- **Aldente** · centre historique d'Aoste.
- **Al Caminetto** · centre-ville, cuisine familiale valdôtaine, sur réservation.

→&nbsp;[Que faire en Vallée d'Aoste](/que-faire-en-vallee-d-aoste/)
· →&nbsp;[Fêtes et traditions de la Vallée d'Aoste](/fetes-vallee-aoste/)

### Comté de Nice

Le label **Cuisine Nissarde**, délivré par l'office de tourisme métropolitain, distingue les
établissements qui proposent au moins cinq plats niçois dans le respect de la recette d'origine.
L'édition 2025-2026 a été remise le 6 novembre 2025 et compte 29 établissements : 20 restaurants,
7 snacks et 2 traiteurs.

**→ La liste complète, table par table : [Où manger niçois : les tables labellisées Cuisine
Nissarde 2025/26](/cuisine-nissarde-tables-labellisees/)**

→&nbsp;[Que faire dans le Comté de Nice](/que-faire-dans-le-comte-de-nice/)
· →&nbsp;[Nice](/que-faire-a-nice/) · [Menton](/que-faire-a-menton/)
· →&nbsp;[Côte d'Azur](/que-faire-sur-la-cote-dazur/)

### Savoie & Haute-Savoie

Rubrique encore courte : quelques fermes-auberges repérées près d'Annecy, à compléter.

- **Auberge La Ferme de Ferrières** · versant sud de la Mandallaz, vue sur le lac d'Annecy,
  produits de la ferme.
- **Ferme de la Charbonnière** · Menthon-Saint-Bernard, repas servi au-dessus de l'étable.
- **La Ferme de la Forclaz** · col de la Forclaz, Menthon-Saint-Bernard, ferme en activité.

→&nbsp;[Que faire en Savoie](/que-faire-en-savoie/)
· →&nbsp;[Chablais](/que-faire-chablais/)
· →&nbsp;[Aix-les-Bains](/que-faire-a-aix-les-bains/) · [Albertville](/que-faire-a-albertville/)
· [Annemasse](/que-faire-a-annemasse/)

### Manger, c'est aussi sortir

Sagre, foires gourmandes, marchés de producteurs, salons du goût : les rendez-vous où l'on mange
sont des événements à part entière, et ils sont dans l'agenda.

→&nbsp;[Tous les événements Gastronomie & Sagre](/evenements/categorie/gastronomie-sagre/)
· →&nbsp;[Tout l'agenda](/tout-l-agenda/) · →&nbsp;[Ce week-end](/ce-week-end/)

---

## 7. Contenu prêt à poser — IT (`/it/dove-mangiare/`)

**Title SEO** — `Dove mangiare in Savoia, Piemonte, Valle d'Aosta e Contea di Nizza`

**Cappello** — Agenda Sabauda è un'agenda di eventi, non una guida di ristoranti — ma ci viene
chiesto spesso da dove cominciare quando si passa da un versante all'altro. Ecco le porte
d'ingresso, territorio per territorio: cucine di terroir, indirizzi gestiti da chi li fa vivere,
e le feste gastronomiche che scandiscono l'anno. Lista in evoluzione, completata nel tempo.

*(Mêmes quatre blocs, mêmes adresses, textes déjà traduits en ligne.)*

Jumelles IT à utiliser — **toutes vérifiées 200 et auto-canoniques le 05/09** :

| Bloc | Lien IT |
|---|---|
| Piémont | `/it/cosa-fare-in-piemonte/` · `/it/sagre-piemonte-2026/` |
| Vallée d'Aoste | `/it/cosa-fare-in-valle-d-aosta/` · `/it/feste-valle-aosta/` |
| Comté de Nice | `/it/cosa-fare-nella-contea-di-nizza/` · `/it/cucina-nizzarda-ristoranti-certificati/` |
| Savoie & Haute-Savoie | `/it/cosa-fare-in-savoia/` |

> ⚠️ **Ne PAS utiliser `/it/scopri/savoia/`**, bien qu'elle réponde 200 et qu'elle soit dans le
> menu : sa canonique déclarée est `/it/home-it/`. C'est la famille défectueuse du §5.1, côté
> italien (`/scopri/` = jumelle de `/explore/`). La bonne URL est `/it/cosa-fare-in-savoia/`,
> qui est auto-canonique et que `/que-faire-en-savoie/` désigne elle-même en `hreflang="it"`.

---

## 8. Ce qu'il reste à décider — pour Franck

1. **Le hub reste-t-il ?** Le plan du site (`PLAN_DU_SITE_AGENDA_SABAUDO.md` §2.1) dit
   explicitement : *« Agenda Sabauda n'est **pas** un guide de ville (pas de restaurants) : c'est
   un agenda d'événements sur 4 territoires. »* La page contredit le plan. Mon avis : **la
   garder**, mais recadrée en carrefour comme ci-dessus — elle sert les visiteurs, et son coût
   d'entretien devient nul une fois qu'elle ne porte plus de listes. Si tu préfères t'y tenir,
   l'alternative propre est de la passer en `noindex` et de la garder comme page de service.
2. **Publication** : je n'ai rien poussé en ligne. Réécrire une page publique est un arbitrage
   éditorial, pas technique. Dis-moi si tu valides l'architecture (§4) et je pose le contenu
   FR + IT, avec les cinq correctifs techniques du §4.4.
3. Les deux anomalies du §5 (URL de nav canonicalisées vers la home, footer IT en français)
   valent plus de trafic que cette page. À planifier à part.

---

## 9. Révision après retour de Franck (05/09, même jour)

Franck : *« on n'a pas ces 3 articles ? il me semblait »* et *« il faut aussi Turin, les Langhe,
voire dans les vallées, voire lac Majeur et Lago d'Orta, voire arrière-pays nissart, voire
Chablais, avant-pays savoyard. »*

### 9.1 Non, ces trois articles n'existent pas — vérifié en base

Requête SQL directe (Novamira), `post_type IN ('post','page')`, **tous statuts sauf
auto-draft/inherit** — donc brouillons, privés et corbeille compris :

| ID | Statut | Type | Titre |
|---|---|---|---|
| 1811 / 1812 | publish | page | Où manger / Dove Mangiare |
| 3648 / 3650 | publish | post | Où manger niçois : Cuisine Nissarde |
| 2418 / 2419 | publish | post | Sagre du Piémont 2026 / Sagre del Piemonte |

**Six entrées, pas une de plus. Aucun brouillon.** Il n'existe pas d'article « où manger » pour
le Piémont, la Vallée d'Aoste ni la Savoie. La confusion vient probablement de
`/sagre-piemont-2026/` : c'est bien du Piémont et de la gastronomie, mais ce sont des
**événements**, pas des tables.

### 9.2 Sur la granularité : Franck a raison, et j'avais tort

Mon §4 proposait des rayons **par territoire**. C'est trop grossier, et il le dit justement :
personne ne cherche « où manger en Piémont ». On cherche « où manger à Turin ». La demande
vit au niveau de la **destination**, pas du territoire administratif. Point accordé.

**Mais la contrainte n'est pas l'architecture d'URL — c'est la matière.** Décompte exact des
44 adresses de la page :

| Destination proposée | Adresses disponibles |
|---|---|
| Comté de Nice (Nice 13 + hors Nice 10 + merenda 9) | **32** — et elles sont déjà dans un article |
| Turin (les piole) | **5** |
| Aoste | **4** |
| Annecy / fermes-auberges | **3** |
| Langhe · vallées piémontaises · Lac Majeur · Lago d'Orta · arrière-pays nissart · Chablais · avant-pays savoyard | **0** |

**Hors Nice, il reste douze adresses pour huit destinations, dont six à zéro.** Ouvrir ces pages
aujourd'hui, c'est publier huit pages vides. C'est exactement ce que `GABARIT_PAGES_HUB.md`
interdit — et ce document a déjà eu raison une fois, sur les pages ville.

### 9.3 La critique de fond — ce que ni Franck ni moi n'avions posé

**(a) Une liste de restaurants est un état terminal sans rouvreur** (règle 3 du CLAUDE.md).

C'est le vrai argument, et il est structurel. Un événement expire proprement : la date passe, la
fiche sort des files, personne n'est trompé. **Une liste de restaurants pourrit en silence.** Un
établissement ferme, change de mains, change de cuisine — et la page continue de l'annoncer,
sans qu'aucun signal ne se déclenche. Qui la rouvre, à quelle condition, et où voit-on le nombre
d'adresses non revérifiées ? Aucune réponse aujourd'hui. Multiplier par huit une file que
personne ne relit, c'est fabriquer huit dettes.

**(b) Sur « où manger à Turin », le combat est perdu d'avance** — face à TripAdvisor, TheFork,
Michelin et GuidaTorino (qui figure dans la base comme source, `organisateur/guidatorino-com`).
Avec cinq piole, il n'y a pas de match. Ce n'est pas du pessimisme, c'est le même constat que les
0 impressions de `/ou-manger/`.

### 9.4 Ce qui marche déjà, et pourquoi — la vraie leçon

`/cuisine-nissarde-tables-labellisees/` ne se classe pas parce qu'elle parle de Nice. Elle se
classe parce que **ce n'est pas une liste de restaurants : c'est la couverture d'une liste
officielle, datée et vérifiable** — un label, un organisme émetteur, une date de remise
(6 novembre 2025), un décompte (29 établissements). C'est du journalisme adossé à une source,
exactement ce que demande la charte éditoriale. Et ça règle le problème (a) : **le label est son
propre rouvreur**, il republie à échéance fixe.

**Or chaque territoire a son label.** Et — c'est le point — ces labels sont déjà découpés à
l'échelle des destinations que Franck réclame :

| Territoire / destination | Label | État de vérification |
|---|---|---|
| Comté de Nice | **Cuisine Nissarde** (office de tourisme métropolitain) | ✅ article en ligne, édition 2025/26 |
| Vallée d'Aoste | **Saveurs du Val d'Aoste** (label régional) | ✅ déjà cité sur `/ou-manger/`, reste à sourcer la liste |
| **Turin & province** | **Maestri del Gusto di Torino e provincia** — Camera di commercio di Torino + Slow Food + Laboratorio Chimico, sélection **biennale** | ✅ existe ; **édition 2025-2026 : 218 lauréats, dont 71 en ville** (192 reconductions, 26 nouveaux) |
| Savoie & Haute-Savoie | **Savoie Mont Blanc Excellence** / restaurants agréés **Marque Savoie** (Savoie Mont Blanc Tourisme) | ⚠️ **piste, à vérifier** — le périmètre « restaurants » semble moins figé que les trois autres |

> ⚠️ **Réserve honnête sur les Maestri del Gusto** : la sélection distingue surtout des
> **artisans du goût** — fromagers, salumieri, pâtissiers, producteurs — pas seulement des
> restaurants. Le cadrage juste n'est donc pas « où manger à Turin » mais « où goûter et
> rapporter » — ce qui est adjacent, et honnête. Ne pas forcer l'étiquette « restaurant » sur
> cette liste : ce serait exactement le genre d'approximation que la charte proscrit.

### 9.5 Architecture révisée

**L'axe n'est pas la géographie, c'est le label vérifiable — et il donne la géographie par
surcroît.**

```
/ou-manger/  (hub, carrefour, jamais un catalogue)
   ├── Comté de Nice     → /cuisine-nissarde-tables-labellisees/     ✅ en ligne
   ├── Turin & province  → « Les Maestri del Gusto 2025-2026 »       ⏳ à écrire, source solide
   ├── Vallée d'Aoste    → « Les tables Saveurs du Val d'Aoste »     ⏳ à écrire, liste à sourcer
   └── Savoie/Hte-Savoie → label à confirmer, sinon reste dans le hub ⚠️
```

Franck obtient sa granularité destination (Maestri del Gusto **est** Turin + province ; Cuisine
Nissarde **est** Nice et son arrière-pays), sans ouvrir de page pour le Chablais ou le lac d'Orta
où il n'y a rien à écrire. Les Langhe, les vallées, Orta viendront **quand une source
institutionnelle leur donnera une liste** — pas avant. Et chaque page a alors un rouvreur : la
prochaine édition du label.

**Ce qui reste dans le hub** : les piole turinoises (elles ne sont pas un label, elles sont un
type de lieu — c'est du contexte, pas une liste à maintenir) et les fermes-auberges de
Haute-Savoie, tant qu'aucun label ne les couvre.

### 9.6 Le point de décision, reformulé

La question n'est plus « une page ou quatre ». Elle est : **Agenda Sabauda couvre-t-il des
listes officielles gastronomiques comme il couvre des événements — avec une source, une date et
une prochaine édition — ou tient-il un guide de restaurants ?** Le premier est du journalisme et
tient dans la charte. Le second est un guide de ville, que le plan du site exclut explicitement,
et qui pourrira faute de rouvreur.

Ma recommandation : le premier. Et le prochain geste concret n'est pas une refonte de gabarit,
c'est **un article « Maestri del Gusto 2025-2026 »** — source institutionnelle, chiffres publics,
ancrage turinois, et le même modèle que la seule page gastronomique du site qui remonte.

*Sources vérifiées le 05/09 :*
*[Camera di commercio di Torino — Maestri del Gusto](https://www.to.camcom.it/maestridelgusto) ·*
*[TorinoToday — édition 2025-2026](https://www.torinotoday.it/social/maestri-gusto-2025-2026-torino-provincia.html) ·*
*[Savoie Mont Blanc Excellence](https://pro.savoie-mont-blanc.com/Demarche-d-Excellence/Savoie-Mont-Blanc-Excellence-c-est-quoi) ·*
*[Marque Savoie — restaurants agréés](http://www.marque-savoie.com/nos-restaurants-agrees-marque-savoie)*
