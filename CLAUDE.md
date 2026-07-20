# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

memory-palace is the **engine** for a persistent per-project memory system for Claude Code: hooks,
slash commands, a resolver CLI, an installer, and tests. It contains no content itself — wings,
session transcripts, and auto-memory live outside the repo (user's vault + `~/.claude`). See
`README.md` and `docs/ARCHITECTURE.md` for the full design; don't duplicate those here, just orient.

## Commands

- Run tests: `bash skills/palace-tests/run.sh` (stdlib `unittest`, no deps/install step)
  - Single test: `cd skills/palace-tests && python3 -m unittest test_palace_map.TestClassName.test_method -v`
- Deploy/reinstall the engine into `~/.claude` + wire hooks/launchd: `./install.sh` (idempotent, safe to
  re-run after `git pull`)
- Remove wiring: `./install.sh --uninstall`
- Resolver CLI (once installed): `~/.claude/hooks/palace-map {resolve|list|validate|render|doctor|doctor --system|archive|unarchive}`
- No linter/formatter/build step configured — this is plain bash + stdlib-only Python 3.

## Architecture

Three layers (full detail in `docs/ARCHITECTURE.md`):
1. **Palace** — hand-curated per-project "wings" (6 files: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`,
   `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`, plus an append-only `QUIZ_LOG.md`) living in the user's
   vault, injected at `SessionStart`.
2. **Auto-memory** — Claude Code's native per-project memory, synced from the wing on `Stop`.
3. **Sessions + recall** — session transcripts + BM25 search; provided by an external plugin
   (`personal-os-skills`), not vendored here.

**Single source of truth**: every project's identity (working-dir globs → wing → auto-memory dir →
repo path) lives in one file, `$VAULT/projects/_mapping.json`. All hooks/scripts resolve identity
through `hooks/palace-map` (a single Python CLI) instead of keeping their own copies or `case` lists —
this is the core invariant of the design. When adding a project-identity consumer, resolve through
`palace-map`, don't hardcode a new lookup.

Key pieces in this repo:
- `hooks/palace-map` — the resolver CLI (resolve/list/validate/render/doctor/archive); ~380 lines,
  stdlib-only Python.
- `hooks/palace-*.sh` — the actual Claude Code hooks (`SessionStart` context injection, `SessionEnd`
  reminder, daily maintenance, secret scanning) that all shell out to `palace-map`.
- `hooks/palace-install.sh` — in-place wiring installer (hooks into `settings.json`, launchd job);
  called by `install.sh` after the vault skeleton is ensured.
- `commands/palace*` — the `/palace`, `/palace:read`, `/palace:create`, `/palace:update`,
  `/palace:doctor`, `/palace:quiz` slash command definitions.
- `templates/projects/` — blank wing skeleton (`.template/`) and starter `_mapping.json`/`.md`/
  `_relations.md`, copied into the vault on first install only (never overwrites existing content).
- `skills/palace-tests/test_palace_map.py` — the test suite; exercises resolve/validate/render/
  staleness/archive/quiz-status/reminder-nudging against throwaway fixture vaults (no real vault touched).

**Config/portability**: one file, `~/.claude/palace.env` (`VAULT_DIR`, `PALACE_CLAUDE_DIR`).
Resolution order everywhere: real env var > `palace.env` > built-in default (`~/obsidian`, `~/.claude`).

**Anti-rot mechanisms** (why several of these hooks/commands exist — don't remove without replacing):
`palace-map validate` catches orphan mappings / unwired wings; `palace-map doctor` reports staleness
(repo commits newer than `CONTEXT.md`) and dormancy (90d+ idle); `doctor --system` verifies the whole
install and gates `install.sh` completion; `palace-context.sh` appends a staleness warning at
`SessionStart` if injected context is behind the repo.

## Scope boundary (important)

This repo must **never** contain: project wings, session transcripts, auto-memory, `palace.env`, or
`~/.claude/tokens`. `.gitignore` guards the obvious cases, but be deliberate — those hold confidential
user work and belong outside version control entirely.

## Platform

macOS-only currently (`launchctl`, `stat -f`, `osascript` in the hooks/installer). Keep that in mind
before assuming Linux compatibility of any hook change.
