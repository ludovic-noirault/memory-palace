# Glossary + Retention Quiz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-wing `GLOSSARY.md` (domain vocabulary, maintained via `domain-modeling`) and an on-demand `/palace:quiz` command (tutor-style comprehension quiz over wing content, with a per-wing `QUIZ_LOG.md` history and a SessionEnd nudge) to the memory-palace engine.

**Architecture:** `GLOSSARY.md` becomes a 6th curated wing file, following the exact same lifecycle as the existing 5 (scaffolded by `/palace:create`, loaded by `/palace:read` and `/palace:update`, maintained surgically in `/palace:update`, required by `palace-map doctor --system`). `QUIZ_LOG.md` is a 7th file but a *log*, not curated content — append-only, written only by `/palace:quiz`, and used by a new `palace-map quiz-status` command to drive a SessionEnd nudge (mirroring how `palace-map activity`/`doctor` already drive staleness/dormancy signals).

**Tech Stack:** Bash (hooks), stdlib-only Python 3 (`palace-map`), Markdown (templates + slash commands), stdlib `unittest` (tests).

## Global Constraints

- Single source of truth invariant: no new hardcoded file-count or project lists outside `palace-map` / the templates dir — reuse existing resolver functions (`entry`, `git_commit_epoch`, `newest_session_epoch`, `DORMANT_DAYS`) rather than duplicating logic.
- stdlib only — no new pip dependencies, matches existing `palace-map` and test suite.
- `GLOSSARY.md` and `QUIZ_LOG.md` are **never** auto-injected at `SessionStart` (`palace-context.sh` stays untouched) and **never** synced to auto-memory (`palace-to-memory` stays untouched) — both stay on-demand only, per the approved design spec (`docs/superpowers/specs/2026-07-20-glossary-and-quiz-design.md`).
- `/palace:quiz` never persists a question deck — questions are regenerated fresh from the wing every run. Only the score/topics summary is persisted, in `QUIZ_LOG.md`.
- Existing wings in the user's real vault are backfilled with `GLOSSARY.md` **manually** (Task 13), not by any automated migration — matches the approved design.
- macOS-only assumptions already in this repo (`launchctl`, `stat -f`) are unaffected by this work — no new platform-specific code introduced.

---

### Task 1: Wing templates + install.sh backfill

**Files:**
- Create: `templates/projects/.template/GLOSSARY.md`
- Create: `templates/projects/.template/QUIZ_LOG.md`
- Modify: `install.sh:46-52`

**Interfaces:**
- Produces: the canonical `GLOSSARY.md` format (`## [Term]` heading, `- **Definition**`, `- **Avoid**`, `- **More info**` bullets) and `QUIZ_LOG.md` format (`| Date | Score | Weak topics |` table, no data rows initially) that every later task reads/writes against.
- Produces: install.sh now backfills individual missing files into an already-existing `$VAULT/projects/.template/` dir (not just a one-shot whole-directory copy).

- [ ] **Step 1: Create the GLOSSARY.md template**

Write `templates/projects/.template/GLOSSARY.md`:

```markdown
---
tags: [project, glossary]
project: {{PROJECT_NAME}}
---
# Glossary — {{PROJECT_NAME}}

Domain terms specific to this project's ubiquitous language — maintained via the `domain-modeling` skill.
Only terms unique to this project belong here; general programming concepts (timeouts, error types, utility
patterns) don't, even if used extensively.

## [Term]

- **Definition**: What it IS, in one or two sentences — not what it does.
- **Avoid**: Other words sometimes used for the same concept, if any.
- **More info**: File path, doc link, or section reference for deeper detail.
```

- [ ] **Step 2: Create the QUIZ_LOG.md template**

Write `templates/projects/.template/QUIZ_LOG.md`:

```markdown
---
tags: [project, quiz-log]
project: {{PROJECT_NAME}}
---
# Quiz Log — {{PROJECT_NAME}}

Append-only history of `/palace:quiz` runs — comprehension score and weak topics per run. Not a
spaced-repetition schedule; questions are regenerated fresh from the wing every time, this file only
tracks how you did.

| Date | Score | Weak topics |
|------|-------|-------------|
```

- [ ] **Step 3: Make install.sh backfill individual template files**

In `install.sh`, replace lines 46-52:

```bash
# 2. vault skeleton — create-if-missing only, never overwrite existing content
mkdir -p "$VAULT/projects" "$VAULT/claude-sessions"
[ -e "$VAULT/projects/.template" ]     || cp -pR "$REPO/templates/projects/.template" "$VAULT/projects/.template"
[ -f "$VAULT/projects/_mapping.json" ] || cp -p  "$REPO/templates/projects/_mapping.json" "$VAULT/projects/_mapping.json"
[ -f "$VAULT/projects/_mapping.md" ]   || cp -p  "$REPO/templates/projects/_mapping.md"   "$VAULT/projects/_mapping.md"
[ -f "$VAULT/projects/_relations.md" ] || cp -p  "$REPO/templates/projects/_relations.md" "$VAULT/projects/_relations.md"
echo "  vault skeleton ensured"
```

