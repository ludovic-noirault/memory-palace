# Anticipated-Queries Search + Feature Sub-Wings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a keyword-overlap search over per-doc "anticipated queries" (a cheap, dependency-free
semantic-search stand-in), and an optional `features/` sub-wing layer for feature/domain deep dives —
both inspired by a comparable project (spine), specced in
`docs/superpowers/specs/2026-07-21-anticipated-queries-design.md` and
`docs/superpowers/specs/2026-07-21-feature-subwings-design.md`.

**Architecture:** A new `anticipated_queries` YAML-ish frontmatter field on every wing doc (the 6
core files, plus optional `features/*.md`), a stdlib-only parser + `palace-map search` subcommand
that scores query/doc overlap by shared words, a new `/palace:search` slash command wrapping it,
and `/palace:update` extensions that keep the field fresh and propose feature docs when a session's
work centers on one.

**Tech Stack:** Python 3 stdlib only (no YAML lib, no new deps) for `hooks/palace-map`; Markdown +
YAML frontmatter for wing docs/templates; bash unchanged.

## Global Constraints

- Stdlib-only Python — no third-party packages (repo-wide constraint, see root `CLAUDE.md`).
- `hooks/palace-map` is the single resolver; do not add parallel lookup logic elsewhere.
- Changes to `hooks/palace-map` are only visible to the test suite / real hooks after running
  `./install.sh` from the repo root (tests drive the **installed** copy at `~/.claude/hooks/palace-map`,
  per `skills/palace-tests/test_palace_map.py`'s existing convention) — every task touching
  `hooks/palace-map` must redeploy before testing.
- `anticipated_queries` is generated/regenerated content — replaced wholesale on regeneration, never
  appended to (matches the spec's "replace, not append" rule; distinct from `QUIZ_LOG.md`, which
  *is* append-only).
- Feature sub-docs are strictly optional/additive — never part of `doctor --system`'s "every wing
  has its 6 files" completeness check.

---

### Task 1: `anticipated_queries` frontmatter parser + `palace-map search` subcommand

**Files:**
- Modify: `hooks/palace-map`
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Produces: `anticipated_queries(path: Path) -> list[str]` (module-level function in
  `hooks/palace-map`) — parses the `anticipated_queries:` YAML-list field from a doc's frontmatter;
  returns `[]` on missing/malformed field, never raises.
- Produces: `palace-map search <query> [--slug SLUG] [--all]` CLI subcommand — prints ranked
  `slug/relpath — "matched query" (score)` lines (top 8), or `no matches`. Scans each wing's 6 core
  `*.md` files plus `features/*.md` if that subdirectory exists.

- [ ] **Step 1: Add the frontmatter + search helpers to `hooks/palace-map`**

Insert after the existing `wing_files_mtime` function (before `def cmd_resolve`):

```python
_WORD_RE = re.compile(r"[a-z0-9]+")


def _words(text):
    return set(_WORD_RE.findall(text.lower()))


def _frontmatter_block(text):
    """Raw text between the first two '---' lines, or '' if there's no frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return ""
    return "\n".join(lines[1:end])


def anticipated_queries(path):
    """Parse the anticipated_queries: YAML list from a doc's frontmatter. Never raises —
    missing field, no frontmatter, or a malformed (non-list) value all return []."""
    try:
        text = path.read_text()
    except OSError:
        return []
    block = _frontmatter_block(text)
    if not block:
        return []
    out = []
    in_list = False
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("anticipated_queries:"):
            in_list = True
            continue
        if in_list and stripped.startswith("- "):
            item = stripped[2:].strip().strip('"').strip("'").strip()
            if item:
                out.append(item)
        elif in_list:
            in_list = False
    return out


def _wing_docs(slug):
    d = VAULT_PROJECTS / slug
    if not d.is_dir():
        return []
    docs = list(d.glob("*.md"))
    feat_dir = d / "features"
    if feat_dir.is_dir():
        docs += list(feat_dir.glob("*.md"))
    return docs


def cmd_search(args):
    slug_filter = None
    words = []
    it = iter(args)
    for a in it:
        if a == "--slug":
            slug_filter = next(it, None)
        elif a == "--all":
            pass
        else:
            words.append(a)
    if not words:
        print("usage: palace-map search <query> [--slug SLUG] [--all]")
        sys.exit(2)
    q_words = _words(" ".join(words))
    slugs = [slug_filter] if slug_filter else [p["slug"] for p in load()]
    results = []
    for slug in slugs:
        d = VAULT_PROJECTS / slug
        if not d.is_dir():
            continue
        for doc in _wing_docs(slug):
            rel = doc.relative_to(d)
            for aq in anticipated_queries(doc):
                score = len(q_words & _words(aq))
                if score > 0:
                    results.append((score, slug, str(rel), aq))
    results.sort(key=lambda r: -r[0])
    if not results:
        print("no matches")
        return
    for score, slug, rel, aq in results[:8]:
        print(f'{slug}/{rel} — "{aq}" ({score})')
```

- [ ] **Step 2: Register the subcommand**

In `hooks/palace-map`, update the `CMDS` dict:

```python
CMDS = {
    "resolve": cmd_resolve, "memdir": cmd_memdir, "repo": cmd_repo, "list": cmd_list,
    "activity": cmd_activity, "validate": cmd_validate, "render": cmd_render, "doctor": cmd_doctor,
    "archive": cmd_archive, "unarchive": cmd_unarchive, "quiz-status": cmd_quiz_status,
    "search": cmd_search,
}
```

Also add a line to the module docstring's command list (after the `quiz-status` line):

```
  search <query> [--slug S] [--all]  keyword-overlap search over anticipated_queries frontmatter
```

- [ ] **Step 3: Deploy the change so tests exercise it**

```bash
./install.sh
```

Expected: exits 0, ends with `doctor --system` reporting `ALL GREEN`.

- [ ] **Step 4: Write the failing tests**

Add to `skills/palace-tests/test_palace_map.py`:

```python
class SearchTests(unittest.TestCase):
    def _wing_with_aq(self, root, slug, relpath, queries):
        d = root / "projects" / slug / relpath
        d.parent.mkdir(parents=True, exist_ok=True)
        text = f"---\ntags: [project]\nproject: {slug}\nanticipated_queries:\n"
        for q in queries:
            text += f'  - "{q}"\n'
        text += "---\n# doc\n"
        d.write_text(text)

    def test_present_frontmatter_matches(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        self._wing_with_aq(root, "alpha", "CONTEXT.md",
                            ["what's the current focus", "what's blocked right now"])
        rc, out, _ = run(root, "search", "current focus", "--slug", "alpha")
        self.assertEqual(rc, 0)
        self.assertIn("alpha/CONTEXT.md", out)
        self.assertIn("current focus", out)

    def test_absent_frontmatter_no_match(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        out = run(root, "search", "anything at all here", "--slug", "alpha")[1]
        self.assertIn("no matches", out)

    def test_malformed_frontmatter_no_crash(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        (root / "projects" / "alpha" / "BUGS.md").write_text(
            '---\nanticipated_queries: "not a list"\n---\n# bugs\n')
        rc, out, _ = run(root, "search", "bugs", "--slug", "alpha")
        self.assertEqual(rc, 0)

    def test_slug_scope_excludes_other_wings(self):
        root = make_vault([
            {"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"},
            {"slug": "beta", "globs": ["*/beta*"], "memdir": "-b", "repo": "~/b"},
        ])
        self._wing_with_aq(root, "alpha", "DECISIONS.md", ["why did we pick postgres"])
        self._wing_with_aq(root, "beta", "DECISIONS.md", ["why did we pick postgres"])
        out = run(root, "search", "postgres", "--slug", "alpha")[1]
        self.assertIn("alpha/DECISIONS.md", out)
        self.assertNotIn("beta/DECISIONS.md", out)

    def test_all_scope_includes_every_wing(self):
        root = make_vault([
            {"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"},
            {"slug": "beta", "globs": ["*/beta*"], "memdir": "-b", "repo": "~/b"},
        ])
        self._wing_with_aq(root, "alpha", "DECISIONS.md", ["why did we pick postgres"])
        self._wing_with_aq(root, "beta", "DECISIONS.md", ["why did we pick postgres"])
        out = run(root, "search", "postgres", "--all")[1]
        self.assertIn("alpha/DECISIONS.md", out)
        self.assertIn("beta/DECISIONS.md", out)

    def test_features_subdir_included(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        self._wing_with_aq(root, "alpha", "features/billing.md",
                            ["how does billing retry failed charges"])
        out = run(root, "search", "billing retry", "--slug", "alpha")[1]
        self.assertIn("alpha/features/billing.md", out)

    def test_top_8_cap(self):
        root = make_vault([{"slug": "alpha", "globs": ["*/alpha*"], "memdir": "-a", "repo": "~/a"}])
        for i in range(10):
            self._wing_with_aq(root, "alpha", f"features/f{i}.md", [f"widget topic {i}"])
        out = run(root, "search", "widget topic", "--slug", "alpha")[1]
        self.assertEqual(len(out.strip().splitlines()), 8)
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd skills/palace-tests && python3 -m unittest test_palace_map.SearchTests -v
```

Expected: 7 tests, all PASS. (They should already pass after Steps 1–3 since this is additive code
with no prior implementation to fail against — if any fail, fix `cmd_search`/`anticipated_queries`
before continuing.)

- [ ] **Step 6: Full suite regression check**

```bash
bash skills/palace-tests/run.sh
```

Expected: all tests pass, including pre-existing ones (confirms no regression in `doctor`,
`validate`, etc.).

- [ ] **Step 7: Commit**

```bash
git add hooks/palace-map skills/palace-tests/test_palace_map.py
git commit -m "feat: add anticipated_queries search to palace-map"
```

---

### Task 2: `anticipated_queries` frontmatter on wing templates

**Files:**
- Modify: `templates/projects/.template/readme.md`
- Modify: `templates/projects/.template/ARCHITECTURE.md`
- Modify: `templates/projects/.template/BUGS.md`
- Modify: `templates/projects/.template/CONTEXT.md`
- Modify: `templates/projects/.template/DECISIONS.md`
- Modify: `templates/projects/.template/GLOSSARY.md`
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: none (pure content change).
- Produces: every shipped template's frontmatter includes a non-empty `anticipated_queries` list,
  so newly-created wings (`/palace:create`) start with the field populated instead of it being added
  only via later `/palace:update` regeneration.

- [ ] **Step 1: Write the failing test**

Add to `skills/palace-tests/test_palace_map.py` (near the top-level constants, add
`REPO_ROOT = Path(__file__).resolve().parents[2]` and `TEMPLATE_DIR = REPO_ROOT / "templates" / "projects" / ".template"`):

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "templates" / "projects" / ".template"


class TemplateFrontmatterTests(unittest.TestCase):
    def test_every_core_template_has_anticipated_queries(self):
        for name in ("readme.md", "ARCHITECTURE.md", "BUGS.md", "CONTEXT.md",
                     "DECISIONS.md", "GLOSSARY.md"):
            text = (TEMPLATE_DIR / name).read_text()
            self.assertIn("anticipated_queries:", text, f"{name} missing anticipated_queries")
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd skills/palace-tests && python3 -m unittest test_palace_map.TemplateFrontmatterTests -v
```

Expected: FAIL — `AssertionError: anticipated_queries: not found in ...` for all 6 files.

- [ ] **Step 3: Add the field to each template's frontmatter**

`templates/projects/.template/readme.md` — frontmatter becomes:

```yaml
---
tags: [project]
project: {{PROJECT_NAME}}
status: active
client: {{CLIENT}}
stack: [{{STACK}}]
anticipated_queries:
  - "what does this project do"
  - "who is it for"
---
```

`templates/projects/.template/ARCHITECTURE.md` — frontmatter becomes:

```yaml
---
tags: [project, architecture]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "what's the tech stack"
  - "what are the critical gotchas"
---
```

`templates/projects/.template/BUGS.md` — frontmatter becomes:

```yaml
---
tags: [project, bugs]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "what bugs are open"
  - "are there any security issues"
---
```

`templates/projects/.template/CONTEXT.md` — frontmatter becomes:

```yaml
---
tags: [project, context]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "what's the current focus"
  - "what's blocked right now"
---
```

`templates/projects/.template/DECISIONS.md` — frontmatter becomes:

```yaml
---
tags: [project, decisions]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "why did we choose this approach"
  - "what alternatives were rejected"
---
```

`templates/projects/.template/GLOSSARY.md` — frontmatter becomes:

```yaml
---
tags: [project, glossary]
project: {{PROJECT_NAME}}
anticipated_queries:
  - "what does this term mean"
---
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd skills/palace-tests && python3 -m unittest test_palace_map.TemplateFrontmatterTests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/projects/.template/readme.md templates/projects/.template/ARCHITECTURE.md \
        templates/projects/.template/BUGS.md templates/projects/.template/CONTEXT.md \
        templates/projects/.template/DECISIONS.md templates/projects/.template/GLOSSARY.md \
        skills/palace-tests/test_palace_map.py
git commit -m "feat: add anticipated_queries frontmatter to wing templates"
```

---

### Task 3: `features/` convention on wing templates

**Files:**
- Modify: `templates/projects/.template/readme.md`
- Test: `skills/palace-tests/test_palace_map.py`

**Interfaces:**
- Consumes: `TEMPLATE_DIR` from Task 2's test additions.
- Produces: `readme.md` template ships a `## Features` section (empty), establishing the convention
  every new wing starts with; `features/` itself is not scaffolded as a directory since feature docs
  are created on demand (per spec, no backfill/pre-creation).

- [ ] **Step 1: Write the failing test**

Add to `skills/palace-tests/test_palace_map.py`:

```python
class ReadmeFeaturesSectionTests(unittest.TestCase):
    def test_readme_template_has_features_section(self):
        text = (TEMPLATE_DIR / "readme.md").read_text()
        self.assertIn("## Features", text)
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd skills/palace-tests && python3 -m unittest test_palace_map.ReadmeFeaturesSectionTests -v
```

Expected: FAIL — `## Features` not found.

- [ ] **Step 3: Add the section to the readme template**

Append to `templates/projects/.template/readme.md` (after the existing `## Quick Start` section):

```markdown

## Features

> Links to `features/{feature-slug}.md` deep-dives, added as they're created via `/palace:update`.
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd skills/palace-tests && python3 -m unittest test_palace_map.ReadmeFeaturesSectionTests -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/projects/.template/readme.md skills/palace-tests/test_palace_map.py
git commit -m "feat: add Features section convention to readme template"
```

---

### Task 4: `/palace:search` slash command

**Files:**
- Create: `commands/palace/search.md`

**Interfaces:**
- Consumes: `palace-map resolve <pwd>` (existing), `palace-map search <query> [--slug SLUG] [--all]`
  (Task 1).
- Produces: a user-invokable `/palace:search <query>` command.

- [ ] **Step 1: Create the command file**

```markdown
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
```

- [ ] **Step 2: Deploy and manually verify**

```bash
./install.sh
```

Then, from a directory that maps to a real wing in your vault, run `/palace:search <some query
that matches an existing anticipated_queries entry>` in a Claude Code session and confirm it prints
a ranked match.

- [ ] **Step 3: Commit**

```bash
git add commands/palace/search.md
git commit -m "feat: add /palace:search command"
```

---

### Task 5: `/palace:update` — regenerate anticipated_queries + propose feature docs

**Files:**
- Modify: `commands/palace/update.md`

**Interfaces:**
- Consumes: `anticipated_queries` field convention (Task 1/2), `features/` convention (Task 3).
- Produces: updated Step 7 behavior — every `/palace:update` run keeps `anticipated_queries` in
  sync with rewritten docs, and proposes capturing feature-centric work in `features/{slug}.md`.

- [ ] **Step 1: Extend Step 7 in `commands/palace/update.md`**

In the bullet list under `## Step 7 — Update the wing`, after the existing `GLOSSARY.md` bullet,
add:

```markdown
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
```

- [ ] **Step 2: Manually verify**

Read back `commands/palace/update.md` and confirm Step 7 now has 7 bullets (5 original + the 2
new ones) and no duplicated/contradictory instructions with Step 4 (which loads only the 6 core
files — Step 7's feature-doc bullet is the only place `features/` gets read/written, so no
overlap).

- [ ] **Step 3: Commit**

```bash
git add commands/palace/update.md
git commit -m "feat: /palace:update regenerates anticipated_queries and proposes feature docs"
```

---

### Task 6: `/palace:read` — mention feature docs as on-demand

**Files:**
- Modify: `commands/palace/read.md`

**Interfaces:**
- Consumes: `features/` convention (Task 3).
- Produces: `/palace:read` documents that feature docs exist and how to reach them, without loading
  them by default (keeps the command's zero-writes, fixed-6-files read behavior unchanged).

- [ ] **Step 1: Add a note after the file list in Step 3**

In `commands/palace/read.md`, after the `GLOSSARY.md` bullet in `## Step 3 — Load the wing`, add:

```markdown

Feature-specific deep dives may also exist at `features/{feature-slug}.md` (see `readme.md`'s
`## Features` section for the list) — not loaded by default here; load one only if the user's
question clearly concerns that feature, or point them at `/palace:search`.
```

- [ ] **Step 2: Manually verify**

Read back `commands/palace/read.md` and confirm the zero-writes guarantee in the command's intro
still holds (this change is documentation-only, no new file writes).

- [ ] **Step 3: Commit**

```bash
git add commands/palace/read.md
git commit -m "docs: /palace:read mentions on-demand feature sub-docs"
```

---

### Task 7: `docs/ARCHITECTURE.md` — document both mechanisms

**Files:**
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: nothing (documentation only).
- Produces: architecture doc reflects `anticipated_queries`/`/palace:search` and the `features/`
  convention, so future readers don't have to reverse-engineer them from code.

- [ ] **Step 1: Extend the wing description paragraph**

In `docs/ARCHITECTURE.md`, in the paragraph starting "Layer 1 is the load-bearing one...", after
the existing sentence about `QUIZ_LOG.md`, add:

```markdown
Every wing doc also carries an `anticipated_queries` frontmatter field — 2-5 sample questions the
doc answers, kept in sync by `/palace:update` — searchable via `palace-map search` /
`/palace:search`, a dependency-free keyword-overlap lookup (no embeddings). An optional
`features/{feature-slug}.md` layer holds deep dives on a specific feature or domain, additive to
the 6 core files (never part of the 6-file completeness check), indexed from `readme.md`'s
`## Features` section and included in the same search.
```

- [ ] **Step 2: Manually verify**

Read back `docs/ARCHITECTURE.md` and confirm the addition doesn't contradict the "Layer 1" table
or the "Anti-rot mechanisms" section (it doesn't touch either — it's additive prose in the wing
description paragraph).

- [ ] **Step 3: Commit**

```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: document anticipated_queries search and feature sub-wings"
```

---

## Post-plan verification

After all 7 tasks:

```bash
bash skills/palace-tests/run.sh
./install.sh
```

Expected: full test suite green, `install.sh` ends with `doctor --system` reporting `ALL GREEN`.
