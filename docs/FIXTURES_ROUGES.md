# Les fixtures qui ne passent pas ici — et pourquoi ce n'est pas toi

Écrit le 2026-08-17 à la demande de Franck : « écris quelque part les tests rouges
antérieurs, avec la raison de leur exclusion, sinon la prochaine session les redécouvrira
et croira les avoir cassés. »

C'est exactement ce qui a failli arriver : la suite affichait « 5 au rouge » avant et
après mes modifications, et il a fallu les ouvrir une par une pour établir qu'aucune ne
me concernait. Ce document est là pour que la prochaine session ne repaie pas ce quart
d'heure.

**Où le voir sans lire ce fichier** : `.venv/bin/python tests/run_all.py` les affiche
séparément, sous « NON EXÉCUTABLES ICI », avec la raison en clair. Elles ne comptent plus
comme des échecs et ne mettent plus le code de sortie à 1.

---

## Quatre fixtures dépendent de `pytest`, absent de ce venv

| Fixture | Ce qu'elle couvre |
|---|---|
| `test_eval` | l'évaluation / le barème |
| `test_gmail` | la collecte par boîte mail |
| `test_gabarit_health` | la santé des gabarits |
| `test_site_health_solde` | le solde de `site_health` |

    $ .venv/bin/python -m tests.test_eval
    /root/evenements/.venv/bin/python: No module named pytest

Ce ne sont pas des régressions : ces quatre fichiers sont écrits pour le lanceur `pytest`,
là où les 71 autres sont des scripts autonomes qui rendent leur propre code de sortie.

**Ce qu'il faudrait pour les rendre au vert** : `pip install pytest` dans `.venv`.
CLAUDE.md classe `pip` parmi les gestes qui **demandent encore Franck** (hors projet), donc
aucune session ne doit l'installer d'elle-même. Tant que ce n'est pas fait, elles restent
non exécutables — et visibles.

### Pourquoi elles ne comptent plus comme des échecs

`tests/run_all.py` n'a qu'une vertu, son code de sortie — il a été écrit le 2026-08-16
parce qu'une boucle shell affichait « ÉCHEC » tout en rendant 0, et qu'un commit était
parti sur une suite rouge. Or quatre fixtures définitivement rouges mettaient ce code à 1
**en permanence** : la vertu devenait inutilisable, et une suite qui ne peut jamais être
verte finit par ne plus être lue. C'est le même piège, retourné.

La séparation est **étroite exprès** (`run_all._outil_manquant`) : on ne reconnaît que
l'absence d'un **lanceur de tests**. Un `No module named 'utils'` reste un échec — c'est du
code cassé, et le déguiser en « non exécutable » rendrait `run_all` complice de ce qu'il
est censé empêcher.

---

## Une cinquième, qui n'en était pas une : `test_autocomplete_resurface`

Comptée rouge dans les passages de 23:57 et 00:07 le 2026-08-16/17, **verte** à 00:41 et
sur trois relances consécutives ensuite, sans que personne n'ait touché ni à la fixture ni
à `scripts/autocomplete.py`.

Elle recule des horodatages de `RESURFACE_DAYS` jours pour rejouer un ressurfaçage
(`autocomplete_notified_at`, `autocomplete_state_since`). Une fixture qui arithmétise des
jours autour de l'horloge courante peut changer de couleur au passage de minuit — c'est
l'explication la plus probable, mais **elle n'est pas établie** : je ne l'ai pas
reproduite. Écrit ici pour que la prochaine session qui la voit rouge sache qu'elle a déjà
oscillé, et cherche du côté de l'heure avant de chercher du côté du code.

---

## La règle, pour la suite

Une fixture qui ne peut pas tourner ici doit être **nommée, comptée et expliquée** — jamais
silencieusement ignorée, jamais mélangée aux vraies régressions. Si une cinquième
s'ajoute, elle vient dans ce tableau avec sa raison, et `_outil_manquant` n'apprend un
nouveau motif que si c'est bien un outil qui manque.

---

## Trois de plus, et elles ne sont rouges QUE hors du serveur (2026-08-18)

| Fixture | Ce qui manque | Où c'est vert |
|---|---|---|
| `test_action_annuler` | `flask` | sur le VPS : le back-office tourne dessus |
| `test_file_verifier` | `flask` | idem |
| `test_image_audit_plafond` | `PIL` (Pillow) | idem, `requirements.txt` l'installe |

Constaté dans un conteneur de développement où seules les dépendances strictement
nécessaires étaient posées. Ce ne sont pas des régressions : ces trois-là importent des
bibliothèques de l'APPLICATION, présentes dans le `.venv` du serveur.

**Pourquoi `run_all` les compte quand même comme rouges, et pourquoi c'est juste.**
`_outil_manquant` ne reconnaît que l'absence d'un **lanceur de tests** (pytest). Élargir
ce motif à « n'importe quelle bibliothèque absente » ferait passer pour « non exécutable »
un vrai `ModuleNotFoundError` dû à du code cassé — exactement ce que ce lanceur existe pour
attraper. La distinction reste donc étroite, et c'est ce document qui porte le contexte.

