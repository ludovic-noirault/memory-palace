#!/usr/bin/env python3
"""Tests for skills/recall/scripts/palace-harvest.py candidate templates."""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "recall" / "scripts" / "palace-harvest.py"

# Imported, not run: format_candidate has no CLI. The import lists projects/ at module
# level, so it gets an empty vault instead of the real one.
sys.dont_write_bytecode = True
os.environ["VAULT_DIR"] = tempfile.mkdtemp(prefix="harvest-vault-")
_spec = importlib.util.spec_from_file_location("palace_harvest", SCRIPT)
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)

RESULT = {"file": "qmd://sessions/2026-05-05-1406-ba01345c.md", "score": 0.8,
          "title": "t", "snippet": "s"}


def suggested_block(wing):
    out = harvest.format_candidate("alpha", wing, RESULT, 1)
    return out.split("```markdown\n", 1)[1].split("\n```", 1)[0]


class CandidateSourceTests(unittest.TestCase):
    def test_decision_candidate_links_its_session(self):
        self.assertIn("- **Source**: [[2026-05-05-1406-ba01345c]]", suggested_block("DECISIONS"))

    def test_bug_candidate_links_its_session_in_description(self):
        row = suggested_block("BUGS")
        description = row.split("|")[2]
        self.assertIn("([[2026-05-05-1406-ba01345c]])", description)


if __name__ == "__main__":
    unittest.main(verbosity=2)
