# /palace:read Optional Query Arg Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `/palace:read` an optional trailing query argument that runs the existing
`anticipated_queries` search and inlines the top 2-3 matches into the session brief, so answering a
specific question is one command instead of `/palace:search` + manually reading the matched file.

**Architecture:** `commands/palace/read.md` is a prose instruction file executed by Claude, not
code — there is no unit-testable function to add. The change adds a conditional Step 3.5 (search +
load, only when a query argument is present) and a conditional "Answering" section in the Step 4
brief template. No changes to `hooks/palace-map` — the `search` subcommand, scoring, and tie-break
logic are reused exactly as-is. Verification is a real dry run against an existing populated wing
(`acme`, which already has `anticipated_queries` on 5 of its docs) plus the existing regression
suite to confirm `palace-map search` itself is untouched.

**Tech Stack:** Markdown slash-command instruction file (Claude Code convention); underlying CLI is
`hooks/palace-map` (stdlib-only Python 3), already implemented and unmodified by this plan.

## Global Constraints

- `/palace:read` with no argument must remain byte-for-byte behaviorally unchanged (per spec
  section 1 — no argument means the existing flow, untouched).
- No changes to `hooks/palace-map`'s `search` subcommand, scoring, or tie-break ordering (per spec
  "Out of scope") — Step 3.5 only *calls* the existing command.
- No changes to `/palace:search`, `/palace:update`, or `/palace:create` (per spec "Out of scope").
- Take top 2–3 non-zero-scoring results from `palace-map search` output (per spec section 2, step
  3 — confirmed with user during brainstorming).
- The "Answering" section must be a synthesized answer citing source files, not a raw dump of
  matched file contents (per spec section 3).
- No-match case must still produce an answer, falling back to the 6 already-loaded core docs, with
  an explicit note that no `anticipated_queries` matched (per spec section 2, step 5).

---

### Task 1: Add optional query arg support to `/palace:read`

**Files:**
- Modify: `commands/palace/read.md` (currently 131 lines — see full content already read this
  session; header at lines 1-6, Step 3 at lines 33-45, Step 4 at lines 49-67, Step 5 begins line 71)

**Interfaces:**
- Consumes: `~/.claude/hooks/palace-map search "{query}" --slug {slug}` — existing CLI, output
  format `slug/file.md — "matched query" (score)`, ranked highest-first, capped at top 8, or the
  literal line `no matches` when nothing scores (per `commands/palace/search.md:24-27` and the
  anticipated-queries design spec).
- Produces: nothing consumed by later tasks — this is the only task in this plan.

- [ ] **Step 1: Update the command header to document the optional argument**

Edit the description frontmatter and opening paragraph (lines 1-6) so the argument is documented.
Replace:

```markdown
---
description: Load memory palace context for the active project — read-only, never creates or modifies anything
---

You are loading the memory palace for the active project. The palace lives at `~/obsidian/projects/`. This command performs **zero writes** — no wing creation, no file edits, no session stamping. If anything is missing, tell the user and point at `/palace:create` or `/palace:update` instead of acting on their behalf.
```

with:

```markdown
---
description: Load memory palace context for the active project — read-only, never creates or modifies anything. Optionally accepts a trailing query to answer a specific question in the same command.
---

You are loading the memory palace for the active project. The palace lives at `~/obsidian/projects/`. This command performs **zero writes** — no wing creation, no file edits, no session stamping. If anything is missing, tell the user and point at `/palace:create` or `/palace:update` instead of acting on their behalf.

If the user invoked this with trailing text after `/palace:read` (e.g. `/palace:read how does auth work`), treat that text as `QUERY` and run Step 3.5 below. With no trailing text, `QUERY` is unset and behavior is identical to today — skip Step 3.5 entirely.
```

- [ ] **Step 2: Insert new Step 3.5 after today's Step 3**

Today's Step 3 ends at line 45 (the `features/{feature-slug}.md` note), and Step 4 begins at line
49. Insert this new section between them:

