---
tags: [meta, relations]
---
# Project Relations

Dataview queries over `client`/`stack` frontmatter in each wing's `readme.md`. Source of truth = frontmatter — edit there when a wing's client/stack changes, this file just renders it. New wing → copy `.template/readme.md`, fill `client`/`stack`, done.

Active views exclude wings marked `status: archived`. Run `palace-map doctor` to see dormancy candidates; `palace-map archive <slug>` / `unarchive <slug>` flips the flag.

## Active wings

```dataview
TABLE client, stack, status
FROM "projects"
WHERE project AND !contains(file.path, ".template") AND status != "archived"
SORT client ASC
```

## Grouped by client

```dataview
TABLE rows.project AS "Projects"
FROM "projects"
WHERE project AND !contains(file.path, ".template") AND status != "archived"
GROUP BY client
```

## Grouped by stack (shared tech across clients)

```dataview
TABLE rows.project AS "Projects"
FROM "projects"
WHERE project AND !contains(file.path, ".template") AND status != "archived"
FLATTEN stack
GROUP BY stack
```

## Archived wings

```dataview
TABLE client, stack
FROM "projects"
WHERE project AND status = "archived"
SORT file.name ASC
```
