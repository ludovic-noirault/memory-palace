# Glossary + Retention Quiz — Design

Two additions to the wing system: a per-project glossary for shared vocabulary, and an on-demand
comprehension quiz to test retention of wing content (not just storage of it).

## 1. Glossary (`GLOSSARY.md`)

**Problem**: no shared vocabulary across sessions/tools — terms get redefined or misused because
there's nowhere authoritative to check them.

**Design**:
- 6th wing file, alongside `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`.
- Format: term → definition → pointer to more info (file path, doc link, or a reference like
  "see ARCHITECTURE.md §X").
- Populated/maintained by invoking the existing `domain-modeling` skill — reuses its
  terminology-capture process instead of building new logic. Output goes to `GLOSSARY.md`.
- Not auto-injected at `SessionStart` (keeps injection light, matches CONTEXT.md-only injection
  today). Pulled in via `/palace:read`, or on demand when a term needs clarifying.

**Touches**:
- `templates/projects/.template/GLOSSARY.md` — new template file.
- `commands/palace/create.md` — scaffold `GLOSSARY.md` for new wings.
- `commands/palace/update.md` — Step 4 (load wing) reads `GLOSSARY.md` alongside the other 5;
  Step 7 (update wing) gains a glossary sub-step: invoke `domain-modeling` to spot new/changed
  terms from the session, append only what's new (same surgical rule as the rest of Step 7 —
  don't rewrite what's accurate).
- `hooks/palace-map doctor` — wing-completeness check moves from 5 files to 6.
- `docs/ARCHITECTURE.md` — mention the 6th file in the wing description.
- Existing wings: `GLOSSARY.md` backfilled once, manually, not automatically.

## 2. Retention quiz (`/palace:quiz`)

**Problem**: ingesting info into the palace (highlighting/storing) isn't the same as understanding
or being able to recount it. Being quizzed on stored content forces genuine comprehension, not just
digital storage.

**Design**:
- New command `commands/palace/quiz.md`.
- Reads all 6 wing files (`readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`,
  `GLOSSARY.md`).
- Generates 5–8 questions on the fly from that content — no stored deck, no spaced-repetition
  scheduling. Always matches current wing state since nothing is pre-baked.
- Skips sections that are thin or empty rather than forcing questions from nothing (relevant for
  early-stage projects).
- Style: tutor, not adversarial — ask one question, wait for the answer, confirm or correct with a
  brief explanation, move to the next. Deliberately distinct from the existing `grilling` skill
  (relentless/adversarial, built for stress-testing plans and decisions, not for recall).
- Question mix drawn across the wing: glossary terms, decisions ("why did we choose X"),
  architecture gotchas, open bugs — the point is confirming absorption of what's stored, not just
  re-reading it back.
- Scope: whole wing each run (not just the latest session's delta).
- Triggered manually (`/palace:quiz`) — no forced interruption mid-session.

**Retention state — `QUIZ_LOG.md`**:
- New per-wing file, append-only markdown table: `date | score | weak topics`.
- Not one of the 6 curated files — it's a log (machine-appended), not hand-curated content, closer
  in spirit to a session history than to CONTEXT.md/DECISIONS.md.
- Each quiz run appends one row (e.g. `2026-07-20 | 6/8 | GLOSSARY: term X, DECISIONS: why Y`).
- The log's last row is also the "last quizzed" timestamp — no separate state needed elsewhere.

**Nudge**:
- `hooks/palace-reminder.sh` (SessionEnd) gains a second check alongside its existing
  `/palace:update` nudge: if ≥4 days since the last `QUIZ_LOG.md` row AND the wing has had recent
  activity (mirrors existing dormancy logic in `palace-map doctor`), nudge to run `/palace:quiz`.
- No nudge for wings with no activity — avoids nagging dormant projects.

**Touches**:
- `commands/palace/quiz.md` — new.
- `templates/projects/.template/QUIZ_LOG.md` — new template, empty table.
- `hooks/palace-reminder.sh` — add the quiz-nudge check.
- `hooks/palace-map doctor` — optionally surface wings never quizzed (informational only, not a
  hard gate like the 6-file completeness check).

## Out of scope

- Spaced-repetition scheduling (SM-2 or similar) — explicitly rejected in favor of simplicity;
  `QUIZ_LOG.md` tracks history, not per-card intervals.
- Auto-injecting `GLOSSARY.md` at `SessionStart` — stays on-demand to avoid token bloat.
- Automatic quiz triggering mid-session — `/palace:quiz` is always user-invoked; the nudge only
  suggests, never runs it.
