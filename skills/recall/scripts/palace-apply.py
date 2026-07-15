#!/usr/bin/env python3
"""Apply approved palace harvest candidates to wing files.

Usage:
    python3 palace-apply.py --review ~/theTribe/obsidian/palace-harvest-2026-05-11.md
    python3 palace-apply.py --review ~/theTribe/obsidian/palace-harvest-2026-05-11.md --dry-run
"""

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

VAULT = Path.home() / "theTribe/obsidian"
PROJECTS_DIR = VAULT / "projects"

# Content containing any of these was never actually filled in — either the
# harvest script's NEEDS-FILL sentinel, or a leftover fragment from the old
# regex-heuristic auto-fill (removed 2026-07-08 because it produced
# plausible-looking garbage). Refuse to write any of this to a wing file even
# if the candidate got checked [x].
PLACEHOLDER_MARKERS = [
    "NEEDS-FILL",
    "fill in]",
    "extracted from snippet]",
    "Description from snippet]",
    "[ID]",
    "Pattern/Component name]",
]

WING_SECTION_HEADERS = {
    "DECISIONS": "## Decisions",
    "BUGS": "## Open",
    "ARCHITECTURE": "## Key Patterns",
}


def parse_review_file(path: Path) -> list[dict]:
    """Extract approved [x] candidates from review file."""
    text = path.read_text()
    candidates = []

    current_project = None
    current_wing = None

    for line in text.splitlines():
        # Track current project (## myproject)
        m = re.match(r"^## ([a-zA-Z0-9_-]+)$", line)
        if m and not m.group(1).startswith("Candidate"):
            current_project = m.group(1)
            continue

        # Track current wing (### DECISIONS.md)
        m = re.match(r"^### (DECISIONS|BUGS|ARCHITECTURE)\.md$", line)
        if m:
            current_wing = m.group(1)
            continue

        # Approved candidate
        m = re.match(r"^#### \[x\] (.+)$", line, re.IGNORECASE)
        if m and current_project and current_wing:
            candidates.append({
                "project": current_project,
                "wing": current_wing,
                "title": m.group(1),
                "start_line_idx": None,
            })

    # Now extract suggested addition blocks for each approved candidate
    approved_titles = {c["title"] for c in candidates}

    # Re-parse to extract content blocks
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^#### \[x\] (.+)$", line, re.IGNORECASE)
        if not m:
            continue
        title = m.group(1)
        if title not in approved_titles:
            continue

        # Find the ```markdown block after this heading
        content = None
        in_block = False
        block_lines = []
        for j in range(i + 1, min(i + 40, len(lines))):
            if lines[j].strip() == "```markdown" and not in_block:
                in_block = True
                continue
            if in_block and lines[j].strip() == "```":
                content = "\n".join(block_lines).strip()
                break
            if in_block:
                block_lines.append(lines[j])

        # Find matching candidate and set content
        for c in candidates:
            if c["title"] == title and c.get("content") is None:
                c["content"] = content
                break

    return [c for c in candidates if c.get("content")]


def apply_to_wing(project: str, wing: str, content: str, dry_run: bool) -> bool:
    wing_file = PROJECTS_DIR / project / f"{wing}.md"
    if not wing_file.exists():
        print(f"  SKIP — {wing_file} not found")
        return False

    wing_text = wing_file.read_text()

    # Back up first
    if not dry_run:
        backup = wing_file.with_suffix(".md.bak")
        shutil.copy2(wing_file, backup)

    # Find insertion point — end of file or after last section
    # For BUGS: append inside ## Open table
    # For others: append at end of file
    if wing == "BUGS":
        section = "## Open"
        if section in wing_text:
            # Find end of the Open section (next ## or EOF)
            idx = wing_text.index(section)
            next_section = wing_text.find("\n## ", idx + len(section))
            if next_section == -1:
                insert_at = len(wing_text)
            else:
                insert_at = next_section
            new_text = wing_text[:insert_at].rstrip() + "\n" + content + "\n" + wing_text[insert_at:]
        else:
            new_text = wing_text.rstrip() + "\n\n" + content + "\n"
    else:
        new_text = wing_text.rstrip() + "\n\n" + content + "\n"

    print(f"  {'[DRY RUN] ' if dry_run else ''}Apply to {project}/{wing}.md:")
    for line in content.splitlines():
        print(f"    + {line}")

    if not dry_run:
        wing_file.write_text(new_text)

    return True


def main():
    parser = argparse.ArgumentParser(description="Apply approved palace harvest items to wing files")
    parser.add_argument("--review", required=True, help="Path to the harvest review markdown file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    review_path = Path(args.review).expanduser()
    if not review_path.exists():
        print(f"Error: review file not found: {review_path}")
        return

    candidates = parse_review_file(review_path)

    if not candidates:
        print("No approved [x] candidates found in review file.")
        return

    print(f"Found {len(candidates)} approved candidate(s)\n")

    applied = 0
    skipped_unfilled = 0
    for c in candidates:
        print(f"• {c['project']}/{c['wing']} — {c['title']}")
        marker = next((m for m in PLACEHOLDER_MARKERS if m in c["content"]), None)
        if marker:
            print(f"  SKIP — content still unfilled (contains {marker!r}). Have an LLM read the")
            print(f"  linked session and write real content, then re-run.")
            skipped_unfilled += 1
            print()
            continue
        ok = apply_to_wing(c["project"], c["wing"], c["content"], args.dry_run)
        if ok:
            applied += 1
        print()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Applied {applied}/{len(candidates)} items.")
    if skipped_unfilled:
        print(f"Skipped {skipped_unfilled} unfilled candidate(s) — see SKIP lines above.")
    if not args.dry_run and applied > 0:
        print("Backups saved as *.md.bak alongside each modified wing file.")


if __name__ == "__main__":
    main()
