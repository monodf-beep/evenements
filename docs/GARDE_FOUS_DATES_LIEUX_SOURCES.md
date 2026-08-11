# Garde-fous : dates, lieux et sources

Écrit le 2026-08-12 après avoir remonté à la cause sept fiches dont l'information était
contredite par leur propre source. Chaque mécanisme ci-dessous a été **établi en comparant la
base au HTML réellement servi par la source**, pas déduit. Les URL ont été rechargées le
2026-08-12 et les extraits cités viennent de ces pages.

Le sujet n'est pas cosmétique : ces erreurs sont celles qu'un lecteur constate lui-même. Il se
déplace un jour où il n'y a rien, ou il cherche une forteresse dans la mauvaise commune.

---

## 1. Les sept cas, et ce qui les a produits

### 2334 · Nice Classic Festival · l'édition précédente recopiée entière
- Source `niceclassiclive.com` : « 21 juillet au 09 août **2026** ».
- Fiche : du **22/07/2025** au **09/08/2025**. Créée le 2026-07-20.
- Mécanisme : les dates de l'édition **2025** ont été reprises telles quelles. Le jour de début
  diffère aussi (22 contre 21), donc ce ne sont pas les dates de la page officielle décalées,
  ce sont celles d'une autre page ou d'un cache.
- Le signal qui aurait suffi : **une fiche créée le 20 juillet 2026 avec une date de début au
  22 juillet 2025**, soit douze mois dans le passé. Un événement ne commence pas avant d'être
  collecté.

### 2319 · Ah ! La Belle Saison · année supposée, dates fabriquées
- Source `theatredescollines.annecy.fr` : la page ne mentionne **que 2025**, « belle saison 2025,
  7ème édition », toutes ses dates sont en juin et juillet 2025.
- Fiche : du **01/06/2026** au **31/07/2026**.
- Mécanisme : l'année a été supposée être l'année courante faute d'être lue, et les bornes sont
  le **premier et le dernier jour d'un mois**, ce qui ne se lit sur aucune page : elles ont été
  calculées, pas extraites.
- Le signal qui aurait suffi : **l'année de l'événement n'apparaît nulle part dans la source.**

### 2289 · Guitare en scène · un jour perdu à la fin
- Source `guitare-en-scene.com` : « du 14 au **18** Juillet 2026 ».
- Fiche : du 14 au **17**.

### 2265 · Festa di San Savino · le même jour perdu à la fin
- Source `comune.ivrea.to.it` : « Dal 4 all'**8** luglio 2026 ».
- Fiche : du 4 au **7**.
- Mécanisme commun à 2289 et 2265 : sur les deux seuls cas multi-jours vérifiés, la borne de fin
  est **exclusive au lieu d'inclusive**. Deux sur deux, ce n'est plus un accident.
- 2265 porte en plus deux faits que la source ne contient pas, une foire équine et un défilé de
  chars. Invention à l'enrichissement, non rattrapée par le panel.

### 3729 · Forte di Bard · l'erreur est dans la fiche lieu, pas dans l'événement
- Les dates de l'événement sont justes (9 juillet 2026, conformes à la source).
- La **fiche lieu 208**, « Forte di Bard, Piazza d'Armi », porte `_VenueCity = Aosta`. La
  forteresse est à **Bard**, à 40 km d'Aoste.
- **Trois événements** pointent sur cette fiche lieu et héritent tous de l'erreur. Corriger un
  événement ne corrigerait rien : c'est l'enregistrement partagé qu'il faut reprendre.
- Mécanisme : la ville a été renseignée depuis l'entité administrative de rattachement, la
  Vallée d'Aoste, au lieu de la commune.
- Défaut annexe : le titre de la fiche lieu contient un **tiret demi-cadratin** stocké en entité
  (`&#8211;`), proscrit par la charte, plus un `&rsquo;` brut.

### 864 · Château d'Introd · une source de 2023 pour un événement de 2026
- Source : `grand-paradis.it/it/news/**2023**/visite-guidate-notturne-...`
- Fiche : événement au 19/07/2026.
- Mécanisme : un communiqué de 2023 a servi de source à une édition 2026. La page est une
  archive d'actualités qui cite toutes les années de 2010 à 2026, donc un contrôle « l'année
  figure-t-elle dans la page » ne l'aurait pas attrapée.