with:

```bash
# 2. vault skeleton — create-if-missing only, never overwrite existing content
mkdir -p "$VAULT/projects" "$VAULT/claude-sessions"
mkdir -p "$VAULT/projects/.template"
for f in "$REPO"/templates/projects/.template/*; do
  name="$(basename "$f")"
  [ -f "$VAULT/projects/.template/$name" ] || cp -p "$f" "$VAULT/projects/.template/$name"
done
[ -f "$VAULT/projects/_mapping.json" ] || cp -p  "$REPO/templates/projects/_mapping.json" "$VAULT/projects/_mapping.json"
[ -f "$VAULT/projects/_mapping.md" ]   || cp -p  "$REPO/templates/projects/_mapping.md"   "$VAULT/projects/_mapping.md"
[ -f "$VAULT/projects/_relations.md" ] || cp -p  "$REPO/templates/projects/_relations.md" "$VAULT/projects/_relations.md"
echo "  vault skeleton ensured (backfilled any new template files)"
```

This is the same create-if-missing-per-item semantics as before, just per-file instead of per-directory — so a `.template/` dir that already exists (real installs) still picks up newly-added template files on the next `./install.sh` run, without touching any file a user may have hand-edited.

- [ ] **Step 4: Verify manually**

```bash
rm -rf /tmp/palace-fixture-vault && mkdir -p /tmp/palace-fixture-vault/projects/.template
touch /tmp/palace-fixture-vault/projects/.template/readme.md   # simulate a pre-existing template dir missing the new files
VAULT_DIR=/tmp/palace-fixture-vault PALACE_CLAUDE_DIR=/tmp/palace-fixture-claude ./install.sh || true
ls /tmp/palace-fixture-vault/projects/.template/
```
Expected: listing includes `GLOSSARY.md` and `QUIZ_LOG.md` alongside the untouched `readme.md`. (The `|| true` is because `doctor --system` will report red against the throwaway `PALACE_CLAUDE_DIR` — irrelevant to this check.) Clean up: `rm -rf /tmp/palace-fixture-vault /tmp/palace-fixture-claude`.

- [ ] **Step 5: Commit**

```bash
git add templates/projects/.template/GLOSSARY.md templates/projects/.template/QUIZ_LOG.md install.sh
git commit -m "feat: add GLOSSARY.md/QUIZ_LOG.md wing templates, backfill install.sh"
```

---

### Task 2: `palace-map` — require GLOSSARY.md as the 6th wing file

**Files:**
- Modify: `hooks/palace-map:289-296`
- Modify: `skills/palace-tests/test_palace_map.py:24-34`
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: `GLOSSARY.md` filename from Task 1.
- Produces: `WING_FILES` list and `make_wing()` / new `write_quiz_log()` fixture helpers in the test file, reused by Task 3's and Task 4's new tests.

- [ ] **Step 1: Write the failing test**

In `skills/palace-tests/test_palace_map.py`, add a new test class (after `SystemDoctorTests`):

```python
class SystemDoctorGlossaryTests(unittest.TestCase):
    def test_missing_glossary_flags_red(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        (root / "projects" / "alpha" / "GLOSSARY.md").unlink()
        rc, out, _ = run(root, "doctor", "--system")
        self.assertEqual(rc, 1)
        self.assertIn("GLOSSARY.md", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map.SystemDoctorGlossaryTests -v`
Expected: FAIL — `make_wing()` doesn't create `GLOSSARY.md` yet, so `.unlink()` raises `FileNotFoundError` (or, if you stub around that, the doctor check doesn't yet look for `GLOSSARY.md` so it stays green regardless).

- [ ] **Step 3: Update the fixture helper to create GLOSSARY.md and QUIZ_LOG.md**

Replace `skills/palace-tests/test_palace_map.py:24-34`:

```python
WING_FILES = ["readme.md", "ARCHITECTURE.md", "BUGS.md", "CONTEXT.md", "DECISIONS.md"]


def make_wing(projects: Path, slug: str, status: str = "active"):
    d = projects / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "readme.md").write_text(f"---\ntags: [project]\nproject: {slug}\nstatus: {status}\n---\n# {slug}\n")
    (d / "CONTEXT.md").write_text(f"---\nproject: {slug}\n---\n# Context — {slug}\n\n## Current Focus\nstuff\n")
    for f in ("ARCHITECTURE.md", "BUGS.md", "DECISIONS.md"):
        (d / f).write_text(f"# {f} — {slug}\n")
    return d
```

with:

