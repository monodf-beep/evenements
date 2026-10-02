# Les lieux payés au modèle : la mesure dit non

**Question posée par Franck le 2026-08-18** : « toutes les sources donnent les informations,
c'est juste que des fois c'est mal cherché ». Traduite en mesure : les 454 lieux payés au
modèle étaient-ils trouvables gratuitement ?

**Réponse : non, pas par les signaux les moins chers.** Ce document existe pour que
personne — moi le premier — ne reparte sur cette piste en croyant l'avoir trouvée.

## Ce que j'avais annoncé, et qui était faux

J'avais écrit, après avoir vu 15 % de lieux gratuits contre 59 % de dates : « la dépense
qui rapporterait le plus n'est pas de brancher la couche payante, c'est de mieux lire les
pages qu'on télécharge déjà ». C'était une inférence, pas une mesure. Elle ne tient pas.

## Le chiffre

`scripts/audit_lieux_gratuits`, sur 454 fiches encore devant nous dont le lieu vient d'un
appel payant :

| signal | propose | d'accord | **en désaccord** | gain net |
|---|---|---|---|---|
| titre | 57 | 53 | **4** | +49 |
| url | 43 | 33 | **10** | +23 |
| repertoire | 0 | 0 | 0 | 0 |
| soeur | 0 | 0 | 0 | 0 |

**Au moins un signal tombe juste sur 67 fiches sur 454 — 15 %.** Les quatre cinquièmes
restants, aucun signal gratuit ne les atteint.

## Pourquoi les deux signaux qui marchent un peu marchent MAL

Les désaccords ne sont pas du bruit, ils ont deux causes nettes, et les lire a plus appris
que le tableau :

**1. L'adresse de la page donne la ville de l'ÉDITEUR, pas celle de l'événement.**

    [47] url propose « Annecy » — le lieu réel est Hauteville-sur-Fier
    [49] url propose « Annecy » — le lieu réel est Lovagny (château de Montrottier)
    [51] url propose « Annecy » — le lieu réel est Fillière

L'office de tourisme du Grand Annecy publie des sorties dans tout son territoire. Le signal
`url` ne trouve donc pas le lieu : il trouve qui en parle. C'est structurel, pas
corrigeable par un réglage.

**2. Des noms de communes sont aussi des mots courants ou des noms de saints.**

    [473] « La Saint-Ours 2026 » → la commune de Saint-Ours, alors que c'est Aoste
    [2113] « L'école Montessori fête ses 10 ans » → la commune d'École (Savoie)

C'est exactement la faute du 2026-08-08 sur la fiche 3588, où un marqueur « français »
venait du NOM PROPRE de l'événement. Un dictionnaire de communes appliqué à du texte libre
ramassera toujours ces collisions.

## La conclusion, et ce qu'elle interdit

**Ne pas brancher ces signaux.** 67 lieux économisés sur 454, au prix d'un risque de ville
fausse en ligne sur les autres, n'est pas un bon échange : une ville fausse se voit sur la
carte du site et demande une correction humaine, alors qu'un appel de modèle coûte une
fraction de centime.

**Et surtout : le modèle gagne ses 454 appels.** Sur ce champ-là, il fait un travail que le
code ne sait pas faire — distinguer le lieu de l'événement de la ville de celui qui
l'annonce. C'est la réponse à « pourquoi on a besoin d'agents », et elle est l'inverse de
ce que je pensais ce matin.

## Ce que la mesure n'a PAS testé, et qu'il ne faut pas confondre avec un verdict

Les quatre signaux éprouvés n'utilisent que ce qui est déjà en base — aucun ne relit la
page. Restent donc ouverts, et non mesurés :

- le bloc `<address>` ou les coordonnées de contact de la page ;
- une adresse postale en texte libre dans le corps de l'article ;
- la page de l'organisateur plutôt que celle de l'agrégateur.

Un « non » sur quatre signaux n'est pas un « non » sur tous. Mais il faudra les mesurer
avant de les écrire, pas l'inverse.

## Deux trouvailles annexes, qui valent plus que le sujet principal

**`config/lieux_villes.json` ne contient qu'UNE entrée.** Ce registre est censé accumuler
les arbitrages « ce lieu-là est dans cette ville-là » et éteindre les signalements
correspondants. Après des semaines, il en a un. Ce n'est pas un fichier qui sert : c'est un
fichier qu'on a oublié de remplir — encore un dispositif dont personne n'est le rouvreur.

**403 fiches ont un `venue_source` VIDE.** Sur les 1378 fiches du périmètre, 403 n'ont
jamais été examinées par `venues.py` — ni gratuitement, ni au modèle. C'est presque autant
que les 454 qu'on cherchait à économiser, et ça ne coûte rien de comprendre pourquoi. Le
sujet n'est peut-être pas « payer moins pour les 454 », mais « pourquoi 403 ne sont jamais
passées ».
