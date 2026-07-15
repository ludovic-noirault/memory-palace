# memory-palace

A per-project memory system for Claude Code, built on Obsidian. It kills the cold-start tax:
every session, the `SessionStart` hook auto-injects the current project's context, so Claude knows
the stack, current focus, open bugs, and gotchas before you type anything.

This repo is the **engine** — hooks, commands, the resolver, the installer, tests, and blank
templates. It contains **no content**: your project wings, session transcripts, and auto-memory
never live here (see [Scope](#scope--privacy)).

## Layers

| Layer | What | Where |
|-------|------|-------|
| 1 — Palace | Hand-curated per-project wings (5 files: readme/ARCHITECTURE/BUGS/CONTEXT/DECISIONS) | `$VAULT/projects/{slug}/` |
| 2 — Auto-memory | Claude Code native per-project memory, synced from wings | `~/.claude/projects/*/memory/` |
| 3 — Sessions + recall | Session transcripts + QMD search (**external**, see Prerequisites) | `$VAULT/claude-sessions/` |

Identity for every project lives in **one** file, `$VAULT/projects/_mapping.json`, resolved by
`palace-map`. No hand-synced hook case-lists.

## Install

```sh
git clone git@github.com:ludovic-noirault/memory-palace.git
cd memory-palace
cp palace.env.example ~/.claude/palace.env   # edit VAULT_DIR / PALACE_CLAUDE_DIR (absolute paths)
./install.sh                                  # deploy engine → ~/.claude, wire hooks + launchd, gate on doctor
```

`install.sh` is idempotent — re-run after `git pull` to redeploy. `./install.sh --uninstall`
removes the wiring (your wings and content are never touched).

## Prerequisites

- **Obsidian** vault at `$VAULT` (the [Dataview](https://github.com/blacksmithgu/obsidian-dataview)
  plugin renders `_relations.md`, optional).
- **Layer 3 is external** — session sync (`claude-sessions`), `extract-sessions`, and `/recall` come
  from the [`personal-os-skills`](https://github.com/ArtemXTech/personal-os-skills) plugin, plus `qmd`
  for the BM25 index. Install those separately. Until then, the session-sync/index Stop hooks are
  no-ops and `palace-map doctor --system` will flag the missing `claude-sessions` path — the palace
  itself (Layers 1 & 2) works without them.
- macOS (`launchctl` for the daily maintenance job; `stat -f` in the staleness guard).
- `python3` (stdlib only — no pip installs) and `git`.

## Commands

- `/palace` — explains the system.
- `/palace:read` — load a wing + print a session brief (read-only).
- `/palace:create` — set up a new wing and wire it (edits `_mapping.json`, runs `render` + `validate`).
- `/palace:update` — flush session learnings back to the wing + sync auto-memory.
- `/palace:doctor` — interpret `doctor --system` + per-wing health and propose fixes (read-only until you approve).

## CLI (`hooks/palace-map`)

```
palace-map resolve <pwd>     slug whose glob matches <pwd>
palace-map validate          orphan mappings / unwired wings; exit 1 on error
palace-map render            regenerate the table in _mapping.md from _mapping.json
palace-map doctor            per-wing staleness + dormancy
palace-map doctor --system   whole-install health (config, hooks, launchd, paths, sync)
palace-map archive <slug>    set a wing status: archived  (unarchive to reverse)
```

## Config

One file, `~/.claude/palace.env`: `VAULT_DIR` + `PALACE_CLAUDE_DIR`. Precedence everywhere is
**real env var > palace.env > built-in default** (`~/theTribe/obsidian`, `~/.claude`). Moving machines
= edit those two lines and re-run `install.sh`.

## Tests

```sh
bash skills/palace-tests/run.sh   # stdlib unittest — resolve, validate, render, staleness, archive, doctor
```

## Scope / privacy

The repo is engine-only by design. It must never contain: project wings, session transcripts,
auto-memory, `palace.env`, or `~/.claude/tokens`. `.gitignore` guards the obvious cases; the split is
deliberate because wings and sessions hold confidential work.
