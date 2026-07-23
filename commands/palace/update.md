---
description: Flush current session's learnings into the memory palace wing for the active project
---

You are updating the memory palace wing for the active project. The palace lives at `~/obsidian/projects/`. This command requires an existing wing — it never creates one. Execute every step below in order without asking for confirmation unless you hit an ambiguous case.

---

## Step 1 — Identify the project

Run `pwd`. Read `~/obsidian/projects/_mapping.md` and match `$PWD` against the "SessionStart/hook `$PWD` match" column (glob patterns, same semantics as bash `case`). No match → fall back to the last path component of `$PWD` as the project name.

Set `WING=~/obsidian/projects/{project-name}`.

---

## Step 2 — Wing exists?

Run `ls "$WING" 2>/dev/null`. If it does not exist, print exactly this and stop:

```
No palace wing for {project-name} at {WING}.
Run /palace:create first.
```

---

## Step 3 — Stamp current session with project

Try `$CLAUDE_SESSION_ID` first:
```bash
grep -rl "$CLAUDE_SESSION_ID" ~/obsidian/claude-sessions/*.md 2>/dev/null | head -1
```

If empty (env var unavailable in Bash tool), fall back to the most recently modified session file with `projects: []` unset:
```bash
ls -t ~/obsidian/claude-sessions/*.md | head -20 | xargs grep -l "^projects: \[\]" | head -1
```

Once found, update the `projects` frontmatter field — replace `projects: []` with:
```
projects:
  - {project-name}
```
If `projects` already has entries, append only if not already listed. Do this silently.

---

## Step 4 — Load the wing

Read all 6 files in parallel: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`.

---

## Step 5 — Session brief

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

## Step 6 — Recent sessions + Open MRs (append to brief)

Same as `/palace:read` Steps 5–6 (recent sessions table from `claude-sessions/`, open MRs/PRs via git remote + GitHub/GitLab API using `~/.claude/tokens/{host}`).

---

## Step 7 — Update the wing

Explore the current project state for anything new or changed since the wing was last updated:

1. `git log --oneline -10` — recent commits not reflected in CONTEXT.md
2. `git status` — dirty files signalling in-progress work
3. `git branch --show-current` — matches what CONTEXT.md says?
4. Scan for recently added `TODO`, `FIXME`, `HACK`, `XXX` comments

Then update only what actually changed:
- **CONTEXT.md**: Current Focus, Recent Work table, Next Up, Blocked, and replace `## Open MRs` with the freshly-fetched table from Step 6 (add the section if missing)
- **BUGS.md**: newly discovered or resolved bugs
- **DECISIONS.md**: any decision inferable from recent commits or code patterns
- **ARCHITECTURE.md / Critical Gotchas**: any new gotcha surfaced during exploration
- **GLOSSARY.md**: invoke the `domain-modeling` skill against this session's conversation and code changes to spot new or changed domain terms. Write resolved terms into `GLOSSARY.md` using its `## [Term]` / `- **Definition**` / `- **Avoid**` / `- **More info**` format — **not** into `CONTEXT.md`, which in this wing already means "current focus," a different file than domain-modeling's own default glossary location. Append only new/changed terms; leave existing ones untouched unless they've demonstrably changed.
- **`anticipated_queries` frontmatter**: for every doc actually rewritten above, regenerate its
  `anticipated_queries` field to 2-5 short questions reflecting the doc's *new* content — replace
  the list wholesale, don't append to it. Leave `anticipated_queries` untouched in docs this run
  didn't touch.
- **Feature docs** (`features/{feature-slug}.md`): if this session's work clearly centered on one
  feature or domain area, ask the user whether to capture it in `features/{feature-slug}.md`
  instead of `DECISIONS.md`/`ARCHITECTURE.md` — don't create one unprompted. On confirmation:
  create the file if missing (same frontmatter conventions as the 6 core docs, including its own
  `anticipated_queries`), update it surgically if it exists, and add a link under `readme.md`'s
  `## Features` section if not already listed there.

Be surgical — only write lines that genuinely changed. Do not rewrite files that are already accurate. Tell the user what was updated and what was already current.

---

## Step 8 — Sync to auto-memory

```bash
python3 ~/.claude/skills/sync-claude-sessions/scripts/palace-to-memory --project {project-name} --force
```

Do this silently — no output to the user unless it errors.
