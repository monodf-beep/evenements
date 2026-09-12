# Ce que le brief du 12 août affirme, et ce que la base dit

Écrit le 2026-08-13, avant d'écrire la moindre ligne de correctif. Le brief
(`docs/GARDE_FOUS_DATES_LIEUX_SOURCES.md`, repris dans `BACKLOG.md`) demande sept
corrections « à la source ». Il annonce lui-même avoir été « vérifié en base ou sur le HTML
servi, pas déduit ». Il l'a été **côté WordPress**. Côté pipeline, **cinq griefs sur sept ne
tiennent pas**, et deux d'entre eux auraient abîmé la production s'ils avaient été
implémentés tels quels.

Ce document existe parce que la même erreur a déjà coûté une matinée le 2026-08-11 :
*un défaut de forme ne se voit pas dans le code, il se voit dans les RÉSULTATS*
(`CLAUDE.md`, journal des erreurs). Ici, c'est l'inverse et c'est le même piège :
un défaut constaté dans les RÉSULTATS a été attribué à un code qui ne le produit pas.

---

## 1. « La borne de fin est traitée comme exclusive » — **FAUX**

Le grief le plus dangereux du lot : appliqué, il aurait ajouté un jour à la fin de
**toutes** les fiches multi-jours du corpus.

`scripts/dates.py::parse_dates` est **strictement inclusif**. Sur le texte exact des deux
pages officielles citées par le brief :

| Texte donné à `parse_dates` | Rendu |
|---|---|
| « du 14 au **18** juillet » (guitare-en-scene.com) | `2026-07-14` → `2026-07-**18**` |
| « Dal 4 all'**8** luglio 2026 » (comune.ivrea.to.it) | `2026-07-04` → `2026-07-**08**` |

La borne de fin est rendue telle qu'elle est écrite. Le code n'a jamais retiré un jour.

**D'où vient alors le « 14 au 17 » de la fiche 2289 ?** De notre propre matière. La fiche
`events_raw` 1533 porte cette description, collectée sur `74.agendaculturel.fr` :

> « Le Festival Guitare en scène 2026 revient **du 14 au 17 juillet** à Saint-Julien-en-Genevois. »

`parse_dates` a lu 14 → 17 parce que **l'agrégateur écrit 14 → 17**. Le pipeline a
fidèlement transcrit une source fausse. Il n'a jamais ouvert `guitare-en-scene.com`.

Même mécanisme sur 2265 : notre source n'est pas `comune.ivrea.to.it` mais une newsletter
de Turismo Torino, et la fiche 783 porte `date_source='page'`.

**Le vrai défaut n'est pas un décalage d'un jour, c'est qu'on date depuis un agrégateur
sans jamais confronter la page officielle.** C'est exactement le garde-fou (c) que le brief
réclame par ailleurs — donc le brief a raison sur le remède et tort sur la cause.
Fixture de non-régression : `tests/test_bornes_inclusives.py`.

---

## 2. « Faits absents de la source : foire équine, défilé de carrosses, feu d'artifice » — **FAUX**

Le brief parle d'« invention à l'enrichissement, non rattrapée par le panel ». Les trois
faits sont **mot pour mot dans notre source**, la description stockée de la fiche 783 :

> « Festa patronale che combina tradizione e modernità con cerimonie religiose, una storica
> **fiera equina di rilevanza nazionale** e un ricco programma di eventi culturali e
> artistici. Tra gli highlight la **sfilata delle carrozze** e lo **spettacolo pirotecnico**. »

`source_name` : **Turismo Torino e Provincia** — un office de tourisme, pas un blog. Aucune
invention : l'enrichissement a fait son travail sur la matière qu'on lui a donnée.

Le brief a comparé la fiche à `comune.ivrea.to.it`, qui n'est pas la source de la fiche.
Deux sources officielles ne disent pas la même chose du même événement, ce qui est banal —
la commune annonce les dates, l'office de tourisme décrit le programme.

**Pourquoi le garde-fou proposé serait nuisible.** « Aucun fait qui ne figure pas dans la
source » — comprendre *la page officielle* — supprimerait ici du contenu exact et sourcé.
Il frapperait d'abord les fiches écrites depuis un **dossier de presse**, que la charte §5
classe pourtant comme la matière **prioritaire**, au-dessus de la page officielle. Le
contrôle doit porter sur « la matière qu'on a lue », jamais sur « une page choisie après
coup ».

---

## 3. « Événements dupliqués : même festival, même langue, mêmes dates » — **FAUX**

Le brief nomme WP **591** et WP **2319**, « créées le même jour à quinze minutes
d'intervalle ». En base :

| | `events_raw` | WP | `translation_of` | `translated_lang` | collectée |
|---|---|---|---|---|---|
| 591 | 845 | 591 | — | — | 2026-07-01 21:51 |
| 2319 | 3537 | 2319 | **845** | **it** | 2026-07-20 20:49 |

Ce ne sont pas deux doublons : c'est **l'original français et sa traduction italienne**,
liés par `translation_of`. Ni la même langue, ni le même jour, ni quinze minutes — dix-neuf
jours.

Les titres sont identiques parce que la traduction a conservé le **nom propre** du
festival. C'est le piège déjà documenté dans `CLAUDE.md` règle 3 (fiche 3588, « La Rencontre
Valdôtaine », dont le marqueur « français » venait du nom propre), et déjà payé deux fois
dans l'historique de cette branche : *« J'ai averti Franck d'un doublon qui n'en était pas »*
et *« Retirer une fiche traduite sans son jumeau ferait un orphelin »*.

