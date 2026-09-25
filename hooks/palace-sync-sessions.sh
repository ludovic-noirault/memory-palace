#!/bin/bash
# Stop hook: sync this session's transcript into the vault, then mask tokens in it.
# Config: env var > palace.env > default. stdin carries the hook JSON for claude-sessions.
_OV_VAULT="$VAULT_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${PALACE_CLAUDE_DIR:-$HOME/.claude}"

VAULT_DIR="$VAULT_DIR" python3 "$PALACE_CLAUDE_DIR/skills/sync-claude-sessions/scripts/claude-sessions" sync
python3 "$PALACE_CLAUDE_DIR/hooks/scan-secrets.py" --redact "$VAULT_DIR/claude-sessions" --days 1 > /dev/null
