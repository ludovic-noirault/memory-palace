# Architecture

memory-palace gives Claude Code **persistent, per-project memory** so sessions stop starting cold.
This doc explains the layers, the single-source design, and the mechanisms that keep it from rotting.

## The problem

Claude Code sessions are stateless. Every new session forgets the stack, what's broken, what was
decided, and what's in progress — so you re-explain context each time, and months of accumulated
knowledge is inaccessible. Ad-hoc fixes (a growing `CLAUDE.md`) drift: stale, contradictory, unread.

## The three layers

| Layer | Answers | Where | Trigger |
|-------|---------|-------|---------|
| **1 — Palace** | "What am I working on? What's blocked?" | `$VAULT/projects/{slug}/` — 5 files per wing | `SessionStart` hook auto-injects `CONTEXT.md`; `/palace:*` commands |
| **2 — Auto-memory** | "What are the standing rules/blockers here?" | `~/.claude/projects/*/memory/` | Synced from the wing on `Stop` (`palace-to-memory --if-newer`) |
| **3 — Sessions + recall** | "What did I ever decide about X?" | `$VAULT/claude-sessions/` + a BM25 index | Session sync + `/recall` (**external**, see README prerequisites) |

Layer 1 is the load-bearing one: hand-curated, stable, strategic. A wing has six curated files —
`readme.md` (overview/team/links), `ARCHITECTURE.md` (stack/patterns/gotchas), `BUGS.md`
(open bugs/security/debt), `CONTEXT.md` (current focus/next up/blocked — the file that gets injected),
`DECISIONS.md` (the *why* behind choices), and `GLOSSARY.md` (domain terms, maintained via the
`domain-modeling` skill, loaded on demand rather than injected). A seventh file, `QUIZ_LOG.md`, is an
append-only log — not hand-curated content — tracking `/palace:quiz` comprehension scores over time.

Every wing doc also carries an `anticipated_queries` frontmatter field — 2-5 sample questions the
doc answers, kept in sync by `/palace:update` — searchable via `palace-map search` /
`/palace:search`, a dependency-free keyword-overlap lookup (no embeddings). An optional
`features/{feature-slug}.md` layer holds deep dives on a specific feature or domain, additive to
the 6 core files (never part of the 6-file completeness check), indexed from `readme.md`'s
`## Features` section and included in the same search.

## Single source of truth

Every project's identity — which working directories map to which wing, its auto-memory dir, its repo —
lives in **one** file: `$VAULT/projects/_mapping.json`. A single resolver, `hooks/palace-map`, reads it;
**all** consumers call the resolver instead of carrying their own copy:

```
_mapping.json ──▶ palace-map resolve ──▶ palace-context.sh   (SessionStart: inject CONTEXT.md)
                                    ├──▶ palace-reminder.sh   (SessionEnd: nudge /palace:update)
                                    ├──▶ Stop hook            (sync wing → auto-memory)
                                    └──▶ palace-to-memory     (reads the same JSON)
```

There are no hand-synced `case` lists to drift. Adding a project is a one-line JSON edit followed by
`palace-map render` (regenerates the human-readable table in `_mapping.md`) and `palace-map validate`.

## Anti-rot mechanisms

The point of the system is that it stays *true*, not just that it stores things:

- **`palace-map validate`** — fails on an orphan mapping (entry with no wing) or an unwired wing (wing with
  no entry). These are the two ways the identity map silently goes wrong; validate makes them loud.
- **`palace-map doctor`** — reports per-wing **staleness** (repo has commits newer than `CONTEXT.md`) and
  **dormancy** (no activity in 90d), keyed off real git/session activity, not file mtime.
- **`palace-map doctor --system`** — verifies the whole install: config present, hooks registered in
  `settings.json`, launchd job loaded, referenced paths exist, every wing has its 6 files, `_mapping.md`
  in sync, validate clean. One green/red report; non-zero exit on any red.
- **Staleness guard** — `palace-context.sh` appends a warning at SessionStart when the injected context is
  behind the repo, so you never silently trust a stale wing.
- **Tests** — `skills/palace-tests/` (stdlib `unittest`) exercise resolve/validate/render/staleness/archive
  against throwaway fixture vaults, so refactors can't silently break a hook.

## Configuration & portability

One file, `~/.claude/palace.env`, holds `VAULT_DIR` and `PALACE_CLAUDE_DIR`. Resolution order everywhere
is **real env var > palace.env > built-in default**. That single indirection is what makes the engine
testable (point `VAULT_DIR` at a fixture) and portable (edit two lines to move machines).

`install.sh` deploys the engine from this repo into `~/.claude`, ensures the vault skeleton from
`templates/`, wires the hooks + launchd job, and refuses to finish unless `doctor --system` is green.
It is idempotent — re-run after `git pull` to redeploy.

## Session flow

```
cd ~/some/project && claude
  → SessionStart → palace-map resolves the wing → CONTEXT.md injected (+ staleness warning if behind)
  → Claude knows the focus/blockers/bugs before your first message

--- work happens; bugs/decisions captured via /palace:update ---

Stop hook → session synced to Layer 3, wing → auto-memory (if changed)
SessionEnd → reminder to /palace:update

Next session, days later → context auto-injected again → zero re-explanation
```

## Scope boundary

This repo is the **engine only**. Content — wings, session transcripts, auto-memory, `palace.env`,
and any tokens — never lives here; it stays private and local to each user's machine. That separation is
deliberate: wings and sessions hold confidential work, the engine does not.
