#!/usr/bin/env bash
# Bilan du matin — 11h. Lance Claude Code en NON-INTERACTIF sur la consigne de
# config/consigne_bilan_matin.txt, puis transmet sa sortie sur Slack.
#
# POURQUOI UN SCRIPT ET PAS UNE LIGNE DE CRON. Trois raisons :
#   1. la consigne se relit et se modifie sans toucher au crontab ;
#   2. la liste des outils autorisés est longue — dans une ligne de cron elle serait
#      illisible, donc jamais relue, donc jamais vérifiée ;
#   3. le « % » est un caractère spécial du crontab (il y est traduit en saut de
#      ligne). Tout texte un peu riche mis directement dans le crontab est un piège.
#
# CE QUI GARANTIT QUE L'AGENT N'ÉCRIT RIEN — quatre verrous, pas un seul :
#   a. --allowedTools ne liste que des lectures et des audits (liste `allow` de
#      .claude/settings.json, MOINS `git add`, `git pull` et `backup_db.py` qui
#      écrivent — inutiles pour un bilan) ;
#   b. --disallowedTools bloque explicitement les outils d'écriture de fichiers ;
#   c. --strict-mcp-config sans --mcp-config : AUCUN serveur MCP n'est chargé. Sans
#      ça, le cron hériterait des connecteurs de la session (Gmail, WordPress,
#      Shopify, Canva, Todoist…), dont plusieurs savent publier ;
#   d. en mode -p, un outil non autorisé ne peut pas demander confirmation : il est
#      refusé. Le défaut est donc « non », pas « oui ».
#   Et par-dessus, .claude/settings.json s'applique quand même : ses règles `deny`
#   (rm -rf, DELETE FROM, lecture du .env…) valent aussi pour cette session.
#
# L'agent NE POSTE PAS lui-même : il écrit son bilan sur la sortie standard, et c'est
# ce script qui l'envoie via scripts/slack_send.py. C'est délibéré — cf. sa docstring.
set -uo pipefail

cd /root/evenements || exit 1

JOURNAL="logs/bilan_matin.log"
CLAUDE="/root/.local/bin/claude"

# Outils autorisés — lecture et audits uniquement.
OUTILS=(
  Read Glob Grep
  "Bash(git status:*)"
  "Bash(git diff:*)"
  "Bash(git log:*)"
  "Bash(git branch:*)"
  "Bash(git show:*)"
  "Bash(.venv/bin/python -m scripts.audit_wp_ghosts:*)"
  "Bash(.venv/bin/python -m scripts.audit_dedupe_damage:*)"
  "Bash(.venv/bin/python scripts/count_grasse.py:*)"
  "Bash(.venv/bin/python scripts/status_report.py:*)"
  "Bash(.venv/bin/python scripts/diagnose_backlog.py:*)"
)
INTERDITS=(Write Edit NotebookEdit WebFetch WebSearch)

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — bilan du matin ===" >> "$JOURNAL"

BILAN="$("$CLAUDE" -p "$(cat config/consigne_bilan_matin.txt)" \
  --allowedTools "${OUTILS[@]}" \
  --disallowedTools "${INTERDITS[@]}" \
  --strict-mcp-config \
  2>> "$JOURNAL")"
CODE=$?

if [ $CODE -ne 0 ]; then
  # Un échec SILENCIEUX est le pire cas : personne ne remarque l'absence d'un
  # message quotidien. On prévient sur Slack que le bilan n'a pas pu être produit.
  echo "claude -p a échoué (code $CODE)" >> "$JOURNAL"
  printf '%s\n' "⚠️ Le bilan de 11h n'a pas pu être produit (claude -p, code $CODE). Voir logs/bilan_matin.log." \
    | .venv/bin/python scripts/slack_send.py
  exit $CODE
fi

printf '%s\n' "$BILAN" >> "$JOURNAL"
printf '%s\n' "$BILAN" | .venv/bin/python scripts/slack_send.py --prefixe "🌅 *Bilan du matin* — $(date '+%d/%m')"
