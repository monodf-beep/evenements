# Backoffice Agenda — Cultura Sabauda (Sprint 1)

Backoffice d'agrégation d'événements culturels pour
[Cultura Sabauda](https://culturasabauda.eu), média culturel bilingue FR/IT couvrant
**Savoie · Piémont · Vallée d'Aoste · Nice**.

Le pipeline scrape des événements depuis des flux RSS, les fait évaluer par Claude
(score éditorial 0-10), puis permet à Franck de valider en quelques minutes ceux qui
apparaîtront sur la homepage. Le reste alimente (Sprint 2) un site dédié pour le SEO.

Cohérent avec l'écosystème de
[l'Observatoire Business Sabaudo](https://github.com/monodf-beep/observatoire-business-sabaudo) :
mêmes choix (SDK `anthropic` direct, SQLite stdlib, pas de framework lourd) et
réutilisation directe de ses utilitaires (voir [Fichiers synchronisés](#fichiers-synchronisés)).

## Architecture

```
┌─────────────────────┐
│ config/sources.txt  │   url_rss ; territoire ; nom_source
└──────────┬──────────┘
           │
           ▼   cron 8h
┌──────────────────────────────────────────────────────────────┐
│ scripts/scraper_events.py                                      │
│  • feedparser sur chaque flux                                  │
│  • déduplication STRICTE par url_source (UNIQUE en base)       │
│  • extraction image (media:content / enclosures / thumbnail)   │
│    + filtrage des CDN de presse (utils.sources.is_blocked_image)│
└──────────┬───────────────────────────────────────────────────┘
           │ INSERT statut='pending'
           ▼
┌──────────────────────┐
│ data/events.db        │   SQLite — table events_raw
└──────────┬───────────┘
           │
           ▼   cron 9h
┌──────────────────────────────────────────────────────────────┐
│ scripts/evaluator.py                                           │
│  • SDK anthropic direct (ANTHROPIC_MODEL), 100 events/run      │
│  • prompt éditorial → JSON {score, categorie, justification}   │
│  • suivi coût/quota API : utils.usage (record_message / note_api_error)
│  • bifurcation par score (voir ci-dessous)                     │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│ app/app.py  (Flask + gunicorn, auth HTTP Basic)               │
│  • liste les events statut='evaluated' & score≥7 (tri desc)   │
│  • encart « Coûts API » (semaine + cumul) + alerte crédit      │
│  • actions : [Publier CS] [Subdomain] [Rejeter]               │
└──────────┬───────────────────────────────────────────────────┘
           │ [Publier CS]
           ▼
┌──────────────────────────────────────────────────────────────┐
│ scripts/publisher.py                                           │
│  • upload image → /wp-json/wp/v2/media → featured_media        │
│  • crée le post en status='draft' TOUJOURS (jamais publish)    │
│  • retourne wp_post_id → stocké en base                        │
└──────────────────────────────────────────────────────────────┘
```

## Bifurcation par score

| Score | Statut posé      | Destination                                   |
|-------|------------------|-----------------------------------------------|
| ≥ 7   | `evaluated`      | Validation Franck → homepage Cultura Sabauda  |
| 4-6   | `published_sub`  | Publication auto site dédié (Sprint 2)        |
| < 4   | `rejected`       | Rejet automatique                             |

## Statuts possibles (champ `statut` de `events_raw`)

| Statut          | Posé par            | Signification                                              |
|-----------------|---------------------|-----------------------------------------------------------|
| `pending`       | scraper             | Collecté, en attente d'évaluation LLM                     |
| `evaluated`     | evaluator (score≥7) | À valider par Franck dans le backoffice                  |
| `published_sub` | evaluator (4-6) ou backoffice | Destiné au site dédié (Sprint 2)               |
| `rejected`      | evaluator (<4 ou erreur de parsing) ou backoffice | Écarté            |
| `published_cs`  | backoffice          | Publié en **draft** sur WordPress CS (`wp_post_id_cs` rempli) |

Garde-fou : une **erreur d'appel API** (réseau / statut) laisse l'événement en
`pending` — il sera réévalué au run suivant (jamais perdu, jamais rejeté à tort).
Seul un JSON LLM illisible aboutit à `rejected`.

## Suivi des coûts API

`utils/usage.py` (repris de l'Observatoire) journalise chaque appel LLM dans
`logs/api_usage.jsonl` (tokens, coût estimé) et pose un drapeau d'alerte
(`logs/api_alert.json`) si une exception évoque un problème de crédit / facturation /
**limite d'usage**. Le backoffice affiche :

- un encart **Coûts API** : coût de la semaine en cours + cumul + nombre d'appels ;
- une **bannière rouge** tant qu'une alerte crédit/quota est active (levée
  automatiquement au prochain appel réussi).

Objectif : ne plus jamais être surpris par une limite d'usage sans visibilité.

## Fichiers synchronisés

Ces fichiers sont **repris tels quels** de l'Observatoire et portent l'en-tête
`# SYNCED FROM observatoire-business-sabaudo`. **Ne pas les faire diverger** : toute
amélioration doit se faire à la source puis être resynchronisée des deux côtés.

- `utils/logger.py` — logger horodaté (console + fichier)
- `utils/sources.py` — domaine/libellé de source, filtrage images presse, bannières
- `utils/usage.py` — suivi tokens/coût API + alerte crédit/quota
- `config/blocked_image_domains.txt` — CDN de presse proscrits
- `config/territory_images.txt` — bannières de substitution par territoire

### Plan d'extraction `cultura-core` (futur)

Ces fichiers dupliqués entre l'Observatoire et l'Agenda sont la première brique
d'un paquet partagé **`cultura-core`** :

1. **Aujourd'hui** — copie verbatim dans chaque projet, marquée `SYNCED FROM …`,
   source unique = l'Observatoire.
2. **Étape 1** — extraire `logger`, `sources`, `usage` (+ les `config/*.txt`) dans un
   dépôt `cultura-core` versionné (package Python installable).
3. **Étape 2** — Observatoire et Agenda dépendent de `cultura-core`
   (`pip install cultura-core` / sous-module), suppression des copies locales.
4. **Étape 3** — y faire converger les conventions communes (modèles, tarifs API,
   territoires, bannières de marque) pour tout futur projet de l'écosystème.

L'en-tête `SYNCED FROM` sert de marqueur pour repérer ce qui devra migrer.

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

## Configuration (`.env`)

Voir `.env.example`. Variables : `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `DB_PATH`,
`WP_URL`, `WP_USER`, `WP_APP_PASSWORD`, `BACKOFFICE_USER`, `BACKOFFICE_PASSWORD`,
`DOMAIN`. Le `.env` n'est **jamais** committé (`.gitignore`).

Les sources RSS se déclarent dans `config/sources.txt` (`url;territoire;nom`).

## Tests

```bash
pip install pytest
pytest tests/
```

`tests/test_eval.py` couvre la bifurcation des scores et le fait qu'une erreur API
laisse l'événement en `pending`.

## Garde-fous

- **Tout part en `draft` WordPress** — jamais `publish` automatique. Franck reste seul RC.
- **Géographie stricte** : hors des 4 territoires → score 0.
- **Erreur API → `pending`** (réévalué), jamais rejeté à tort.
- **RSS uniquement** en Sprint 1 (scraping HTML reporté en Sprint 2).

## Hors Sprint 1

Scraping HTML · publication auto du site dédié · CPT JetEngine `agenda` ·
SSL/certbot · billetterie · extraction `cultura-core`.
