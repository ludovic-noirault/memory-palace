---
description: Search wing docs (including feature sub-docs) for the ones that answer a question, for the active project
---

You are looking up which palace wing doc answers a question, for the active project. The palace lives at `~/obsidian/projects/`. This command performs **zero writes**.

---

## Step 1 — Identify the project

Run `pwd`. Resolve the slug:

```bash
~/.claude/hooks/palace-map resolve "$PWD"
```

---

## Step 2 — Run the search

If Step 1 resolved a slug, scope the search to it:

```bash
~/.claude/hooks/palace-map search "{query}" --slug {slug}
```

If no slug resolved, search every wing:

```bash
~/.claude/hooks/palace-map search "{query}" --all
```

---

## Step 3 — Report

Print the ranked results verbatim (`slug/file.md — "matched query" (score)`, highest score first).

If the output is `no matches`, tell the user no doc's `anticipated_queries` matched this query, and
suggest `/palace:read` to browse the wing directly, or `/palace:update` if the doc covering this
likely doesn't exist yet.
