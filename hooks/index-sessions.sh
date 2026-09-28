#!/bin/bash
# Re-index sessions into QMD on Stop. Config: env var > palace.env > default.
_OV_VAULT="$VAULT_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
export VAULT_DIR   # extract-sessions.py reads it from the environment

# Bound our own log: the Stop hook appends here every turn, so without this it grows
# without limit (it had reached 2.3 MB / 70k lines). Keep the most recent half MB.
LOG="$PALACE_CLAUDE_DIR/hooks/index-sessions.log"
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1048576 ]; then
  tail -c 524288 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

QMD_DIR="$VAULT_DIR/Notes/Projects/claude-sessions-qmd"
python3 "$PALACE_CLAUDE_DIR/skills/recall/scripts/extract-sessions.py" --days 3 --output "$QMD_DIR"

# extract-sessions copies prompts verbatim, so a pasted token lands here: mask it before
# qmd makes it searchable.
python3 "$PALACE_CLAUDE_DIR/hooks/scan-secrets.py" --redact "$QMD_DIR" --days 3

# qmd is an npm global on nvm's node, which is not on the Stop hook's PATH — the
# launchd job pins the same dir for this reason. Resolve it here too, then degrade
# with one clear line rather than a "command not found" on every single Stop.
if ! command -v qmd > /dev/null 2>&1; then
  for d in "$(dirname "$(command -v node 2>/dev/null || echo /nonexistent)")" \
           "$HOME"/.nvm/versions/node/*/bin; do
    if [ -x "$d/qmd" ]; then PATH="$d:$PATH"; break; fi
  done
fi

if command -v qmd > /dev/null 2>&1; then
  qmd update
else
  echo "qmd not on PATH, BM25 index not updated (topic recall will be stale)"
fi
