# Commandes terminales — au retour du 3 septembre

Compagnon PUREMENT PRATIQUE de `docs/AU_RETOUR_2026-09-03.md`. Ici : la commande, rien
d'autre. Pour le POURQUOI de chaque étape, ouvrir l'autre document — les motifs, les
décisions déjà prises et ce qu'elles excluent y sont détaillés.

Tout se lance depuis le VPS, dans `~/evenements`.

---

## 1. Vérifier que le site répond

```bash
curl -4 -sS -m 10 -o /dev/null -w "%{http_code}\n" https://agendasabauda.eu/wp-json/cs/v1/
```

`200` → continuer. `000` ou timeout → s'arrêter là, voir `docs/PANNE_OVH_2026-08-18.md`.
Ne pas relancer en boucle.

---

## 2. Déployer et rattraper le retard de publication

```bash
bash deploy/update.sh
```

```bash
nohup .venv/bin/python -m scripts.publish_batch_as --update --skip-media --cap 200 > /tmp/lot.log 2>&1 &
tail -20 /tmp/lot.log
```

Le lendemain, vérifier qu'il n'est rien resté derrière le plafond de 200 :

```bash
.venv/bin/python -m scripts.publish_batch_as --update --skip-media --cap 200 --dry-run
```

---

## 3. Les quatre mesures (lecture seule — rien n'est modifié)

```bash
.venv/bin/python -m scripts.audit_deplacement
```

Deux relevés dans sa sortie : le premier à jalons espacés (0/15/30/60/90/120/180 jours),
le second — « Si je reviens chaque semaine, est-ce que je vois autre chose ? » — un point
par semaine sur tout l'horizon, avec la PIRE série de semaines consécutives sans
changement par territoire. C'est le second qui répond à la question posée le 24/08.

```bash
.venv/bin/python -m scripts.audit_home_visible
```

```bash
.venv/bin/python -m scripts.audit_acronymes
```

```bash
.venv/bin/python -m scripts.audit_vocabulaire
```

Ces quatre chiffres ont dû arriver dans le digest Slack les 19 et 20 août. Si le digest
est introuvable, ces commandes redonnent tout — elles ne modifient rien, on peut les
relancer sans risque.

---

## 4. Rejouer ce que la panne a empêché

```bash
.venv/bin/python -m scripts.verifier_doublons_publies --en-ligne
```

Trois traductions refusées le 18/08 parce que la panne rendait leur original injoignable —
à rejouer telles quelles :

```bash
.venv/bin/python -m scripts.translate_events --retranslate 2414 4576 3314 --apply
```

Un trash proposé le 17/08 à 9h54, jamais confirmé exécuté — vérifier D'ABORD à la main
avant toute commande (dans Novamira, pas ici : lire l'état réel des posts 2466, 3087, 4621
avant de les corbeiller une seconde fois).

---

## 5. Vérifier l'état général

```bash
.venv/bin/python -m tests.run_all
```

```bash
.venv/bin/python -m scripts.publier_sante
```

---

# Ajouts de la dernière semaine

Ces commandes-ci ne sont pas dans le déroulé principal : ce sont des vérifications
ponctuelles, ajoutées entre le 25 et le 31/08. À faire après le tour ci-dessus.

### Vérifier la branche du serveur, et la fiche 4839

```bash
# Confirmer que le serveur est bien reparti sur la bonne branche et à jour
cd ~/evenements && git rev-parse --abbrev-ref HEAD && git log -1 --format='%h %ci'
# Attendu : claude/quirky-davinci-jvqrnw, commit 545b8fa ou plus récent
```

```bash
# Fiche 4839 « Coro & Bentu » (restaurant mal catégorisé) — trouver le bon audit d'abord
grep -rln "4839\|Coro.*Bentu" logs/*.log
```

Une fois le script identifié : le lancer SANS `--apply`/`--execute` d'abord (règle 4),
lire la sortie, puis appliquer.

---

### Relire ce que le cerveau a fait pendant l'absence

```bash
# Son journal, jour par jour (gestes posés, différés, escaladés)
less logs/cerveau.log
```

```bash
# L'arrêter si besoin : commenter sa ligne dans crontab.txt puis
crontab crontab.txt
```

---

### Inventaire WordPress — premier lancement, SUPERVISÉ

```bash
scripts/audit_wp_code.sh
```

Lire la sortie en entier avant d'en tirer une conclusion : jamais éprouvé contre la
vraie production (voir `AU_RETOUR_2026-09-03.md`, section 0 sexies). Pas de cron tant
que ce premier passage n'a pas été relu.

---

### Sources par province — voir les manques

```bash
.venv/bin/python -m scripts.audit_sources_provinces
```

Ou directement dans le back-office : `/sources-provinces` (menu Analyse). Manque déjà
trouvé au 31/08 : la province de Novara (Piémont), zéro source RSS. Le zéro newsletter a
été comblé le même jour (recherche exhaustive, voir `AU_RETOUR_2026-09-03.md`
section 0 septies) — le zéro source RSS, lui, reste ouvert.

---

### Heure de l'événement — vérifier avant de déployer

```bash
curl -4 -sS https://agendasabauda.eu/wp-json/cs/v1/version
```

`404` → toujours pas déployé, suivre `docs/DEPLOIEMENT_WORDPRESS.md` §3 (Novamira,
sauvegarde d'abord) pour coller `deploy/wordpress/cs-publish.php`. Une réponse JSON →
déjà réglé par une autre voie, ne rien écraser sans vérifier ce qui tourne.

---

## ~~Nettoyer le crontab temporaire~~ — FAIT le 31/08

Les quatre lignes datées `19-20 8` ont été retirées du dépôt. Reste à vérifier que le
crontab INSTALLÉ a suivi :

```bash
crontab -l | grep '19-20'   # ne doit RIEN rendre
```

Si une ligne sort encore, le fichier du dépôt est propre — seule l'installation a pu
rester en retard :

```bash
crontab crontab.txt
```

