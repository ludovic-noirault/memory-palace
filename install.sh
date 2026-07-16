#!/bin/bash
# memory-palace bootstrap installer — deploys the engine from this repo into ~/.claude,
# ensures the vault skeleton, then wires hooks + launchd and gates on doctor.
# Idempotent: safe to re-run after `git pull`.
#
#   ./install.sh              deploy + wire (idempotent)
#   ./install.sh --uninstall  remove wiring (delegates to palace-install.sh --uninstall)
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"

# --- config: env var > palace.env > default ---
_OV_VAULT="${VAULT_DIR:-}"; _OV_PCD="${PALACE_CLAUDE_DIR:-}"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
CLAUDE="$PALACE_CLAUDE_DIR"; VAULT="$VAULT_DIR"

if [ "${1:-}" = "--uninstall" ]; then
  exec bash "$CLAUDE/hooks/palace-install.sh" --uninstall
fi

echo "Deploying palace engine:  REPO=$REPO"
echo "                          CLAUDE=$CLAUDE   VAULT=$VAULT"

# 0. palace.env — create with absolute paths if missing; never clobber an existing one
if [ ! -f "$CLAUDE/palace.env" ]; then
  mkdir -p "$CLAUDE"
  printf '# Palace config (absolute paths). Precedence: env > this file > default.\nVAULT_DIR=%s\nPALACE_CLAUDE_DIR=%s\n' "$VAULT" "$CLAUDE" > "$CLAUDE/palace.env"
  echo "  wrote $CLAUDE/palace.env (edit if these paths are wrong, then re-run)"
fi

# 1. copy engine into ~/.claude — files only, never rm existing dirs/content
mkdir -p "$CLAUDE/hooks" "$CLAUDE/commands/palace" \
         "$CLAUDE/skills/sync-claude-sessions/scripts" \
         "$CLAUDE/skills/recall/scripts" "$CLAUDE/skills/palace-tests"
cp -p "$REPO"/hooks/* "$CLAUDE/hooks/"
cp -p "$REPO"/commands/palace.md "$CLAUDE/commands/palace.md"
cp -p "$REPO"/commands/palace/* "$CLAUDE/commands/palace/"
cp -p "$REPO"/skills/sync-claude-sessions/scripts/* "$CLAUDE/skills/sync-claude-sessions/scripts/"
cp -p "$REPO"/skills/recall/scripts/* "$CLAUDE/skills/recall/scripts/"
cp -p "$REPO"/skills/palace-tests/* "$CLAUDE/skills/palace-tests/"
chmod +x "$CLAUDE/hooks/palace-map" "$CLAUDE"/hooks/*.sh "$CLAUDE/skills/palace-tests/run.sh" 2>/dev/null || true
echo "  engine files deployed"

# 2. vault skeleton — create-if-missing only, never overwrite existing content
mkdir -p "$VAULT/projects" "$VAULT/claude-sessions"
[ -e "$VAULT/projects/.template" ]     || cp -pR "$REPO/templates/projects/.template" "$VAULT/projects/.template"
[ -f "$VAULT/projects/_mapping.json" ] || cp -p  "$REPO/templates/projects/_mapping.json" "$VAULT/projects/_mapping.json"
[ -f "$VAULT/projects/_mapping.md" ]   || cp -p  "$REPO/templates/projects/_mapping.md"   "$VAULT/projects/_mapping.md"
[ -f "$VAULT/projects/_relations.md" ] || cp -p  "$REPO/templates/projects/_relations.md" "$VAULT/projects/_relations.md"
echo "  vault skeleton ensured"

# 3. wire hooks + launchd + health gate (in-place installer, deployed in step 1)
bash "$CLAUDE/hooks/palace-install.sh"
