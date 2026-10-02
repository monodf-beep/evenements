# Jev, nœud par nœud — et la question de la complétion

> ⛔ **REMPLACÉ par `docs/TYPESAFE_JEV_CHAINE.md`** (22/09, même jour). Ce passage-ci
> cherchait ce que Jev pouvait REMPLACER ; la bonne question est ce qu'on ne fait PAS
> faute de pouvoir se le payer. Conservé pour ce qu'il dit du dépôt, pas pour ses
> verdicts.
>
> ⚠️ **À lire avec le verdict en deux temps de `docs/TYPESAFE_JEV.md`.** Comme
> SUBSTITUTION à la facture, non : 91 % est hors de portée par construction. Mais la
> substitution n'était pas la question — c'est la MOISSON qui est le sujet, et ce
> passage nœud par nœud ne la regardait pas assez : il classait `scraper_events.py` en
> « CODE, format connu », ce qui est vrai des 92 flux RSS et passe à côté de tout ce
> qu'on ne moissonne pas FAUTE de flux.



Suite de `docs/TYPESAFE_JEV.md` (22/09). Franck, le même jour : « regarde tous les nœuds
du processus et dis si ça peut être intéressant ou pas. J'ai l'impression que ça peut être
vraiment intéressant, surtout pour la partie complétion — que notre site puisse être le
plus complet possible. Mais regarde dans la documentation de cet outil. »

**Statut des chiffres.** Tout ce qui vient de `docs.typesafe.ai` est annoncé par
l'éditeur ; tout ce qui décrit le dépôt est lu dans le code. **Aucun coût réel du dépôt
n'a été mesuré** (le conteneur de session n'a ni `data/` ni `logs/`), et **la question du
français et de l'italien reste entière** — la documentation n'en dit rien.

---

## 1. La complétion : l'intuition est juste, et le motif porte un nom

C'est le résultat principal de cette relecture.

TypeSafe publie un cookbook, *Pre-parsed value extraction*, dont la méthode tient en trois
temps :

1. **une expression régulière volontairement TROP LARGE** ramène tous les candidats
   possibles d'une page (tous les montants, tous les horaires, toutes les adresses) ;
2. **Jev choisit** lequel remplit le rôle demandé, via une question `Choice` dont les
   options sont ces candidats — avec une option `"none"` (« aucun de ceux-ci n'est la
   valeur demandée ») ;
3. la valeur rendue est **l'un des extraits trouvés, recopié sans modification**.

Leur phrase exacte : *« Because TypeSafe only ever chooses among the spans the regex
found, the value you get back is one of those spans, copied unchanged. »* Le modèle **ne
peut pas inventer un chiffre** — ce n'est pas une promesse de prudence, c'est une
propriété de la forme de la question.

**Or `utils/infos_pratiques.py` fait DÉJÀ l'étape 1, et s'arrête volontairement avant
l'étape 2.** Sa docstring dit pourquoi :

> « Des EXTRAITS de la page, jamais une interprétation : la phrase où le prix apparaît,
> telle quelle. […] C'est délibéré — « 12 € » isolé peut être le tarif plein, le tarif
> réduit, le prix d'un catalogue ou celui du parking. La phrase, elle, tranche. »

Ce module a donc été écrit avec, en creux, la question à laquelle Jev répond : *lequel de
ces montants est le tarif de CET événement ?* Elle n'a pas été posée jusqu'ici parce que la
poser à un LLM coûtait trop cher pour un champ accessoire, et parce qu'un LLM peut
répondre « 12 € » sans que ce « 12 » vienne de la page. Les deux objections tombent :
0,042 $ le million de jetons d'entrée, et une réponse qui est forcément un des extraits.

C'est ce qui s'approche le plus, dans ce dossier, d'un gain **de complétude** et pas
seulement de facture. Et ça vise exactement le grief du 11/08 : sur « 454 points à
contrôler », **315 étaient des informations que la source ne publie pas**. La forme
`Choice` + option `"none"` sépare les deux cas que la file confondait — *la page le dit et
on ne l'a pas lu* (à remplir, automatiquement) contre *la page ne le dit pas* (à ne jamais
mettre en file, personne ne peut le vérifier).

Ce qu'il faut dire aussi, pour ne pas vendre plus que ce qu'il y a : **ça ne complète que
ce qui est ÉCRIT sur une page qu'on a déjà téléchargée.** Ça ne va rien chercher — Jev ne
sait pas naviguer, et la recherche web reste à Claude. Le gain porte sur la matière déjà
sous la main et mal exploitée, pas sur de la matière nouvelle.

---

## 2. Les nœuds, un par un

Verdicts : **OUI** (candidat net) · **PARTIEL** (une partie du nœud seulement) ·
**NON** (hors des capacités de Jev) · **CODE** (doit rester déterministe).

