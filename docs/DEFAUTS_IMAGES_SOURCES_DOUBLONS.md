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

---

## Le Vélotour de Chambéry : ce n'était pas une anomalie (2026-08-18)

**Je cherchais un défaut là où le site faisait ce qu'on lui avait demandé.**

La fiche 1917 est publiée, française, avec son occurrence, `as_deplacement` à 8
pour le 30 août : éligible sur tous les critères, et pourtant absente de toute
la page Savoie. J'avais éliminé six pistes sans trouver.

La cause est le **snippet 126**, `CS - Exclusion editoriale (as_exclu)`, créé le
2026-08-03 à la demande de Franck pour les contenus liés aux unités militaires
de montagne, 13e BCA côté français, Alpini et ANA côté italien. Le Vélotour
ouvre les portes du 13e BCA. **Une seule fiche du catalogue porte ce drapeau, et
c'est celle-là.**

Le mécanisme fonctionnait correctement : `posts_where` la retire des listes,
`template_redirect` renvoie 404 sur son permalien.

### Le vrai défaut, lui, était ailleurs

**Elle restait au sitemap.** Google était donc invité sur une URL que le site
refuse volontairement, et le contrôle de santé du pipeline la signalait en
critique chaque jour depuis le 16 août.

Correctif ajouté au snippet 126, filtre `wpseo_exclude_from_sitemap_by_post_ids`,
vérifié présent dans Yoast 28 avant de s'en servir. Sauvegarde de l'ancien code
dans `cs_bk_snippet126_20260818`. Après vidage du cache Yoast :
`tribe_events-sitemap.xml` répond 200, 158 URLs, la fiche n'y est plus.

> **Une exclusion éditoriale doit valoir sur les trois surfaces à la fois :** les
> listes, l'accès direct, et ce que l'on déclare aux moteurs. Deux sur trois ne
> suffisent pas.

### Deux erreurs de méthode à retenir

**Chercher un bug avant de chercher une décision.** Six pistes techniques
éliminées alors qu'un `grep as_exclu` sur les snippets donnait la réponse en une
requête. Devant un contenu qui ne sort pas, lire d'abord ses métas et les
comparer à une fiche témoin.

**Vérifier sur le bon fichier.** J'ai d'abord interrogé
`tribe_events-sitemap1.xml`, `2` et `3`, qui n'existent pas : trois zéros
rassurants qui ne prouvaient rien. Le sitemap réel est
`tribe_events-sitemap.xml`, sans numéro, et l'index le dit.

---

## Neuf fiches françaises publiées sous l'étiquette italienne (2026-08-18)

Parti chercher des slugs mal traduits, trouvé plus grave.

**Neuf fiches déclarées italiennes étaient écrites en français**, titre et corps.
Sur la 6405, 75 marqueurs français contre 7 italiens en 377 mots. Un lecteur
piémontais ouvrant la section italienne tombait sur neuf pages en français.

**Huit des neuf n'avaient aucune jumelle française** : il n'existait donc aucune
version française de ces événements, tous piémontais ou valdôtains.

> **À ne pas confondre avec un défaut général.** 126 des 244 fiches publiées
> n'ont pas de jumelle, toutes langues confondues. L'absence de jumelle est un
> état du catalogue. Ce qui était propre à ces neuf, c'est **le décalage entre
> la langue déclarée et la langue écrite**.

### Correction retenue

Décision de Franck : **rebasculer en français**, plutôt que traduire ou
dépublier. Aucun texte inventé, la page devient exacte immédiatement, et la
version italienne viendra par le pipeline avec passage au panel. Conforme au
non-négociable « aucune publication autonome ».

Huit fiches basculées : 6405, 6445, 6373, 7455, 7548, 7552, 7598, 7648.
Sauvegarde complète, langue, URL et groupe de traduction, dans
`cs_bk_langue9_20260818`. Les huit répondent 200.

**La 732 a été laissée de côté** : elle a une jumelle française (2232), la
basculer aurait mis deux fiches françaises dans le même groupe Polylang. C'est
une vraie traduction jamais faite, doublée d'un quasi-doublon de la 2232.

### Ce que fait l'ancienne URL

Elle ne redirige pas : `/it/evenement/<slug>/` continue de répondre 200. Mais
elle **déclare le canonique vers la nouvelle adresse**, vérifié sur le HTML
servi. Le signal est correct pour les moteurs, qui consolideront. Une 301 serait
plus propre, elle n'est pas nécessaire.

### Deux restes à traiter

**Slug italien sur page française**, l'inverse du défaut d'origine, sur 6445 et
7455. Changer un slug change une URL : c'est une décision, pas une réparation.

**Un nom de site tiers dans une URL** : la 6445 porte
`...-il-grand-continent-summit-valledaostaglocal-it`. Le nom de la source a fini
dans notre slug. À corriger avec le point précédent.

---

## Chaque version dans sa langue : le reste du lot (2026-08-19)

Règle posée par Franck : le français quand le français est choisi, l'italien
quand l'italien est choisi. Les noms propres d'institutions et d'événements se
citent tels quels, comme le prévoit le vault.

### Les résumés de hubs respectaient déjà la règle

Mesure sur les 232 hubs : **zéro écart**.

> **Mon premier détecteur en avait signalé quatorze, tous faux.** Il comptait
> « la » et « le » comme français alors qu'ils sont aussi italiens, et il
> comptait les mots français contenus dans les noms propres, comme
> « Maison **des** Jeux Olympiques ». Un détecteur de langue doit retirer les
> noms propres et n'utiliser que des mots-outils non ambigus.

