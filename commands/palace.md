---
description: Explain what the memory palace is, why it exists, and how to use /palace:read, :create, :update, :doctor
---

Print exactly the block below, verbatim. Do not run any tools, read any files, or take any action — this command only explains.

```
## 🏛 Memory Palace

**Why it exists:** Claude Code sessions are stateless — every new session starts cold. The palace is a per-project memory
of what's being worked on, what's broken, and why past decisions were made, so you don't re-explain context every time.

**Where it lives:** ~/obsidian/projects/{project-name}/ — 5 files: readme.md, ARCHITECTURE.md, BUGS.md,
CONTEXT.md, DECISIONS.md. CONTEXT.md is auto-injected into every session via the SessionStart hook.

**Commands:**
  /palace:read    Load the wing + print a session brief (focus, blockers, bugs, gotchas, recent sessions, open MRs).
                  Read-only — never creates or modifies anything. Use this at the start of a work session.

  /palace:create  Set up a new wing for a project that doesn't have one yet. Explores the repo, populates all 5
                  files, and wires the new project into every hook + projects/_mapping.md so SessionStart injection
                  and auto-memory sync work going forward. Refuses to run if a wing already exists.

  /palace:update  Flush what happened this session back into the wing — new bugs, decisions, changed focus, refreshed
                  MRs — then sync to Claude auto-memory. Refuses to run if no wing exists yet (run /palace:create first).

  /palace:doctor  Health-check the whole install (hooks, launchd, paths, config) + every wing (staleness, dormancy),
                  interpret the results, and propose fixes. Read-only — never changes anything without your yes.

**Maintenance (CLI, rarely needed):** `palace-install.sh` (re)installs/moves the system to a new machine;
`palace-map validate|render` are plumbing run by /palace:create. See the Operations section of memory-setup.md.

**More detail:** ~/obsidian/memory-setup.md (architecture + Operations) and projects/_mapping.json
(canonical project ↔ hook ↔ auto-memory identity source).
```
