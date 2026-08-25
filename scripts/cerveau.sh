#!/usr/bin/env bash
# Cerveau du matin — 10h40. Lance Claude Code en NON-INTERACTIF sur la consigne de
# config/consigne_cerveau.txt, puis transmet sa sortie sur Slack.
#
# D'OÙ ÇA VIENT — Franck, 2026-08-25 : « les décisions tu dois les prendre en autonomie,
# et les informations via les différents scripts ». Le déclencheur concret : la fiche
# 4839 (un restaurant classé comme événement) proposée à l'écartement QUATRE matins de
# suite sans qu'aucun geste ne soit posé — le bilan de 11h la voyait, mais il est en
# lecture seule PAR CONSTRUCTION, et personne d'autre ne lisait.
#
# LA DIVISION DU TRAVAIL, et pourquoi elle est ce qu'elle est :
#   10h40  cerveau (CE script)  — AGIT, dans les limites du réversible ;
#   11h00  bilan_matin          — lecture seule, RELIT ce que le cerveau a fait ;
#   11h45  slack_digest         — livre le tout sur le téléphone de Franck.
# L'acteur et le contrôleur sont deux agents SÉPARÉS, et le contrôleur n'a pas le droit
# d'écrire : le cerveau ne peut donc pas maquiller son propre bilan (règle 6 incarnée).
#
# CE QUI BORNE L'AGENT — même architecture de verrous que bilan_matin.sh :
#   a. --allowedTools : lectures, audits, et les SEULS scripts d'action que CLAUDE.md
#      classe réversibles (corbeille via route cs/v1, changements de statut, marqueurs
#      de résolution, pipeline normal). Chaque script est nommé UN PAR UN — jamais de
#      joker large. La fixture tests/test_cerveau.py refuse tout motif irréversible ici ;
#   b. --disallowedTools : AUCUNE écriture de fichier. Le cerveau tape des commandes,
#      il n'écrit pas de code — un correctif de code se relit dans une session, pas
#      dans un cron. C'est aussi pour ça qu'il n'a ni git add ni git commit ;
#   c. --strict-mcp-config sans --mcp-config : aucun connecteur MCP chargé ;
#   d. en mode -p, un outil non listé est refusé, pas confirmé ;
#   e. .claude/settings.json s'applique PAR-DESSUS : ses deny (rm -rf, --hard,
#      DELETE FROM, force=true, lecture du .env…) valent aussi pour cette session.
#
# L'agent NE POSTE PAS lui-même : sa sortie est le message, ce script l'envoie.
set -uo pipefail

cd /root/evenements || exit 1

JOURNAL="logs/cerveau.log"
CLAUDE="/root/.local/bin/claude"

# Lectures et audits (le même socle que bilan_matin.sh)…
OUTILS=(
  Read Glob Grep
  "Bash(git status:*)"
  "Bash(git diff:*)"
  "Bash(git log:*)"
  "Bash(git branch:*)"
  "Bash(git show:*)"
  "Bash(curl:*)"
  "Bash(.venv/bin/python -m scripts.audit_annulations:*)"
  "Bash(.venv/bin/python -m scripts.audit_non_events:*)"
  "Bash(.venv/bin/python -m scripts.audit_excluded_events:*)"
  "Bash(.venv/bin/python -m scripts.audit_wp_ghosts:*)"
  "Bash(.venv/bin/python -m scripts.audit_deplacement:*)"
  "Bash(.venv/bin/python -m scripts.audit_home_visible:*)"
  "Bash(.venv/bin/python -m scripts.audit_langue_polylang:*)"
  "Bash(.venv/bin/python scripts/status_report.py:*)"
  "Bash(.venv/bin/python scripts/diagnose_backlog.py:*)"
  "Bash(.venv/bin/python -m scripts.publier_sante:*)"
  "Bash(.venv/bin/python -m scripts.sans_api:*)"
# …et les gestes RÉVERSIBLES, un par un (CLAUDE.md, arbitrage du 2026-08-03).
# La corbeille passe par la route MAISON cs/v1/trash — réversible en un clic.
  "Bash(.venv/bin/python -m scripts.backup_db:*)"
  "Bash(.venv/bin/python scripts/backup_db.py:*)"
  "Bash(.venv/bin/python -m scripts.trash_by_ids:*)"
  "Bash(.venv/bin/python -m scripts.reconcile_catalogue:*)"
  "Bash(.venv/bin/python -m scripts.reconcile_wp_deleted:*)"
  "Bash(.venv/bin/python -m scripts.unreject_wp_online:*)"
  "Bash(.venv/bin/python -m scripts.classer_sans_suite:*)"
  "Bash(.venv/bin/python -m scripts.purge_out_of_zone:*)"
  "Bash(.venv/bin/python -m scripts.trier_sans_date:*)"
  "Bash(.venv/bin/python -m scripts.publish_batch_as:*)"
  "Bash(.venv/bin/python scripts/translate_events.py:*)"
  "Bash(.venv/bin/python -m scripts.solder_verifications:*)"
)
INTERDITS=(Write Edit NotebookEdit WebFetch WebSearch)

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — cerveau du matin ===" >> "$JOURNAL"

SORTIE="$("$CLAUDE" -p "$(cat config/consigne_cerveau.txt)" \
  --allowedTools "${OUTILS[@]}" \
  --disallowedTools "${INTERDITS[@]}" \
  --strict-mcp-config \
  2>> "$JOURNAL")"
CODE=$?

if [ $CODE -ne 0 ]; then
  # Un échec SILENCIEUX du cerveau ressemblerait à un matin sans rien à faire —
  # exactement le zéro qui ne dit pas d'où il vient. On le dit.
  echo "claude -p a échoué (code $CODE)" >> "$JOURNAL"
  printf '%s\n' "⚠️ Le cerveau de 10h40 n'a pas pu tourner (claude -p, code $CODE). Voir logs/cerveau.log — les signalements du jour n'ont PAS été traités." \
    | .venv/bin/python scripts/slack_send.py
  exit $CODE
fi

printf '%s\n' "$SORTIE" >> "$JOURNAL"
printf '%s\n' "$SORTIE" | .venv/bin/python scripts/slack_send.py --prefixe "🧠 *Cerveau du matin* — $(date '+%d/%m')"
