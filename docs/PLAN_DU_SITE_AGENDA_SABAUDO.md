# Agenda Sabauda — Plan du site & contenus fondateurs

*Document de travail — 02/07/2026. À utiliser en parallèle de la maquette Claude Design.
Complète le brief `BRIEF_DESIGN_AGENDA_SABAUDO.md` : ici on fige l'arborescence, les 3 modules
de home retenus par Franck (6 tuiles, « En évidence », nav thématique), et les textes prêts à
coller (À propos FR/IT).*

---

## 1. Plan du site (arborescence)

```
Agenda Sabauda  (/fr/  ·  /it/)
│
├─ ACCÈS TEMPOREL  (le réflexe agenda — en tête de menu)
│  ├─ Aujourd'hui                     /fr/aujourdhui/
│  ├─ Ce week-end                     /fr/ce-week-end/          ◀ la page reine
│  │   ├─ …en Savoie / Haute-Savoie   /fr/ce-week-end/savoie-haute-savoie/
│  │   ├─ …en Piémont                 /fr/ce-week-end/piemont/
│  │   ├─ …en Vallée d'Aoste          /fr/ce-week-end/vallee-d-aoste/
│  │   └─ …à Nice / Alpes-Maritimes   /fr/ce-week-end/nice-alpes-maritimes/
│  ├─ Cette semaine                   /fr/cette-semaine/
│  ├─ Les 10 du week-end (listicle)   /fr/les-10-du-week-end/   ◀ URL fixe recyclée
│  └─ Agenda du mois          (v2)    /fr/agenda/2026/07/
│
├─ TERRITOIRES  (l'axe identitaire — 4 hubs géographiques)
│  ├─ Savoie / Haute-Savoie           /fr/territoire/savoie-haute-savoie/
│  ├─ Piémont                         /fr/territoire/piemont/
│  ├─ Vallée d'Aoste                  /fr/territoire/vallee-d-aoste/
│  └─ Nice / Alpes-Maritimes          /fr/territoire/nice-alpes-maritimes/
│      └─ (v2) pages villes : Turin, Nice, Annecy, Chambéry, Aoste…  seuil ≥15 événements
│
├─ CATÉGORIES  (les 11 — hubs thématiques)
│  ├─ Expositions & Patrimoine        /fr/evenements/expositions-patrimoine/
│  ├─ Concerts & Musique              /fr/evenements/concerts-musique/
│  ├─ Spectacle vivant                /fr/evenements/spectacle-vivant/
│  ├─ Festivals                       /fr/evenements/festivals/
│  ├─ Gastronomie & Sagre             /fr/evenements/gastronomie-sagre/
│  ├─ Marchés & Foires                /fr/evenements/marches-foires/
│  ├─ Sport                           /fr/evenements/sport/
│  ├─ Cinéma                          /fr/evenements/cinema/
│  ├─ Jeune public & Famille          /fr/evenements/jeune-public-famille/
│  ├─ Conférences & Rencontres        /fr/evenements/conferences-rencontres/
│  └─ Fêtes & Traditions populaires   /fr/evenements/fetes-traditions/
│      └─ croisements cat.×territoire (~12-16, ceux à ≥10 événements) :
│         /fr/evenements/concerts-musique/piemont/  …
│
├─ FICHE ÉVÉNEMENT                     /fr/evenement/nom-ville/   ◀ sans millésime (récurrents)
│
├─ RECHERCHE            overlay  +     /fr/recherche/  (noindex)
│
├─ NEWSLETTER                         /fr/newsletter/
│
├─ LE PROJET
│  ├─ À propos                        /fr/a-propos/
│  ├─ Proposer un événement           /fr/proposer-un-evenement/   ◀ machine à contenu
│  ├─ Contact                         /fr/contact/
│  ├─ Politique crédits photos        /fr/credits-photos/
│  ├─ Mentions légales                /fr/mentions-legales/
│  └─ Confidentialité / cookies       /fr/confidentialite/
│
├─ 404
└─ Flux RSS publics   /fr/feed/  (+ par territoire et par catégorie)
```

**Miroir italien** : chaque URL a sa jumelle `/it/…` (slugs traduits : `/it/questo-weekend/`,
`/it/evento/…`). Une fiche non traduite n'existe pas en IT (repli vers le hub parent).

---

## 2. La page d'accueil — les 3 modules retenus par Franck

### 2.1 Les 6 tuiles-raccourcis (adaptation des « Cosa fare e vedere »)

GuidaTorino aligne 6 tuiles illustrées : un mix « 1 générique + tout-événements + catégories
phares ». Agenda Sabauda n'est **pas** un guide de ville (pas de restaurants, pas de « uscire
la sera ») : c'est un **agenda d'événements sur 4 territoires**. On garde le principe des
6 tuiles, adapté.

**Recommandation — 6 tuiles « familles de sorties »** (ordre = du plus cherché au plus
identitaire) :

