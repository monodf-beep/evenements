#!/usr/bin/env bash
# ============================================================================
# Pipeline QUOTIDIEN Agenda Sabauda — collecte → préparation → porte qualité.
# Conçu pour cron : chaque étape est IDEMPOTENTE (ne retraite que le nouveau) et
# NON BLOQUANTE (un échec isolé n'arrête pas la chaîne). Rien n'est publié en
# ligne : l'auto-complétion pousse en BROUILLON WordPress + signale sur Slack.
#
# Coût API : évaluation / enrichissement / visuels / recherches web sont bornés
# (période + score + --cap). Ajuste les caps/fenêtre selon ton budget.
#
# Installation (crontab de root sur le VPS) :
#   crontab -e   puis ajoute :
#     # Pipeline Agenda Sabauda — tous les jours à 6h05
#     5 6 * * *  /root/evenements/deploy/cron_pipeline.sh >> /root/evenements/logs/cron_pipeline.log 2>&1
#     # Auto-complétion seule à 6h40 (rattrape ce qui reste)  — optionnel
#     40 6 * * * /root/evenements/deploy/cron_pipeline.sh autocomplete >> /root/evenements/logs/cron_pipeline.log 2>&1
#     # Brouillon newsletter — lundi 7h00 (envoi manuel ensuite)
#     0 7 * * 1  /root/evenements/deploy/cron_pipeline.sh newsletter  >> /root/evenements/logs/cron_pipeline.log 2>&1
#     # Audit visuel en lot (planches contact + agent vision, tout le catalogue) —
#     # dimanche 5h00, digest Slack des photos suspectes. Coût borné mais réel (une
#     # planche ~20 événements = 1 appel vision) : hebdo, pas quotidien.
#     0 5 * * 0  /root/evenements/deploy/cron_pipeline.sh images-audit >> /root/evenements/logs/cron_pipeline.log 2>&1
#
#   (rends-le exécutable une fois : chmod +x /root/evenements/deploy/cron_pipeline.sh)
# ============================================================================
set -uo pipefail

ROOT="/root/evenements"
PY="$ROOT/.venv/bin/python3"
cd "$ROOT" || exit 1

# Fenêtre de travail glissante : aujourd'hui → +N jours (pour les étapes bornées à
# une période : évaluation, enrichissement, visuels). Configurable via
# PIPELINE_WINDOW_DAYS (.env) — défaut 180 j. Une fenêtre trop courte (ex. 90) laisse
# les événements annoncés tôt (festivals/expos, fréquent côté italien) coincés en
# 'pending' : jamais évalués → jamais publiés. Voir scripts/diagnose_italien.py.
FROM="$(date +%F)"
TO="$(date -d "+${PIPELINE_WINDOW_DAYS:-180} days" +%F)"

log() { echo "[$(date '+%F %T')] $*"; }

# Lance une étape sans jamais casser la chaîne (log l'échec et continue).
step() {
  local name="$1"; shift
  log "▶ $name"
  if "$@"; then log "✓ $name"; else log "✗ $name (échec — on continue)"; fi
}

MODE="${1:-full}"

run_autocomplete() {
  # Porte qualité : complète (scrape + recherche web + image vérifiée), pousse les
  # COMPLETS en brouillon, signale le reste sur Slack. Borné à 30 / run.
  step "autocomplete" "$PY" -m scripts.autocomplete --cap 30
}

case "$MODE" in
  autocomplete)
    run_autocomplete
    ;;
  newsletter)
    step "newsletter (brouillon)" "$PY" -m scripts.newsletter
    ;;
  images-audit)
    step "audit visuel (planches contact)" "$PY" -m scripts.image_audit
    ;;
  full|*)
    log "=== PIPELINE QUOTIDIEN (fenêtre $FROM → $TO) ==="
    # 1) Collecte
    step "scrape RSS"        "$PY" -m scripts.scraper_events
    step "gmail newsletters" "$PY" -m scripts.gmail_collect
    step "gmail relink"      "$PY" -m scripts.gmail_relink --execute
    step "dossiers de presse" "$PY" -m scripts.press_kits
    # 2) Préparation
    step "déduplication"     "$PY" -m scripts.dedupe
    step "datation"          "$PY" -m scripts.dates
    step "lieux"             "$PY" -m scripts.venues
    step "évaluation"        "$PY" -m scripts.evaluator --from "$FROM" --to "$TO"
    step "visuels"           "$PY" -m scripts.visuals   --from "$FROM" --to "$TO"
    step "enrichissement"    "$PY" -m scripts.enrich     --from "$FROM" --to "$TO"
    # 3) Complétion haut de panier (coûteux, borné) + porte qualité
    step "lieux (web)"       "$PY" -m scripts.venues_web --cap 15 --min-score 7
    step "dates (web)"       "$PY" -m scripts.dates_web  --cap 15 --min-score 7
    # Cible spécifiquement les événements encore en bannière générique (ou sans image) —
    # recherche web + double vérif vision, seul étage capable de vraiment TROUVER une
    # photo pertinente. Cooldown 7j intégré (WEB_COOLDOWN_DAYS) : ne re-tente pas tous
    # les jours un cas déjà essayé récemment.
    step "images (web)"      "$PY" -m scripts.images_web --cap 15 --min-score 7
    step "écarter les passés" "$PY" -m scripts.purge_past --execute
    run_autocomplete
    log "=== FIN PIPELINE ==="
    ;;
esac