- Le signal qui aurait suffi : **l'URL contient une année, 2023, différente de celle de
  l'événement.**

### 909 · Opéra de Nice · une source qui n'a jamais été ouverte
- Source `opera-nice.org/agenda/chopin/**20260918**-1800/` : **404** au 2026-08-12.
- Mécanisme probable : l'URL a la forme `AAAAMMJJ-HHMM`, entièrement dérivable des données de
  l'événement lui-même. Tout indique qu'elle a été **construite par motif plutôt que relevée**.
  À défaut, elle n'a jamais été rechargée depuis.
- Le signal qui aurait suffi : **une URL de source qui ne répond pas 200 au moment où on
  l'écrit.**

---

## 2. Les causes communes

1. **Rien ne compare la sortie à la source.** Le pipeline extrait, enrichit, publie. À aucun
   moment il ne relit la page pour vérifier que ce qu'il a écrit s'y trouve.
2. **L'année courante sert de valeur par défaut** quand la page n'en donne pas.
3. **La borne de fin est traitée comme exclusive**, sur les deux cas multi-jours vérifiés.
4. **La ville d'un lieu vient de l'entité administrative**, pas de la commune, et l'erreur se
   propage à tous les événements qui partagent la fiche lieu.
5. **Une URL de source peut être fabriquée** et n'est jamais rechargée.
6. **Le verdict de panel « revise » est enregistré sans motif** (8 fiches connues : 6297, 7225,
   6373, 7223, 2255, 6405, 7197, 6433), donc le seul filet posé en aval est inexploitable.

---

## 3. Les garde-fous, par ordre de coût

Tous sont mécaniques : ils se calculent sans jugement, et chacun aurait attrapé au moins un des
sept cas. Ils bloquent la **publication**, pas la collecte : une fiche recalée part en brouillon
avec son motif, elle n'est pas perdue.

| # | Contrôle | Attrape | Coût |
|---|---|---|---|
| 1 | Date de début **antérieure à la date de collecte** | 2334 | Trivial |
| 2 | **L'année de l'événement figure dans le texte de la source** | 2319 | Faible |
| 3 | **L'URL de source ne contient pas une autre année** que celle de l'événement | 864 | Trivial |
| 4 | **L'URL de source répond 200** au moment de l'écriture, et est recontrôlée périodiquement | 909 | Faible |
| 5 | Les **numéros de jour** encadrant le nom du mois dans la source correspondent aux bornes stockées | 2289, 2265 | Moyen |
| 6 | La **ville d'une fiche lieu est une commune existante**, et ne contredit pas un nom de commune contenu dans le titre du lieu | 3729 | Moyen |
| 7 | Un verdict de panel `revise` **sans motif** est un échec de traitement, pas un verdict | les 8 fiches | Faible |

Deux contrôles de forme à ajouter au même endroit, déjà constatés ailleurs :

- **Aucun tiret cadratin ni demi-cadratin** dans un titre, y compris de fiche lieu, y compris
  stocké en entité HTML (`&#8212;`, `&#8211;`, `&mdash;`, `&ndash;`).
- **Aucune entité HTML brute** dans un titre (`&rsquo;`, `&amp;` en double échappement).

### Où les poser

Le contrôle 1 et le contrôle 3 sont assez simples pour être posés **des deux côtés** : dans le
pipeline avant publication, et dans l'audit quotidien WordPress (snippet 130) comme filet.

Les contrôles 2, 5 et 6 supposent de relire la source, donc ils appartiennent au **pipeline**,
au moment de l'enrichissement, quand la page est déjà en mémoire.

Le contrôle 4 doit tourner **en continu** côté WordPress : une source valide le jour de
l'écriture peut mourir ensuite, comme celle de 909.

> **Rappel qui vaut pour tout ce document.** Corriger les sept fiches dans WordPress ne tient
> que jusqu'à la republication suivante. Sans ces contrôles en amont, les mêmes erreurs
> reviendront à l'identique. C'est le même constat que pour le rejet des événements
> professionnels, `CHARTE_EDITORIALE.md` §3 bis.