### Les fiches, elles, étaient en écart

L'audit du snippet 130 tenait la liste : **17 fiches déclarées italiennes,
rédigées en français**. Quinze n'avaient aucune jumelle, deux en avaient une.

Décision de Franck de la veille appliquée telle quelle : **les 15 sans jumelle
sont rebasculées en français**. Sauvegarde `cs_bk_langue17_20260819`.
Indexables Yoast reconstruits dans la foulée, sauvegarde
`cs_bk_yoast_indexable17_20260819`, zéro permalien resté en `/it/`.

**732 et 7610 sont laissées** : elles ont une jumelle française (2232 et 2255),
les basculer mettrait deux fiches françaises dans le même groupe Polylang. Ce
sont de vraies traductions jamais faites.

Après passage, l'audit tombe de **17 à 2**.

### Ce que cet épisode apprend

**L'audit avait déjà tout trouvé.** Ses listes `langue_it_fr` et `doublons`
contenaient les fiches et les paires que j'ai redécouvertes en enquêtant, dont
6373+7223 et 6405+7197. Le rapport partait sur Slack depuis le 18 août.

> **Lire le rapport avant d'enquêter.** Un audit qui tourne tous les jours et que
> personne ne dépouille coûte autant qu'il rapporte.

Reste ouvert : **33 signalements de vocabulaire proscrit**, dont six pages
institutionnelles (À propos, Aujourd'hui, Où manger, Chi siamo, Aoste, Vallée
d'Aoste) et la fiche Collontrek 2026 qui en cumule sept à elle seule.

---

## Le vocabulaire proscrit : 33 signalements traités (2026-08-19)

### Le tri d'abord, la correction ensuite

**Cinq signalements sur trente-trois n'étaient pas des fautes.** L'audit repère
le mot, pas le sens. « Le versant sud de la Mandallaz » et « le Col d'Èze répété
par deux versants différents » sont de la topographie ; le vault proscrit
*versant* comme métaphore de limite, pas comme flanc de montagne. De même,
« les frontières contemporaines » dans une fiche sur Gaza ne parle pas de notre
espace.

Ils sont inscrits dans `cs_doctrine_audit_ignore_vocab`, l'option prévue pour
ça, format `array('terme' => array(ids))`. Ils ne reviendront plus.

> **Corriger un signalement sans le lire, c'est abîmer un texte juste.**

### Ce qui a été corrigé

| Page ou fiche | Avant | Après |
|---|---|---|
| Aujourd'hui (929) | les Alpes franco-italiennes | l'espace sabaudo |
| À propos (933) | des Alpes franco-italiennes | de l'espace sabaudo |
| Vallée d'Aoste (2861) | un bilinguisme franco-italien toujours vivant | une région bilingue à statut spécial, terre de langue française et de langue savoyarde |
| Chi siamo (2170) | da un versante all'altro delle Alpi | nello spazio sabaudo |
| Aoste (2468) | …, de part et d'autre des Alpes. | … (clause retirée) |
| Forte di Bard (3737) | le versant savoyard et le versant piémontais · espace alpin occidental | la Savoie et le Piémont · arc alpin occidental |
| Barbara Tutino (7578) | sur le versant piémontais | du côté piémontais |
| Marché au Fort (6805), Anni '90 (7217) | al confine con il Piemonte | al limite provinciale con il Piemonte |
| Niccolò Fabi (3749) | la chanson d'auteur transalpine | la chanson d'auteur italienne |
| Salone Auto (6405, 7197) | constructeurs historiques transalpins | constructeurs historiques italiens |
| Cosmojazz (2207), OSR (2299) | in Alta Savoia | in Savoia (prov. Annecy) |
| Turin / Gaza (7552) | espace alpin occidental | arc alpin occidental |

`Alta Savoia` méritait deux passages : le terme vivait dans la **méta description
Yoast** pour l'une et dans le **post_excerpt** pour l'autre, jamais dans le corps.
Un audit de vocabulaire doit lire tous les champs publiés, pas seulement le corps.

Sauvegardes : `cs_bk_vocab_20260819`, `cs_bk_metadesc_2207`, `cs_bk_excerpt_2207`.

### Résultat

| | Avant | Après |
|---|---|---|
| Vocabulaire proscrit | 33 | **12** |
| Fiches concernées | 17 | **1 paire** |
| Langue déclarée fausse | 17 | 2 |
| Doublons | 7 | 4 |

### Les 12 restants sont une seule fiche, et elle demande un arbitrage

**Collontrek 2026 (1920 fr / 3761 it)** cumule *transfrontalier*, *frontière*,
*frontalier*, *francoprovençal*, *versant*, *côté national*, *confine*.

La course relie **Bionaz, en Vallée d'Aoste, à Arolla, en Valais**. Or la règle
du vault porte sur *notre* espace, et le Valais n'en fait pas partie : le vault
admet explicitement « franco-italien » pour Lyon-Milan ou Paris-Rome, qui ne sont
pas nos territoires. Décrire une limite réelle entre Vallée d'Aoste et Valais
n'est peut-être pas la faute que la règle vise.

**Un point n'est pas ambigu :** « le dialecte francoprovençal » doit devenir
« la langue savoyarde », la règle du 3 août ne souffre que les noms propres.