**Conséquence pratique, à connaître depuis le 2026-08-18** : `scripts/auto_deploiement`
lance cette suite AVANT chaque déploiement et refuse de déployer si elle est rouge. Sur le
serveur, ces trois fixtures sont vertes, donc le déploiement passe. Mais si un jour le
message Slack annonce « Déploiement REFUSÉ », il NOMME désormais les fixtures fautives :
commencer par vérifier si c'est une dépendance absente (`.venv/bin/pip install -r
requirements.txt`) avant de soupçonner le code.

---

## 2026-09-21 — quatre rouges qui bloquaient le déploiement automatique, et aucun n'était une régression

Franck, ce soir-là : « c'est quoi le pb ? » — parce que `auto_deploiement` (7h50) ne
déploie QUE si `tests.run_all` sort à 0, et qu'il ne sortait plus à 0. Il tapait donc
`deploy/update.sh` à la main depuis deux semaines sans que personne fasse le lien.

**Mesuré d'abord, parce que mon premier chiffre était faux.** J'avais annoncé « trois
fixtures rouges » à partir du sous-ensemble que j'avais lancé ; la suite complète en
donnait **dix**. Sept ne l'étaient que dans le conteneur de session (flask, httpx, PIL
absents) — installés, elles passent. Restaient quatre vrais cas, et chacun avait une
racine différente :

### 1. `test_dedupe_coincidence` — la fixture punissait une CORRECTION

Elle exigeait « la commande de corbeille est proposée, entière ». Or le **19/09**
(`abf3213`) les groupes formés par COÏNCIDENCE sont sortis de cette commande : le cerveau
du matin l'avait lue et aurait corbeillé TO Play et Mobilità dolce, deux vrais événements
différents. La fixture n'a pas suivi le code, et rougissait donc **parce que le code était
devenu plus prudent** — le pire genre de rouge.

Réparée en retournant l'assertion : le groupe reste AFFICHÉ avec son motif, ses ids
n'entrent PAS dans la commande, et la sortie dit pourquoi. Le contrôle porte désormais sur
l'absence, il est plus fort qu'avant.

### 2. `test_audit_substance_published` — une fenêtre d'inspection trop large

Elle cherchait `[    1]` dans TOUT ce qui suit le titre du panier 4 — donc aussi dans le
panier 5, qui CONTIENT les paniers 1 et 2 **par construction et le dit lui-même**. La
fiche 1 y figurait à bon droit ; la fixture y voyait une fuite.

Et en la réparant, un second défaut est sorti : la fiche 6, « Longue mais jamais rédigée »,
n'était longue nulle part. Sa longueur ne vient pas d'une colonne mais de `_MOTS`, où elle
n'était pas — elle valait ZÉRO mot et tombait dans le panier des maigres. La fixture
testait le contraire de ce qu'elle annonçait, et son contrôle « listée à part » ne
vérifiait qu'un titre de section. **Un test qui ne cherche qu'à se donner raison ne prouve
rien.**

### 3. `test_dates_repasse_texte` — une date écrite en dur qui a vieilli

Elle datait ses fiches au « 20 septembre 2026 », devant nous quand elle a été écrite le
08/09, passé depuis la veille. La passe page applique la règle 5 — une fiche dont la FIN
est passée est terminée, on ne lit pas sa page — et écartait donc à RAISON les fiches que
la fixture attendait de voir traitées.

Ni le code ni le scénario n'avaient tort : **c'est la date qui avait vieilli.** Les dates
sont désormais ancrées sur l'AN PROCHAIN (`_date.today().year + 1`), qui est forcément
devant nous et ne fait jamais chevaucher deux années sur un intervalle juin→septembre.
La fixture ne peut plus expirer.

> Le dépôt connaissait déjà ce piège : « un motif de date fixe ne meurt pas, il dort onze
> mois puis repart » (crontab.txt, les quatre lignes d'août). **Une fixture qui a besoin
> d'une date DEVANT NOUS ne l'écrit pas, elle la calcule.**

### 4. `test_yoast_scores` — le rouge permanent, et le vrai blocage

Celui-là ne serait jamais passé, quoi qu'on répare ailleurs. `auto_deploiement` sort le
code candidat dans un `git worktree` **jetable** et y lance `run_all` — or `node_modules/`
est dans `.gitignore` (ligne 40) et rien n'exécute `npm install` dans ce worktree. La
fixture y échoue donc à tous les coups, pour une raison qui n'est pas du code.

C'est un LANCEUR de test absent, au même titre que `pytest` : un paquet npm externe,
jamais versionné. `run_all._outil_manquant` le reconnaît désormais — la liste reste
étroite, et son commentaire d'origine (« ne jamais déguiser du code cassé en non
exécutable ») n'est pas contourné. **Là où `npm install` a été lancé, la fixture tourne et
doit passer** ; si elle échoue avec `yoastseo` présent, c'est un vrai rouge.

### Résultat

    161 fixture(s) — 160 au vert, 0 au rouge, 1 non exécutable(s) ici.
    code de sortie : 0

Le déploiement automatique de 7h50 peut repartir. À vérifier sur le VPS, où `npm install`
a été lancé : la 161ᵉ doit y être VERTE, pas « non exécutable ».
