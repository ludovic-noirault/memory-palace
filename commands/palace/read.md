---
description: Load memory palace context for the active project — read-only, never creates or modifies anything. Optionally accepts a trailing query to answer a specific question in the same command.
---

You are loading the memory palace for the active project. The palace lives at `~/obsidian/projects/`. This command performs **zero writes** — no wing creation, no file edits, no session stamping. If anything is missing, tell the user and point at `/palace:create` or `/palace:update` instead of acting on their behalf.

If the user invoked this with trailing text after `/palace:read` (e.g. `/palace:read how does auth work`), treat that text as `QUERY` and run Step 3.5 below. With no trailing text, `QUERY` is unset and behavior is identical to today — skip Step 3.5 entirely.

---

## Step 1 — Identify the project

Run `~/.claude/hooks/palace-map resolve "$PWD"`. It prints the wing slug from `_mapping.json`, the single source of project identity (first matching glob wins).

- Slug printed → that is the project.
- Empty output → fall back to the last path component of `$PWD` as a guess, but do not treat this as confirmed — say so in the brief ("no entry in _mapping.json for this path, guessing project = `{name}`").

Set `WING=~/obsidian/projects/{project-name}`.

---

## Step 2 — Wing exists?

Run `ls "$WING" 2>/dev/null`.

If it does not exist: print exactly this and stop — do not create anything:

```
No palace wing for {project-name} at {WING}.
Run /palace:create to set one up.
```

---

## Step 3 — Load the wing

Read all 6 files in parallel:
- `readme.md` — project overview and links
- `ARCHITECTURE.md` — stack, patterns, critical gotchas
- `BUGS.md` — open bugs, security issues, debt
- `CONTEXT.md` — current focus, blocked items, next up
- `DECISIONS.md` — architectural decisions and rationale
- `GLOSSARY.md` — domain terms and their definitions

Feature-specific depth lives in spine docs under `<repo>/<feature>/`, indexed by the wing's
`_features.md`, plus a few legacy docs under `features/`. Not loaded by default here; load one
only if the user's question clearly concerns that feature, or point them at `/palace:search`.

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
   outside them (a spine doc under `<repo>/<feature>/`, or a legacy `features/` doc), read it now.
4. If the output was `no matches` (or scoring produced nothing above zero): do not skip the
   answer. Synthesize from the 6 core docs already loaded in Step 3 instead, and say so explicitly
   — this becomes the fallback note in Step 4's Answering section.

Hold the synthesized answer and its source file(s) for the Step 4 brief — do not print anything
yet.

---

## Step 4 — Session brief

Output:

```
## 🏛 Palace Brief — {project-name}

**Focus**: {current focus from CONTEXT.md}

**Blocked**: {blocked items, or "nothing blocked"}

**Open bugs**: {count and top severity, or "none"}

**Security**: {critical issues if any, or "clean"}

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

---

## Step 5 — Recent sessions (append to brief)

```bash
grep -rl --include="*.md" "{project-name}" ~/obsidian/claude-sessions/ 2>/dev/null | awk -F/ '{print $NF "\t" $0}' | sort -r | cut -f2 | head -3
```

For each file found, extract `date`, `title`, `status` from YAML frontmatter. Truncate title to 40 chars, strip any XML-like tags. If any found, append:

```
**Recent sessions**:
| Date | Title | Status |
|------|-------|--------|
| YYYY-MM-DD | [[claude-sessions/{stem}\|Short title]] | status |
```

If none found, omit the section.

---

## Step 6 — Open MRs / PRs (append to brief)

Discover git repos within the active project directory (up to 3 levels deep):

```bash
find . -maxdepth 3 -name ".git" -type d 2>/dev/null | while read gitdir; do
  dir=$(dirname "$gitdir")
  remote=$(git -C "$dir" remote get-url origin 2>/dev/null)
  [ -n "$remote" ] && echo "$dir|$remote"
done
```

For each remote, parse host + project path (SSH `git@HOST:ORG/REPO.git` or HTTPS `https://HOST/ORG/REPO.git`).

Token lookup: `cat ~/.claude/tokens/{host} 2>/dev/null`

**GitLab** (host ≠ `github.com`):
```bash
curl -sf --max-time 5 -H "PRIVATE-TOKEN: $TOKEN" \
  "https://$HOST/api/v4/projects/$PROJECT_ENCODED/merge_requests?state=opened&per_page=20"
```

**GitHub**:
```bash
curl -sf --max-time 5 -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/ORG/REPO/pulls?state=open&per_page=20"
```

Render:
```
**Open MRs**:
| Repo | Branch | Title | Author | Updated |
|------|--------|-------|--------|---------|
| web-api | fix/PROJ-150 | fix: response ordering | @you | 2026-06-10 |
```

- Missing token → skip repo silently, add `_(token missing for HOST — run: echo TOKEN > ~/.claude/tokens/HOST)_`
- Empty result → `No open MRs.`
- `curl` failure → `⚠ Could not reach HOST`, continue.

Stop here. Do not update any files.