`````markdown
---

## Step 3.5 — Answer the query (only if `QUERY` is set)

Skip this step entirely if no query argument was given.

1. Run:
   ```bash
   ~/.claude/hooks/palace-map search "{QUERY}" --slug {project-name}
   ```
2. Take the top 2–3 results with a non-zero score (the command already ranks highest-first and
   caps at 8 — just use a prefix of the non-`no matches` lines).
3. The 6 core docs are already loaded from Step 3 — do not re-read them. For any matched result
   under `features/{feature-slug}.md` not already loaded, read it now.
4. If the output was `no matches` (or scoring produced nothing above zero): do not skip the
   answer. Synthesize from the 6 core docs already loaded in Step 3 instead, and say so explicitly
   — this becomes the fallback note in Step 4's Answering section.

Hold the synthesized answer and its source file(s) for the Step 4 brief — do not print anything
yet.
`````

- [ ] **Step 3: Add the conditional "Answering" section to the Step 4 brief template**

Step 4 currently ends with:

````markdown
```
**Next up**: {next 1-2 items from CONTEXT.md}
```
````

Change the closing of the Step 4 code block so the template includes a conditional line, and add
explanatory text below the block. Replace:

````markdown
```
**Key gotchas**: {top 2-3 from ARCHITECTURE.md Critical Gotchas}

**Next up**: {next 1-2 items from CONTEXT.md}
```
````

with:

````markdown
```
**Key gotchas**: {top 2-3 from ARCHITECTURE.md Critical Gotchas}

**Next up**: {next 1-2 items from CONTEXT.md}
```

If `QUERY` was set (Step 3.5 ran), append immediately after the code block above:

```
**Answering: "{QUERY}"**
{2-5 sentence synthesized answer, drawn from the docs identified in Step 3.5 — not a raw file dump}
_Sourced from: {file1}, {file2}_
```

If Step 3.5's fallback path ran (no `anticipated_queries` match), use this form instead, still
naming the core docs actually drawn from:

```
**Answering: "{QUERY}"**
No wing doc's anticipated_queries matched this question — answering from the core docs already
loaded; if this is a recurring question, /palace:update can add proper coverage for it.
{2-5 sentence synthesized answer from the core docs}
_Sourced from: {file1}, {file2}_
```
````

- [ ] **Step 4: Re-read the edited file and check it renders as one coherent flow**

Read `commands/palace/read.md` top to bottom. Confirm: Step 1/2 unchanged, Step 3 unchanged, new
Step 3.5 clearly conditional on `QUERY`, Step 4's brief template has the conditional Answering
block, Steps 5/6 (recent sessions, open MRs) unchanged and still numbered correctly relative to the
new 3.5 insertion (they don't need renumbering since 3.5 sits between 3 and 4).

- [ ] **Step 5: Dry-run against a real wing with populated `anticipated_queries`**

The `acme` wing at `~/obsidian/projects/acme/` already has `anticipated_queries` on `ARCHITECTURE.md`,
`BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, and `GLOSSARY.md` (no `features/` dir yet, so this
exercises the core-docs path, not the feature-doc-load branch — that's fine, both branches read
already-loaded content differently but the command itself is identical either way).

Run the underlying search call exactly as Step 3.5 instructs, from anywhere (it's an absolute-path
lookup, not scoped to `$PWD`):

```bash
~/.claude/hooks/palace-map search "what open bugs exist" --slug acme
```

Expected: at least one ranked result referencing `acme/BUGS.md` (its literal `anticipated_queries`
entry is "What open bugs exist right now, and what's the top severity?" — near-total word overlap
should score highest). Confirm the output format matches what Step 3.5 expects to parse (`slug/file.md
— "matched query" (score)`, highest first).

Then run a query with no realistic match to confirm the fallback path's precondition:

```bash
~/.claude/hooks/palace-map search "unrelated nonsense xyz123" --slug acme
```

Expected: `no matches` (or equivalent zero-result output) — confirms Step 3.5's step 4 (fallback to
core docs) is reachable and correctly triggered by this exact output.

- [ ] **Step 6: Run the existing regression suite**

```bash
bash skills/palace-tests/run.sh
```

Expected: all tests pass, unchanged from before this plan — confirms this plan touched no code
path the test suite covers (`hooks/palace-map` itself is untouched).

- [ ] **Step 7: Commit**

```bash
git add commands/palace/read.md
git commit -m "$(cat <<'EOF'
feat: /palace:read accepts optional query arg, folds in search

Adds a conditional Step 3.5 that runs the existing anticipated_queries
search and inlines an Answering section into the brief, so answering a
specific question is one command instead of /palace:search followed by
manually reading the matched file. No-argument invocation is unchanged.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
