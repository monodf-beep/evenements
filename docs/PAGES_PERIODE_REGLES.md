# Le template « Que faire à X aujourd'hui / ce week-end / cette semaine »

**Modèle faisant foi : Chambéry.** Arbitrage de Franck, 2026-09-22 :
*« https://agendasabauda.eu/que-faire-a-chambery/aujourdhui/ doit être un template
pour les autres ! »* Ce document décrit ce template, pour l'appliquer aux
**192 pages hub** (64 villes × 3 périodes, en deux langues).

Règles posées le **2026-09-22**, sur quatre reproches de Franck dans la journée :

> « les liens externes ne sont pas tout le temps utiles, par exemple le lien pour le
> décret Rattazzi, on s'en fout » · « "Les concerts, eux, ne se rattrapent pas" : pas
> du tout utile » · « "Les horaires commandent la journée…" c'est super bateau, toutes
> les villes c'est pareil » · **« on n'est pas le site officiel. S'il change, c'est pas
> à nous la responsabilité. Donc pas de chiffres, pas de choses périssables. »**

Et la question qu'il a posée lui-même, traitée en dernière partie avec des chiffres :
*« si tu es générique, tu ne vas peut-être pas ressortir, alors que ces pages sont
quand même vachement importantes »*.

---

## 1. Ce que la page doit faire, et rien d'autre

Un visiteur arrive de Google avec une question précise : **qu'est-ce qu'il y a à X
aujourd'hui ?** La page doit y répondre en trois secondes. Le texte n'est pas là pour
raconter la ville : il est là pour dire au lecteur **ce qu'il va trouver dessous, et
où ça se passe**.

La ville se raconte dans le **guide** (`/que-faire-a-annecy/`), qui est fait pour ça.
Les pages de période, non.

## 2. Rien de PÉRISSABLE — on nomme, et on renvoie

**C'est la règle la plus importante, et celle qui coûte le plus cher quand on l'oublie.**
Ces pages sont écrites une fois et restent en ligne des années. Un tarif, un horaire ou
un jour de fermeture recopié dedans devient faux sans que personne le sache — et il
devient faux sur 192 pages à la fois, qu'aucun humain ne relira.

Donc :

- **jamais un prix**, un horaire d'ouverture, un jour de fermeture, une gratuité datée,
  une consigne d'exploitation (« dernière entrée 45 minutes avant ») ;
- **on nomme le lieu et on renvoie à SON site**, qui est responsable de ses propres
  horaires : « un billet commun les relie » + le lien, jamais « il coûte 8 € ».

**La frontière n'est pas « chiffre ou pas chiffre ».** Une date d'histoire ne périme
jamais, et c'est justement elle qui distingue une page des 191 autres. Chambéry en
porte quatre — le 10 décembre 1838, 1834, de 1502 à 1578, le XIXe siècle — et pas un
seul chiffre périssable. Ce qui périme, c'est ce qui décrit **l'exploitation** d'un
lieu, pas son histoire.

