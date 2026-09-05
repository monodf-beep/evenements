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
