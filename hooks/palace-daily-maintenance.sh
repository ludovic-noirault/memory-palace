#!/bin/bash
# Daily palace maintenance: harvest candidates, scan for stray secrets, fleet-health report.
# Runs via launchd (StartCalendarInterval) so it also fires on wake if the Mac was asleep
# at the scheduled time — plain cron would just skip the run instead.
# Config precedence: real env var > palace.env > built-in default.
_OV_VAULT="$VAULT_DIR"; _OV_PCD="$PALACE_CLAUDE_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/theTribe/obsidian}}"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
export VAULT_DIR PALACE_CLAUDE_DIR   # so child python scripts inherit the config
LOG="$PALACE_CLAUDE_DIR/hooks/palace-daily-maintenance.log"

{
  echo "=== $(date) ==="

  echo "--- palace-harvest ---"
  HARVEST_OUT=$(python3 "$PALACE_CLAUDE_DIR/skills/recall/scripts/palace-harvest.py" 2>&1)
  echo "$HARVEST_OUT"
  if echo "$HARVEST_OUT" | grep -q "Review file:"; then
    HARVEST_SUMMARY="new harvest candidates"
  else
    HARVEST_SUMMARY="no new candidates"
  fi

  echo "--- scan-secrets ---"
  SECRETS_OUT=$(python3 "$PALACE_CLAUDE_DIR/hooks/scan-secrets.py" 2>&1)
  echo "$SECRETS_OUT"
  SECRETS_SUMMARY=$(echo "$SECRETS_OUT" | tail -1)

  echo "--- palace-doctor (staleness / dormancy — report only, no changes) ---"
  DOCTOR_OUT=$("$PALACE_CLAUDE_DIR/hooks/palace-map" doctor 2>&1)
  echo "$DOCTOR_OUT"
  DOCTOR_SUMMARY="$(echo "$DOCTOR_OUT" | grep -cE 'STALE|DORMANT|no activity signal') flagged"

  echo ""
} >> "$LOG" 2>&1

osascript -e "display notification \"$HARVEST_SUMMARY — $SECRETS_SUMMARY — doctor: $DOCTOR_SUMMARY\" with title \"Palace maintenance ran\"" 2>/dev/null
