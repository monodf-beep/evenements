# Écrire une page « Que faire à X aujourd'hui / ce week-end / cette semaine »

Règles posées le **2026-09-22**, après la rédaction de Chambéry puis d'Annecy, et
sur trois reproches de Franck sur la page d'Annecy :

> « les liens externes ne sont pas tout le temps utiles, par exemple le lien pour le
> décret Rattazzi, on s'en fout » · « "Les concerts, eux, ne se rattrapent pas" : pas du
> tout utile » · « dans ces pages, il faut être très générique ».

Il a ajouté la vraie question : *« si tu es générique, tu ne vas peut-être pas ressortir,
alors que ces pages sont quand même vachement importantes »*. Elle est traitée en
dernière partie, avec des chiffres.

---

## 1. Ce que la page doit faire, et rien d'autre

Un visiteur arrive de Google avec une question précise : **qu'est-ce qu'il y a à X
aujourd'hui ?** La page doit y répondre en trois secondes. Le texte n'est pas là pour
raconter la ville : il est là pour dire au lecteur **ce qu'il va trouver dessous, et où
ça se passe**.

La ville se raconte dans le **guide** (`/que-faire-a-annecy/`), qui est fait pour ça.
Les pages de période, non.

## 2. Générique dans la FORME, précis dans les NOMS PROPRES

C'est la règle qui résout la tension entre « très générique » et « 192 pages qui ne
doivent pas être des copies ».

- **les tournures peuvent se répéter** d'une ville à l'autre. « Les musées ouvrent le
  matin, les salles en fin d'après-midi » vaut pour Annecy comme pour Albertville, et
  ce n'est pas un défaut : c'est vrai ;
- **les noms propres doivent différer** : la salle, le musée, le marché, le quartier.
  C'est ce qui distingue une page d'une autre, pour le lecteur comme pour Google.

Autrement dit, on ne cherche pas 192 récits. On cherche **un gabarit de phrases et une
liste de lieux par ville**.

## 3. Pas d'histoire, pas d'érudition

Le décret Rattazzi n'a rien à faire sur une page « aujourd'hui ». Ni la fondation de la
ville, ni les comtes, ni les toponymes anciens. Ce sont de bonnes matières — **pour le
guide**.

Test : si le paragraphe serait encore vrai dans dix ans et ne parle pas de ce qu'on peut
faire cette semaine, il est au mauvais endroit.

## 4. Les liens externes : une adresse que le lecteur VOUDRAIT ouvrir

Un lien externe se justifie s'il mène quelque part d'utile **au visiteur qui prépare sa
sortie** : la salle, le musée, l'office de tourisme, la page des marchés de la mairie.

**Jamais un lien qui sert à prouver une affirmation.** Si un fait a besoin d'une source
pour être crédible sur une page d'agenda, c'est qu'il n'a pas sa place sur cette page.
C'est la différence entre un lien utile et une note de bas de page déguisée.

Ordre de grandeur : **deux à quatre liens externes**, tous vers des lieux ou des
institutions. Vérifier qu'ils répondent en 200 avant de publier — la règle du dépôt vaut
ici comme ailleurs.

## 5. Pas de phrases-commentaires

« Les concerts, eux, ne se rattrapent pas. » n'apprend rien à personne. C'est une
remarque de rédacteur, pas une information.

**Le test, mécanique :** une phrase qui reste vraie si on remplace le nom de la ville par
n'importe quel autre **et** qui n'apporte aucun nom, aucun horaire, aucun lieu, saute.
Une phrase générique qui porte une information (« les musées ouvrent le matin ») reste ;
une phrase générique qui ne porte qu'un ton part.

## 6. La forme, mesurée sur le modèle de Chambéry

| | valeur |
|---|---|
| mots | 380 à 480 |
| chapitres `<h2>` | 4 |
| expressions en gras | 4 à 5, jamais sur un nom propre, un lieu, une date ou un chiffre |
| phrase la plus longue | sous 20 mots |
| clé exacte | 3 fois, dont une dans le premier `<h2>` |
| `<!--more-->` | après le chapeau, qui passe AU-DESSUS de la liste des événements |
| liens internes | vers les deux pages sœurs, plus « LIRE AUSSI » vers le guide et le territoire |

Et un piège mortel, payé le 22/09 : **le shortcode `[cs_hub_ville …]` doit rester en fin
de contenu.** C'est lui qui affiche la liste des événements. Les 66 octets d'une page
vierge ne sont pas du vide : ils sont cette ligne.

Contrôle mécanique avant publication : `scripts/verif_texte_hub.py`.

---

## 7. Le SEO : ce que la prose peut faire, et ce qu'elle ne peut pas

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
