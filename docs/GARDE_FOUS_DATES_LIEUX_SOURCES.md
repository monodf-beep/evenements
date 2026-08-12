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

### 3729 · Forte di Bard · l'erreur est dans la fiche lieu, et la cause est la duplication
- Les dates de l'événement sont justes (9 juillet 2026, conformes à la source).
- La **fiche lieu 208**, « Forte di Bard - Piazza d'Armi », portait `_VenueCity = Aosta`. La
  forteresse est à **Bard**, à 40 km d'Aoste. Corrigé le 2026-08-12, sauvegarde
  `cs_bk_venue208_ville_20260812`. **Trois événements** en héritaient (209, 631, 3729).
- **Le mécanisme n'est pas celui que j'avais supposé.** J'ai d'abord écrit que la ville venait de
  l'entité administrative de rattachement. Le comptage le dément : il existe **cinq fiches lieu
  pour le même endroit**, et **quatre disent Bard**.

  | Lieu | Titre | Ville | Événements |
  |---|---|---|---|
  | 28 | Forte di Bard | Bard | 40 |
  | 80 | Forte di Bard - Museo delle Fortificazioni | Bard | 0 |
  | 208 | Forte di Bard - Piazza d'Armi | **Aosta** | 3 |
  | 218 | Forte di Bard, Piazza d'Armi | Bard | 3 |
  | 237 | Piazza d'Armi - Forte di Bard | Bard | 4 |

  La cause réelle est donc la **création d'une fiche lieu à chaque variante de libellé**, sans
  déduplication. Une seule des cinq a été mal renseignée, et rien ne l'a rattrapée parce que
  rien ne compare les fiches lieu entre elles. Le garde-fou utile n'est pas « d'où vient la
  ville » mais **« deux lieux dont les titres contiennent les mêmes noms propres sont le même
  lieu, et doivent avoir la même ville »**.

> **Note de méthode.** J'avais aussi écrit que le titre de la fiche lieu contenait un tiret
> demi-cadratin stocké en entité. **C'est faux.** Le titre stocké contient un simple trait
> d'union ; c'est `wptexturize`, filtre natif de WordPress, qui transforme « espace tiret
> espace » en demi-cadratin **à l'affichage**. Je l'avais lu avec `get_the_title()`, qui applique
> les filtres, au lieu de `get_post_field()`, qui ne les applique pas.
> Le défaut existe quand même, mais il est ailleurs et il est plus large : **11 titres**
> d'événements et de lieux contiennent « espace tiret espace » et sont donc tous rendus avec un
> demi-cadratin, proscrit par la charte. Dix sont des fiches lieu. La correction est d'écrire une
> virgule plutôt qu'un tiret dans les titres, pas de désactiver un filtre de WordPress.

### 864 · Château d'Introd · une source de 2023 pour un événement de 2026
- Source : `grand-paradis.it/it/news/**2023**/visite-guidate-notturne-...`
- Fiche : événement au 19/07/2026.
- Mécanisme : un communiqué de 2023 a servi de source à une édition 2026. La page est une
  archive d'actualités qui cite toutes les années de 2010 à 2026, donc un contrôle « l'année
  figure-t-elle dans la page » ne l'aurait pas attrapée.
- Le signal qui aurait suffi : **l'URL contient une année en segment de chemin**, `/2023/`,
  différente de celle de l'événement.
- **Précision acquise en implémentant le contrôle.** Cherchée n'importe où dans l'URL, l'année
  produit des faux positifs : un événement intitulé « Torino 1946-2026 » ou une saison
  « 2025-2026 » se font signaler pour rien. Cherchée **entre deux barres**, elle ne retient que
  le motif d'archive, qui est le vrai symptôme.
- **Et ce n'est un signal, pas un verdict.** Le contrôle remonte aussi trois fiches sourcées sur
  `visitmondovi.it/2020/...` : ce sont des pages permanentes d'office de tourisme, publiées en
  2020, qui décrivent un événement récurrent et ne contiennent **aucune année**. La source est
  légitime, elle ne confirme simplement pas les dates. À traiter comme « dates non confirmées »,
  pas comme « source fausse ».

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
4. **Les fiches lieu se dupliquent à chaque variante de libellé**, cinq pour le Forte di Bard,
   et rien ne compare leurs champs entre elles : une seule mal renseignée contamine tous les
   événements qui la référencent.
4 bis. **Les événements aussi se dupliquent** : « Festival Ah ! La Belle Saison » existait en
   deux fiches, 591 et 2319, même langue, mêmes dates, créées le même jour à quinze minutes
   d'intervalle.
5. **Une URL de source peut être fabriquée** et n'est jamais rechargée.
6. **Le verdict de panel « revise » est enregistré sans motif** (8 fiches connues : 6297, 7225,
   6373, 7223, 2255, 6405, 7197, 6433), donc le seul filet posé en aval est inexploitable.

---

## 3. Les garde-fous, par ordre de coût

