# Images sans rapport, sources qui ne prouvent rien, doublons d'affichage

*Constaté le 2026-08-17 sur la production. Tout ce qui suit a été mesuré en base ou
sur le HTML servi, rien n'est déduit. Trois défauts, une cause commune pour deux
d'entre eux.*

---

## 1. Une affiche de bibliothèque illustre une étape cycliste

**Le cas.** La fiche « Tour de l'Avenir 2026 : l'étape finale relie Strambino au
Lago Serrù » (6380 en français, 7113 en italien, publiées) est illustrée par
l'affiche d'un tout autre événement : « Compiti insieme », l'aide aux devoirs de la
bibliothèque communale de Strambino, dont l'affiche annonce le 6 septembre **2025**.
Même commune, événement sans rapport, mauvaise année.

**La cause.** `as_source_officielle_url` vaut `https://www.comune.strambino.to.it/`,
c'est-à-dire **la page d'accueil de la commune**, pas la page de l'événement. Une
page d'accueil municipale affiche ce que la commune met en avant ce jour-là. Toute
image récoltée là est sans rapport avec l'événement par construction : ce n'est pas
un raté ponctuel du collecteur, c'est la conséquence mécanique du choix de l'URL.

**Ce qui rend le défaut invisible.** La pièce jointe (7110) porte le nom de fichier
`tour-de-l-avenir-2026-strambino-lago-serru-carte.jpg`, le titre
« Tour de l'Avenir 2026 - Strambino - Lago Serrù » et **le même texte alternatif**.
Le fichier, le titre et l'alternative décrivent tous les trois l'événement, quand
les pixels montrent une affiche de bibliothèque. Rien dans WordPress ne permet de
s'en apercevoir. La seule trace survivante de l'origine réelle est
`as_image_original`, et elle pointe ici vers un actif `cms2.turismotorino.org`,
c'est-à-dire encore un autre site.

**Ce qu'il faut changer dans le pipeline.**

1. **Ne pas récolter d'image quand l'URL de source n'a pas de chemin.** Si
   `parse_url($u, PHP_URL_PATH)` rend `''` ou `/`, la page est une accueil : aucune
   image ne doit en être tirée, et la fiche doit tomber sur le repli visuel par
   territoire (`cs_fallback_visual()`), qui est honnête.
2. **Ne jamais dériver le texte alternatif du seul titre de l'événement.** L'alt
   doit décrire l'image, pas la fiche. À défaut de savoir ce qu'elle montre, laisser
   l'alt vide vaut mieux que le remplir d'une affirmation fausse.
3. **Conserver le nom de fichier d'origine** dans la description de la pièce jointe,
   en plus de `as_image_original`. Renommer d'après l'événement détruit la seule
   preuve exploitable a posteriori.

---

## 2. Plus d'une source publiée sur deux est une page d'accueil

**La mesure.** 178 fiches publiées portent une `as_source_officielle_url` non vide.
**93 d'entre elles, soit 52 %, ont pour source une page d'accueil**, dont le chemin
est vide ou réduit à `/`.

Échantillon : `albertville.fr`, `montmelian.com`, `moutiers.org`, `tnn.fr`,
`opera-nice.org`, `festivaldelriso.it`, `lasaintours.it`,
`chateaudemontrottier.com`, `lacitadellevsm.fr`.

**Pourquoi c'est grave, au delà des images.** Une page d'accueil ne confirme ni une
date, ni un lieu, ni un tarif, et son contenu change chaque semaine. Une source qui
ne prouve rien aujourd'hui prouvera encore moins dans six mois. Cela vide de leur
sens les trois garde-fous qui exigent de relire la page source (année présente dans
le texte, URL qui répond 200, quantièmes encadrant le mois) : ils s'exécuteront sur
une page qui ne parle pas de l'événement.

**Ce qu'il faut changer.** Refuser d'écrire une `as_source_officielle_url` sans
chemin. Si l'enrichissement n'a pas trouvé la page de l'événement, laisser le champ
vide et le signaler, plutôt que d'y mettre le domaine par défaut. Une fiche sans
source est un manque connu ; une fiche dont la source est une accueil est un manque
déguisé en preuve.

---

## 3. Le même événement trois fois sur une page territoire

**Le cas.** La page `/explore/comte-de-nice/` sert trois entrées qui parlent de la
même production d'Orlando à l'Opéra de Nice. Vérifié sur le HTML servi : le titre de
la fiche 745 y apparaît **deux fois**.

