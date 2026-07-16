#!/usr/bin/env python3
"""Search QMD session transcripts for palace wing candidates.

Generates a review markdown file. Mark [x] on items you want, then run palace-apply.py.

Usage:
    python3 palace-harvest.py
    python3 palace-harvest.py --project myproject
    python3 palace-harvest.py --project myproject --wings DECISIONS,BUGS
    python3 palace-harvest.py --min-score 0.7 --output ~/review.md
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

VAULT = Path(os.environ.get("VAULT_DIR", str(Path.home() / "obsidian")))
PROJECTS_DIR = VAULT / "projects"
DEFAULT_OUTPUT = VAULT / f"palace-harvest-{datetime.now().strftime('%Y-%m-%d')}.md"

# Sentinel for "an LLM needs to read the linked session and write this."
# Keep this string in sync with PLACEHOLDER_MARKERS in palace-apply.py —
# that script refuses to apply any candidate whose content still contains it.
NEEDS_FILL = "[NEEDS-FILL — read the linked session, write the real content]"


def discover_projects() -> list[str]:
    """Palace wings = subdirectories of projects/, excluding dotfiles/underscore-prefixed meta dirs."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        d.name for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_"))
    )


PROJECTS = discover_projects()


def load_already_seen_filenames() -> set[str]:
    """Session filenames that already appeared as a candidate in a prior harvest review file."""
    seen: set[str] = set()
    for path in VAULT.glob("palace-harvest-*.md"):
        text = path.read_text(errors="replace")
        seen.update(re.findall(r"\*\*File:\*\* `([^`]+)`", text))
    return seen

WING_QUERIES = {
    "DECISIONS": [
        "{project} decision chose why",
        "{project} alternative rejected approach",
    ],
    "BUGS": [
        "{project} bug issue broken error",
        "{project} fix crash problem workaround",
    ],
    "ARCHITECTURE": [
        "{project} architecture pattern component structure",
        "{project} stack setup configuration",
    ],
}


