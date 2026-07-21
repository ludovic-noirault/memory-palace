# Anticipated-Queries Frontmatter + `/palace:search` — Design

Adds a lightweight, grep-based "which doc answers this?" mechanism to the wing system, inspired by
a feature seen in a comparable project (spine). No embeddings, no vector search — just a small,
Claude-maintained list of sample questions per doc, plus a keyword-overlap search over it.

## 1. Frontmatter field: `anticipated_queries`

**Problem**: with 6 wing files per project, it's not always obvious which file answers a given
question without opening several and skimming. There's no cheap index of "what does this doc
answer".

**Design**:
- Every wing doc (`readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`,
  `GLOSSARY.md`) gains an `anticipated_queries` list in its YAML frontmatter: 2-5 short
  natural-language questions the doc's current content answers.

```yaml
---
tags: [project, context]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "what's the current focus"
  - "what's blocked right now"
---
```

- Parsed with a small stdlib-only reader in `palace-map` (no YAML library, matching the existing
  stdlib-only constraint): find the frontmatter block between the first two `---` lines, locate the
  `anticipated_queries:` key, and collect the following `  - "..."` lines until a line that isn't
  indented list syntax.
- Missing or malformed field → treated as empty list, not an error (docs predating this feature,
  or hand-edited ones, shouldn't break tooling).

**Touches**:
- `templates/projects/.template/*.md` (all 6) — add the frontmatter field with a placeholder
  comment/example.
- `hooks/palace-map` — new frontmatter-parsing helper function.
- Existing wings: backfilled over time via `/palace:update` (see below), not a one-shot migration.

## 2. Authoring — `/palace:update`

**Design**:
- When `/palace:update`'s existing Step 7 (update wing) rewrites a section of a doc, it also
  regenerates that doc's `anticipated_queries` list to match the new content — replaced wholesale,
  not appended to, since the point is "what does this doc answer *now*", not a growing log.
- Docs `/palace:update` doesn't touch in a given run keep their existing list untouched.
- Docs with no `anticipated_queries` yet (pre-existing wings) get one generated the first time
  `/palace:update` touches them — this is how backfill happens, organically.

**Touches**:
- `commands/palace/update.md` — Step 7 gains an `anticipated_queries` regeneration sub-step,
  scoped to whichever files that step actually rewrites.

## 3. Command — `palace-map search <query> [--slug SLUG] [--all]`

**Design**:
- Loads all wings (or just `--slug`'s wing, or `--all` explicitly for fleet-wide), reads each
  doc's `anticipated_queries`.
- Matching: lowercase the query and each anticipated-query line, split both into words, score by
  count of overlapping words. Zero-overlap lines are dropped.
- Output: ranked list, highest score first, capped at top 8: `slug/file.md — "matched query" (score)`.
- No matches anywhere → print a plain "no matches" line, exit 0 (not an error condition).

**Touches**:
- `hooks/palace-map` — new `search` subcommand + scoring helper, added to `CMDS` dispatch table
  and the module docstring's command list.

## 4. Slash command — `/palace:search <query>`

**Design**:
- Thin wrapper: resolve `$PWD` → slug via the existing `palace-map resolve`; if a slug resolves,
  call `palace-map search <query> --slug <slug>`; if not (pwd isn't a mapped project), call
  `palace-map search <query> --all`.
- Prints the ranked results so Claude/the user can jump straight to the right doc instead of
  re-reading all 6 files.

**Touches**:
- `commands/palace/search.md` — new.
- `docs/ARCHITECTURE.md` — mention `anticipated_queries` + `/palace:search` alongside the other
  wing mechanisms.

## 5. Tests

- `skills/palace-tests/test_palace_map.py`:
  - frontmatter parsing: field present, absent, empty list, malformed (non-list value, unterminated
    quotes) — all must not raise.
  - scoring/ranking: overlapping-word count, tie-breaking (stable order), zero-overlap exclusion.
  - `search` subcommand: `--slug` scope vs `--all` scope, top-8 cap, no-matches case.

## Out of scope

- No embeddings/vector search — word-overlap matching only, deliberately cheap and deterministic.
- No auto-run of `/palace:search` (e.g. at `SessionStart`) — always user/Claude-invoked on demand.
- No dedicated migration script to backfill `anticipated_queries` on all existing wings at once —
  backfill happens lazily, per-doc, the next time `/palace:update` touches that doc.
- No cross-file relevance ranking beyond the simple word-overlap score (e.g. no TF-IDF, no recency
  weighting) — if this proves too coarse in practice, that's a follow-up design, not part of this one.
