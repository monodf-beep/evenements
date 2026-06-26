# Backoffice Agenda — Cultura Sabauda (Sprint 1)

Backoffice d'agrégation d'événements culturels pour [Cultura Sabauda](https://culturasabauda.eu),
média culturel bilingue FR/IT couvrant **Savoie · Piémont · Vallée d'Aoste · Nice**.

Le pipeline scrape des événements depuis des flux RSS, les fait évaluer par Claude
(score éditorial 0-10), puis permet à Franck de valider en quelques minutes ceux qui
apparaîtront sur la homepage. Cohérent avec l'écosystème de
[l'Observatoire Business Sabaudo](https://github.com/monodf-beep/observatoire-business-sabaudo)
(réutilise `utils/logger.py`, `utils/sources.py` et les `config/*.txt`).

## Pipeline

```
scraper_events.py   (cron 8h)   RSS → SQLite (statut=pending), dédup stricte par url_source
evaluator.py        (cron 9h)   Claude évalue → score ≥7 evaluated · 4-6 published_sub · <4 rejected
app.py              (gunicorn)  Backoffice Franck : valide les score≥7 → draft WordPress
publisher.py                    WP REST API + Application Password — TOUJOURS en draft
```

### Bifurcation par score

| Score | Statut          | Destination                                   |
|-------|-----------------|-----------------------------------------------|
| ≥ 7   | `evaluated`     | Validation Franck → homepage Cultura Sabauda  |
| 4-6   | `published_sub` | Publication auto site dédié (Sprint 2)        |
| < 4   | `rejected`      | Rejet automatique                             |

## Installation (VPS)

```bash
cd /var/www
git clone <repo> agenda-backoffice
cd agenda-backoffice
cp .env.example .env          # puis remplir les variables
pip install -r requirements.txt --break-system-packages
mkdir -p data logs

python scripts/scraper_events.py   # test scraping
python scripts/evaluator.py        # test évaluation
gunicorn -w 1 -b 127.0.0.1:5001 'app.app:app'   # backoffice

# Configurer nginx (nginx.conf) + crontab (crontab.txt)
```

## Configuration

Toutes les variables sont dans `.env` (voir `.env.example`) :
`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `DB_PATH`, `WP_URL`, `WP_USER`,
`WP_APP_PASSWORD`, `BACKOFFICE_USER`, `BACKOFFICE_PASSWORD`.

Les sources RSS se déclarent dans `config/sources.txt` (`url;territoire;nom`).

## Garde-fous

- **Tout part en `draft` WordPress** — jamais `publish` automatique. Franck reste seul RC.
- **Géographie stricte** : hors des 4 territoires → score 0.
- **RSS uniquement** en Sprint 1 (scraping HTML reporté en Sprint 2).

## Hors Sprint 1

Scraping HTML · publication auto du site dédié · CPT JetEngine `agenda` ·
SSL/certbot · billetterie.