def qmd_search(query: str, collection: str, min_score: float, n: int = 5) -> list[dict]:
    try:
        result = subprocess.run(
            ["qmd", "search", query, "-c", collection, "--json", "-n", str(n)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return [r for r in data if r.get("score", 0) >= min_score]
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []


def qmd_get(file_uri: str, lines: int = 75) -> str:
    try:
        result = subprocess.run(
            ["qmd", "get", file_uri, "-l", str(lines)],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def extract_date_from_uri(file_uri: str) -> str:
    # qmd://sessions/2026-05-05-1406-ba01345c.md → 2026-05-05
    m = re.search(r"(\d{4}-\d{2}-\d{2})", file_uri)
    return m.group(1) if m else "unknown"


def extract_session_filename(file_uri: str) -> str:
    return file_uri.split("/")[-1]


def deduplicate(results: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for r in results:
        key = extract_session_filename(r["file"])
        if key not in seen or r["score"] > seen[key]["score"]:
            seen[key] = r
    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


def harvest_wing(project: str, wing: str, min_score: float, seen: set[str]) -> list[dict]:
    queries = WING_QUERIES[wing]
    all_results = []
    for q in queries:
        query = q.format(project=project)
        hits = qmd_search(query, "sessions", min_score)
        all_results.extend(hits)
    candidates = deduplicate(all_results)
    if seen:
        candidates = [c for c in candidates if extract_session_filename(c["file"]) not in seen]
    return candidates[:5]


def format_candidate(project: str, wing: str, result: dict, idx: int) -> str:
    date = extract_date_from_uri(result["file"])
    filename = extract_session_filename(result["file"])
    score_pct = int(result["score"] * 100)
    title = result.get("title", "")[:80]
    snippet = result.get("snippet", "")

    # Clean up snippet diff header
    snippet_clean = re.sub(r"^@@ .+?@@\s*\n?", "", snippet).strip()

    # No regex/heuristic auto-fill: pattern-matching on session text produced
    # plausible-looking garbage (e.g. mid-sentence fragments) that was easy to
    # mistake for real content. Content only ever comes from an LLM actually
    # reading the linked session — palace-apply.py refuses to apply anything
    # that still looks like this unfilled template (see PLACEHOLDER_MARKERS).
    if wing == "DECISIONS":
        template = (
            f"## {NEEDS_FILL}\n"
            f"- **Decision**: {NEEDS_FILL}\n"
            f"- **Why**: {NEEDS_FILL}\n"
            f"- **Alternatives**: [if mentioned, else delete this line]\n"
            f"- **Date**: {date}"
        )
    elif wing == "BUGS":
        template = f"| [ID] | {NEEDS_FILL} | [low/medium/high] | open |"
    else:  # ARCHITECTURE
        template = f"### {NEEDS_FILL}\n{NEEDS_FILL}"

    snippet_display = snippet_clean[:3000]
    if len(snippet_clean) > 3000:
        snippet_display += f"\n... [{len(snippet_clean) - 3000} chars truncated — open {filename}]"

    return f"""#### [ ] Candidate {idx} — {filename}
**Score:** {score_pct}% | **Session:** {date} | **File:** `{filename}`
**Title:** {title}

<details><summary>Session snippet ({len(snippet_clean)} chars)</summary>

```
{snippet_display}
```

</details>

**Suggested addition to {wing}.md:**
```markdown
{template}
```

---
"""


def main():
    parser = argparse.ArgumentParser(description="Harvest palace wing candidates from session transcripts")
    parser.add_argument("--project", default="all", help="Project name or 'all'")
    parser.add_argument("--wings", default="DECISIONS,BUGS,ARCHITECTURE", help="Comma-separated wing names")
    parser.add_argument("--min-score", type=float, default=0.7, dest="min_score")
    parser.add_argument("--include-seen", action="store_true",
                        help="Don't skip candidates already surfaced in a prior harvest file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output markdown file path")
    args = parser.parse_args()

    projects = PROJECTS if args.project == "all" else [args.project]
    wings = [w.strip().upper() for w in args.wings.split(",")]
    output_path = Path(args.output).expanduser()
    seen = set() if args.include_seen else load_already_seen_filenames()

    lines = [
        f"# Palace Harvest — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "Review candidates below. Change `[ ]` to `[x]` on items worth keeping",
        "(score is search relevance only, not content quality — check by reading",
        "the snippet, not by score alone).",
        "",
        "Every **Suggested addition** block starts as `NEEDS-FILL` — this script",
        "does no automatic extraction. Before applying, have an LLM (Claude) open",
        f"`claude-sessions/<project-slug>/<filename>` for each `[x]` candidate and",
        "replace the `NEEDS-FILL` block with real content in the same shape.",
        "`palace-apply.py` refuses anything still marked `NEEDS-FILL`.",
        "",
        "Then run: `python3 palace-apply.py --review <this-file>`",
        "",
        "---",
        "",
    ]
    any_content = False

    for project in projects:
        wing_dir = PROJECTS_DIR / project
        if not wing_dir.exists():
            print(f"  Skip {project} — no wing directory")
            continue

        project_has_content = False
        project_lines = [f"## {project}", ""]

        for wing in wings:
            if wing not in WING_QUERIES:
                continue

            print(f"  Searching {project}/{wing}...", end=" ", flush=True)
            candidates = harvest_wing(project, wing, args.min_score, seen)
            print(f"{len(candidates)} candidates")

            if not candidates:
                continue

            project_has_content = True
            project_lines.append(f"### {wing}.md")
            project_lines.append("")

            for idx, result in enumerate(candidates, 1):
                project_lines.append(format_candidate(project, wing, result, idx))

        if project_has_content:
            lines.extend(project_lines)
            any_content = True

    if not any_content:
        print("\nNo new candidates above threshold — nothing written.")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"\nReview file: {output_path}")
    print("Edit it in Obsidian, mark [x] on items to keep, then run palace-apply.py")


if __name__ == "__main__":
    main()
