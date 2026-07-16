---
description: Create a new memory palace wing for the active project and wire it into every hook + the identity map
---

You are creating a new memory palace wing. The palace lives at `~/obsidian/projects/`. This command only runs when a wing does not already exist for the active project — it never overwrites an existing one. Wiring a new project touches 5 files across the system; be precise about insertion points, and confirm the slug/pattern with the user before writing anything (this is the one ambiguous step worth a pause).

---

## Step 1 — Determine project slug + PWD pattern

Run `pwd`. Read `~/obsidian/projects/_mapping.md` and check if `$PWD` already matches an existing row's pattern.

- **Match found** → check `WING=~/obsidian/projects/{that-project-name}`. If it already exists, print `Wing already exists for {project-name}. Use /palace:read or /palace:update.` and stop.
- **No match** → propose defaults: `slug = basename($PWD)`, `pattern = */{slug}*`. Use `AskUserQuestion` to confirm (or let the user override) both the slug and the glob pattern before proceeding — a bad pattern here silently breaks `SessionStart` injection later (this is exactly the class of bug found and fixed on 2026-07-08 for `dev`/`library-destiny-migration`/`swizzin-migration`).

Also check the pattern doesn't collide with (i.e. isn't a substring match of, or matched by) any existing pattern in `_mapping.md` — if it does, flag it to the user in the same question instead of guessing silently.

Set `WING=~/obsidian/projects/{slug}`.

---

## Step 2 — Create the wing

1. `mkdir -p "$WING"`
2. Copy all 5 template files from `~/obsidian/projects/.template/` into `$WING`.
3. Replace every `{{PROJECT_NAME}}` placeholder with `{slug}`.
4. Explore the active project directory (git log, key source files, package.json / composer.json / pyproject.toml) to gather: tech stack, recent commits, current branch, any open issues visible in code or TODO comments.
5. Populate all 5 wing files with real data — do not leave template placeholders.

---

## Step 3 — Wire the project (single source)

Identity lives in ONE file — `~/obsidian/projects/_mapping.json`. The hooks/scripts (`palace-context.sh`, `palace-reminder.sh`, the `settings.json` Stop hook, `palace-to-memory`) all resolve through `~/.claude/hooks/palace-map`, so there is **nothing else to edit** — do NOT re-add a `case` list anywhere.

Compute `MEMDIR = $PWD with every "/" replaced by "-"` (how Claude Code encodes project dirs under `~/.claude/projects/`).

Append one entry to the `projects` array in `_mapping.json` (preserve the order/first-match semantics — put more-specific globs before broader ones):

```json
{ "slug": "{slug}", "globs": ["{pattern}"], "memdir": "{MEMDIR}", "repo": "{$PWD}" }
```

Then regenerate the human table and validate:
```bash
~/.claude/hooks/palace-map render     # refreshes the table in _mapping.md
~/.claude/hooks/palace-map validate   # must print OK — errors mean orphan mapping / unwired wing
~/.claude/hooks/palace-map resolve "{$PWD}"   # must print {slug}
```

If `validate` reports an ERROR or `resolve` prints the wrong slug (glob collision), fix the JSON before continuing — do not leave broken wiring in place.

---

## Step 4 — Report + brief

Tell the user: **"Wing created for {slug}, wired via _mapping.json (one source — validate passed)."**

Then print the session brief (same format as `/palace:read` Step 4, plus recent sessions and open MRs — Steps 5–6 of that command).
