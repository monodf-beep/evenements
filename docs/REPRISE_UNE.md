# « À la une » — où on en est, et par quoi reprendre

État au **2026-08-17, fin de journée**. Ce document existe parce que la session qui a fait
ce travail ne sera plus là demain, et que trois quarts de la journée sont passés à
re-découvrir des choses déjà sues.

---

## Le point de blocage, et il n'y en a qu'un

**On ne sait pas encore si le méta `as_une_now` arrive sur WordPress.**

Tout le reste est prêt. La prochaine action est une VÉRIFICATION, pas une écriture — et
tant qu'elle n'est pas faite, republier ou changer un tri ne sert à rien.

### L'action à faire en premier, demain

La fiche 4421 (Tour de l'Avenir, post WP **6380**) a été republiée seule à 16h26. Elle
doit porter `as_une_now = 13`. Le vérifier via Novamira :

> Sur le post WordPress 6380, lis la méta `as_une_now` dans postmeta et donne-moi sa
> valeur exacte. Puis compte combien de posts au total portent cette clé. Ne modifie rien.

- **13** → l'allowlist est bonne, enchaîner sur « la suite » ci-dessous ;
- **vide ou absente** → `'as_une_now'` n'est pas (ou mal) ajouté au `$allowed` du snippet
  `cs-publish` **en ligne**. C'est ça qu'il faut régler avant tout le reste ;
- **autre valeur** → le calcul et la publication divergent : à creuser avant d'aller plus
  loin.

---

## Pourquoi cette vérification, et pas la confiance dans le journal

Le lot de la nuit du 16 au 17 a rendu **« 156 publié(s), 0 échec(s) »**. Le lendemain
matin, l'inventaire WordPress comptait **zéro** fiche portant `as_une_now`.

`publisher_as` envoyait bien la valeur. Le tableau `$allowed` de `cs-publish.php` ne la
connaissait pas, `update_post_meta` n'a donc jamais été appelé — **un méta inconnu est
jeté en silence**, sans rien changer au code HTTP.

Un lot « 0 échec » et un lot dont la donnée n'arrive pas sont **indistinguables vus depuis
le journal du publieur**. C'est pour ça que la vérification passe par le site, jamais par
la sortie du script (règle 1).

⚠️ Le même incident, exactement, s'était produit le 2026-08-12 avec `as_deplacement_now`.
Un commentaire avait été écrit dans `cs-publish.php` pour que ça n'arrive plus ; il n'a
rien empêché, parce qu'un commentaire n'est lu que par qui ouvre déjà le bon fichier.
D'où `tests/test_contrat_meta_as.py`, qui compare les clés envoyées par le publieur au
`$allowed` et échoue sur la moindre qui ne traverse pas.

**Rappel qui vaut pour tout ce dossier :** `deploy/wordpress/cs-publish.php` n'est PAS le
code qui tourne. Le vrai vit dans **Code Snippets**, en base, et sa version en ligne
contient du code absent du dépôt. Une clé s'y ajoute **ligne à ligne**, jamais en écrasant
le snippet (voir `docs/DEPLOIEMENT_WORDPRESS.md`).

---

## La suite, une fois la méta confirmée

**1. Reprendre le lot complet.** Celui de 16h11 a été coupé par une déconnexion SSH à
90 fiches sur 166. Le relancer détaché, pour qu'une coupure ne le tue plus :

```
cd ~/evenements && nohup .venv/bin/python -m scripts.publish_batch_as \
    --update --skip-media --cap 200 > /tmp/lot.log 2>&1 &
tail -20 /tmp/lot.log      # pour suivre, même après reconnexion
```

**2. Recompter** : environ 24 fiches doivent porter `as_une_now`, valeurs entre 6 et 14.

**3. Alors seulement, le tri.** Et c'est là qu'est le piège principal.

### Ce que l'inventaire Novamira a établi le 17/08

Il n'y a **aucune requête JetEngine Query Builder** derrière « À la une ». Les quatorze
blocs de l'accueil sont sans `query_id`. La sélection et le tri sont calculés en PHP par
le **snippet 44**, « CS · Anti-doublon home (offsets sections dynamiques) », qui impose
ses identifiants au bloc via `post__in`.

Tri actuel, un `usort` à quatre niveaux :

1. `as_home_override === 'featured'` en tête ;
2. `as_home_order` croissant, vide relégué ;
3. `as_home_score` décroissant, vide traité comme −1 ;
4. `_EventStartDate` croissant.

Filtres : `_EventStartDate >= maintenant`, exclusion de `as_home_override = 'excluded'`,
`as_enrich_status = 'enriched'` strict, et `post__not_in` des sections prioritaires.
Territoire : conditionnel (`cs_territoire_actif`). Langue : explicite, `'lang' => $lang`,
cache indexé par langue. Vivier de 60 fiches, 6 allouées à `ala-une`, **3 affichées**.

> ⚠️ **CE TRI SERT TOUTES LES SECTIONS DE L'ACCUEIL**, pas seulement « à la une ».
> `as_une_now` est vide sur la grande majorité des fiches : l'appliquer au classement
> général mettrait « ce week-end », « les 7 prochains jours » et « en évidence » à égalité
> sur du vide. **Le changement doit être limité à l'allocation `ala-une`**, en laissant
> `as_home_score` gouverner le reste.

`as_home_override` est en place mais **inerte** : trois fiches seulement le portent, une
seule avec une valeur (`excluded`), aucune avec `featured`. Ne pas y toucher.

---

## Pourquoi `as_une_now` plutôt que `as_home_score`

Capture d'écran de Franck, 17/08 : « pilate en "à la une" ??? les 2 autres, ça fait des
semaines qu'ils sont à la une, c'est des événements fin septembre. »

`as_home_score` mesure la **qualité du rendu** (panel + source officielle + visuels) et
reste figée au jour de la rédaction. Un cours de pilates bien illustré y battait un
festival, et rien ne savait qu'on était à cinq semaines de la date.

`as_une_now` (`utils/une.py`) combine l'**intérêt intrinsèque** de l'événement et son
**imminence** : vide si la fiche n'a pas sa place en une, sinon 6 à 14 — jamais 0, jamais
négatif. Un filtre numérique `> 0` suffit donc à écarter les vides.

Une fiche entre en une quand elle **ouvre** bientôt ou quand elle **ferme** bientôt ; pas
pendant les quatre mois qui séparent les deux. Le banc de mesure est
`scripts/audit_une.py`, qui rejoue les règles à J+0/7/14/21 par versant linguistique.

---

## Ce qui reste ouvert, et qui demande un arbitrage humain

- **La Savoie n'a qu'UNE fiche** qui passe le plancher d'intérêt 6. À 4 elle en aurait
  trois — mais ramènerait le cours de pilates, exactement ce qui a déclenché la demande.
  Ce n'est pas un problème de seuil, c'est un problème de sources.
- **Deux traductions du mauvais côté du sélecteur de langue** (fiches 3495 et 3509), sur
  47 examinées : `.venv/bin/python -m scripts.audit_langue_polylang` les liste, avec
  l'adresse REST à ouvrir pour vérifier l'état réel.
- **MonumenTO (fiche 308)** s'est débloquée toute seule au lot de 16h11 et a été publiée
  (nouveau post 7750). Ça règle l'orphelinat de sa traduction 3509 — **à revérifier** une
  fois le lot complet passé.
