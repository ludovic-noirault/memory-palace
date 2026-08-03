# memory-palace

**Your projects remember themselves.**

Claude Code starts every session cold. You re-explain the stack, what's broken, what you decided last
week — every time. memory-palace ends that: `cd` into a project and its context is already loaded before
you type a word — current focus, open bugs, key decisions, gotchas — injected automatically at session start.

The hard part isn't storing notes; it's keeping them *true*. Most people solve cold-start with a growing
pile of `CLAUDE.md` files that quietly rot — stale, contradictory, unread. memory-palace is engineered
against that: **one source of truth** for project identity (no hand-synced config to drift), a **`doctor`**
that flags stale, dead, or dormant state before it bites, and a **test suite** so the wiring can't silently
break. It's not a notes convention — it's a small, self-checking system.

Three layers: hand-curated per-project **wings** (what matters, stable), Claude's native **auto-memory**
(synced from the wings), and searchable **session history** (what actually happened). One config file,
one command to install. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for how it fits together.

This repo is the **engine** — hooks, commands, the resolver, the installer, tests, and blank templates.
It contains **no content**: your project wings, session transcripts, and auto-memory never live here
(see [Scope](#scope--privacy)).

## Layers

| Layer | What | Where |
|-------|------|-------|
| 1 — Palace | Hand-curated per-project wings (5 files: readme/ARCHITECTURE/BUGS/CONTEXT/DECISIONS) | `$VAULT/projects/{slug}/` |
| 2 — Auto-memory | Claude Code native per-project memory, synced from wings | `~/.claude/projects/*/memory/` |
| 3 — Sessions + recall | Session transcripts + QMD search (**external**, see Prerequisites) | `$VAULT/claude-sessions/` |
| 4 — Spine bridge | Feature-level depth docs, indexed into the wing (**external + optional**) | `$VAULT/projects/{slug}/{repo}/{feature}/` |

Identity for every project lives in **one** file, `$VAULT/projects/_mapping.json`, resolved by
`palace-map`. No hand-synced hook case-lists.

A wing can span several git repos. Each is declared under `repos` with the name an external tool sees
(`remote`, i.e. `basename $(git remote get-url origin)`), its checkout `path`, the wing subdirectory
`dir` holding its docs, and an optional human `label`. `palace-map repos <slug>` prints them; the legacy
single `repo` string still works. See [Layer 4](docs/ARCHITECTURE.md#why-the-wings-repo-dirs-are-named-after-git-remotes)
for why `dir` has to match `remote` and has to be a real directory.

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
- **Layer 4 is external and optional** — [`spine`](https://github.com/nodewarrior/spine) writes
  per-feature docs under a wing. `hooks/spine-palace-link.py` bridges the two: it generates a
  `_features.md` index in the wing, stamps `wing: {slug}` into each spine doc's frontmatter, and adds a
  pointer from the wing's root docs to the index. Wings without spine docs are skipped, so `--all` is
  safe to run across the whole vault. Without spine installed, nothing happens.
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
**real env var > palace.env > built-in default** (`~/obsidian`, `~/.claude`). Moving machines
= edit those two lines and re-run `install.sh`.

## Tests

```sh
bash skills/palace-tests/run.sh   # stdlib unittest — resolve, validate, render, staleness, archive, doctor
```

## Scope / privacy

The repo is engine-only by design. It must never contain: project wings, session transcripts,
auto-memory, `palace.env`, or `~/.claude/tokens`. `.gitignore` guards the obvious cases; the split is
deliberate because wings and sessions hold confidential work.

## Credits

Layer 3 (session sync + `/recall`) is provided by the
[`personal-os-skills`](https://github.com/ArtemXTech/personal-os-skills) plugin plus `qmd`, installed
separately — this repo integrates with it but does not vendor it. Everything else (the palace wings,
`palace-map`, the hooks, `/palace` commands, and the installer) is original to this project.

## License

[MIT](LICENSE) © 2026 Ludovic Noirault.

## Status

macOS-only today (`launchctl`, `stat -f`, `osascript`). Linux support, CI, and worked examples are
tracked for a possible public release — see the repo's open items.
