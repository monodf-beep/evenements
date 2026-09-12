# Audit de simplification — 2026-08-31

Demandé par Franck : « faire le ménage dans tout ce qu'on a mis en place, afin d'épurer,
de simplifier », avec un classement en trois : **ce qui se fait sans son accord**, **ce
qui demande son accord**, **ce qui demande une réflexion plus approfondie**.

## La règle suivie pour cet audit

`docs/ERREURS_2026-08-17.md` : quatre audits WordPress avaient été déclarés « redondants »
sur la seule ressemblance de leurs TITRES — aucun ne l'était, et leur suppression avait
été proposée. Ici, **rien n'est classé sans avoir été ouvert et lu**.

## ⚠️ Une précaution de mesure, trouvée en cours de route

Le bac à sable où tourne cette session était un **clone git tronqué**
(`git rev-parse --is-shallow-repository` → `true`, historique coupé au 17/08). Première
conséquence mesurée : les branches parallèles semblaient n'avoir **aucun ancêtre commun**
avec la branche de travail, et compter 260, 381, 976 commits « en avance ». C'était faux
— un artefact du clone. Après `git fetch --unshallow`, les vrais chiffres sont 1, 126 et
0. **La fausse alerte était spectaculaire et prête à être livrée.**

À retenir pour toute session future : les chiffres d'historique git mesurés ici ne valent
rien tant que le clone n'a pas été complété. Ceux que `auto_deploiement` publie sur Slack,
eux, viennent du VPS (clone complet) et sont justes.

---

# 1. À FAIRE SANS TON ACCORD — c'est réversible et ça retire un risque

### 1.1 🔴 `deploy.sh` (racine) est un jumeau plus DANGEREUX de `deploy/update.sh`

Le plus sérieux de tout l'audit. Les deux font 48 lignes et le même travail (fetch, force
la branche, `reset --hard`, dépendances, redémarrage du service). **Sauf que :**

| | `deploy/update.sh` | `deploy.sh` (racine) |
|---|---|---|
| protège `.claude/settings.json` | oui (6 mentions) | **non (0 mention)** |
| désigné par CLAUDE.md | oui, l.288 | non |
| appelé par `auto_deploiement` | oui | non |
| appelé automatiquement par autre chose | — | **rien** (vérifié : ni `install.sh`, ni `nginx.conf`, ni `deploy/`) |
| cité par un document | — | `docs/DEPLOIEMENT_HOSTINGER.md` l.133 |

La protection de `settings.json` a été ajoutée à `update.sh` le 2026-08-11, **après un
incident réel** : Franck avait posé ses permissions d'autonomie à 18h30, le déploiement de
18h45 les a effacées en silence. `deploy.sh` rejouerait cet incident à l'identique — et
c'est vers LUI qu'un document envoie le lecteur.

**Geste** : transformer `deploy.sh` en simple renvoi vers `deploy/update.sh` (plutôt que
le supprimer : un document et une habitude pointent dessus), et corriger
`DEPLOIEMENT_HOSTINGER.md`. Strictement moins de risque, aucune perte.

### 1.2 Quatre lignes de cron mortes qui repartiraient l'an prochain

`crontab.txt`, lignes 289-292 : `40-43 11 19-20 8 *` — les quatre audits envoyés sur le
téléphone de Franck pendant ses congés, datés **19-20 août**. Passés depuis deux semaines,
mais le motif `19-20 8` **se redéclenchera en août 2027**.

Déjà signalées comme « à nettoyer » dans `AU_RETOUR_2026-09-03.md` §5. Rien n'en dépend.

### 1.3 `audit_orphelins` a un angle mort qui produit 14 fausses alertes

Il annonce « 14 scripts annoncés périodiques mais jamais planifiés ». Or sa liste de
points d'entrée shell ne regarde que `scripts/` :

```python
ENTREES_SHELL = ("agent_quotidien.sh", "bilan_matin.sh", "revue_hebdo.sh", "cerveau.sh")
```

…alors que le lanceur que ces 14 scripts citent, `cron_pipeline.sh`, vit dans **`deploy/`**.
Un audit qui crie 14 fois pour rien finit par ne plus être lu — c'est le défaut que ce
dépôt documente ailleurs sous le nom de `gabarit_health`.