```python
WING_FILES = ["readme.md", "ARCHITECTURE.md", "BUGS.md", "CONTEXT.md", "DECISIONS.md", "GLOSSARY.md"]
QUIZ_LOG_HEADER = "| Date | Score | Weak topics |\n|------|-------|-------------|\n"


def make_wing(projects: Path, slug: str, status: str = "active"):
    d = projects / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "readme.md").write_text(f"---\ntags: [project]\nproject: {slug}\nstatus: {status}\n---\n# {slug}\n")
    (d / "CONTEXT.md").write_text(f"---\nproject: {slug}\n---\n# Context — {slug}\n\n## Current Focus\nstuff\n")
    for f in ("ARCHITECTURE.md", "BUGS.md", "DECISIONS.md", "GLOSSARY.md"):
        (d / f).write_text(f"# {f} — {slug}\n")
    (d / "QUIZ_LOG.md").write_text(f"# Quiz Log — {slug}\n\n{QUIZ_LOG_HEADER}")
    return d


def write_quiz_log(projects: Path, slug: str, rows):
    """rows: list of (date_str, score_str, topics_str). Overwrites QUIZ_LOG.md's table body."""
    body = QUIZ_LOG_HEADER
    for date_str, score, topics in rows:
        body += f"| {date_str} | {score} | {topics} |\n"
    (projects / slug / "QUIZ_LOG.md").write_text(f"# Quiz Log — {slug}\n\n{body}")
```

- [ ] **Step 4: Update `palace-map`'s completeness check**

In `hooks/palace-map`, replace lines 289-296:

```python
    # 5. every wing has its 5 files
    missing = []
    for p in load():
        d = VAULT_PROJECTS / p["slug"]
        for f in ("readme.md", "ARCHITECTURE.md", "BUGS.md", "CONTEXT.md", "DECISIONS.md"):
            if not (d / f).is_file():
                missing.append(f"{p['slug']}/{f}")
    ck(not missing, "every wing has its 5 files", ", ".join(missing[:5]))
```

with:

```python
    # 5. every wing has its 6 files
    missing = []
    for p in load():
        d = VAULT_PROJECTS / p["slug"]
        for f in ("readme.md", "ARCHITECTURE.md", "BUGS.md", "CONTEXT.md", "DECISIONS.md", "GLOSSARY.md"):
            if not (d / f).is_file():
                missing.append(f"{p['slug']}/{f}")
    ck(not missing, "every wing has its 6 files", ", ".join(missing[:5]))
```

Also update the module docstring's `doctor --system` line (`hooks/palace-map:19`) — no code meaning change, just keeps the doc accurate; leave as-is (it already just says "verify the whole install", no file count mentioned).

