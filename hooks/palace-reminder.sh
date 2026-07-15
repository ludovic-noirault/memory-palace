#!/bin/bash
# SessionEnd reminder to flush learnings. Fires only when pwd maps to a wing.
# Project identity resolved via palace-map (single source: projects/_mapping.json).
_OV_PCD="$PALACE_CLAUDE_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
export VAULT_DIR PALACE_CLAUDE_DIR
CURRENT_PWD="${PWD:-$(pwd)}"
project="$("$PALACE_CLAUDE_DIR/hooks/palace-map" resolve "$CURRENT_PWD")"
[ -n "$project" ] && echo '{"systemMessage": "Palace: run /palace update to persist session learnings."}'
