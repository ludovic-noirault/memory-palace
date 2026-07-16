#!/bin/bash
# Injects the memory palace CONTEXT.md for the active project into the session
# as system context. Only fires when pwd maps to a known project wing.
# Project identity is resolved via palace-map (single source: projects/_mapping.json).
# Do NOT re-add a case list here — edit _mapping.json instead.

# Config precedence: real env var > palace.env > built-in default.
_OV_VAULT="$VAULT_DIR"; _OV_PCD="$PALACE_CLAUDE_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
export VAULT_DIR PALACE_CLAUDE_DIR   # child palace-map inherits the resolved config

VAULT="$VAULT_DIR/projects"
MAP="$PALACE_CLAUDE_DIR/hooks/palace-map"
CURRENT_PWD="${PWD:-$(pwd)}"

project="$("$MAP" resolve "$CURRENT_PWD")"
[ -z "$project" ] && exit 0

CONTEXT_FILE="$VAULT/$project/CONTEXT.md"
[ -f "$CONTEXT_FILE" ] || exit 0

echo "## Palace Context — $project"
echo ""
# Strip YAML frontmatter (between --- delimiters)
awk '/^---$/{if(fm<2)fm++;next} fm>=2{print}' "$CONTEXT_FILE"

# --- staleness guard (#1) ---
# If the project has newer real activity (git HEAD) than CONTEXT.md's last edit,
# warn that the injected context may be behind. No signal (non-git repo) → no warning.
ACT="$("$MAP" activity "$project")"
if [ -n "$ACT" ]; then
  CTX_MTIME=$(stat -f %m "$CONTEXT_FILE" 2>/dev/null)
  if [ -n "$CTX_MTIME" ] && [ "$ACT" -gt "$((CTX_MTIME + 3 * 86400))" ]; then
    DAYS=$(( (ACT - CTX_MTIME) / 86400 ))
    echo ""
    echo "> ⚠ **Palace context may be stale** — the repo has commits ~${DAYS}d newer than this CONTEXT.md. Run \`/palace:update\` to refresh before trusting the above."
  fi
fi
