# « À la une » — état, et ce qui reste

Dernière mise à jour : **2026-08-18, fin de journée**.

---

## FAIT — la section fonctionne

Deux jours après la capture d'écran de Franck (« pilate en "à la une" ??? les 2 autres, ça
fait des semaines qu'ils sont à la une »), la vitrine tourne. Ce qu'elle sert au 18/08 :

| | versant FR | versant IT |
|---|---|---|
| 1 | 6380 · **13** · Tour de l'Avenir, étape finale | 7113 · **13** · Tour de l'Avenir |
| 2 | 6311 · **11** · Treno storico Torino-Lanzo-Ceres | 7209 · **11** · Treno storico |
| 3 | 6386 · **10** · Fiera del Peperone | 7518 · **10** · Filarmonica della Scala |

La chaîne complète, dans l'ordre où elle a été montée :

1. `utils/une.py` — la note : intérêt intrinsèque RELEVÉ par l'imminence. Vide si la fiche
   n'a pas sa place, sinon 6 à 14. Une une annonce une OUVERTURE ou signale une DERNIÈRE
   CHANCE, jamais le milieu d'un parcours de quatre mois ;
2. `scripts/audit_une.py` — le banc de mesure, qui rejoue les règles à J+0/7/14/21 par
   versant linguistique et montre ce qu'elles ÉCARTENT ;
3. `publisher_as` pousse `as_une_now` ; l'allow-list du snippet 6 l'accepte (ajoutée le
   18/08 — sans elle WordPress la jetait en silence) ;
4. `refresh_deplacement` la RECALCULE tous les jours à 10h45, en même temps que
   `as_deplacement_now`. Sans ce rouvreur la note serait gelée au jour de la publication,
   et le correctif aurait recréé la plainte de départ ;
5. snippet 44, mode `une_now` : exclut les métas vides du vivier (exclusion, jamais
   relégation — sinon le tri retombe sur la date), trie en numérique décroissant,
   `$max_reuse = 0` pour ne pas recombler la section.

**Le mode `une_now` ne sert QUE `ala-une`.** `evidence` et `evidence-bottom` restent sur
`vedette` — les toucher les aurait mis à égalité sur du vide.

### Décisions prises, et pourquoi

- **La une ne se sert PAS en premier** dans le plan d'allocation. Servir `ala-une` avant
  `weekend` lui donnerait 6377 et 7295 (notés 11) à la place d'une fiche notée 10 — un
  point d'écart — mais retirerait deux cartes sur six au week-end, alors que ce sont
  justement des événements du week-end. Un lecteur qui prépare son samedi les cherche là.
- **Moins de trois candidates → moins de trois cartes.** Une une comblée par l'ancien
  classement ramènerait le cours de pilates, qui est le problème de départ.
- **`as_une_now` commande, pas `cs_une_note`** (snippet 140). Cette dernière dérive de
  `as_deplacement`, qui inclut `accessibilite_langue` — un critère fait pour décider si on
  traverse une frontière. Sur une home lue dans sa propre langue il n'a aucun sens.

### ⚠️ LA RÈGLE QUI PRIME SUR TOUTES LES AUTRES (Franck, 2026-08-18)

> « On ne doit pas vouloir changer les règles du nombre d'éléments affichés, les
> événements vont arriver, on aura assez de contenu. »

**On ne calibre pas les seuils sur la pénurie du moment.** Le catalogue est en train de
grandir, et il a cessé de grandir CETTE SEMAINE seulement, à cause de la coupure réseau
(`docs/INCIDENT_RESEAU_2026-08-18.md`). Une règle taillée pour le stock d'aujourd'hui sera
fausse dans un mois, et personne ne pensera à la desserrer.

Ce que cette consigne interdit, nommément :

- **baisser `UNE_INTERET_MIN` de 6 à 4** parce que la Savoie n'a qu'une candidate. Ça
  ferait revenir le cours de pilates, qui est le problème de départ. La Savoie manque de
  SOURCES, pas de seuil ;
- **réduire le nombre de cartes** d'une section parce qu'elle est courte aujourd'hui ;
- **combler une section** avec un classement de repli pour qu'elle paraisse pleine. Une
  rangée à deux cartes est honnête ; une rangée remplie de médiocre ment.

