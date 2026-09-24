#!/bin/bash
# palace-install.sh — idempotent (re)install of the memory-palace wiring on this machine.
# Reads palace.env for identity, then: ensures the vault skeleton, merges the palace hooks
# into settings.json (without touching unrelated hooks), installs+loads the launchd daily job,
# and refuses to finish unless `palace-map validate` and `doctor --system` are green.
#
#   palace-install.sh              install / re-sync (idempotent)
#   palace-install.sh --uninstall  remove palace hooks + launchd job (leaves wings/content)
set -euo pipefail

# --- config (env var > palace.env > default) ---
_OV_VAULT="${VAULT_DIR:-}"; _OV_PCD="${PALACE_CLAUDE_DIR:-}"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
VAULT_DIR="${_OV_VAULT:-${VAULT_DIR:-$HOME/obsidian}}"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
CLAUDE="$PALACE_CLAUDE_DIR"; VAULT="$VAULT_DIR"
SETTINGS="$CLAUDE/settings.json"
LABEL="com.$(id -un).palace-maintenance"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ACTION="${1:-install}"

MERGE_PY="$CLAUDE/hooks/.palace-settings-merge.py"  # written on the fly below

write_merge_helper() {
  cat > "$MERGE_PY" <<'PY'
import json, sys
settings, claude, vault, action = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(settings) as f:
    data = json.load(f)
hooks = data.setdefault("hooks", {})

# Canonical palace hooks, keyed by event, identified by a stable substring so we never
# duplicate and never touch non-palace hooks (e.g. the rtk PreToolUse hook).
PALACE = {
    "SessionStart": [("palace-context.sh", {"type": "command", "command": f"{claude}/hooks/palace-context.sh"})],
    "Stop": [
        ("skills/sync-claude-sessions/scripts/claude-sessions sync",
         {"type": "command", "command": f"VAULT_DIR={vault} python3 {claude}/skills/sync-claude-sessions/scripts/claude-sessions sync", "timeout": 10}),
        ("index-sessions.sh",
         {"type": "command", "command": f"bash {claude}/hooks/index-sessions.sh >> {claude}/hooks/index-sessions.log 2>&1", "timeout": 30}),
        ("palace-map resolve",
         {"type": "command", "command": "bash -c 'p=$(" + claude + "/hooks/palace-map resolve \"$PWD\"); [ -n \"$p\" ] && python3 " + claude + "/skills/sync-claude-sessions/scripts/palace-to-memory --project \"$p\" --if-newer >> " + claude + "/hooks/palace-to-memory.log 2>&1'", "timeout": 10}),
    ],
    "SessionEnd": [("palace-reminder.sh", {"type": "command", "command": f"bash {claude}/hooks/palace-reminder.sh", "timeout": 5})],
}

def has(event, needle):
    for group in hooks.get(event, []):
        for h in group.get("hooks", []):
            if needle in h.get("command", ""):
                return group
    return None

changed = False
if action == "install":
    for event, specs in PALACE.items():
        for needle, hook in specs:
            if has(event, needle) is None:
                groups = hooks.setdefault(event, [])
                # reuse a matcher-less group if present, else make one
                target = next((g for g in groups if g.get("matcher", "") == ""), None)
                if target is None:
                    target = {"matcher": "", "hooks": []} if event in ("Stop",) else {"hooks": []}
                    groups.append(target)
                target["hooks"].append(hook)
                changed = True
elif action == "uninstall":
    for event, specs in PALACE.items():
        for needle, _ in specs:
            for group in list(hooks.get(event, [])):
                before = len(group.get("hooks", []))
                group["hooks"] = [h for h in group.get("hooks", []) if needle not in h.get("command", "")]
                if len(group["hooks"]) != before:
                    changed = True
            hooks[event] = [g for g in hooks.get(event, []) if g.get("hooks")]
            if not hooks[event]:
                del hooks[event]

if changed:
    with open(settings, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
print("changed" if changed else "unchanged")
PY
}

build_plist() {
  # `type -P`, not `command -v`: nvm's lazy loader defines `node` as a shell function, and
  # `command -v` would return the function name instead of a binary path.
  local node_dir; node_dir="$(dirname "$(type -P node 2>/dev/null || echo /usr/local/bin/node)")"
  cat <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$CLAUDE/hooks/palace-daily-maintenance.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key><integer>13</integer>
        <key>Minute</key><integer>0</integer>
    </dict>
    <key>RunAtLoad</key>
    <false/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$node_dir:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StandardOutPath</key>
    <string>$CLAUDE/hooks/palace-maintenance.launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$CLAUDE/hooks/palace-maintenance.launchd.log</string>
</dict>
</plist>
PLISTEOF
}

if [ "$ACTION" = "--uninstall" ]; then
  echo "Uninstalling palace wiring (wings/content untouched)…"
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  write_merge_helper
  python3 "$MERGE_PY" "$SETTINGS" "$CLAUDE" "$VAULT" uninstall
  rm -f "$MERGE_PY"
  echo "Done. Palace hooks stripped, launchd job removed."
  exit 0
fi

echo "Installing/syncing palace wiring for VAULT=$VAULT  CLAUDE=$CLAUDE"

# A. vault skeleton (create-if-missing; never overwrites existing content)
mkdir -p "$VAULT/projects" "$VAULT/claude-sessions"
[ -f "$VAULT/projects/_mapping.json" ] || printf '{\n  "projects": []\n}\n' > "$VAULT/projects/_mapping.json"
if [ ! -f "$VAULT/projects/_mapping.md" ]; then
  {
    echo "# Project Identity Map"; echo
    echo "Canonical source: _mapping.json. Run \`palace-map render\` + \`palace-map validate\`."; echo
    echo "<!-- palace-map:table:begin — generated by \`palace-map render\`, do not edit by hand -->"
    echo "<!-- palace-map:table:end -->"
  } > "$VAULT/projects/_mapping.md"
fi

# B. settings.json hooks (write only if something changed)
cp "$SETTINGS" "$SETTINGS.palace-bak" 2>/dev/null || true
write_merge_helper
echo "  settings.json: $(python3 "$MERGE_PY" "$SETTINGS" "$CLAUDE" "$VAULT" install)"
rm -f "$MERGE_PY"

# C. launchd plist (write only if changed)
mkdir -p "$HOME/Library/LaunchAgents"
NEW_PLIST="$(build_plist)"
if [ ! -f "$PLIST" ] || [ "$NEW_PLIST" != "$(cat "$PLIST")" ]; then
  printf '%s\n' "$NEW_PLIST" > "$PLIST"
  echo "  launchd plist: written"
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST" 2>/dev/null || true
  echo "  launchd: reloaded"
else
  echo "  launchd plist: unchanged"
fi

# D. render + gate on health
"$CLAUDE/hooks/palace-map" render >/dev/null || true
echo "  --- validate ---";       "$CLAUDE/hooks/palace-map" validate
echo "  --- doctor --system ---"; "$CLAUDE/hooks/palace-map" doctor --system
echo "Install complete — green."
