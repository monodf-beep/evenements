# Jev sur TOUTE la chaîne — le passage demandé par Franck

> Remplace `docs/TYPESAFE_JEV_NOEUDS.md`, qui posait la mauvaise question. Celui-là
> cherchait ce que Jev pouvait REMPLACER dans la facture ; Franck a corrigé le cadrage le
> 22/09 : « c'est sur du scraping, c'est de faire en sorte que les données soient
> identifiées […] tu es parti sur du LLM, alors que Jev, c'est pas du LLM. »
>
> Trois questions par nœud, dans cet ordre :
> 1. **Est-ce une DÉCISION** (choisir, noter, trancher vrai/faux) ou une GÉNÉRATION ?
> 2. Si c'est une décision, **la fait-on aujourd'hui** — et si non, pourquoi ?
> 3. **Que gagne-t-on** : moins cher, ou une chose qu'on ne fait pas du tout ?
>
> La troisième réponse est la seule qui compte. Le gain par substitution est mesuré à
> ~11 $/mois sur 157 $ (`docs/TYPESAFE_JEV.md`) : négligeable. Tout l'intérêt est en
> colonne 3.

---

## 1. Tes trois exemples, répondus

### « Est-ce qu'il peut remplacer le panel de personas avec des notes ? »

**Oui pour les notes. Non pour les remarques. Et ce n'est pas le remplacement qui vaut le
coup — c'est la fréquence.**