| # | Tuile | Pointe vers | Pourquoi |
|---|---|---|---|
| 1 | **Ce week-end** | `/fr/ce-week-end/` | Le raccourci temporel roi — remplace le « cosa fare » générique. C'est LE réflexe agenda. |
| 2 | **Tout l'agenda** | `/fr/evenements/` (liste filtrable) | L'équivalent « Eventi a Torino » : la porte vers l'exhaustivité. |
| 3 | **Expositions & Patrimoine** | catégorie | Requête forte, evergreen (musées, expos longues). |
| 4 | **Concerts & Musique** | catégorie | Requête forte. |
| 5 | **Festivals & Sagre** | Festivals + Gastronomie & Sagre | Très cherché ET identitaire du territoire alpin FR/IT. |
| 6 | **En famille** | Jeune public & Famille | Public à forte intention (« que faire avec les enfants »). |

Les **11 catégories** restent toutes accessibles via le menu « Catégories ▾ » : les 6 tuiles
sont les *raccourcis vedettes*, pas la liste complète. Icônes : trait simple façon guide
(comme les pictos GuidaTorino), pas d'emoji.

**Alternative** (si tu préfères mettre l'axe géographique en avant) : 6 tuiles = **Ce week-end
+ Tout l'agenda + les 4 territoires** (chacun sa couleur). Plus identitaire « transfrontalier »,
mais moins « catégories de sorties ». *Mon avis : garder les catégories en tuiles (plus proche
de l'esprit « cosa fare »), et traiter les 4 territoires dans le bloc dédié ci-dessous (2.3) +
le menu — ils méritent leur propre axe, pas d'être noyés dans les tuiles.*

### 2.2 Le bloc « En évidence » / « In Evidenza »

Chez GuidaTorino : un encadré de contenus **populaires evergreen**, choisis à la main
(les 10 choses du week-end, les sagre du mois, les incontournables). C'est de la **curation
éditoriale**, distincte du flux automatique.

**Pour Agenda Sabauda — bloc « À ne pas manquer »** (ou « En ce moment ») :
- 4 à 6 entrées **choisies manuellement** par toi dans le backoffice (le bouton de sélection
  existe déjà — c'est la logique « choix manuel → Agenda Sabauda »).
- Contenu type : le gros festival de la saison, une expo phare en cours, l'événement à la une,
  un temps fort par territoire.
- Vignette + titre + date. Se distingue visuellement du flux daté (fond légèrement teinté,
  ou filet coloré à gauche comme dans ta capture).
- Emplacement : colonne latérale (desktop) et section pleine largeur après le hero (mobile).

### 2.3 La navigation thématique (adaptation « Ritrovate su Guida Torino… »)

GuidaTorino ferme ses pages sur une liste thématique : *« Retrouvez sur Guida Torino toutes
les informations à ne pas manquer : Attractions · Événements · Manger & boire · Infos utiles
· Sortir le soir · Alentours »*.

**Pour Agenda Sabauda** (footer + bas de l'À propos) :

> **Retrouvez sur Agenda Sabauda tout ce qu'il ne faut pas manquer :**
> – Que faire ce week-end
> – Les 4 territoires : Savoie & Haute-Savoie · Piémont · Vallée d'Aoste · Nice
> – Expositions & patrimoine
> – Concerts, spectacles & festivals
> – Gastronomie, sagre & marchés
> – En famille & jeune public

Version IT :

> **Ritrovate su Agenda Sabauda tutto ciò da non perdere:**
> – Cosa fare questo weekend
> – I 4 territori: Savoia & Alta Savoia · Piemonte · Valle d'Aosta · Nizza
> – Mostre & patrimonio
> – Concerti, spettacoli & festival
> – Gastronomia, sagre & mercati
> – In famiglia & per i bambini

---

## 3. Menu principal & pied de page (rappel)

**Header** : `Aujourd'hui | Ce week-end | Catégories ▾ | Territoires ▾ | Agenda ▾ | 🔍 | FR|IT`
(le temporel en accès direct, sans sous-menu). Commutateur **FR|IT en texte, jamais de
drapeaux**.

**Footer (4 colonnes)** : Explorer (temporels) · Catégories (11) · Territoires (4 + villes) ·
Le projet (À propos, Proposer un événement, Newsletter, Crédits photos, Mentions, RSS).
+ la nav thématique (2.3) + « édité par Cultura Sabauda ».

---

## 4. Texte « À propos » — prêt à coller (FR + IT)

*Calqué sur la structure du « Chi Siamo » de GuidaTorino (ce que c'est · l'objectif · qui l'a
créé · pour qui · ce qu'on y trouve · engagement), adapté à l'identité transfrontalière et aux
règles de la charte (rien d'inventé, sources officielles, crédits respectés).*

### 🇫🇷 À propos d'Agenda Sabauda

Agenda Sabauda est l'agenda culturel de l'espace alpin occidental — un territoire sans
frontière qui relie la Savoie et la Haute-Savoie, le Piémont, la Vallée d'Aoste et Nice.
Notre objectif : rassembler en un seul endroit tout ce qu'il y a à faire, à voir et à vivre sur
ces quatre territoires que l'histoire, la langue et la montagne ont toujours reliés.

Né de la conviction que la culture ne s'arrête pas aux frontières administratives, Agenda
Sabaudo recense chaque semaine les expositions, concerts, spectacles, festivals, sagre,
marchés, fêtes traditionnelles, rendez-vous en famille et grands moments sportifs — des
institutions les plus prestigieuses aux plus petites communes de village.

Agenda Sabauda s'adresse à tous : au voyageur de passage pour un week-end comme à l'habitant
qui veut découvrir, ou redécouvrir, ce qui se passe près de chez lui — d'un versant à l'autre
des Alpes. Vous y trouverez, semaine après semaine, une sélection vivante et l'agenda complet
de la période : ce qui commence, ce qui se termine, et ce qu'il ne faut pas manquer ce
week-end.

Nous nous engageons à vérifier nos informations à la source officielle — le lieu, l'organisateur
—, à créditer chaque photographie et à ne jamais publier autre chose que des événements réels,
à venir. Agenda Sabauda est édité par **Cultura Sabauda**, média culturel bilingue de l'espace
alpin occidental.

*Retrouvez sur Agenda Sabauda tout ce qu'il ne faut pas manquer : que faire ce week-end · les
4 territoires · expositions & patrimoine · concerts, spectacles & festivals · gastronomie,
sagre & marchés · en famille.*

### 🇮🇹 Chi siamo — Agenda Sabauda

Agenda Sabauda è l'agenda culturale dello spazio alpino occidentale — un territorio senza
confini che unisce la Savoia e l'Alta Savoia, il Piemonte, la Valle d'Aosta e Nizza. Il nostro
obiettivo: riunire in un unico luogo tutto ciò che c'è da fare, da vedere e da vivere in questi
quattro territori che la storia, la lingua e la montagna hanno da sempre legato.

Nato dalla convinzione che la cultura non si ferma ai confini amministrativi, Agenda Sabauda
raccoglie ogni settimana mostre, concerti, spettacoli, festival, sagre, mercati, feste
tradizionali, appuntamenti per le famiglie e grandi eventi sportivi — dalle istituzioni più
prestigiose ai più piccoli comuni di paese.

Agenda Sabauda si rivolge a tutti: al viaggiatore di passaggio per un weekend come all'abitante
che vuole scoprire, o riscoprire, ciò che accade vicino a casa — da un versante all'altro delle
Alpi. Vi troverete, settimana dopo settimana, una selezione viva e l'agenda completo del
periodo: ciò che inizia, ciò che finisce e ciò da non perdere questo weekend.

Ci impegniamo a verificare le nostre informazioni alla fonte ufficiale — il luogo,
l'organizzatore —, a citare ogni fotografia e a non pubblicare mai altro che eventi reali e in
programma. Agenda Sabauda è edito da **Cultura Sabauda**, testata culturale bilingue dello
spazio alpino occidentale.

*Ritrovate su Agenda Sabauda tutto ciò da non perdere: cosa fare questo weekend · i 4 territori
· mostre & patrimonio · concerti, spettacoli & festival · gastronomia, sagre & mercati · in
famiglia.*

---

## 5. Inventaire des pages & priorités

| Page | MVP | v2 | Note |
|---|:--:|:--:|---|
| Home (hero + 6 tuiles + Ce week-end + Tour des territoires + En évidence + catégories + newsletter) | ✅ | | Les 3 modules du §2 y sont |
| Aujourd'hui / Ce week-end / Cette semaine | ✅ | | + « Ce week-end × territoire » (×4) |
| Les 10 du week-end (listicle) | ✅ | | URL fixe recyclée, contenu à partager |
| Territoires (×4) | ✅ | | Intro pérenne 150-250 mots |
| Catégories (×11) | ✅ | | Intro pérenne 100-150 mots |
| Croisements cat.×territoire (~12-16) | ✅ | | Le reste = filtres |
| Fiche événement — mode minimal | ✅ | | **Le cas majoritaire** (score 4-6, pas d'article) |
| Fiche événement — mode riche | ✅ | | Score ≥7 enrichis |
| Recherche (overlay + résultats) | ✅ | | Facettes en v2 |
| Newsletter | ✅ | | |
| À propos / Proposer un événement / Contact / Crédits photos / Mentions / Confidentialité | ✅ | | Textes du §4 prêts |
| 404 + RSS publics | ✅ | | |
| Agenda du mois (archives) | | ✅ | |
| Pages villes | | ✅ | Seuil ≥15 événements |
| Vue carte (Leaflet/OSM) | | ✅ | |
| Météo contextuelle fiche | | ✅ | |

---

## 6. Points ouverts (décisions Franck)

1. **Domaine** : `agendasabauda.eu` à réserver — il n'existe pas encore (seul
   `agenda.culturasabauda.eu` existe, pour le backoffice).
2. **6 tuiles** : familles de catégories (ma reco) *ou* mix temporel + territoires ? (§2.1)
3. **Auto-publication du site de volume** : les score 4-6 partent-ils en ligne
   automatiquement, ou passent-ils par une file de relecture ? (question déjà ouverte au
   backlog — impacte le volume affiché dès le lancement).
4. **Tagline de marque** à figer (piste : *« L'agenda des 4 territoires alpins, de Chambéry à
   Turin »*).
```