| Fiche | Langue | Titre | Dates | Score | Source |
|---|---|---|---|---|---|
| 745 | fr | À l'Opéra de Nice, la folie d'Orlando revisite le mythe de l'Arioste | 29/09 au 06/10 | 7 | `opera-nice.org/agenda/orlando/` |
| 2340 | **it** | Orlando de Haendel à l'Opéra Nice Côte d'Azur | 29/09 au 06/10 | 7 | `opera-nice.org/` |
| 917 | fr | Face à face : Orlando | 29/09 | 5 | `opera-nice.org/` |

**Trois causes distinctes, à ne pas confondre.**

1. **Aucune déduplication entre les blocs d'une même page.** Le bloc de tête et la
   liste de droite interrogent le catalogue chacun de leur côté et servent tous deux
   la fiche 745. Il faut que les blocs d'une page partagent une liste d'identifiants
   déjà servis, comme le fait `cs-agenda-list-shared.php`.

2. **Un événement satellite est catalogué comme une fiche autonome.** « Face à
   face : Orlando » (917) est une rencontre autour de la production, pas une
   représentation. Elle a sa propre date, son propre score, et rien ne la relie à
   745. Pour le lecteur, c'est un doublon ; pour la base, ce sont deux objets sans
   lien. Il faut un rattachement, du satellite vers l'événement principal, et ne
   servir le satellite que si le principal n'est pas déjà affiché.

3. **Une fiche étiquetée italienne porte un titre français.** 2340 est bien la
   traduction Polylang de 745, mais son titre est
   « Orlando de Haendel à l'Opéra Nice Côte d'Azur ». Le catalogue italien sert donc
   du français. C'est la famille de défaut déjà connue, la fiche de traduction créée
   avant que la traduction existe.

---

## 4. Le contrôle quotidien surveille moins de mots que la doctrine

**Découvert en corrigeant les guides le 2026-08-17.** Le snippet 130, qui envoie le
rapport doctrine quotidien, surveille huit termes : transfrontalier, frontière,
frontalier, patois, francoprovençal, arpitan, langues régionales, espace alpin,
plus leurs équivalents italiens.

**Le lexique en proscrit davantage**, et ceux qui manquent au contrôle sont
précisément ceux qui sont passés en production :

| Terme proscrit par le lexique | Surveillé par le snippet 130 |
|---|---|
| **versant / versante** | non |
| transalpin, transalpino, oltralpe | non |
| côté français, côté italien | non |
| de part et d'autre | non |
| franco-italien (entre nos territoires) | non |
| haut-savoyard, néo-savoyard | non |

**Ce que cette lacune a laissé passer**, corrigé le 2026-08-17 :

- 2422 et 2423, « Festivals de l'été en Savoie », un **titre de section**
  « du jardin au versant italien » et la phrase « du versant français aux vallées
  italiennes voisines », qui cumulent le mot proscrit et la nationalisation de nos
  territoires ;
- 2420 et 2421, « Expositions à Turin », « présent sur les deux versants » ;
- 2419, « Sagre del Piemonte », « Sul versante della Savoia ».

Remplacements retenus, tirés du lexique : **deçà et delà les monts** pour l'axe
Savoie vers Piémont, et le nom de la province (« de la Maurienne au val de Suse »)
partout ailleurs.

**Ce qu'il faut changer.** Aligner la liste du snippet 130 sur le lexique, et non
sur un extrait de celui-ci. Une liste partielle donne l'assurance d'un contrôle
sans en donner la couverture, ce qui est pire qu'une absence de contrôle.

---

## 5. Ce que ces quatre points ont en commun

Dans les quatre cas, un champ **paraît** renseigné : une image existe, une source
existe, une traduction existe, un contrôle tourne. Le défaut n'est jamais un vide,
c'est un remplissage qui ne tient pas ses promesses. Un vide se voit et se compte ;
un faux positif de complétude, non.

D'où la règle à retenir pour les correctifs : quand une valeur ne peut pas être
établie, **laisser le champ vide et le signaler** plutôt que le remplir d'un défaut
plausible. Le repli visuel par territoire, la source absente, l'alt vide sont des
manques honnêtes. L'affiche d'une bibliothèque sous le nom d'une étape cycliste ne
l'est pas.