Les deux fiches ont bien été dépubliées le 12/08, mais le second motif du brief (dates
fabriquées, cf. §6 ci-dessous) est le bon ; le motif « doublon » ne l'est pas.

---

## 4. « Verdict de panel `revise` sans motif, rendre le motif bloquant » — **DÉJÀ FAIT**

Corrigé sur cette branche le 2026-08-12, le jour même du brief, dans
`scripts/publisher_as.py::motif_du_panel` — dont le commentaire répond nommément au
diagnostic :

> « Le diagnostic était juste, la cause non : `as_panel_revision` n'est pas un motif, c'est
> un STATUT à trois valeurs — 'aucune', 'appliquée', 'tentée'. Un motif, il n'y en a jamais
> eu sur WordPress. Or il existe, et depuis toujours : chaque persona rend `manques` et
> `note`. Tout ça dort dans `enrich_data`, et `publisher_as` n'envoyait que les chiffres. »

La méta `as_panel_motif` est désormais construite (personas ayant voté la révision
uniquement, dédupliquée) et poussée par `cs-publish.php`. Les 8 ou 12 fiches citées n'ont
donc pas besoin d'un correctif : elles ont besoin d'être republiées.

**Rendre le motif bloquant à l'écriture serait une régression.** Un panel qui refuse de
rendre son verdict quand il n'a pas su formuler de reproche fait disparaître l'information
au lieu de l'expliciter — et rejouerait à l'identique au run suivant sur la même matière,
ce que `CLAUDE.md` règle 3 interdit nommément.

---

## 5. « Rejet des événements professionnels : pas encore dans la notation » — **DÉJÀ FAIT**

`scripts/evaluator.py` porte une **ÉTAPE 1 bis — PUBLIC VISÉ** complète (l. 109-146), avec
le basculement exact que demande la charte : de « le public **peut** assister » à
« à supposer que je n'exerce PAS ce métier, ai-je une raison d'y aller ? », le champ
`public_vise`, et le rejet câblé (`pro` → `statut='rejected'`, score 0, justification
préfixée).

Le piège est traité, et il l'est dans le bon sens : *« NE JUGE PAS SUR LE MOT DU TITRE […]
un filtre sur ces mots viderait une catégorie entière du site »*, suivi des contre-exemples
(salon du livre, café philo, dédicace…). Un pré-filtre gratuit par mots-clés double le
dispositif (`utils/sources.py::is_excluded_event`), avec sa fixture bidirectionnelle
`tests/test_exclusion_pro.py` — laquelle contient déjà un cas-frontière qui **doit passer**
(Salone Auto Torino, grand public, attrapé à tort par « btob » en description).

**Ce qui manquait réellement** : le §3 bis n'était pas dans la charte *de cette branche*.
Porté. Décidia est ajouté aux fixtures comme cas-frontière qui doit être **rejeté**.

---

## 6. Les deux griefs qui tiennent

### a. Bornes de mois fabriquées par la datation LLM — **VRAI**

Fiche 845, `date_source='llm'`, `2026-06-01` → `2026-07-31`. La description dit seulement
« se déroulera **en juin et juillet** ». Aucun quantième n'est écrit nulle part : le modèle
a rendu le premier et le dernier jour des deux mois.

La cause est dans le prompt de `dates.py::_llm_dates`, qui autorise explicitement à déduire
(« Date du jour, pour déduire l'année si absente ») et n'interdit nulle part d'inventer un
quantième. Ce n'est **pas** `_year()`, dont la grâce de 60 jours est documentée et bornée.

### b. Corps tronqués — **VRAI**, et plus large qu'annoncé

Le brief dit « vers 260 caractères, 11 fiches ». Mesuré en base :

- **279 fiches** ont une description de **exactement 255 caractères** — la coupe est celle
  du flux RSS d'`agendaculturel.fr`, pas la nôtre : aucun `[:255]` n'existe dans le dépôt ;
- **40 fiches publiées** ont un corps finissant par une troncature (`…`, `[…]`, « Lire la
  suite »), **dont 19 encore devant nous** au sens de la règle 5.

*Périmètre de ces deux nombres* : lignes `events_raw` avec `wp_post_id_as` non nul ; corps =
`article_md` à défaut `description` ; « devant nous » = `date_event_end` (à défaut
`date_event_start`) ≥ aujourd'hui, ou `recurring`, ou sans date. Toutes ont
`enrich_status IS NULL` : **ce sont des fiches publiées sans avoir jamais été enrichies**,
donc le corps est l'extrait brut de l'agrégateur.

---

## Ce qu'il faut en retenir pour la suite

Le brief se trompe sur cinq causes mais **converge avec la réalité sur le remède** : les
trois garde-fous (a) année dans la source, (b) URL qui répond 200, (c) bornes confrontées à
la page, sont bien les seuls qui auraient attrapé 2334, 2289, 2265, 864 et 909. Ils sont à
poser à l'enrichissement, quand la page officielle est déjà en mémoire.

Un mot sur la méthode, puisque le brief affirme avoir tout vérifié : il a vérifié la fiche
WordPress contre une page officielle, ce qui est juste et utile. Mais **il n'a pas ouvert
`events_raw`**, où se lisent la matière réellement collectée, `date_source`,
`translation_of` et `source_name` — les quatre champs qui expliquent les cinq
requalifications ci-dessus. Un écart entre une fiche et une page n'a jamais dit **par où**
il est entré.
