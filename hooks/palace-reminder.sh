#!/bin/bash
# SessionEnd reminder to flush learnings + (occasionally) nudge a retention quiz.
# Fires only when pwd maps to a wing. Project identity resolved via palace-map
# (single source: projects/_mapping.json).
_OV_VAULT="$VAULT_DIR"
_OV_PCD="$PALACE_CLAUDE_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
export VAULT_DIR PALACE_CLAUDE_DIR
CURRENT_PWD="${PWD:-$(pwd)}"
MAP="$PALACE_CLAUDE_DIR/hooks/palace-map"
project="$("$MAP" resolve "$CURRENT_PWD")"
[ -z "$project" ] && exit 0

msg="Palace: run /palace update to persist session learnings."
if [ "$("$MAP" quiz-status "$project")" = "NUDGE" ]; then
  msg="$msg Also: it's been a few days since /palace:quiz on $project — worth testing retention."
fi
printf '{"systemMessage": "%s"}\n' "$msg"
