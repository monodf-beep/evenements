# Déploiement sur le VPS Hostinger — backoffice Agenda

Même topologie que l'Observatoire : l'app tourne en **loopback** via **systemd**,
exposée en **HTTPS par Traefik** (Let's Encrypt). Le backoffice occupe un
sous-domaine dédié **`agenda.culturasabauda.eu`**.

> 🔒 L'auth HTTP Basic ne transite jamais en clair : Traefik impose HTTPS.
> Les secrets (`.env`, `config/credentials.json`, `config/token.json`) ne sont
> **jamais** committés (voir `.gitignore`).

## Pré-requis

- VPS Ubuntu avec **Traefik** déjà en place (entryPoint `websecure`, certResolver
  `letsencrypt`, provider fichier dynamique surveillé — c'est le cas pour
  l'Observatoire).
- **DNS** : un enregistrement **A `agenda.culturasabauda.eu` → IP du VPS**.
- Accès SSH `root`.

## 1. Récupérer le code

```bash
cd /root
git clone <URL_du_repo> evenements
cd evenements
git checkout claude/quirky-davinci-jvqrnw
```

## 2. Installer (venv + dépendances + .env)

```bash
bash install.sh
nano .env      # remplir les variables (voir ci-dessous)
```

Variables `.env` à renseigner (voir `.env.example`) :
`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_MODEL_EXTRACT`,
`WP_URL`, `WP_USER`, `WP_APP_PASSWORD`,
`BACKOFFICE_USER`, `BACKOFFICE_PASSWORD`,
`GMAIL_LABEL` (= `Agenda`), `GMAIL_LOOKBACK_DAYS`.

## 3. (Canal Gmail) autoriser l'accès en lecture

Voir `docs/SETUP_GMAIL.md` pour générer `config/credentials.json`, puis :

```bash
.venv/bin/python scripts/authorize.py --manual   # VPS sans navigateur
```

## 4. Tester la collecte et l'évaluation

```bash
.venv/bin/python scripts/scraper_events.py   # RSS → SQLite
.venv/bin/python scripts/gmail_collect.py     # newsletters → SQLite (si Gmail configuré)
.venv/bin/python scripts/evaluator.py         # évaluation LLM
```

## 5. Installer le service systemd

```bash
sudo cp deploy/agenda-admin.service /etc/systemd/system/
# adapter User=/WorkingDirectory=/ExecStart= si le projet n'est pas sous /root/evenements
sudo systemctl daemon-reload
sudo systemctl enable --now agenda-admin
systemctl status agenda-admin          # doit être "active (running)" sur 127.0.0.1:8098
```

## 6. Exposer en HTTPS via Traefik

```bash
sudo cp deploy/traefik-agenda.yml /docker/traefik/dynamic/
# Traefik charge le fichier à chaud (providers.file.watch=true)
```

Ouvrir **https://agenda.culturasabauda.eu** → login `BACKOFFICE_USER` /
`BACKOFFICE_PASSWORD`. Le certificat Let's Encrypt est émis au 1er accès.

## 7. Planifier la collecte (cron)

```bash
crontab crontab.txt      # scraping 8h, newsletters 8h15, évaluation 9h
crontab -l               # vérifier
```

## Mettre à jour (déploiements suivants)

```bash
cd /root/evenements && bash deploy.sh
```

`deploy.sh` force la branche canonique, met à jour les dépendances et redémarre
le service. Les secrets et la base `data/events.db` sont préservés (non suivis par git).

## Dépannage

| Symptôme | Vérifier |
|---|---|
| 502 / Bad Gateway | `systemctl status agenda-admin` (le service écoute-t-il sur 8098 ?) |
| Certificat absent / HTTP | DNS `agenda.culturasabauda.eu` → VPS ? Fichier Traefik bien copié ? |
| 401 en boucle | `BACKOFFICE_USER` / `BACKOFFICE_PASSWORD` du `.env` |
| Gmail vide | label `Agenda` posé sur les mails ? `token.json` généré (étape 3) ? |
| Pas d'événements à valider | lancer `scraper_events.py` + `evaluator.py`, puis voir le dashboard |