> **Le contrôle 1 a été mesuré avant d'être écrit ainsi, et la première rédaction était fausse.**
> Formulé « date de début antérieure à la date de collecte », il signale **94 fiches** sur le
> corpus actuel, en très grande majorité des faux positifs : une exposition longue commence
> légitimement avant qu'on la collecte. Avec le seuil de six mois, il tombe à **5 fiches**, et ce
> sont les bonnes. Un contrôle qui crie sur 94 fiches n'est pas un contrôle, c'est du bruit que
> personne ne lira.
>
> **Deuxième correction, du même jour.** J'avais écrit que 6171 et 6176 portaient une date à
> l'epoch Unix, 1970. C'est faux : leur `_EventStartDate` est **vide**, et c'est `strtotime('')`
> qui renvoie zéro. Deux défauts distincts se cachaient donc derrière un seul compteur. Le
> contrôle les sépare désormais : **fiche sans aucune date** d'un côté (6171, 6176), **début
> antérieur de plus de six mois** de l'autre (2013 publiée, 578 et 6245 en brouillon).

Tous sont mécaniques : ils se calculent sans jugement, et chacun aurait attrapé au moins un des
sept cas. Ils bloquent la **publication**, pas la collecte : une fiche recalée part en brouillon
avec son motif, elle n'est pas perdue.

| # | Contrôle | Attrape | Coût |
|---|---|---|---|
| 1 | Date de début antérieure de **plus de six mois** à la date de collecte | 2334 | Trivial |
| 2 | **L'année de l'événement figure dans le texte de la source** | 2319 | Faible |
| 3 | L'URL de source ne porte pas **une autre année en segment de chemin** (`/2020/`) que celle de l'événement | 864 | Trivial |
| 4 | **L'URL de source répond 200** au moment de l'écriture, et est recontrôlée périodiquement | 909 | Faible |
| 5 | Les **numéros de jour** encadrant le nom du mois dans la source correspondent aux bornes stockées | 2289, 2265 | Moyen |
| 6 | Deux fiches lieu dont les titres partagent les mêmes noms propres **ne peuvent pas avoir deux villes différentes** | 3729 | Moyen |
| 6 bis | Un titre d'événement ou de lieu ne contient **pas « espace tiret espace »**, que `wptexturize` rend en demi-cadratin | 11 titres | Trivial |
| 7 | Un verdict de panel `revise` **sans motif** est un échec de traitement, pas un verdict | les 8 fiches | Faible |

Trois contrôles de forme à ajouter au même endroit, constatés en corrigeant les sept fiches :

- **Aucun tiret cadratin ni demi-cadratin** dans un titre, ni en caractère, ni en entité
  (`&#8212;`, `&#8211;`), ni en « espace tiret espace » que `wptexturize` convertira.
- **Aucun corps ne se termine par une troncature d'agrégateur** : « Leggi di più... », « Lire la
  suite », ou une virgule suivie de points de suspension. Constaté sur 2334 et 2289, dont les
  corps étaient des extraits copiés puis coupés.
- **Aucun fait qui ne figure pas dans la source.** 2265 affirmait une foire équine d'importance
  nationale, un défilé de carrosses et un feu d'artifice ; aucun des douze termes correspondants
  n'apparaît sur la page officielle, qui dit seulement « Festa Patronale di San Savino. Dal 4
  all'8 luglio 2026 ». Le corps a été ramené aux faits vérifiés.

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

---

## 4. Ce qui a été corrigé le 2026-08-12

Chaque correction a été faite après avoir rouvert la source, jamais en recopiant une note.
Toutes ont une sauvegarde en option WordPress.

| Fiche | Correction | Sauvegarde |
|---|---|---|
| Lieu 208 | Ville Aosta corrigée en Bard, héritée par 3 événements | `cs_bk_venue208_ville_20260812` |
| 2334 | Dates 2025 remplacées par 21/07 au 09/08/2026, via `tribe_update_event` pour que la table des occurrences suive. Corps : année, jour de début, nom de l'Académie Internationale d'Été de Nice, et retrait du « Leggi di più... » | `cs_bk_2334_dates_20260812`, `cs_bk_2334_corps_20260812` |
| 2289 | Fin portée au 18/07 conformément à la source. Corps : même date, retrait de la troncature, « Grégory Porter » corrigé en Gregory Porter | `cs_bk_2289_dates_20260812`, `cs_bk_2289_corps_20260812` |
| 2265 | Fin portée au 08/07. Corps ramené aux seuls faits que la source soutient | `cs_bk_2265_dates_20260812`, `cs_bk_2265_corps_20260812` |
| 591 et 2319 | Dépubliées : doublon l'une de l'autre, et dates fabriquées pour une édition 2026 que la source ne documente pas | `cs_bk_belle_saison_statuts_20260812` |
| 864 | Source retirée : communiqué de 2023, dont l'URL ne résout plus que vers l'index des actualités de cette année-là | `cs_bk_sources_annee_20260812` |
| 909 | Source retirée : 404 | `cs_bk_sources_annee_20260812` |

Deux fiches restent sans source, 864 et 909, ce que la charte préfère à une source douteuse.
Elles portent le motif dans la méta `cs_source_retiree_motif`.

**Reste ouvert :** la déduplication des cinq fiches lieu du Forte di Bard, qui touche 50
événements, et celle des titres en « espace tiret espace ». Aucune des deux n'est urgente, les
deux demandent un arbitrage sur les URL et le graphe Yoast avant d'être menées.
