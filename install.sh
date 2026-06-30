#!/usr/bin/env bash
# Installation du backoffice Agenda Cultura Sabauda.
# Crée l'environnement virtuel, installe les dépendances et prépare le .env.
# Usage : bash install.sh
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Vérification de Python 3.10+"
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERREUR : Python 3 introuvable. Installe Python 3.10+ puis relance." >&2
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit("ERREUR : Python 3.10+ requis (version detectee : %d.%d)" % sys.version_info[:2])
PY

echo "==> Création de l'environnement virtuel (.venv)"
python3 -m venv .venv

echo "==> Installation des dépendances"
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Création du fichier .env (à compléter)"
  cp .env.example .env
else
  echo "==> .env déjà présent, conservé tel quel"
fi

mkdir -p config data logs

echo ""
echo "✅ Installation terminée."
echo ""
echo "Étapes suivantes :"
echo "  1. Éditer .env : ANTHROPIC_API_KEY, WP_URL/WP_USER/WP_APP_PASSWORD,"
echo "     BACKOFFICE_USER/BACKOFFICE_PASSWORD."
echo "  2. (Canal Gmail) déposer config/credentials.json puis :"
echo "         .venv/bin/python scripts/authorize.py --manual   (voir docs/SETUP_GMAIL.md)"
echo "  3. Test collecte + évaluation :"
echo "         .venv/bin/python scripts/scraper_events.py"
echo "         .venv/bin/python scripts/evaluator.py"
echo "  4. Service + Traefik + cron : voir docs/DEPLOIEMENT_HOSTINGER.md"
