---
description: Health-check the whole memory-palace install + fleet, interpret the results, and propose fixes (read-only until you approve)
---

You are running a health check on the memory-palace system. This command is **read-only by default** — you run diagnostics, interpret them, and *propose* fixes, but you do **not** apply any write-y fix (re-install, `/palace:update`, archive, render) until the user explicitly says yes. Diagnostics themselves make no changes.

---

## Step 1 — Run both diagnostics

Run these two commands and capture their output:

```bash
~/.claude/hooks/palace-map doctor --system   # wiring: config, hooks, launchd, paths, sync, validate (23 checks)
~/.claude/hooks/palace-map doctor            # per-wing: staleness (wing behind activity) + dormancy (>90d idle)
```

Both are read-only. `doctor --system` exits non-zero if any check is red.

---

## Step 2 — Print an interpreted health report

Summarize, don't just echo. Structure:

- **System wiring** — one line: `✓ all green (N checks)` or list only the ✗ red lines.
- **Wings** — a short table of any wing flagged `STALE`, `DORMANT`, `no activity signal`, or `archived`. Omit the healthy ones (just say "N wings ok").

Keep it scannable. If everything is green and no wing is flagged, say so in one line and stop — nothing to propose.

---

## Step 3 — Propose fixes (do NOT apply yet)

For each problem found, name the concrete fix. Map symptoms → remedies:

| Symptom (from doctor) | Proposed fix |
|---|---|
| Any `doctor --system` red line (missing hook entry, unloaded launchd, missing path, `_mapping.md` out of sync) | `bash ~/.claude/hooks/palace-install.sh` (idempotent re-sync) |
| `validate` ERROR — orphan mapping (entry, no wing) | edit `projects/_mapping.json` to remove the entry (or create the wing), then `palace-map render` + `validate` |
| `validate` WARN — unwired wing (wing, no entry) | add the wing to `_mapping.json`, or `/palace:create` from its repo |
| Wing `STALE` (repo commits newer than CONTEXT.md) | `cd` into that repo and run `/palace:update` |
| Wing `DORMANT` (>90d no activity) / `no activity signal` | offer to archive: `~/.claude/hooks/palace-map archive <slug>` — but confirm it's genuinely dormant first (a "no activity signal" wing may just have an uncloned repo — verify the repo path in `_mapping.json` before archiving) |

Present the proposed actions as a numbered list and **ask which to apply** (or none). Only after an explicit yes:
- re-install / render / archive → run the command;
- stale wing → note that `/palace:update` must be run from inside that project's repo (offer to guide, don't fake it from here).

Never archive or edit wing content without confirmation. Never run `--uninstall`.