⚠️ Nuance importante, et elle change le geste : `crontab.txt` (l.65-68) dit lui-même que
**`deploy/cron_pipeline.sh` n'est PAS planifié** — « le crontab réel appelle les scripts un
par un, donc une ligne ajoutée là ne tourne jamais ». Il ne suffit donc pas d'ajouter le
fichier à la liste : il faut d'abord établir, script par script, lesquels de ces 14 sont
réellement planifiés à l'unité dans le crontab. C'est en cours de vérification.

### 1.4 Trois branches distantes entièrement fusionnées

Mesuré sur clone complet : `claude-seo-ph80al`, `morning-api-credit-duplicates-sobc4i` et
`nuove-fonti-intenzioni-meaff7` sont à **0 commit en avance** — tout leur contenu est déjà
dans la branche de travail. Elles n'encombrent que la liste.

(Elles ne produisent aucune alerte Slack : `auto_deploiement` ignore déjà les branches à
zéro. Le gain est de la lisibilité, pas du bruit en moins.)

### 1.5 Le document de retour a grossi par empilement — et c'est ma faute

`AU_RETOUR_2026-09-03.md` fait 494 lignes et **15 sections, dont 8 commencent par « 0 »**
(0, 0 bis, 0 ter, 0 quater, 0 quinquies, 0 sexies, 0 septies, 0 octies). J'ai ajouté
chaque nouveauté de la semaine en tête plutôt que de restructurer. Pour quelqu'un qui
rentre de vacances et lit sur un téléphone, c'est huit préambules avant le premier vrai
chapitre.

**Geste** : réorganiser par PRIORITÉ et par THÈME, pas par ordre d'arrivée. Aucun contenu
perdu, seulement remis dans un ordre lisible.

---

# 2. À FAIRE AVEC TON ACCORD

Rien ici n'est dangereux ; tout y touche soit du contenu, soit une décision qui t'appartient.

### 2.1 Deux étapes du ménage hebdomadaire font le même geste

`purge_uncompletable` et `discard_uncompletable` tournent **l'une après l'autre** dans le
cron du dimanche. Lecture faite, leur requête de sélection est **identique caractère pour
caractère**, leur prédicat `_is_radar` aussi, et leur écriture aussi
(`UPDATE … SET statut='rejected'`).

Ce qui reste vraiment propre à chacune : la première couvre le manque de **Lieu** et écrit
une justification ; la seconde couvre la branche « année révolue dans le titre ». Sa
branche « sans page », elle, est entièrement absorbée par la première, qui passe avant —
le dépôt l'a d'ailleurs mesuré : `discard_uncompletable --no-page` rend **0**.

**Geste proposé** : garder `purge_uncompletable`, y porter les trois lignes de la branche
« passé », retirer l'autre du hebdo. Deux compteurs qui décrivent le même geste
disparaissent du rapport du dimanche.
**Pourquoi ton accord** : les deux n'écrivent pas le même motif sur la fiche. Fusionner
change ce qui restera écrit sur des fiches écartées — c'est de la donnée éditoriale.

### 2.2 Trois scripts écrits, corrects, et qui n'ont jamais tourné

