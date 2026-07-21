# Feature Sub-Wings ("métier" docs) — Design

Adds an optional, feature/domain-oriented layer on top of the existing category-based wing files,
inspired by a comparable project (spine)'s per-feature note structure. Category files
(`readme.md`, `ARCHITECTURE.md`, `BUGS.md`, `CONTEXT.md`, `DECISIONS.md`, `GLOSSARY.md`) stay the
required, project-wide 6 files — this adds a second, optional axis for deep dives on a specific
feature or business domain ("métier") within the project, without restructuring the core wing shape.

## 1. File layout

**Design**:
- New optional subdirectory: `projects/{slug}/features/{feature-slug}.md` — one file per
  feature/domain, kebab-case filenames (e.g. `features/billing.md`, `features/quiz-system.md`).
- Not one of the 6 required wing files — `palace-map doctor --system`'s "every wing has its 6
  files" check is unaffected; feature docs are additive, never required.
- Same frontmatter conventions as the 6 category files, including `anticipated_queries`
  (see `2026-07-21-anticipated-queries-design.md`) — feature docs participate in
  `/palace:search` the same way category docs do.

**Touches**:
- `templates/projects/.template/` — document the `features/` convention (no scaffolded example
  file needed at wing-creation time, since feature docs are created on demand, not up front).

## 2. Trigger — `/palace:update` extension

**Design**:
- When a session's work clearly centers on one feature/domain area, `/palace:update`'s existing
  Step 7 proposes (asks, never auto-creates) spinning up or updating
  `features/{feature-slug}.md`, instead of the notes landing in `DECISIONS.md`/`ARCHITECTURE.md`
  by default.
- Same surgical-edit rule as the rest of Step 7: append/update only what's new, don't rewrite
  unrelated content in the feature doc.
- No new detection heuristic (e.g. branch name, touched files) — Claude judges from session
  content whether the work centers on a feature, same trust model as the rest of Step 7's
  judgment calls. Explicitly rejected as a first pass (see Out of scope).

**Touches**:
- `commands/palace/update.md` — Step 7 gains a propose-a-feature-doc sub-step.

## 3. Linking — both directions

**Design**:
- `readme.md` gains a "## Features" section: a flat index list of links to each existing
  `features/{Feature}.md` — one place to see what sub-wings exist for a project.
- Category docs (`ARCHITECTURE.md`, `DECISIONS.md`, `BUGS.md`) may link out inline to a feature
  doc where relevant (e.g. a `DECISIONS.md` entry: "see `features/billing.md` for the full
  design") — spine-style cross-references, added organically as content warrants, not
  backfilled all at once.
- `/palace:update` keeps the readme index in sync whenever it creates or touches a feature doc:
  add the link if missing, never remove links to docs it didn't touch.

**Touches**:
- `templates/projects/.template/readme.md` — add a "## Features" section (empty by default).
- `commands/palace/update.md` — Step 7's feature-doc sub-step also syncs the readme index.

## 4. Injection / read

**Design**:
- Not auto-injected at `SessionStart` — same treatment as `GLOSSARY.md`, to keep injection light.
- Reachable via `/palace:read` (on request), `/palace:search <query>`, or whenever
  `/palace:update` is actively working on that feature.

**Touches**:
- `commands/palace/read.md` — mention feature docs as an on-demand-loadable set, alongside the
  existing on-demand treatment of `GLOSSARY.md`.
- `docs/ARCHITECTURE.md` — document the `features/` convention alongside the 6 core files.

## 5. Search integration

**Design**:
- `palace-map search` (from the anticipated-queries spec) globs `features/*.md` in addition to
  the 6 fixed category filenames, so feature docs are found the same way category docs are.

**Touches**:
- `hooks/palace-map` — `search` subcommand's file-discovery step covers `features/*.md` per wing,
  not just the 6 fixed filenames.

## Out of scope

- Ghost-link validation (readme links to a feature file that no longer exists) — natural fit for
  a future "doctor v2" pass (duplicate/overlap + ghost-link checks), not this design.
- Auto-detecting which feature a session belongs to via branch name, touched files, or any other
  heuristic — explicitly rejected; no such heuristic exists elsewhere in the system and this
  design doesn't introduce one.
- Migrating existing `DECISIONS.md`/`ARCHITECTURE.md` content into feature docs — feature docs
  are populated organically going forward, no backfill of historical content.
- Making feature docs one of the required 6 wing files, or changing `doctor --system`'s
  completeness check — they stay strictly optional/additive.
