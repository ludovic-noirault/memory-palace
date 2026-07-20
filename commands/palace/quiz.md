---
description: Quiz you on the active project's palace wing to test retention — tutor-style, questions generated fresh each run, no stored deck
---

You are running a comprehension quiz against the memory palace wing for the active project. Style is
tutor, not adversarial: ask one question, wait for the answer, confirm or correct, move on. This is
distinct from the `grilling` skill (adversarial stress-testing of plans/decisions) — the goal here is
confirming retention of facts already stored in the wing, not pressure-testing a decision.

---

## Step 1 — Identify the project

Run `pwd`. Read `~/obsidian/projects/_mapping.md` and match `$PWD` against the "SessionStart/hook `$PWD` match" column (glob patterns, same semantics as bash `case`). No match → fall back to the last path component of `$PWD` as the project name, and say so.

Set `WING=~/obsidian/projects/{project-name}`.

---

## Step 2 — Wing exists?

Run `ls "$WING" 2>/dev/null`. If it does not exist, print exactly this and stop:

```
No palace wing for {project-name} at {WING}.
Run /palace:create first.
```

---

## Step 3 — Load the wing

Read all 6 files in parallel: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`.

---

## Step 4 — Generate questions

Draw 5–8 questions from across the wing content loaded in Step 3:
- **GLOSSARY.md** — "what does {term} mean", "where would you use {term}"
- **DECISIONS.md** — "why did we choose {X} over {alternative}"
- **ARCHITECTURE.md / Critical Gotchas** — "what happens if you forget {gotcha}"
- **BUGS.md** — "what's the status of {open bug}", "what's the severity of {bug}"

Skip any section that is empty or still has only template placeholder content (e.g. a `DECISIONS.md`
with just the `## [Decision title]` heading and no real entries contributes zero questions). If fewer
than 5 real questions can be drawn from non-empty sections, ask fewer — do not invent facts not present
in the wing.

Do not show the user the full question list up front — ask one at a time (Step 5).

---

## Step 5 — Run the quiz

For each question: ask it, wait for the user's answer, then:
- If correct (or substantially correct): confirm briefly, move to the next question.
- If incorrect or incomplete: give the correct answer in one line, sourced from the wing file it came from, then move on.

Track a running tally: `correct` count, `total` count, and a list of `weak_topics` (short label per
file/section where an answer was wrong, e.g. `DECISIONS: why Postgres`).

---

## Step 6 — Score + log

Report the final score conversationally (e.g. "6/8 — solid, but the Postgres decision needs another look").

Get today's date: `date +%F`.

If `QUIZ_LOG.md` doesn't exist yet (a wing created before this feature), create it first with:

```
---
tags: [project, quiz-log]
project: {project-name}
---
# Quiz Log — {project-name}

Append-only history of `/palace:quiz` runs — comprehension score and weak topics per run. Not a
spaced-repetition schedule; questions are regenerated fresh from the wing every time, this file only
tracks how you did.

| Date | Score | Weak topics |
|------|-------|-------------|
```

Then append one row to its table:

```
| {YYYY-MM-DD} | {correct}/{total} | {comma-separated weak_topics, or "none"} |
```

Tell the user the row was appended so they know their score is recorded.