`cleanup_cinema` (tri des séances de cinéma commerciales), `images_wide` (le visuel
paysage 16:9) et `gmail_relink` (rattrapage des fiches venues d'un mail) ne sont atteints
que par `deploy/cron_pipeline.sh` — un lanceur que le crontab réel n'appelle pas.

**Ce n'est ni du mort ni du dormant** : ce sont des étapes de production qui n'ont jamais
démarré. Les brancher ou les retirer est un arbitrage : `cleanup_cinema` **écarte du
contenu**, `images_wide` **coûte des appels API**.

### 2.3 Le cap de traduction : la décision est déjà écrite, il manque la lecture

`crontab.txt` porte lui-même la consigne : « REDESCENDRE À 5 quand le digest du lundi
affiche "à traduire" proche de zéro : le cap à 10 coûte le double d'appels API par jour ».
Le cap est passé à 10 le 04/08 sur un stock de ~56 fiches, avec la prévision « il draine
en deux semaines ». Nous sommes à 27 jours. **La condition est probablement remplie — mais
la ligne exige de la LIRE dans le digest, pas de la supposer.**

### 2.4 Quatre documents contredisent la pratique ou le périmètre

- **`docs/NEWSLETTERS_A_SABONNER.md`** liste neuf newsletters de l'arrondissement de
  Grasse comme cases à cocher (Cannes, Antibes, Vence…), dont une déjà cochée — alors que
  `config/newsletters.txt` les marque « NE PAS s'abonner » et que CLAUDE.md les met hors
  périmètre. *(La liste que je t'ai donnée hier était propre : aucune n'en venait.)*
- **`wordpress/README.md`** décrit `apply-components.mjs` comme « idempotent » (= sans
  risque à relancer) quand deux autres documents avertissent qu'il **détruirait 40 Ko de
  CSS de production sans retour arrière**.
- **`docs/IMAGES.md`** se contredit lui-même : son schéma décrit le modèle de repli
  abandonné le 31/07, son §10 décrit le bon.
- **`docs/CHANTIER_CONTENU_CASSE_2026-07-29.md`** et **`LEXIQUE-espace-alpin.md`** posent
  des interdits de vocabulaire (« transfrontalier », « espace alpin ») que la source
  unique `config/vocabulaire_interdit.json` ne porte pas — or vingt documents du dépôt
  emploient « transfrontalier », dont un qui en fait son titre.

**Pourquoi ton accord** : ce sont des règles éditoriales. Je peux aligner les documents sur
le code, mais c'est toi qui dis si « transfrontalier » est interdit ou non.

### 2.5 Le vocabulaire interdit n'est unifié qu'à moitié

`utils/vocabulaire.consigne_prompt()` existe, est testée, et **n'a aucun appelant en
production** : les quatre prompts recopient toujours la règle à la main. Et ils ont déjà
divergé — `enrich.py` interdit « petite Venise » et « perle des Alpes », que le JSON ne
liste pas. **Donc l'audit ne les cherche pas** : ces deux expressions passeraient en ligne
sans être vues. Deux lignes à corriger, mais elles touchent les prompts de rédaction.

### 2.6 Ménage de branches et de documents

- **Trois branches distantes entièrement fusionnées** (§1.4) — suppression sans perte.
- **Quatre documents dont le sujet est clos** (`ROADMAP_ET_RISQUES`, `REGLE_CANONICAL`,
  `PLAN_DEV`, `TAGS_CONTROLES`) : à déplacer dans un `docs/archive/`, après avoir remonté
  ailleurs les deux ou trois règles qu'ils sont seuls à porter.
- **`GUIDE_FRANCK.md` est orphelin** : 295 lignes, le seul document écrit pour toi, exact
  là où d'autres se trompaient — et rien ne le cite, pas même CLAUDE.md.

### 2.7 Du code mort qui traverse six fichiers exécutés tous les jours

La plomberie `fallback_images` : un chargeur, une variable et un paramètre traversés sur
deux à trois niveaux d'appel dans `visuals`, `newsletter`, `autocomplete`,
`refill_images_as`, `app.py` et `upgrade_category_banners_as` — pour un argument que la
fonction destinataire **ignore explicitement** depuis qu'un repli a été retiré (violation
de charte §9). S'y ajoutent une fonction morte dans `publisher_as`, deux imports devenus
inutiles, sept fonctions publiques orphelines dans `utils/sources.py` dont quatre lisent
des fichiers de config **qui n'existent pas**, et une vingtaine d'imports inutilisés.

**Pourquoi ton accord** : ça touche des fichiers du chemin de publication quotidien. Le
retrait est mécanique et testable, mais il se fait à froid, pas en fin de journée.

