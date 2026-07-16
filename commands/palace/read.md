---
description: Load memory palace context for the active project — read-only, never creates or modifies anything
---

You are loading the memory palace for the active project. The palace lives at `~/obsidian/projects/`. This command performs **zero writes** — no wing creation, no file edits, no session stamping. If anything is missing, tell the user and point at `/palace:create` or `/palace:update` instead of acting on their behalf.

---

## Step 1 — Identify the project

Run `pwd`. Read `~/obsidian/projects/_mapping.md` and match `$PWD` against the "SessionStart/hook `$PWD` match" column (glob patterns, same semantics as bash `case`).

- Match found → that row's palace wing name is the project.
- No match → fall back to the last path component of `$PWD` as a guess, but do not treat this as confirmed — say so in the brief ("no entry in _mapping.md for this path, guessing project = `{name}`").

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

Read all 5 files in parallel:
- `readme.md` — project overview and links
- `ARCHITECTURE.md` — stack, patterns, critical gotchas
- `BUGS.md` — open bugs, security issues, debt
- `CONTEXT.md` — current focus, blocked items, next up
- `DECISIONS.md` — architectural decisions and rationale

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

---

## Step 5 — Recent sessions (append to brief)

```bash
grep -rl "{project-name}" ~/obsidian/claude-sessions/*.md 2>/dev/null | sort -r | head -3
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
