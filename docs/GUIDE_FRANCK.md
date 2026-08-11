# Ce que tu dois savoir pour tenir l'agenda

Écrit le 2026-08-11 au soir, à ta demande. Ce document ne s'adresse qu'à toi : il dit ce
qui tourne tout seul, ce que tu tapes toi-même, comment lire ce que ça répond, et ce qui
est vrai en ce moment. Tout le reste de `docs/` s'adresse à la machine ou à moi.

**Une règle avant toutes les autres : rien de ce qui est décrit ici ne casse quoi que ce
soit.** Les commandes destructives demandent `--apply`, et ce qu'elles font se défait
(corbeille WordPress, changement de statut). Ce qui ne se défait pas est bloqué au niveau
du harnais, pas de ta vigilance.

---

## 1. Ce qui se fait sans toi

Vingt-deux tâches automatiques par jour (`crontab.txt`). Tu n'as rien à lancer le matin.
Les heures qui comptent :

| heure | ce qui se passe |
|---|---|
| 3h00 | **sauvegarde de la base** — le filet, tous les jours |
| 8h00 → 8h52 | collecte : flux RSS, boîte mail, dédoublonnage, dates, lieux |
| 9h00 | évaluation (note d'importance de chaque événement) |
| 9h15 | **l'agent quotidien** — il ouvre les pages une par une et complète ce qu'il peut |
| 9h30 | rédaction + publication du lot du jour |
| 10h45 | traductions italiennes |
| **11h00** | **bilan du matin sur Slack** — c'est ton point de contrôle |
| 12h00 | chien de garde : il te prévient si un cron n'a pas tourné |
| dimanche 5h/6h | audits hebdomadaires + revue |

Si tu ne reçois rien sur Slack à 11h, quelque chose est cassé. C'est le seul signal qui
compte vraiment.

---

## 2. Les commandes que tu tapes toi-même

Toujours dans cet ordre : `cd /root/evenements` d'abord (tu y es déjà en général).

### Mettre à jour le serveur — **une seule commande, jamais plusieurs**

```bash
bash deploy/update.sh
```

Elle fait tout : récupérer le code, installer ce qu'il faut, redémarrer le back-office.
Elle conserve tes réglages locaux et te le dit. **Ne tape jamais `git pull` / `pip install`
/ `systemctl` à la main** — ce script existe pour ça, et si je te dicte la suite longue un
jour, rappelle-le-moi.

### Vérifier que nos dates ne mentent pas

```bash
.venv/bin/python -m scripts.verifier_dates              # tout ce qui est devant nous
.venv/bin/python -m scripts.verifier_dates --en-ligne   # seulement ce que le public lit
```

Il compare **notre** date à ce que dit **la source**, et ne signale que trois choses
franches. Il ne touche à rien. C'est celui qui a trouvé les dix-sept fiches périmées du
11 août.

### Compléter, corriger, écarter

```bash
.venv/bin/python -m scripts.lister_a_completer          # ce qui manque, avec l'adresse à ouvrir
.venv/bin/python -m scripts.completer_verifie           # simulation
.venv/bin/python -m scripts.completer_verifie --apply   # écrit
```

### Retirer des fiches du site

```bash
.venv/bin/python -m scripts.trash_by_ids 123 456 --statut rejected --motif "..."
# puis la même chose avec --apply si la sortie est conforme
```

Corbeille WordPress + rejet en base. **Les deux se défont d'un clic.** Le `--statut
rejected` est obligatoire quand la fiche est encore retenue : sans lui, elle part à la
corbeille le soir et revient en ligne le lendemain à 9h30.

### Avant une opération de masse

```bash
.venv/bin/python scripts/backup_db.py
```

---

## 3. Comment lire ce que ça te répond

Trois habitudes suffisent, et elles viennent toutes d'erreurs réelles.

**① Le nombre sans son périmètre ne veut rien dire.** « 793 points à vérifier » et « 28
points à vérifier » décrivaient le même écran le même jour : l'un comptait le passé, l'autre
non. Tout compteur écrit maintenant ce qu'il compte à côté de lui. S'il ne le fait pas,
c'est un bug — dis-le-moi.

**② Un zéro doit dire d'où il vient.** « Aucune anomalie » et « ma requête était vide » se
ressemblent trait pour trait. C'est pour ça que les audits affichent toujours combien de
fiches ils ont examinées, et leur entonnoir de sélection. Si tu vois un zéro sans
dénominateur, ne le crois pas.

**③ Un signalement sans sa phrase ne se juge pas.** Chaque ligne d'alerte doit citer le
texte de la source. C'est ce qui a permis, le 11 août, de voir en dix secondes que deux
signalements sur dix-neuf étaient faux — et l'un d'eux parce que **la source officielle
elle-même s'était trompée**.

Corollaire : **lis la phrase avant d'appliquer.** Les scripts proposent, ils ne décident
pas.

---

## 4. Les quatre files du back-office, et ce qu'elles ne sont pas

| file | la question posée | le geste |
|---|---|---|
| **À traiter** | est-ce que ça a sa place dans l'agenda ? | valider ou écarter |
| **À compléter** | il **manque** une donnée obligatoire (date, lieu, ville, image…) | trouver la valeur et la poser |
| **À vérifier** | une donnée est **là** mais on doute qu'elle soit juste | ouvrir la source, corriger l'article |
| **Audit visuel** | l'image ne va pas (cadrage, affiche coupée) | recadrer ou remplacer |

**« À compléter » est un trou, « À vérifier » est un doute.** Un trou empêche la
publication ; un doute concerne souvent une fiche déjà en ligne, donc déjà lue. C'est pour
ça que les deux ne sont pas fusionnées : neuf trous et neuf doutes ne demandent ni le même
travail ni la même urgence.

**Une file ne doit contenir que ce sur quoi tu peux agir.** Si tu y vois une question à
laquelle personne ne peut répondre — « accueil PMR ? », « langue de la médiation ? » sur une
source qui ne le publie pas — ce n'est pas une tâche, c'est du bruit, et il faut la retirer.
Signale-le-moi : une file de trois cents silences cache les deux vraies questions.

---

## 5. Ce qui est vrai ce soir (11 août 2026, 20h30)

| | |
|---|---|
| fiches en base | 4 741, dont 2 608 écartées et 1 910 doublons fusionnés |
| **dates publiées confirmées par leur source** | **101** |
| dates publiées dont la source ne dit rien | 86 — voir §6 |
| fiches retirées du site aujourd'hui | **18**, toutes réversibles |
| faux organisateurs nettoyés aujourd'hui | 187 |
| file « À compléter » | 9 |
| file « À vérifier » | 9 |

**Les dix-huit retirées annonçaient des événements déjà passés** — dont une soirée de
soutien à l'Ukraine d'avril 2022, en ligne pour avril 2027. Le mécanisme : quand le texte
d'une source ne porte pas d'année et que le jour est déjà écoulé, la chaîne bascule à
l'année suivante. L'événement devient « à venir », traverse toutes les portes, et se publie.

Ce qui les a démasquées : **le jour de la semaine**. « sabato 7 maggio » ne colle qu'à une
année sur sept. C'est une donnée gratuite, écrite par quelqu'un qui savait de quoi il
parlait, et personne ne la lisait.

---

## 6. Ce qui reste ouvert, par ordre d'importance

**a) Le flux Paratissima republie ses archives.** Neuf de ses fiches étaient des annonces
de 2021-2023 remises en ligne comme à venir. Les corriger ce soir ne l'empêche pas de
recommencer : la règle du jour de la semaine doit descendre **au niveau de la collecte**,
pas seulement après publication.

**b) Les cinq signalements qui vont revenir tous les jours.** Terra Madre et les autres sont
vérifiés et bons ; ils réapparaîtront à chaque passage à l'identique. Une liste qui affiche
toujours les mêmes lignes connues apprend à ne plus la lire — et le jour où une sixième
arrive, personne ne la voit. Il manque une mémoire « vérifié, classé sans suite ».

**c) Les 86 muettes.** Quatre fiches publiées sur dix portent une date qu'aucun texte en
notre possession ne corrobore : elle vient de la page ou du modèle, et on n'en garde aucune
trace. Garder la phrase source au moment de la datation ferait monter ce chiffre
mécaniquement.

**d) Ce qui attend le 1ᵉʳ septembre** (le plafond d'API bloque la rédaction jusque-là) :
le titre de la fiche Saint-Ours, qui annonce « 2026 » pour un événement de 2027 ; et six
articles en ligne qui nomment un faux organisateur (une journaliste prise pour
l'organisatrice).

---

## 7. Quand quelque chose ne va pas

| symptôme | où regarder |
|---|---|
| pas de bilan Slack à 11h | `logs/bilan_matin.log`, puis `logs/` du cron concerné |
| une fiche a disparu du site | elle est probablement à la **corbeille** WordPress, pas supprimée |
| un chiffre te paraît faux | il l'est peut-être : demande-moi son périmètre |
| un script s'arrête en erreur | colle-moi la sortie complète, c'est ce qui marche le mieux |
| tu ne sais plus si c'est réversible | si c'est décrit dans ce guide, ça l'est |

**Le meilleur outil de diagnostic de ce projet, c'est toi qui colles une sortie de
terminal.** Sur les vingt-et-une erreurs relevées le 11 août, tu en as attrapé sept — pas
en lisant du code, en regardant des chiffres qui ne collaient pas entre eux.

---

## 8. Ce que je ne ferai jamais sans te demander

Effacer (`rm -rf`, `DELETE`, `DROP`), forcer un push git, supprimer définitivement un post
WordPress, lire le `.env`, installer quoi que ce soit sur le serveur, ou élargir mes
propres droits.

Ce que je fais seul, parce que ça se défait : corbeille, changement de statut, publication,
traduction, enrichissement, dates, lieux, `git commit` et `git push` sur la branche de
travail.

**Et ce qui reste ton arbitrage même si rien ne me bloque techniquement** : défusionner
deux fiches, re-classer une fiche que tu as rejetée toi-même, trancher un cas éditorial
limite, déployer du CSS. Dans le doute sur une décision **éditoriale**, je propose au lieu
d'agir.
