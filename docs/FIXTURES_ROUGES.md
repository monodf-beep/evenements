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
