# `/palace:read` Optional Query Arg — Design

Folds `anticipated_queries` search into `/palace:read` so answering a specific question about a
project is one command instead of two (`/palace:search` then manually reading the matched file).
`/palace:read` with no argument is unchanged.

## Problem

`/palace:search` finds which doc(s) answer a question via `anticipated_queries` word-overlap, but
it only prints a ranked list — the user (or Claude) still has to separately open and read the
matched file(s). `/palace:read`'s own Step 3 already loads the 6 core docs but explicitly does
**not** load `features/*.md` docs unless the question "clearly concerns that feature," at which
point it just points at `/palace:search` (`read.md:43-45`). Two round-trips for what should be one.

## Design

### 1. Optional query argument

`/palace:read` accepts an optional trailing query string:
- `/palace:read` — no argument, behavior is byte-for-byte unchanged from today.
- `/palace:read how does auth work` — everything after the command is the query string.

### 2. New step: search + load, inserted after today's Step 3 (wing load)

Only runs when a query argument is present:

1. Resolve slug (already done in Step 1 — reuse it, don't re-resolve).
2. Run `~/.claude/hooks/palace-map search "{query}" --slug {slug}`.
3. Take the top 2–3 non-zero-scoring results (the command already returns them ranked highest-first,
   capped at 8 — just take a prefix).
4. The 6 core docs are already in context from Step 3 — no re-read needed for those. For any matched
   result under `features/{slug}.md` not already loaded, read it now.
5. No matches at all → do not skip the answer entirely. Fall back to synthesizing from the 6
   core docs already loaded in Step 3 (they're in context regardless of query) and note explicitly
   that no `anticipated_queries` matched, so the answer may be incomplete:
   `No wing doc's anticipated_queries matched "{query}" — answering from the core docs already
   loaded; if this is a recurring question, /palace:update can add proper coverage for it.`

### 3. Brief format — new section

Inserted before today's Step 5 (recent sessions), after Step 4 (the standard Focus/Blocked/etc.
brief — unchanged, always printed regardless of query):

```
**Answering: "{query}"**
{synthesized answer, 2-5 sentences}
_Sourced from: {file1}, {file2}_
```

Synthesized, not a raw dump of matched file contents — cite sources so the user knows where to look
if they want the full context. This mirrors how Step 4 already synthesizes rather than dumping
`CONTEXT.md` verbatim.

## Touches

- `commands/palace/read.md`:
  - Header: note the optional query argument.
  - New Step 3.5 (search + load), runs only when a query argument is present: search execution,
    extra feature-doc loading, no-match fallback.
  - Step 4 brief template: add the `**Answering: "{query}"**` section, conditional on a query
    being present.
- No changes to `hooks/palace-map` (`search` subcommand, scoring, tie-break) — reused as-is.
- No changes to `/palace:search` itself — remains the standalone, all-docs-ranked-list tool (still
  useful for browsing beyond the top 2-3, or fleet-wide `--all` lookups outside a single project).

## Out of scope

- No change to `/palace:update` or `/palace:create` — this is a `/palace:read`-only change.
- No change to `anticipated_queries` scoring, tie-break ordering, or the top-8 cap in `palace-map
  search` — this spec only consumes that command's existing output.
- No persistence of past queries or answers (e.g. no query log) — each `/palace:read {query}` is
  stateless, same as `/palace:search` today.
- No fuzzy/semantic matching beyond the existing word-overlap search — if that proves too coarse for
  this use case specifically, that's a follow-up design.