Et ce qu'elle décide, pour la suite : quand une section paraît figée, **le levier n'est
pas de rétrécir le vivier** (raccourcir l'horizon écarterait du contenu, et viderait la
Vallée d'Aoste qui en produit peu). C'est de faire jouer la DATE dans le classement à
vivier constant.

---

## CE QUI RESTE

### Bloqué par le réseau

Depuis le 18/08 ~13h, **le VPS ne joint plus `agendasabauda.eu`**. Les mesures, la liste
complète de ce qui est à l'arrêt, la phrase pour le ticket et l'ordre de reprise sont dans
**`docs/INCIDENT_RESEAU_2026-08-18.md`** — un seul endroit, pour que les deux documents ne
se contredisent pas.

En attendant, `scripts/export_une_now.py` contourne : le VPS calcule, un autre canal écrit.
265 métas ont été posées comme ça le 18/08. Le scraping, les dates, les lieux,
l'enrichissement et l'évaluation continuent normalement ; seules les publications sont à
l'arrêt.

### À reprendre quand le réseau revient

- **Terra Madre / post 2190.** La version française est en ligne ; la version italienne
  n'existe plus nulle part — le post italien 1931 a été écrasé par le texte français puis
  mis à la corbeille le 03/08. L'article italien est toujours en base (fiche 2507) : il
  faut le republier sur une page neuve et relier la paire.
- **`verifier_doublons_publies --en-ligne`** : il refuse de conclure tant qu'il ne peut pas
  sonder WordPress, et il a raison de le dire.

### Le sujet suivant : l'aiguillage par langue

Trois occurrences en deux jours, ce n'est plus une série d'accidents :

- fiches 3495 et 3509, traductions françaises servies côté italien ;
- Terra Madre : le texte français a écrasé les DEUX pages, dont l'italienne ;
- post 7490 : titre français, étiquette italienne, doublon de 7518 sur le même concert.

Commencer par une MESURE — combien de fiches portent une étiquette de langue qui ne
correspond pas à leur texte — avant d'écrire quoi que ce soit.
`scripts/audit_langue_polylang.py` en couvre une partie, mais seulement les traductions ;
il faudra l'élargir aux originaux.

### Plus petit

- `cs_une_note` (snippet 140) gouverne désormais `evidence`, alors qu'elle a été écrite
  pour la une. Effet de bord du 18/08 au matin, à trancher.
- `$sizes['ala-une']` est passé à 1 le 17/08 ; le prélèvement, lui, est à 3. Si
  l'affichage n'en montre qu'une, c'est là qu'il faut regarder.
- La Savoie n'a qu'UNE fiche qui passe le plancher d'intérêt 6. Descendre à 4 en donnerait
  trois, mais ramènerait le cours de pilates. C'est un problème de sources, pas de seuil.


---

## Les pièges rencontrés, parce qu'ils se représenteront

**Un lot « 0 échec » ne prouve pas que la donnée soit arrivée.** Le lot du 17/08 a rendu
« 156 publié(s), 0 échec(s) » et WordPress n'a rien reçu : l'allow-list `$allowed` du
snippet 6 ne connaissait pas la clé, et un méta inconnu est jeté EN SILENCE, sans rien
changer au code HTTP. Le même incident avait eu lieu le 12/08 avec `as_deplacement_now`,
et un commentaire avait été écrit pour l'empêcher — il n'a servi à rien, parce qu'un
commentaire n'est lu que par qui ouvre déjà le bon fichier. D'où
`tests/test_contrat_meta_as.py`, qui compare les clés envoyées par le publieur à
l'allow-list et échoue sur la moindre qui ne traverse pas.

**Le fichier du dépôt n'est pas le code qui tourne.** `deploy/wordpress/cs-publish.php`
est une copie ; le vrai vit dans Code Snippets, en base, et la version en ligne contient
du code absent du dépôt. Une clé s'y ajoute LIGNE À LIGNE, jamais en écrasant le snippet.

**Une valeur datée doit avoir quelqu'un qui la recalcule.** C'est la règle 3 appliquée aux
valeurs vivantes, et elle était déjà écrite en tête de `refresh_deplacement.py` — je ne
l'avais pas lue avant d'ajouter une méta datée de plus.

**« Il manque une entrée » ne dit pas OÙ elle s'est perdue.** L'export annonçait 266 fiches
et rendait 265 entrées ; j'ai accusé ma recopie, ajouté une empreinte de transport et fait
recommencer deux tours de vérification. La faute était à la source : deux fiches portaient
le même `wp_post_id_as` et l'une écrasait l'autre dans le dictionnaire. Les deux hypothèses
étaient à une commande l'une de l'autre.

**Il existait DEUX fonctions de langue dans ce dépôt, et j'ai pris la mauvaise.**
`effective_lang` privilégie l'article — or `enrich` rédige en français par défaut, donc
elle classait français tout événement italien enrichi. La seule qui compte est celle qui
ÉCRIT la langue sur WordPress : `publisher_as._lang`. Un rapport sur l'état du site doit
appeler le code du site, pas un cousin qui lui ressemble.

**Vérifier au bon endroit.** `/?p=<id>` répond 404 pour tout `tribe_events`, en ligne ou
non. Seule l'API REST par NUMÉRO sépare les trois états. J'ai envoyé Franck sur la
mauvaise adresse et il a vu un 404 qui ne voulait rien dire.

**Raisonner sur le principe sans regarder les fiches.** J'ai recommandé de servir la une
avant le week-end au nom de « une vitrine ne doit pas hériter du reste ». Les deux fiches
concernées étaient des événements DU week-end : les déplacer n'aurait servi personne. Le
gain se chiffrait à un point d'écart, le coût à deux cartes sur six.