### Moisson

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `scraper_events.py` (RSS, HTML) | **CODE** | format connu, `LLM_OU_CODE.md` a raison |
| `moisson_officielle.py` — trouver la page officielle | **PARTIEL** | la recherche web reste à Claude ; le **choix de la bonne page parmi les résultats** est un `Choice` avec option « aucune » |
| `gmail_collect.py` — lire une newsletter | **PARTIEL** | l'extraction est de la génération → reste au LLM. Mais la **cascade SDE** du cookbook s'applique : modèle bon marché extrait, Jev vérifie par nouls (`hallucinated`, `off_target`, `incomplete`), on n'escalade vers le gros modèle que si un noul dépasse 0,7. Annoncé : 78 % de la qualité du modèle haut de gamme à 30 % du coût |
| `gmail_relink.py` — rattacher un mail à une fiche | **OUI** | appariement parmi candidats = `Choice` |

### Dédoublonnage — la question posée explicitement

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `dedupe.py` (heuristique `same_story`) | **CODE + PARTIEL** | le gros reste déterministe et gratuit. Mais le troisième chemin, la **« coïncidence lieu + dates + jeton »** ajoutée le 08/09 (cas Pinocchio WP#6413/WP#8193), **liste sans fusionner** faute de savoir trancher. C'est précisément le résidu ambigu que `LLM_OU_CODE.md` réserve au LLM, et le cookbook *entity alignment* y répond |
| `verifier_doublons_publies.py` | **OUI** | même forme, sur les fiches en ligne |
| `unmerge.py`, `resolve_wp_collision.py` | **CODE** | arbitrage humain, réparation |

Le cookbook *entity alignment* (450 paires de bières, deux catalogues) pose sur chaque
paire **un Score à 3 niveaux** (produits différents / apparentés, peut-être identiques /
même produit) **plus trois nouls factuels** (même nom, même fabricant, même style). Le
routage qui en sort :

```
fusion automatique  40 paires  ( 8,9 %)
file curateur       50 paires  (11,1 %)
laissées non liées 360 paires  (80,0 %)
```

Transposé ici : `Score` « même événement / édition ou déclinaison du même / événements
différents » + nouls « même lieu », « mêmes dates », « même organisateur ». Les trois
sorties existent déjà dans le dépôt (fusionner · signaler à Franck · laisser). **Et c'est
un endroit où l'on ne se trompe pas gratuitement** : une mauvaise fusion corrompt une date
(WP#6798). Donc le niveau du milieu ne fusionne jamais, il notifie.

### Dates — le nœud où il faut se retenir

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `dates.py` — parser un texte en bornes | **NON** | la page des limites de Jev 1.13 range les **comparaisons de dates et d'heures** parmi ses neuf points faibles, et « Jev is not a calculator ». Le parsing reste au code et au LLM |
| `dates.py` — choisir entre plusieurs dates candidates | **PARTIEL** | si le code a déjà extrait deux jeux de bornes, « lequel est celui de l'événement ? » est un `Choice` — pas un calcul |
| `verifier_dates.py`, `audit_annee_date.py`, `utils/confronter.py` | **OUI** | c'est le cookbook *citation check* : `Choice` sur la relation entre la page et la fiche — **soutient / contredit / ne dit rien**. Exactement la forme de `bornes_contre_la_page` (« même début, fin différente »), et le verdict « ne dit rien » est celui qui manque aujourd'hui |

### Lieux

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `venues.py` — extraire lieu + ville | **OUI** | JSON-LD et regex ramènent des candidats, Jev choisit lequel est le lieu de l'événement. Même motif que le tarif |
| `venues_web.py` | **NON** | recherche web |
| `verifier_lieux.py` | **OUI** | confrontation, comme les dates |
| `scripts/perimetre.py` | **CODE** | `config/communes_comte_de_nice.json` fait foi. Une liste ne se devine pas |

### Évaluation

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `evaluator.py` | **OUI** — le plus gros candidat | détaillé dans `TYPESAFE_JEV.md` : six sorties qui sont six primitives, dans un seul appel |
| `utils/eventness.py`, `utils/triage.py`, `utils/temps_recit.py`, `utils/acronymes.py`, `utils/lisibilite.py` | **OUI** | détecteurs à regex dont le CLAUDE.md documente les échecs (« est présenté » pris pour un passé) |
| `utils/completeness.py` | **CODE** | c'est un calcul sur des colonnes, il doit le rester |

### Complétion — le cœur de la demande

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `utils/infos_pratiques.py` | **OUI, le meilleur rapport gain/risque du dossier** | § 1 ci-dessus |
| `scripts/autocomplete.py` | **PARTIEL** | c'est un orchestrateur : il ne change pas, ce sont ses sous-appels qui deviennent des questions typées |
| `lister_a_completer.py`, `trier_sans_date.py` | **OUI** | trier une file = `Choice` sur la cause du blocage |

**Le tableau que tu décris — « toutes les informations, et est-ce qu'il en manque » —
existe déjà à moitié** : `utils.completeness.MANDATORY` tient six champs obligatoires
(date, lieu, ville, territoire, catégorie, image).

> ⚠️ **Correction du 22/09, même jour.** Ce paragraphe affirmait ensuite qu'« aucune
> colonne de la base ne stocke » tarif, horaires, réservation ou accessibilité, en citant
> la docstring d'`utils/infos_pratiques.py` (« sur 81 colonnes, AUCUNE ne stocke un
> tarif »). **C'est faux.** Cette docstring était vraie le jour où elle a été écrite ;
> `scripts/moisson_officielle.py` a créé la colonne `infos_pratiques` depuis, et la
> remplit tous les matins à 8h52 — du JSON `{famille: [extraits]}`. J'ai pris un
> COMMENTAIRE pour un FAIT au lieu d'interroger le schéma, ce qui est exactement la
> racine du CLAUDE.md. Le chantier n'était donc pas « créer les colonnes » : la donnée
> était là, invisible. Elle est depuis dépliée en colonnes du tableur (jeu « Infos
> pratiques »), et `tests/test_colonnes_declarees.py` a montré au passage que **25
> colonnes** manquaient à `init_db`, dont celle-là.

Ce qui reste vrai, et qui est l'apport de Jev : ces extraits sont des PHRASES, pas des
valeurs. « 12 € » y apparaît sans qu'on sache si c'est le plein tarif, le réduit ou le
parking. Choisir lequel est le tarif de CET événement, parmi les extraits déjà trouvés,
reste exactement la question `Choice` décrite au § 1.

### Rédaction, traduction, SEO

| Nœud | Verdict |
|---|---|
| `enrich.py`, `translate_events.py`, `seo_batch.py`, `textes_hubs.py`, légendes sociales | **NON** — génération de texte, Jev n'en fait pas |
| `conform_articles.py`, `audit_substance.py`, `audit_lisibilite.py`, `audit_vocabulaire.py`, `audit_temps_recit.py` | **OUI** — ce sont des **contrôles**, pas de la rédaction |
| `audit_langue_articles.py`, `audit_langue_polylang.py`, `audit_traduction_manquante.py` | **OUI, sous réserve** — « ce texte est-il en italien ? » est un noul. Mais c'est le nœud qui dépend le plus du test multilingue non fait |
| Le portillon de traduction (fiche 3588, « La Rencontre Valdôtaine ») | **OUI, avec une réserve nommée** — voir § 4 |
| Le panel de personas | **PARTIEL** — la note se traduit en `Score`, la remarque rédigée ne se traduit pas. Utilisable en pré-filtre : ne convoquer le panel Claude que sur les fiches dont le Score est bas ou la confiance faible |

### Images

**NON, en bloc.** Aucune mention de multimodal dans la référence API : `image_verify.py`,
`image_audit.py`, `images_web.py`, `images_wide.py`, `refill_images_as.py` sont hors
champ. C'est dommage, parce que c'est là qu'on a perdu le plus de temps ces dernières
semaines.

### Publication et réconciliation WordPress

**CODE, en bloc.** `publish_batch_as.py`, `reconcile_*`, `trash_*`, `relink_*`,
`cs-redirections-301.php` : ce sont des actions déterministes, et la règle 1 du CLAUDE.md
(« interroger WordPress, pas deviner ») n'est pas une affaire de modèle.

### Audits du site — l'autre demande explicite

| Nœud | Verdict | Pourquoi |
|---|---|---|
| `site_audit.py`, `site_health_check.py`, `homepage_health.py`, `gabarit_health.py`, `verifier_liens.py` | **CODE** | codes HTTP, structure, gabarit : des faits, pas des jugements |
| `gsc_report.py` et le connecteur CrawlSEO | **CODE** | des chiffres |
| `audit_coherence.py`, `audit_confrontation.py`, `audit_non_events.py`, `audit_bad_sources.py`, `audit_radar_published.py`, `audit_incomplets.py`, `audit_orphelins.py` | **OUI** | chacun pose une question de jugement sur du texte, aujourd'hui approchée par des heuristiques |
| `utils/site_issues.py` et la file du back-office | **OUI, et c'est le plus politique** | le noul « **un humain qui n'a que la page source sous les yeux peut-il trancher ce point ?** » vide la file de son bruit. C'est la réponse technique à « 548 tâches ! c'est ingérable » |
| `slack_digest.py`, l'anti-spam d'`autocomplete` | **OUI** | « cette notification mérite-t-elle de réveiller quelqu'un ? » est un noul |

---

## 3. Les trois chantiers, dans l'ordre où je les ferais

1. **`infos_pratiques` + les colonnes manquantes.** C'est le seul qui rende le site *plus
   complet* plutôt que *moins cher*. Étape 0 : décider quels champs méritent une colonne.
   Étape 1 : Jev choisit parmi les extraits. Risque faible — un champ vide aujourd'hui,
   un extrait de la page demain, jamais une valeur inventée.
2. **La file d'audit et les détecteurs à regex.** Ils signalent, ils ne publient pas :
   une erreur y coûte une ligne de rapport. C'est le terrain d'essai naturel, et il donne
   la mesure du comportement en français et en italien sans rien risquer.
3. **Le dédoublonnage du résidu ambigu**, sur le chemin « coïncidence » qui liste déjà
   sans fusionner — donc sans rien changer au comportement actuel tant qu'on n'a pas lu
   les propositions (règle 4 : dry-run, et le lire ligne par ligne).

L'évaluateur, malgré son volume, vient **après** : c'est le nœud qui décide ce qui entre
dans le site, et il n'y a pas d'environnement de test.

---

## 4. Ce que le motif de confiance change pour la règle 3

Le CLAUDE.md pose qu'un état terminal doit avoir quelqu'un qui le rouvre, et qu'« un refus
qui se rejoue sur la MÊME entrée n'est pas un rouvreur ». Le premier rapport concluait que
Jev n'y changeait rien. **C'est à nuancer après lecture du cookbook *self-consistency*.**

Leur motif n'est pas « au-dessus de 0,5 c'est oui » mais une **bande d'incertitude
déclarée** :

```python
if probability < 0.30:  return "no"
if probability > 0.70:  return "yes"
return "uncertain"      # → révision humaine
```

La zone grise n'est pas un effet de bord : **c'est une file nommée, bornée et
dénombrable**, avec un propriétaire désigné d'avance. C'est exactement ce que
`docs/ETATS_TERMINAUX.md` exige et que les six culs-de-sac du 03/08 n'avaient pas. Et
l'éditeur annonce un écart-type de 0,0102 sur quinze passages du même dossier, contre des
LLM qui changent d'avis — donc le seuil, lui, tient.

Ce que ça ne règle toujours pas : une fiche dont le noul vaut 0,08 restera à 0,08 demain.
Pour celles-là, le rouvreur reste à écrire — mais on saura **combien il y en a**, ce qui
n'est pas le cas des 823 fiches qui ont dormi dans `venue_source='llm_none'`.

---

## 5. Ce que ça changerait dans `docs/LLM_OU_CODE.md`

Ce document arbitre entre deux colonnes, **code** et **LLM**, et son critère est le bon :
« volume × coût LLM justifié, ou pré-filtre code ? ». Jev ne remet pas la règle en cause,
il **déplace la frontière** : il ajoute une troisième colonne pour les tâches qui sont du
jugement sur du langage (donc pas du code) mais à fort volume et sans génération (donc mal
servies par un LLM).

Trois lignes du tableau actuel basculeraient, si les mesures confirment :

| Ligne du tableau | Aujourd'hui | Deviendrait |
|---|---|---|
| Dédup multi-sources | code | code + **Jev sur le résidu** (ce que le document appelle déjà « LLM uniquement pour confirmer une paire douteuse », sans jamais l'activer faute de budget) |
| Évaluation éditoriale | LLM | **Jev** en première main, LLM sur la zone grise |
| Pré-filtre géographique | code | **code** (inchangé — la liste fait foi) |

Je ne modifie pas ce fichier maintenant : il est commun à trois projets (`cultura-core`),
et rien n'est mesuré.

---

## 6. Ce qui reste non mesuré, et doit l'être avant tout engagement

Inchangé depuis le premier rapport, et rien de ce qui précède ne s'y substitue :

1. `.venv/bin/python -m scripts.audit_couts --jours 30` sur le VPS — **où part l'argent** ;
2. **le français et l'italien** : la documentation n'en dit rien, nos fiches n'ont que ça ;
3. **l'accord avec nous** : rejouer Jev sur des fiches que Franck a corrigées à la main,
   avec des cas qui doivent PASSER près de la frontière (salon du livre, café philo,
   conférence de musée).

Le point 2 et le point 3 se répondent dans le même banc d'essai, hors ligne, sans écrire
une ligne en base.

## Sources

Cookbooks lus pour ce passage : `pre_parsed_value_extraction_cookbook`, `sde_cascade`,
`entity_alignment`, `citation_check`, `consistency_noul_cookbook`, `semantic_find`,
`parallel_questions` — index : <https://docs.typesafe.ai/llms.txt>.
Limites du modèle : <https://docs.typesafe.ai/model-jaggedness/jev-1.13.md>.
