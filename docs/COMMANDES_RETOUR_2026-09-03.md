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

## 5. Nettoyer le crontab temporaire

Ces quatre lignes ne doivent PAS survivre — elles repartiraient l'an prochain sinon.
Les retirer de `crontab.txt` :

```
40 11 19-20 8 * cd /root/evenements && .venv/bin/python -m scripts.audit_deplacement --slack >> logs/audit_deplacement.log 2>&1
41 11 19-20 8 * cd /root/evenements && .venv/bin/python -m scripts.audit_home_visible --slack >> logs/audit_home_visible.log 2>&1
42 11 19-20 8 * cd /root/evenements && .venv/bin/python -m scripts.audit_acronymes --slack >> logs/audit_acronymes.log 2>&1
43 11 19-20 8 * cd /root/evenements && .venv/bin/python -m scripts.audit_vocabulaire --slack >> logs/audit_vocabulaire.log 2>&1
```

(et le bloc de commentaires juste au-dessus, qui n'a plus d'objet une fois les lignes
parties). Puis committer/pousser, et laisser `auto_deploiement` de 7h50 installer le
crontab nettoyé — ou forcer tout de suite :

```bash
.venv/bin/python -m scripts.auto_deploiement --apply
```

---

## 6. Vérifier l'état général

```bash
.venv/bin/python -m tests.run_all
```

```bash
.venv/bin/python -m scripts.publier_sante
```