> ⚠️ **Écrit le matin où je l'ai violée.** Franck avait rejeté une phrase creuse ; j'ai
> cru bien faire en la remplaçant par des faits vérifiés à la source (tarifs, horaires,
> jour de fermeture des musées d'Annecy), et j'ai publié les six pages. Sa réponse :
> « on n'est pas le site officiel ». **Remplacer du vide par du périssable, ce n'est pas
> corriger, c'est déplacer la dette** — et la déplacer vers quelque chose qu'on ne saura
> plus vérifier.

Contrôle mécanique : `scripts/verif_texte_hub.perissable`, avec sa contre-épreuve dans
`tests/test_texte_hub_perissable.py` — dont les cas qui doivent PASSER sont les dates
d'histoire de Chambéry.

## 3. Générique dans la FORME, précis dans les NOMS PROPRES

C'est la règle qui résout la tension entre « très générique » et « 192 pages qui ne
doivent pas être des copies ». Franck, le 22/09 : *« il faut être générique, mais tout
en proposant quand même un mini contenu, pour que au niveau SEO ce soit intéressant. »*

- **les tournures peuvent se répéter** d'une ville à l'autre : « la scène nationale
  porte le théâtre et la danse », « le marché prend les rues du centre ». Un gabarit de
  phrases, c'est voulu ;
- **les noms propres doivent différer**, et ce sont EUX le contenu : la salle, le musée,
  le marché, le quartier, la rivière, les communes voisines.

Autrement dit, on ne cherche pas 192 récits. On cherche **un gabarit de phrases et une
liste de lieux par ville**.

## 4. Peu de noms propres, mais choisis — et jamais un organe d'État

Franck, sur la première version d'Aix-les-Bains, phrase par phrase : *« trop de nom de
place de nom de théâtre »*. La règle 3 dit juste « les noms propres doivent différer » —
elle ne dit pas combien. Le premier jet d'Aix en citait onze en quatre paragraphes :
trois théâtres, deux ports, une place, un arc, un hôtel de ville, une préfecture, un
département, un lac hors du territoire. Aucun n'était faux. Ensemble, ils rendaient la
page illisible — une liste déguisée en prose, exactement ce que la règle 3 essaie
d'éviter par la forme sans l'interdire par le fond.

**La correction : choisir, pas tout garder.** Un lieu culturel par paragraphe, pas trois.
Le nom qui reste doit porter un détail (« à l'italienne, en velours rouge »), pas
seulement exister dans la phrase. Un fait sans détail qui l'accroche à la mémoire est un
candidat à la coupe, même vrai, même vérifié.

**Et jamais un organe d'État comme source ou comme acteur de la phrase.** Sur la même
relecture : *« ne pas parler d'organe administratif : préfecture »*. « La préfecture de
la Savoie consacre une question entière à démentir la formule » a disparu du texte — pas
parce que le fait était faux, mais parce que nommer l'administration qui le dit ne sert à
rien au lecteur et alourdit la phrase d'un acteur de plus. Ça ne contredit pas la règle 5
ci-dessous sur « selon l'office de tourisme » : un office de tourisme est un organisme de
promotion, pas un échelon de l'État — la distinction porte sur préfecture, département,
mairie-comme-source, pas sur toute attribution à un tiers.

**Et une comparaison reste DANS l'espace sabaudo.** Le premier jet d'Aix sortait du
territoire pour dire que le lac du Bourget n'était pas le plus grand de France (comparé
au lac d'Hourtin, en Gironde) — un fait vrai, mais qui oblige à nommer un lieu hors
périmètre pour le démontrer. Franck : *« on va dire que c'est l'un des plus grands lacs
de l'espace sabauda, on reste dans cet espace là. »* La version qui reste : « un des plus
grands lacs naturels de l'espace sabaudo », vérifiable sans quitter les quatre
territoires. Une affirmation qui n'a besoin que de comparaisons internes est toujours
préférable à une qui en demande une externe.

## 5. L'histoire a sa place, mais sans appareil de notes

> ⚠️ **Cette règle disait d'abord l'inverse, et c'était une erreur de ma part.** J'avais
> écrit « pas d'histoire, pas d'érudition » et supprimé tout le chapitre historique
> d'Annecy. Franck : *« Je ne t'ai pas demandé d'enlever le chapitre historique. Je t'ai
> juste demandé de ne pas mettre l'URL sur Rattazzi. Et tu peux dire qui était
> Rattazzi. »* J'avais transformé un reproche sur un LIEN en une interdiction de SUJET.

Un chapitre d'histoire a sa place : il distingue la page, il donne au lecteur une raison
de rester, et c'est la matière du site. Ce qui n'a pas sa place, c'est **l'appareil de
notes** : le lien qui prouve, la référence d'archive, le numéro de décret.

La bonne façon de traiter un fait historique ici : **le dire en clair et nommer les
gens**. « Urbano Rattazzi, ministre de l'Intérieur des États de Savoie, découpe le
royaume en provinces » vaut mieux qu'un lien vers le portail des archives. Le lecteur
apprend quelque chose au lieu d'être renvoyé ailleurs.

Le fact-checking reste dû : la source se vérifie avant d'écrire, elle ne se cite pas
dans le texte. Et quand une affirmation vient d'un tiers, Chambéry montre la tournure
à employer : **« selon l'office de tourisme »**, dans le fil de la phrase.

## 6. Les liens externes : une adresse que le lecteur VOUDRAIT ouvrir

Un lien externe se justifie s'il mène quelque part d'utile **au visiteur qui prépare sa
sortie** : la salle, le musée, l'office de tourisme. C'est aussi lui qui porte le
périssable à notre place (règle 2).

**Jamais un lien qui sert à prouver une affirmation.** Si un fait a besoin d'une source
pour être crédible sur une page d'agenda, c'est qu'il n'a pas sa place sur cette page.

Ordre de grandeur : **deux à quatre liens externes**, tous vers des lieux ou des
institutions.

> ⚠️ **Un 200 ne prouve pas qu'une page existe.** Le lien « les marchés hebdomadaires »
> d'`annecy.fr` figurait dans les SIX pages d'Annecy et rendait 200 — parce que le site
> de la mairie est une application JavaScript qui répond 200 à tout, y compris à ses
> propres 404. Mesuré le 22/09 : son API rend `"Page non trouvée"`, et le sitemap de la
> mairie ne contient aucune page marchés. **Pour un site en JavaScript, contrôler l'API
> ou le titre rendu, jamais le seul code HTTP.** C'est la règle 1 du CLAUDE.md dans un
> autre costume.

## 7. Pas de phrases-commentaires

« Les concerts, eux, ne se rattrapent pas. » n'apprend rien à personne.

> ⚠️ **Le test qui figurait ici était faux, et il avait explicitement béni la phrase que
> Franck a rejetée.** Il disait : *« une phrase générique qui porte une information
> ("les musées ouvrent le matin") reste ; une phrase générique qui ne porte qu'un ton
> part. »* Or « les musées ouvrent le matin, les salles en fin d'après-midi » est vrai
> des 192 villes : ça ressemble à une information, ça n'en est pas une.

**Le bon test, mécanique : une phrase doit pouvoir être FAUSSE ailleurs.**

Si elle reste vraie en remplaçant le nom de la ville par n'importe quel autre, elle
n'apprend rien au lecteur d'Annecy — quelle que soit sa tournure affirmative. Elle part,
ou elle gagne un nom propre.

Corollaire, appris le même jour : **une phrase qui ne survit au test que grâce à un
chiffre périssable ne survit pas** (règle 2). Le remplacement acceptable est un NOM
PROPRE, pas un tarif.

## 8. La forme, mesurée sur le modèle de Chambéry

| | valeur |
|---|---|
| mots | 330 à 450 |
| chapitres `<h2>` | 4 |
| expressions en gras | 4 à 5, jamais sur un nom propre, un lieu, une date ou un chiffre |
| phrase la plus longue | sous 20 mots |
| clé exacte | 3 fois, dont une dans le premier `<h2>` |
| `<!--more-->` | après le chapeau, qui passe AU-DESSUS de la liste des événements |
| liens internes | vers les deux pages sœurs, plus « LIRE AUSSI » vers le guide et le territoire |
| données périssables | **zéro** |

Et un piège mortel, payé le 22/09 : **le shortcode `[cs_hub_ville …]` doit rester en fin
de contenu.** C'est lui qui affiche la liste des événements. Les 66 octets d'une page
vierge ne sont pas du vide : ils sont cette ligne. Je l'ai supprimé des six pages
d'Annecy, qui sont restées quarante minutes en ligne sans aucun événement.

Contrôle mécanique avant publication : `scripts/verif_texte_hub.py`.

## 9. Le gabarit, chapitre par chapitre

Ce que fait Chambéry, et ce qu'on reproduit ville par ville :

1. **chapeau** (3 phrases) : la clé exacte, ce que la page réunit, « la liste se refait
   chaque matin, au rythme des fiches publiées ». Puis `<!--more-->` ;
2. **`<h2>` n° 1** : la clé exacte + deux repères de la ville (« du Thiou aux quais »,
   « de la fontaine des Éléphants aux arcades »). Dessous : les salles nommées, les
   musées nommés, le marché, avec leurs liens ;
3. **`<h2>` n° 2** : le chapitre distinctif — histoire, architecture, une légende
   démentie, une spécialité. C'est lui qui fait que la page n'est pas une copie ;
4. **`<h2>` n° 3** : l'alentour — le lac, les massifs, les communes voisines, ce qui
   revient chaque année (un festival, une foire) ;
5. **`<h2>` n° 4** : « Le reste de la semaine » — les deux pages sœurs en lien, puis la
   ligne « LIRE AUSSI : le guide de la ville · le territoire » ;
6. **le shortcode**, seul, en dernier.

---

## 10. Le SEO : ce que la prose peut faire, et ce qu'elle ne peut pas

**Ce que Search Console dit, sur 90 jours, des pages hub elles-mêmes :**

| requête | position | clics |
|---|---|---|
| `annecy ce weekend` | **57** | 1 |
| `que faire a annecy ce week end` | **52,4** | 0 |
| `aosta eventi` · `eventi aosta` · `manifestazioni aosta` | 45 à 49 | 0 |
| `oggi ad asti` | 34,1 | 0 |
| `que faire à albertville aujourd'hui` | 16,9 | 0 |
| `mentone oggi` | 9,4 | 1 |
| **`événement albertville aujourd'hui`** | **1,0** | 1 |
| `cosa fare questo weekend` | 5,6 | **0 sur 27 impressions** |

Deux enseignements, et aucun ne porte sur le style :

1. **Sur la requête large, la page est à la page 5 de Google.** « que faire à Annecy ce
   week-end » est tenu par l'office de tourisme, les grands agendas et Facebook. Aucune
   qualité de prose ne fait passer de la position 52 à la 5 ;
2. **Sur la requête étroite, la page est première.** « événement albertville
   aujourd'hui » : position 1. Là où peu de sites répondent, le nôtre répond.

**Donc la prose n'est pas le levier.** Les leviers, dans l'ordre :

- **l'indexabilité.** Mesuré le 22/09 : **58 des 192 pages hub sont en `noindex`**, et
  **6 des 10 pages qui ont un texte** en font partie — les six d'Annecy, écrites le jour
  même. Un texte sur une page en `noindex` ne peut rien rapporter. C'est la première
  chose à regarder avant d'écrire quoi que ce soit ;
- **la fraîcheur de la LISTE**, pas du texte. Ce qui fait revenir Google sur ces pages,
  c'est que les événements changent ;
- **le titre et la meta**, qui portent la date et le compte et se remettent à jour seuls.
  `cosa fare questo weekend` est en position 5,6 avec 27 impressions et **zéro clic** :
  ça, c'est un problème de titre, pas de contenu ;
- **l'image mise en avant**, mesurée à +7 points Yoast sur ces pages (19/09).

**Ce que la prose fait quand même**, et pourquoi on en écrit : elle empêche la page
d'être vue comme vide, elle donne au lecteur une raison de rester le temps de lire la
liste, et elle porte les noms propres qui distinguent 192 pages les unes des autres.
C'est utile. Ce n'est pas ce qui décide du classement.

**Conséquence pratique** : écrire court et générique n'est pas un renoncement SEO, c'est
l'usage juste de l'effort. Le temps gagné sur la prose va à l'indexation, aux titres et
à la fraîcheur, qui eux se mesurent.