> **FAIT le 04/09** (Franck : « avance sur d'autres sujets »). Remesuré avant de toucher,
> et l'audit sous-comptait : **11** fonctions publiques de `utils/sources.py` sans aucun
> appelant (grep sur tout le dépôt, tests compris — et aucun `import *` ni import
> dynamique qui aurait pu tromper le grep), pas 7 ; **23** imports inutilisés (`ruff
> F401`), la fonction morte de `publisher_as` (`_banner`, gardée « au cas où » et jamais
> appelée), et la plomberie `fallback_images` sur les six fichiers. Deux docs présentaient
> des fonctions mortes comme actives (`strip_tracking` dans PIPELINE_COLLECTE,
> `est_comte_de_nice` dans la charte) — corrigées. Bilan : 27 fichiers, −313 lignes,
> suite de fixtures 108/108 au vert avant ET après. `config/territory_images.txt` est
> gardé (manifeste de sync amont), plus lu par personne — dit dans son en-tête.

---

# 3. DEMANDE UNE RÉFLEXION PLUS APPROFONDIE

### 3.1 `app/app.py` : 4 672 lignes, 66 routes dans un seul fichier

C'est de loin la plus grosse concentration du dépôt — plus du double du deuxième
(`scripts/enrich.py`, 2 170 lignes). Le découper rendrait chaque écran plus facile à
modifier sans risque… mais c'est le back-office **en production**, et un découpage de
4 700 lignes est précisément le genre de chantier qui casse en silence.

Ce n'est pas urgent : rien ne dysfonctionne. C'est une dette à trancher à froid, avec un
plan d'étapes vérifiables, jamais « en passant ».

### 3.0 ⭐ La règle 5 est écrite 43 fois, et dix fois seulement en entier

La trouvaille la plus structurante de l'audit. « On ne travaille que sur ce qui est encore
devant nous » est la règle la plus citée du dépôt — et elle n'existe nulle part comme du
code partagé. Mesuré : **31 fichiers portent ce prédicat, 43 fois**. Sur ces 43 :

- **10 seulement** incluent les événements RÉCURRENTS ;
- **15 seulement** incluent les fiches SANS DATE ;
- **18** s'écrivent sans `NULLIF`, ce qui **perd les fiches dont la date de fin est une
  chaîne vide** (vérifié sur SQLite : la variante sans `NULLIF` en rate une sur trois dans
  un jeu d'essai).

`app/app.py` à lui seul en porte **trois orthographes différentes**. Et la bonne existe
déjà, nommée et commentée — dans un seul script (`purge_bylines._DEVANT`), sans être
partagée.

Ce n'est pas un nettoyage : c'est le cœur éditorial du projet, écrit trente fois à la main
et en perdant un morceau la plupart du temps. La promouvoir en `utils/perimetre_temporel`
est un vrai chantier (31 fichiers), qui demande une fixture avec un cas `date_end=''` **qui
doit passer**, et une mesure préalable en base :
`SELECT COUNT(*) FROM events_raw WHERE date_event_end='' AND date_event_start >= date('now')`.

### 3.1 bis Deux seuils portent le même nom et n'ont pas le même sens

`RETAIN_MIN_SCORE` se déclare « source unique » dans `evaluator.py` — mais le `7` est écrit
en dur **sept fois dans `app/app.py`**, dans la file de publication du back-office. Le
poser à 8 déplacerait l'évaluateur et laisserait la file à 7.

Pire, et à vérifier sur le VPS : son repli est `os.getenv("ENRICH_MIN_SCORE", "7")`, or
`enrich.py` lit **ce même nom** avec un sens différent (plancher de rédaction, défaut
**1**). Si `.env` pose `ENRICH_MIN_SCORE=1`, alors `RETAIN_MIN_SCORE` **devient 1 en
silence** et le seuil de mise en avant s'effondre. Je n'ai pas pu le vérifier — la lecture
du `.env` m'est interdite.

### 3.2 La branche `agenda-sabauda-homepage-test-exckrp` — 126 commits, 10 285 lignes

Un chantier parallèle entier : `wordpress/design-system/` avec les gabarits de page
(accueil, mentions légales, crédits photos, confidentialité, page newsletter,
en-tête/pied, `tokens.css`, filtre de rail par jour). Dernier travail le **19/08**.

Ce n'est ni du mort ni du mergeable-à-l'aveugle : c'est un travail de design qui touche
l'apparence du site public. La question à trancher n'est pas technique — c'est « veut-on
ce design ? ». Tant qu'elle n'est pas posée, la branche vit à côté sans risque.

---

### 3.3 CLAUDE.md — 331 lignes, dont un quart de journal sédimenté

Le seul document lu **intégralement à chaque session** : chaque ligne s'y paie à tous les
démarrages. Trois défauts précis, dont un savoureux :

- il annonce « **Trois corollaires opérationnels** » et en liste **quatre** — dans le
  fichier qui pose la règle « un compteur doit dire ce qu'il compte » ;
- la **règle 1 y est écrite trois fois** (comme règle, puis « transposée » aux branches,
  puis « transposée au code ») : trois formulations justes, mais dispersées ;
- les lignes 137-215 (**24 % du fichier**) ont grossi par sédimentation. Garder en tête les
  deux formulations qui se déclenchent d'elles-mêmes — « ne jamais présenter une INFÉRENCE
  comme un FAIT » et « un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas » —
  et renvoyer aux trois journaux datés pour le reste : 40 à 50 lignes de gagnées, sans
  perdre un garde-fou.

Toucher à CLAUDE.md n'est pas un nettoyage ordinaire : c'est la loi du dépôt. À faire à
froid, en une passe, avec toi.

### 3.4 `app/app.py` : 4 672 lignes, 66 routes — voir 3.1

---

## Ce qui va BIEN et qu'il ne faut PAS toucher

Un audit qui ne dit que ce qui cloche donne une image fausse.

- **Le harnais de tests : 106 fixtures en 46 secondes.** Il tourne avant chaque
  déploiement et ne coûte presque rien. Aucune raison de l'alléger.
- **Le dépôt est propre** : pas de worktree d'essai résiduel, pas de fichier bâtard à la
  racine, `logs/` à 520 Ko.
- **Les branches de travail sont à jour** : la branche déployée porte exactement ce qui
  est poussé.
- **Le chien de garde n'a aucune entrée fantôme** : chacune de ses 24 lignes d'origine
  correspond à un cron réel, nom de journal compris. C'est rare et ça mérite d'être dit.
- **Aucun module de `utils/` n'est mort** : les 58 ont au moins un appelant en production.
- **Aucune config n'est morte non plus**, à une exception près
  (`radar_offtopic_keywords.txt`, remplacé par un filtre positif). Et
  `config/territory_images.txt`, qui a l'air vide, l'est **délibérément** — son propre
  commentaire l'explique. Ne pas le « réparer ».

### Cinq ressemblances de noms qui ne sont PAS des doublons

Consignées exprès, parce que c'est l'erreur du 17/08 et que quatre d'entre elles
l'auraient rejouée :

| Paire | Ce que la lecture montre |
|---|---|
| `trash_by_ids` / `trash_wp_ids` | Clés différentes (id local vs id WordPress), et le premier porte un verrou que l'autre n'a pas |
| `audit_translation_langs` / `audit_langue_polylang` | L'un audite la donnée, l'autre le risque d'une action future |
| `repair_translation` / `_cycles` / `_dates` | Trois pannes distinctes, aucun recouvrement de requête |
| `purge_radar` / `audit_radar_published` | Le premier renvoie explicitement au second plutôt que de le refaire |
| `daily_batch._porte_publication` / `publish_batch_as` | Doublon VOULU : c'est le seul contrôle du chemin non supervisé |

---

## Ce que cet audit n'a PAS pu trancher — et qui demande le VPS

Écrit ici pour que personne ne le redécouvre à ses frais :

- la **durée réelle** des passages du cerveau et de l'agent quotidien (`logs/*.log`) ;
- le **coût API réel** (le journal d'usage local ne contient que des essais) ;
- la valeur actuelle de la ligne « à traduire » du digest du lundi (§2.3) ;
- ce que vaut `ENRICH_MIN_SCORE` dans le `.env` (§3.1 bis) ;
- s'il reste des fiches avec `date_event_end=''` (§3.0) ;
- et le solde des populations visées par cinq scripts d'incident de juillet, qui ne se
  supprimeront qu'après un dry-run montrant **0 avec son dénominateur**.