- [ ] **Step 5: Run test to verify it passes**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map -v`
Expected: `SystemDoctorGlossaryTests.test_missing_glossary_flags_red` PASSES. Also confirm no regressions: every other test in the file still passes (they all go through the now-6-file `make_wing()`).

Note: `SystemDoctorTests.test_live_install_green` runs against the **real** `~/.claude` / real vault. It will now FAIL (red, missing `GLOSSARY.md` in existing real wings) until Task 13's manual backfill runs. This is expected — don't chase it here.

- [ ] **Step 6: Commit**

```bash
git add hooks/palace-map skills/palace-tests/test_palace_map.py
git commit -m "feat: require GLOSSARY.md as the 6th wing file in doctor --system"
```

---

### Task 3: `palace-map quiz-status` command

**Files:**
- Modify: `hooks/palace-map` (docstring, new functions, new `cmd_quiz_status`, `CMDS` registration)
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: `QUIZ_LOG.md` table format from Task 1; `entry()`, `git_commit_epoch()`, `newest_session_epoch()`, `DORMANT_DAYS` already defined in `hooks/palace-map`; `write_quiz_log()` fixture helper from Task 2.
- Produces: `palace-map quiz-status <slug>` — prints `NUDGE` (with no trailing content) if the wing should be nudged to run `/palace:quiz`, else prints nothing. Consumed by Task 4 (`palace-reminder.sh`) and by the informational check in Task 5.

- [ ] **Step 1: Write the failing tests**

Add to `skills/palace-tests/test_palace_map.py`:

```python
class QuizStatusTests(unittest.TestCase):
    def _repo_with_commit(self, root):
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "c"], check=True)
        return repo

    def test_never_quizzed_active_repo_nudges(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/x"}])
        repo = self._repo_with_commit(root)
        (root / "projects" / "_mapping.json").write_text(json.dumps({"projects": [
            {"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": str(repo)}]}, indent=2))
        self.assertEqual(run(root, "quiz-status", "svc")[1].strip(), "NUDGE")

    def test_recently_quizzed_no_nudge(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/x"}])
        repo = self._repo_with_commit(root)
        (root / "projects" / "_mapping.json").write_text(json.dumps({"projects": [
            {"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": str(repo)}]}, indent=2))
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        write_quiz_log(root / "projects", "svc", [(today, "6/8", "none")])
        self.assertEqual(run(root, "quiz-status", "svc")[1].strip(), "")

    def test_no_activity_no_nudge(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/nonexistent-x"}])
        self.assertEqual(run(root, "quiz-status", "svc")[1].strip(), "")
```

Add `import datetime` to the top of `skills/palace-tests/test_palace_map.py` alongside the existing `import time`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map.QuizStatusTests -v`
Expected: FAIL with `SystemExit` / usage message printed to stdout (unknown command `quiz-status` — `CMDS[sys.argv[1]]` lookup fails, `main` prints `__doc__` and exits 2) — none of the assertions match `"NUDGE"` or `""` as expected.

- [ ] **Step 3: Implement `quiz_log_last_date` and `cmd_quiz_status`**

In `hooks/palace-map`, add after `is_archived()` (currently ending at line 234):

```python
QUIZ_NUDGE_DAYS = 4


def quiz_log_last_date(slug):
    """Epoch seconds of the last dated row in QUIZ_LOG.md, or None if never quizzed."""
    f = VAULT_PROJECTS / slug / "QUIZ_LOG.md"
    if not f.is_file():
        return None
    rows = [l for l in f.read_text().splitlines() if l.strip().startswith("|") and "---" not in l]
    if len(rows) <= 1:  # header only (or nothing) — no quiz run yet
        return None
    cols = [c.strip() for c in rows[-1].split("|") if c.strip()]
    if not cols:
        return None
    try:
        import datetime
        dt = datetime.datetime.strptime(cols[0], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def cmd_quiz_status(args):
    """Print NUDGE if it's been >= QUIZ_NUDGE_DAYS since the wing's last quiz AND the
    wing has real recent activity (not dormant) — else print nothing."""
    slug = args[0] if args else None
    e = entry(slug) if slug else None
    if not e:
        return
    import time
    now = int(time.time())
    act = git_commit_epoch(e["repo"]) or newest_session_epoch(slug)
    if not act or (now - act) // 86400 > DORMANT_DAYS:
        return  # dormant or no activity signal — don't nag a dead project
    last_quiz = quiz_log_last_date(slug)
    if last_quiz is None or (now - last_quiz) // 86400 >= QUIZ_NUDGE_DAYS:
        print("NUDGE")
```

Register it in `CMDS` (currently lines 370-374):

```python
CMDS = {
    "resolve": cmd_resolve, "memdir": cmd_memdir, "repo": cmd_repo, "list": cmd_list,
    "activity": cmd_activity, "validate": cmd_validate, "render": cmd_render, "doctor": cmd_doctor,
    "archive": cmd_archive, "unarchive": cmd_unarchive, "quiz-status": cmd_quiz_status,
}
```

Add one line to the module docstring's command list (after the `activity` line, currently `hooks/palace-map:15`):

```
  quiz-status <slug> print NUDGE if the wing hasn't been quizzed in QUIZ_NUDGE_DAYS+ AND has recent activity
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map -v`
Expected: all tests PASS (aside from the still-expected `test_live_install_green` failure noted in Task 2, unrelated to this task).

- [ ] **Step 5: Commit**

```bash
git add hooks/palace-map skills/palace-tests/test_palace_map.py
git commit -m "feat: add palace-map quiz-status command"
```

---

### Task 4: Wire the quiz nudge into `palace-reminder.sh`

**Files:**
- Modify: `hooks/palace-reminder.sh`
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: `palace-map quiz-status <slug>` from Task 3 (prints `NUDGE` or nothing).
- Produces: `palace-reminder.sh` now emits one combined `systemMessage` (update reminder + optional quiz nudge) instead of just the update reminder.

- [ ] **Step 1: Write the failing tests**

Add to `skills/palace-tests/test_palace_map.py`:

```python
class ReminderTests(unittest.TestCase):
    PALACE_REMINDER = CLAUDE_DIR / "hooks" / "palace-reminder.sh"

    def _run_reminder(self, root, cwd):
        env = {**os.environ, "VAULT_DIR": str(root), "PALACE_CLAUDE_DIR": str(CLAUDE_DIR)}
        work = root / cwd
        work.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["bash", str(self.PALACE_REMINDER)], capture_output=True, text=True,
                           env=env, cwd=str(work))
        return r.stdout

    def test_no_match_silent(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/x"}])
        out = self._run_reminder(root, "other")
        self.assertEqual(out.strip(), "")

    def test_match_no_quiz_nudge_without_activity(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/x"}])
        out = self._run_reminder(root, "svc")
        self.assertIn("run /palace update", out)
        self.assertNotIn("Also", out)

    def test_match_quiz_nudge_when_active_and_never_quizzed(self):
        root = make_vault([{"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": "~/x"}])
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "c"], check=True)
        (root / "projects" / "_mapping.json").write_text(json.dumps({"projects": [
            {"slug": "svc", "globs": ["*/svc*"], "memdir": "-s", "repo": str(repo)}]}, indent=2))
        out = self._run_reminder(root, "svc")
        self.assertIn("Also", out)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map.ReminderTests -v`
Expected: `test_match_quiz_nudge_when_active_and_never_quizzed` FAILS — current `palace-reminder.sh` never emits "Also".

- [ ] **Step 3: Update palace-reminder.sh**

Replace the full contents of `hooks/palace-reminder.sh`:

```bash
#!/bin/bash
# SessionEnd reminder to flush learnings + (occasionally) nudge a retention quiz.
# Fires only when pwd maps to a wing. Project identity resolved via palace-map
# (single source: projects/_mapping.json).
_OV_PCD="$PALACE_CLAUDE_DIR"
PCD_BOOT="${PALACE_CLAUDE_DIR:-$HOME/.claude}"
[ -f "$PCD_BOOT/palace.env" ] && . "$PCD_BOOT/palace.env"
PALACE_CLAUDE_DIR="${_OV_PCD:-${PALACE_CLAUDE_DIR:-$HOME/.claude}}"
export VAULT_DIR PALACE_CLAUDE_DIR
CURRENT_PWD="${PWD:-$(pwd)}"
MAP="$PALACE_CLAUDE_DIR/hooks/palace-map"
project="$("$MAP" resolve "$CURRENT_PWD")"
[ -z "$project" ] && exit 0

msg="Palace: run /palace update to persist session learnings."
if [ "$("$MAP" quiz-status "$project")" = "NUDGE" ]; then
  msg="$msg Also: it's been a few days since /palace:quiz on $project — worth testing retention."
fi
printf '{"systemMessage": "%s"}\n' "$msg"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map -v`
Expected: all `ReminderTests` PASS.

- [ ] **Step 5: Commit**

```bash
git add hooks/palace-reminder.sh skills/palace-tests/test_palace_map.py
git commit -m "feat: nudge /palace:quiz from palace-reminder.sh when overdue"
```

---

### Task 5: Informational "never quizzed" note in `palace-map doctor`

**Files:**
- Modify: `hooks/palace-map:320-345` (`cmd_doctor`)
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: `quiz_log_last_date()` from Task 3.
- Produces: `palace-map doctor` (non-`--system`) appends `" (never quizzed — try /palace:quiz)"` to an otherwise-`ok` wing's status line. Purely informational — does not change exit behavior (this command never calls `sys.exit`).

- [ ] **Step 1: Write the failing test**

Add to `skills/palace-tests/test_palace_map.py` (new class, or append to an existing doctor-related class):

```python
class DoctorQuizNoteTests(unittest.TestCase):
    def test_never_quizzed_wing_gets_note(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        out = run(root, "doctor")[1]
        self.assertIn("never quizzed", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map.DoctorQuizNoteTests -v`
Expected: FAIL — `cmd_doctor` doesn't mention quizzing yet.

- [ ] **Step 3: Add the note in `cmd_doctor`**

In `hooks/palace-map`, `cmd_doctor` currently ends with:

```python
        elif act is None:
            status = "no activity signal (not a local git repo, no tagged sessions) → verify repo path or archive"
        print(f"{slug:32} {(str(act_d)+'d ago' if act_d is not None else '—'):14} {status}")
```

Replace with:

```python
        elif act is None:
            status = "no activity signal (not a local git repo, no tagged sessions) → verify repo path or archive"
        if status == "ok" and quiz_log_last_date(slug) is None:
            status = "ok (never quizzed — try /palace:quiz)"
        print(f"{slug:32} {(str(act_d)+'d ago' if act_d is not None else '—'):14} {status}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd skills/palace-tests && python3 -m unittest test_palace_map -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add hooks/palace-map skills/palace-tests/test_palace_map.py
git commit -m "feat: flag never-quizzed wings in palace-map doctor output"
```

---

### Task 6: `/palace:create` scaffolds the 7 template files

**Files:**
- Modify: `commands/palace/create.md`

**Interfaces:**
- Consumes: template file set from Task 1.

- [ ] **Step 1: Update Step 2 of create.md**

Replace `commands/palace/create.md`'s Step 2 body:

```markdown
1. `mkdir -p "$WING"`
2. Copy all 5 template files from `~/obsidian/projects/.template/` into `$WING`.
3. Replace every `{{PROJECT_NAME}}` placeholder with `{slug}`.
4. Explore the active project directory (git log, key source files, package.json / composer.json / pyproject.toml) to gather: tech stack, recent commits, current branch, any open issues visible in code or TODO comments.
5. Populate all 5 wing files with real data — do not leave template placeholders.
```

with:

```markdown
1. `mkdir -p "$WING"`
2. Copy every template file from `~/obsidian/projects/.template/` into `$WING` (currently 7: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`, `QUIZ_LOG.md`).
3. Replace every `{{PROJECT_NAME}}` placeholder with `{slug}`.
4. Explore the active project directory (git log, key source files, package.json / composer.json / pyproject.toml) to gather: tech stack, recent commits, current branch, any open issues visible in code or TODO comments.
5. Populate `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md` with real data — do not leave template placeholders. Leave `GLOSSARY.md` and `QUIZ_LOG.md` scaffolded (empty) — the glossary fills in over time via `/palace:update`, the quiz log via `/palace:quiz`.
```

- [ ] **Step 2: Verify by reading the diff**

Run: `git diff commands/palace/create.md`
Expected: only Step 2's body changed; Steps 1, 3, 4 untouched.

- [ ] **Step 3: Commit**

```bash
git add commands/palace/create.md
git commit -m "docs: /palace:create scaffolds GLOSSARY.md + QUIZ_LOG.md"
```

---

### Task 7: `/palace:read` loads GLOSSARY.md

**Files:**
- Modify: `commands/palace/read.md`

- [ ] **Step 1: Update Step 3**

Replace `commands/palace/read.md`'s Step 3 body:

```markdown
Read all 5 files in parallel:
- `readme.md` — project overview and links
- `ARCHITECTURE.md` — stack, patterns, critical gotchas
- `BUGS.md` — open bugs, security issues, debt
- `CONTEXT.md` — current focus, blocked items, next up
- `DECISIONS.md` — architectural decisions and rationale
```

with:

```markdown
Read all 6 files in parallel:
- `readme.md` — project overview and links
- `ARCHITECTURE.md` — stack, patterns, critical gotchas
- `BUGS.md` — open bugs, security issues, debt
- `CONTEXT.md` — current focus, blocked items, next up
- `DECISIONS.md` — architectural decisions and rationale
- `GLOSSARY.md` — domain terms and their definitions
```

Step 4 (the session brief format) stays unchanged — the glossary is loaded into context for on-demand term lookups during the session, not force-printed into the brief every time.

- [ ] **Step 2: Verify by reading the diff**

Run: `git diff commands/palace/read.md`
Expected: only Step 3's file list changed.

- [ ] **Step 3: Commit**

```bash
git add commands/palace/read.md
git commit -m "docs: /palace:read loads GLOSSARY.md"
```

---

### Task 8: `/palace:update` loads + maintains GLOSSARY.md

**Files:**
- Modify: `commands/palace/update.md`

- [ ] **Step 1: Update Step 4 (load the wing)**

Replace:

```markdown
Read all 5 files in parallel: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`.
```

with:

```markdown
Read all 6 files in parallel: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`.
```

- [ ] **Step 2: Update Step 7 (update the wing) to maintain GLOSSARY.md**

Replace:

```markdown
Then update only what actually changed:
- **CONTEXT.md**: Current Focus, Recent Work table, Next Up, Blocked, and replace `## Open MRs` with the freshly-fetched table from Step 6 (add the section if missing)
- **BUGS.md**: newly discovered or resolved bugs
- **DECISIONS.md**: any decision inferable from recent commits or code patterns
- **ARCHITECTURE.md / Critical Gotchas**: any new gotcha surfaced during exploration

Be surgical — only write lines that genuinely changed. Do not rewrite files that are already accurate. Tell the user what was updated and what was already current.
```

with:

```markdown
Then update only what actually changed:
- **CONTEXT.md**: Current Focus, Recent Work table, Next Up, Blocked, and replace `## Open MRs` with the freshly-fetched table from Step 6 (add the section if missing)
- **BUGS.md**: newly discovered or resolved bugs
- **DECISIONS.md**: any decision inferable from recent commits or code patterns
- **ARCHITECTURE.md / Critical Gotchas**: any new gotcha surfaced during exploration
- **GLOSSARY.md**: invoke the `domain-modeling` skill against this session's conversation and code changes to spot new or changed domain terms. Write resolved terms into `GLOSSARY.md` using its `## [Term]` / `- **Definition**` / `- **Avoid**` / `- **More info**` format — **not** into `CONTEXT.md`, which in this wing already means "current focus," a different file than domain-modeling's own default glossary location. Append only new/changed terms; leave existing ones untouched unless they've demonstrably changed.

Be surgical — only write lines that genuinely changed. Do not rewrite files that are already accurate. Tell the user what was updated and what was already current.
```

- [ ] **Step 3: Verify by reading the diff**

Run: `git diff commands/palace/update.md`
Expected: Step 4's file list and Step 7's bullet list changed; everything else (Steps 1-3, 5-6, 8) untouched.

- [ ] **Step 4: Commit**

```bash
git add commands/palace/update.md
git commit -m "docs: /palace:update maintains GLOSSARY.md via domain-modeling"
```

---

### Task 9: New `/palace:quiz` command

**Files:**
- Create: `commands/palace/quiz.md`

**Interfaces:**
- Consumes: 6-file wing load pattern (Tasks 1, 2), `QUIZ_LOG.md` format (Task 1).

- [ ] **Step 1: Write commands/palace/quiz.md**

```markdown
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
```

- [ ] **Step 2: Verify the file was written correctly**

Run: `cat commands/palace/quiz.md | head -5`
Expected: shows the `description:` frontmatter line followed by the opening paragraph.

- [ ] **Step 3: Commit**

```bash
git add commands/palace/quiz.md
git commit -m "feat: add /palace:quiz retention quiz command"
```

---

### Task 10: `/palace:doctor` proposes the quiz fix

**Files:**
- Modify: `commands/palace/doctor.md`

**Interfaces:**
- Consumes: the `(never quizzed — try /palace:quiz)` status text produced by Task 5.

- [ ] **Step 1: Add a row to the symptom → fix table**

In `commands/palace/doctor.md`, the Step 3 table currently ends with the `DORMANT` row. Add one row directly after it:

```markdown
| Wing flagged `(never quizzed — try /palace:quiz)` | Purely informational — suggest running `/palace:quiz` from that project's repo; never required, never applied automatically |
```

- [ ] **Step 2: Verify by reading the diff**

Run: `git diff commands/palace/doctor.md`
Expected: one new table row, nothing else changed.

- [ ] **Step 3: Commit**

```bash
git add commands/palace/doctor.md
git commit -m "docs: /palace:doctor surfaces never-quizzed wings"
```

---

### Task 11: `/palace` overview mentions the glossary, quiz log, and /palace:quiz

**Files:**
- Modify: `commands/palace.md`

- [ ] **Step 1: Update the file count + description line**

Replace:

```markdown
**Where it lives:** ~/obsidian/projects/{project-name}/ — 5 files: readme.md, ARCHITECTURE.md, BUGS.md,
CONTEXT.md, DECISIONS.md. CONTEXT.md is auto-injected into every session via the SessionStart hook.
```

with:

```markdown
**Where it lives:** ~/obsidian/projects/{project-name}/ — 7 files: readme.md, ARCHITECTURE.md, BUGS.md,
CONTEXT.md, DECISIONS.md, GLOSSARY.md (6 curated files), plus an append-only QUIZ_LOG.md. CONTEXT.md is
auto-injected into every session via the SessionStart hook; GLOSSARY.md and QUIZ_LOG.md are on-demand
only (loaded via /palace:read and /palace:quiz respectively), never auto-injected.
```

- [ ] **Step 2: Update the /palace:create line**

Replace:

```markdown
  /palace:create  Set up a new wing for a project that doesn't have one yet. Explores the repo, populates all 5
                  files, and wires the new project into every hook + projects/_mapping.md so SessionStart injection
                  and auto-memory sync work going forward. Refuses to run if a wing already exists.
```

with:

```markdown
  /palace:create  Set up a new wing for a project that doesn't have one yet. Explores the repo, populates the 5
                  curated content files (scaffolds GLOSSARY.md and QUIZ_LOG.md empty), and wires the new project
                  into every hook + projects/_mapping.md so SessionStart injection and auto-memory sync work going
                  forward. Refuses to run if a wing already exists.
```

- [ ] **Step 3: Add a /palace:quiz line after /palace:doctor**

Replace:

```markdown
  /palace:doctor  Health-check the whole install (hooks, launchd, paths, config) + every wing (staleness, dormancy),
                  interpret the results, and propose fixes. Read-only — never changes anything without your yes.
```

with:

```markdown
  /palace:doctor  Health-check the whole install (hooks, launchd, paths, config) + every wing (staleness, dormancy),
                  interpret the results, and propose fixes. Read-only — never changes anything without your yes.

  /palace:quiz    Quiz you on the wing's content (glossary terms, decisions, gotchas, open bugs) to test retention —
                  tutor-style, questions generated fresh each run, score appended to QUIZ_LOG.md. Refuses to run if
                  no wing exists yet.
```

- [ ] **Step 4: Verify by reading the diff**

Run: `git diff commands/palace.md`
Expected: the three edits above, nothing else changed.

- [ ] **Step 5: Commit**

```bash
git add commands/palace.md
git commit -m "docs: /palace overview mentions glossary, quiz log, /palace:quiz"
```

---

### Task 12: Update ARCHITECTURE.md and repo CLAUDE.md

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update docs/ARCHITECTURE.md's wing description**

Replace:

```markdown
Layer 1 is the load-bearing one: hand-curated, stable, strategic. A wing has five files —
`readme.md` (overview/team/links), `ARCHITECTURE.md` (stack/patterns/gotchas), `BUGS.md`
(open bugs/security/debt), `CONTEXT.md` (current focus/next up/blocked — the file that gets injected),
and `DECISIONS.md` (the *why* behind choices).
```

with:

```markdown
Layer 1 is the load-bearing one: hand-curated, stable, strategic. A wing has six curated files —
`readme.md` (overview/team/links), `ARCHITECTURE.md` (stack/patterns/gotchas), `BUGS.md`
(open bugs/security/debt), `CONTEXT.md` (current focus/next up/blocked — the file that gets injected),
`DECISIONS.md` (the *why* behind choices), and `GLOSSARY.md` (domain terms, maintained via the
`domain-modeling` skill, loaded on demand rather than injected). A seventh file, `QUIZ_LOG.md`, is an
append-only log — not hand-curated content — tracking `/palace:quiz` comprehension scores over time.
```

- [ ] **Step 2: Update the doctor --system bullet**

Replace `docs/ARCHITECTURE.md`'s line:

```markdown
- **`palace-map doctor --system`** — verifies the whole install: config present, hooks registered in
  `settings.json`, launchd job loaded, referenced paths exist, every wing has its 5 files, `_mapping.md`
  in sync, validate clean. One green/red report; non-zero exit on any red.
```

with:

```markdown
- **`palace-map doctor --system`** — verifies the whole install: config present, hooks registered in
  `settings.json`, launchd job loaded, referenced paths exist, every wing has its 6 files, `_mapping.md`
  in sync, validate clean. One green/red report; non-zero exit on any red.
```

- [ ] **Step 3: Update CLAUDE.md's palace layer description**

Replace:

```markdown
1. **Palace** — hand-curated per-project "wings" (5 files: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`,
   `CONTEXT.md`, `DECISIONS.md`) living in the user's vault, injected at `SessionStart`.
```

with:

```markdown
1. **Palace** — hand-curated per-project "wings" (6 files: `readme.md`, `ARCHITECTURE.md`, `BUGS.md`,
   `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`, plus an append-only `QUIZ_LOG.md`) living in the user's
   vault, injected at `SessionStart`.
```

- [ ] **Step 4: Update CLAUDE.md's command list**

Replace:

```markdown
- `commands/palace*` — the `/palace`, `/palace:read`, `/palace:create`, `/palace:update`,
  `/palace:doctor` slash command definitions.
```

with:

```markdown
- `commands/palace*` — the `/palace`, `/palace:read`, `/palace:create`, `/palace:update`,
  `/palace:doctor`, `/palace:quiz` slash command definitions.
```

- [ ] **Step 5: Update CLAUDE.md's test suite description**

Replace:

```markdown
- `skills/palace-tests/test_palace_map.py` — the test suite; exercises resolve/validate/render/
  staleness/archive against throwaway fixture vaults (no real vault touched).
```

with:

```markdown
- `skills/palace-tests/test_palace_map.py` — the test suite; exercises resolve/validate/render/
  staleness/archive/quiz-status/reminder-nudging against throwaway fixture vaults (no real vault touched).
```

- [ ] **Step 6: Verify by reading the diffs**

Run: `git diff docs/ARCHITECTURE.md CLAUDE.md`
Expected: exactly the edits above.

- [ ] **Step 7: Commit**

```bash
git add docs/ARCHITECTURE.md CLAUDE.md
git commit -m "docs: reflect GLOSSARY.md/QUIZ_LOG.md/palace:quiz in architecture docs"
```

---

### Task 13: Deploy + backfill the real vault, confirm green

**Files:** none (operational task against the live install)

**Interfaces:**
- Consumes: everything from Tasks 1-12.

- [ ] **Step 1: Run the full test suite**

Run: `bash skills/palace-tests/run.sh`
Expected: every test passes **except** `SystemDoctorTests.test_live_install_green` and `SystemDoctorGlossaryTests`-style checks against the real vault, which should still fail until Step 3 below.

- [ ] **Step 2: Re-run the installer to pick up the new templates**

```bash
./install.sh
```
Expected: `engine files deployed`, `vault skeleton ensured (backfilled any new template files)`, ends with `doctor --system` output — it will report `✗ every wing has its 6 files` for existing wings (expected at this point).

- [ ] **Step 3: Backfill GLOSSARY.md into every existing real wing**

```bash
VAULT="$(grep '^VAULT_DIR=' ~/.claude/palace.env | cut -d= -f2)"
for d in "$VAULT"/projects/*/; do
  slug="$(basename "$d")"
  [ -f "$d/readme.md" ] || continue      # skip .template and non-wing dirs
  [ -f "$d/GLOSSARY.md" ] && continue    # already has one
  sed "s/{{PROJECT_NAME}}/$slug/g" "$VAULT/projects/.template/GLOSSARY.md" > "$d/GLOSSARY.md"
  echo "backfilled GLOSSARY.md for $slug"
done
```

- [ ] **Step 4: Re-run doctor --system and the test suite to confirm green**

```bash
~/.claude/hooks/palace-map doctor --system
bash skills/palace-tests/run.sh
```
Expected: `ALL GREEN` from `doctor --system`, and every test in `skills/palace-tests/run.sh` passes, including `test_live_install_green`.

- [ ] **Step 5: No commit needed**

This task only touches the user's local vault (outside this repo) and re-runs the already-committed installer — nothing in `memory-palace` itself changes.
