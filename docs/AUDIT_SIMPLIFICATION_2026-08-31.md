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

*(section complétée après les lectures en cours)*

---

# 3. DEMANDE UNE RÉFLEXION PLUS APPROFONDIE

### 3.1 `app/app.py` : 4 672 lignes, 66 routes dans un seul fichier

C'est de loin la plus grosse concentration du dépôt — plus du double du deuxième
(`scripts/enrich.py`, 2 170 lignes). Le découper rendrait chaque écran plus facile à
modifier sans risque… mais c'est le back-office **en production**, et un découpage de
4 700 lignes est précisément le genre de chantier qui casse en silence.

Ce n'est pas urgent : rien ne dysfonctionne. C'est une dette à trancher à froid, avec un
plan d'étapes vérifiables, jamais « en passant ».

### 3.2 La branche `agenda-sabauda-homepage-test-exckrp` — 126 commits, 10 285 lignes

Un chantier parallèle entier : `wordpress/design-system/` avec les gabarits de page
(accueil, mentions légales, crédits photos, confidentialité, page newsletter,
en-tête/pied, `tokens.css`, filtre de rail par jour). Dernier travail le **19/08**.

Ce n'est ni du mort ni du mergeable-à-l'aveugle : c'est un travail de design qui touche
l'apparence du site public. La question à trancher n'est pas technique — c'est « veut-on
ce design ? ». Tant qu'elle n'est pas posée, la branche vit à côté sans risque.

---

## Ce qui va BIEN et qu'il ne faut PAS toucher

Un audit qui ne dit que ce qui cloche donne une image fausse.

- **Le harnais de tests : 106 fixtures en 46 secondes.** Il tourne avant chaque
  déploiement et ne coûte presque rien. Aucune raison de l'alléger.
- **Le dépôt est propre** : pas de worktree d'essai résiduel, pas de fichier bâtard à la
  racine, `logs/` à 520 Ko.
- **Les branches de travail sont à jour** : la branche déployée porte exactement ce qui
  est poussé.
