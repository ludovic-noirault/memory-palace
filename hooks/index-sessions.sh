#!/bin/bash
# Re-index sessions into QMD on Stop. Config: env var > palace.env > default.
_OV_VAULT="$VAULT_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
export VAULT_DIR   # extract-sessions.py reads it from the environment
python3 "$PALACE_CLAUDE_DIR/skills/recall/scripts/extract-sessions.py" --days 3
qmd update