Ce que le panel fait aujourd'hui : 3 à 4 personas relisent l'article rédigé, chacun rend
une note ; `panel.mean` en sort. 790 appels sur 30 jours, 3,00 $. Il tourne **à la
rédaction, une fois** (×2 s'il y a révision).

Ce que dit la documentation : la primitive `Score` est exactement une grille de notation
— « rate content against ordered descriptive levels », 2 à 10 niveaux, avec
`probabilities` et `confidence`. Et le motif `composite-scoring` recommande de **découper
un jugement complexe en scores atomiques, puis de recomposer avec des poids tenus dans
le code**.

**Or c'est déjà notre architecture.** `utils/home_score.calculer` fait précisément ça :

```
qualité éditoriale   panel (moyenne 0-5) ramené sur 6     → 0 à 6
source directe       la matière vient du site officiel    → +2,5
visuels              deux affiches +1,5 ; une seule +0,75 → 0 à 1,5
```

Un persona = une dimension. La note du panel pèse **60 %** du score de rendu. Le motif
attendu par TypeSafe est donc déjà en place ; seule la notation est faite par un LLM.

CE QU'ON PERD : les REMARQUES rédigées. Un persona qui écrit « le troisième paragraphe
perd le lecteur » donne quelque chose qu'aucun score ne rend. À décider : est-ce qu'on
les lit ? Si personne ne les lit, elles coûtent la moitié du poste pour rien.

CE QU'ON GAGNE, et c'est le vrai point : aujourd'hui le panel tourne **une fois, à la
rédaction**. Une fiche republiée trois mois plus tard garde la note de son premier jet.
`rescore_home.py` existe précisément parce que 21 fiches en ligne n'avaient aucun score.
À 0,042 $ le million de jetons, le panel peut tourner **sur chaque fiche, à chaque
republication, tous les jours** — ce qui n'est pas finançable autrement.

### « Est-ce qu'il peut identifier sur le site des informations qui manquent ? »

**Oui, et c'est le nœud où il apporte le plus — à condition de séparer deux questions
que nos audits confondent encore.**

Une case vide a trois causes, et une seule mérite une tâche :
- **la source le dit et on ne l'a pas lu** → à remplir, automatiquement ;
- **la source ne le dit pas** → rien à faire, et surtout pas de ligne dans une file ;
- **le champ ne s'applique pas** (récurrent sans date, festival itinérant sans lieu) →
  déjà traité par `utils.tableur.sans_objet`.

C'est exactement le grief du 11/08 : sur « 454 points à contrôler », **315 étaient des
informations que la source ne publie pas**. Personne ne peut vérifier la capacité
d'accueil d'une sortie au lac.

La question qui sépare les deux premières est un `Noul` posé sur la page source :

> « Cette page indique-t-elle le tarif de cet événement ? »

Coût : quelques centièmes de centime par fiche. Aujourd'hui, personne ne la pose — la
poser à un LLM sur 359 fiches × 5 champs coûterait plus que le reste du pipeline.

Et pour les fiches DÉJÀ en ligne, le motif documenté est `citation_check` : un `Choice`
sur la relation entre la page et la fiche — **soutient / contredit / ne dit rien**. Le
verdict « ne dit rien » est précisément celui qui nous manque dans `utils/confronter.py`.

### « Est-ce qu'il peut mettre un score sur une home page ? »

**Sur une FICHE, oui et on le fait déjà à moitié. Sur la HOME elle-même, oui et ça
n'existe pas — mais pas sur ce qu'elle a de visuel.**

Il faut distinguer, parce que `utils/une.py` le documente déjà :

- **le RENDU** d'une fiche (peut-on la montrer proprement ?) = `as_home_score`, composite
  déjà en place ;
- **l'INTÉRÊT** de l'événement = autre chose, et c'est l'incident du 17/08 : *« pilates en
  à la une ??? »*. Un cours de pilates bien rédigé, sourcé et illustré battait
  mécaniquement un festival mal illustré. Le score faisait exactement ce qu'on lui avait
  demandé. C'est un `Score` sur le texte, et c'est déjà ce que fait l'évaluateur.

**Ce qui n'existe pas, c'est un score sur la SÉLECTION.** « Ces huit fiches, ensemble,
font-elles une bonne une ? » — diversité des territoires, des catégories, fraîcheur,
absence de doublon thématique. La documentation le permet directement : le champ `state`
accepte **« a plain string for text, or structured data (object/array) »**. On envoie la
liste des huit fiches en JSON et on pose quatre `Score` atomiques, recomposés avec nos
poids. C'est le motif `composite-scoring`, appliqué à la une.

Les seuils actuels de `une.py` — intérêt 6/10, rendu 6/10, horizon 30 jours — sont
« posés au jugé », son propre banc le dit. Un score de sélection leur donnerait enfin un
contradicteur.

**CE QU'IL NE PEUT PAS FAIRE :** juger la une en la REGARDANT. Jev n'est pas multimodal.
Une vignette mal recadrée, une affiche illisible en petit, trois images de la même
couleur côte à côte — rien de tout ça ne lui parvient. Or c'est par une capture d'écran
que Franck a vu le problème les deux fois (17/08, 21/09). Le jugement visuel reste à un
humain ou à un modèle de vision.

---

## 2. La chaîne, étage par étage

**OUVRE** = une chose qu'on ne fait pas aujourd'hui · **REMPLACE** = moins cher, même
service · **NON** = hors de ses capacités · **CODE** = doit rester déterministe.

### Moisson — là où il y a le plus à gagner

| Nœud | | Pourquoi |
|---|---|---|
| `scraper_events.py` (RSS) | **CODE** | format connu |
| **Les sources SANS flux** | **OUVRE** | **92 sources déclarées, 92 sont des flux RSS.** Un lieu sans flux est invisible. Novara 0 source, Asti 1, Haute-Savoie 5. Lire 100 pages/jour : 0,63 $/mois avec Jev, 736 $ au tarif réel du modèle qualité. Motifs : `semantic_find` (218 lignes indexées en UNE requête) et `pre_parsed_value_extraction` |
| `moisson_officielle.py` | **OUVRE** | elle ne lit que ce que `jsonld` déclare et ce qu'une regex attrape. Tout le reste de la page est jeté. Un `Choice` sur les candidats déjà extraits récupère la matière sans rien inventer |
| `gmail_collect.py` | **REMPLACE partiel** | l'extraction reste au LLM ; la cascade `sde_cascade` fait vérifier sa sortie par des nouls et n'escalade que sur alerte (78 % de la qualité du gros modèle à 30 % du coût) |

### Évaluation et tri

| Nœud | | Pourquoi |
|---|---|---|
| `evaluator.py` | **REMPLACE** | six sorties = six primitives, en un appel. Mais 5,84 $/mois : le gain est la CONFIANCE calibrée, pas le prix |
| `eventness.py`, `triage.py`, `temps_recit.py` | **OUVRE** | détecteurs à regex dont le CLAUDE.md documente les échecs (« est présenté » pris pour un passé). Gratuits mais faux ; un noul comprend |
| `perimetre.py` | **CODE** | la liste des communes fait foi |

### Complétude — la demande initiale

| Nœud | | Pourquoi |
|---|---|---|
| **« la source le dit-elle ? »** | **OUVRE** | § 1 ci-dessus. La question n'est posée nulle part aujourd'hui |
| `infos_pratiques.py` | **OUVRE** | la regex ramène les candidats, `Choice` désigne le bon avec une option « aucun ». La valeur rendue est un extrait recopié : impossible d'inventer un tarif |
| `confronter.py`, `verifier_dates`, `verifier_lieux` | **OUVRE** | `citation_check` : soutient / contredit / **ne dit rien** |
| `completeness.py` | **CODE** | calcul sur des colonnes |

### Rédaction et relecture

| Nœud | | Pourquoi |
|---|---|---|
| `enrich.py`, `translate_events.py`, `seo_batch.py` | **NON** | génération. 71 % de la facture, hors d'atteinte |
| **`panel_lecteur`** | **REMPLACE + OUVRE** | § 1. Les notes oui, les remarques non ; le gain est de pouvoir le rejouer en continu |
| `panel_site` | **OUVRE** | même chose sur le SITE, qui n'est relu qu'épisodiquement |
| `audit_substance`, `audit_lisibilite`, `audit_temps_recit`, `audit_vocabulaire` | **OUVRE** | ce sont des contrôles, pas de la rédaction |
| `audit_langue_*` | **OUVRE sous réserve** | « ce texte est-il en italien ? » est un noul — mais c'est le nœud qui dépend le plus du test multilingue jamais fait |

### Une, home, dédoublonnage

| Nœud | | Pourquoi |
|---|---|---|
| **score de SÉLECTION de la une** | **OUVRE** | § 1. N'existe pas. `state` accepte du JSON structuré |
| `une.py`, `home_score.py` | **CODE + REMPLACE** | la recomposition pondérée reste au code (c'est le motif recommandé) ; les dimensions notées passent en `Score` |
| `dedupe.py`, chemin « coïncidence » | **OUVRE** | il LISTE sans fusionner faute de savoir trancher. `entity_alignment` : un Score à 3 niveaux + trois nouls factuels, trois sorties (fusion auto / file humaine / laissé) |

### Hors d'atteinte, en bloc

**Images** — pas de multimodal : `image_verify`, `image_audit`, `images_web`, et tout
jugement visuel sur la home. **Recherche web** — `site_officiel_recherche` (22 % de la
facture), `dates_web`, `venues_web`. **Publication WordPress** — actions déterministes.
**Dates** — les comparaisons temporelles sont un point faible annoncé de Jev 1.13 ; le
parsing reste au code.

---

## 3. Ce que ça donne, en trois chantiers

1. **Les sources sans flux.** Le seul qui change la taille du site plutôt que sa facture.
   0,63 $/mois contre 736 $. C'est là que Franck attendait l'outil, et il avait raison.
2. **« La source le dit-elle ? »** sur chaque champ manquant. Vide les files de leur
   bruit et remplit ce qui est remplissable. Répond à « 548 tâches ! c'est ingérable ».
3. **Le panel en continu**, et le score de sélection de la une. Le premier existe mais ne
   tourne qu'une fois ; le second n'existe pas.

Les détecteurs à regex (`temps_recit`, `eventness`, `triage`) viennent après : risque
faible, gain réel, bon terrain d'essai — ils signalent, ils ne publient pas.

## 4. Ce qui décide, et qui n'a toujours pas été mesuré

Inchangé depuis le premier jour, et aucun de ces chantiers ne démarre sans :

1. **Le français et l'italien.** La documentation n'en dit RIEN. Toutes nos pages en sont.
2. **Une vraie page d'agenda.** Longue, bruyante, trente blocs dont cinq sont des
   événements — et « contexte volumineux » figure parmi les points faibles annoncés de
   Jev 1.13. C'est précisément la forme du chantier n° 1.
3. **L'accord avec nous.** Rejouer l'évaluateur et le panel sur des fiches que Franck a
   corrigées, et compter les désaccords.

Les trois tiennent dans un banc d'essai hors ligne, sans écrire une ligne en base. Il ne
manque qu'une clé.
