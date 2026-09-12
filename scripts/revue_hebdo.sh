#!/usr/bin/env bash
# Revue adversariale hebdomadaire — dimanche 6h, après le grand ménage de 5h.
#
# POURQUOI ELLE EXISTE. Le 2026-08-04, quatre agents relisant huit fichiers écrits le jour
# même y ont trouvé QUINZE défauts — dont plusieurs dans les correctifs censés fermer les
# défauts de la veille, et trois fois la même faute de méthode (une fixture incapable de
# contredire son auteur). Aucun n'avait été vu par celui qui les avait écrits, et tous
# l'ont été en quelques minutes par quelqu'un d'autre.
#
# La leçon n'est pas « il faut mieux se relire » : c'est que se relire soi-même ne marche
# pas, et qu'attendre qu'un défaut se voie sur la home coûte des semaines. Cette revue
# rejoue donc ce dispositif chaque dimanche, sur ce qui a changé dans la semaine.
#
# ELLE N'ÉCRIT RIEN, et c'est délibéré (cf. --disallowedTools plus bas). Un correctif
# appliqué sans relecture humaine, un dimanche matin, sur un dépôt en production, serait
# l'automatisme que Franck refuse : « on ne doit pas faire des choses automatiques pour
# faire des choses automatiques sans réfléchir ». Elle CONSTATE, et le geste reste humain.
#
# Mêmes quatre verrous que scripts/bilan_matin.sh — lire sa docstring, elle explique
# pourquoi --strict-mcp-config sans --mcp-config est indispensable (sans ça, le cron
# hériterait des connecteurs de la session, dont plusieurs savent publier).
#
# Dimanche 6h et non le matin en semaine : la revue lit `git log --since="8 days ago"`, et
# une semaine entière de commits est le bon grain. Après weekly_audits (5h) pour qu'elle
# voie l'état d'après ménage, avant le digest du lundi 8h qui la reprendra si besoin.
set -uo pipefail

cd /root/evenements || exit 1

JOURNAL="logs/revue_hebdo.log"
CLAUDE="/root/.local/bin/claude"

# Lecture et exécution de tests SEULEMENT. `python3` est autorisé sans restriction d'argument
# parce que la revue DOIT pouvoir exécuter ses propres cas de test sur une base jetable —
# c'est tout l'intérêt du dispositif, une lecture de code n'ayant rien trouvé le 2026-08-04.
# Le risque est borné par --disallowedTools : sans Write ni Edit, un script de test ne peut
# pas être déposé dans le dépôt, et la consigne impose le tempfile.
OUTILS=(
  Read Glob Grep
  "Bash(git log:*)"
  "Bash(git diff:*)"
  "Bash(git show:*)"
  "Bash(git status:*)"
  "Bash(python3:*)"
  "Bash(.venv/bin/python:*)"
)
INTERDITS=(Write Edit NotebookEdit WebFetch WebSearch)

echo "=== $(date '+%Y-%m-%d %H:%M:%S') — revue hebdomadaire ===" >> "$JOURNAL"

REVUE="$("$CLAUDE" -p "$(cat config/consigne_revue_hebdo.txt)" \
  --allowedTools "${OUTILS[@]}" \
  --disallowedTools "${INTERDITS[@]}" \
  --strict-mcp-config \
  2>> "$JOURNAL")"
CODE=$?

if [ $CODE -ne 0 ]; then
  # Un échec SILENCIEUX est le pire cas : personne ne remarque l'absence d'un message
  # hebdomadaire, et celui-ci est justement là pour attraper ce qui passe inaperçu.
  echo "claude -p a échoué (code $CODE)" >> "$JOURNAL"
  printf '%s\n' "⚠️ La revue hebdomadaire n'a pas pu être produite (claude -p, code $CODE). Voir logs/revue_hebdo.log." \
    | .venv/bin/python scripts/slack_send.py
  exit $CODE
fi

printf '%s\n' "$REVUE" >> "$JOURNAL"
printf '%s\n' "$REVUE" | .venv/bin/python scripts/slack_send.py --prefixe "🔍 *Revue du code — semaine du $(date '+%d/%m')*"
