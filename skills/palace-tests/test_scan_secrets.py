#!/usr/bin/env python3
"""Tests for hooks/scan-secrets.py: report mode over the wings, redact mode over transcripts.

Fake tokens are assembled at runtime so no literal secret-shaped string sits in the repo
for a push-protection scanner to trip on.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "hooks" / "scan-secrets.py"

GITHUB = "ghp_" + "A1b2" * 9
AWS = "AKIA" + "Z" * 16
PEM = ("-----BEGIN OPENSSH " + "PRIVATE KEY-----\nb3BlbnNzaC1rZXk\nAAAAB3NzaC1\n"
       "-----END OPENSSH " + "PRIVATE KEY-----")
WEAK = "api_key = " + "hunter2hunter2"


class ScanSecretsBase(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp(prefix="scan-vault-"))
        self.claude = Path(tempfile.mkdtemp(prefix="scan-claude-"))
        (self.claude / "hooks").mkdir()
        (self.vault / "projects" / "alpha").mkdir(parents=True)
        self.sessions = self.vault / "claude-sessions"
        self.sessions.mkdir()

    def run_scan(self, *args, vault=None):
        env = {**os.environ, "VAULT_DIR": str(vault or self.vault),
               "PALACE_CLAUDE_DIR": str(self.claude)}
        return subprocess.run(["python3", str(SCRIPT), *args], capture_output=True, text=True,
                              env=env)

    def log_text(self):
        log = self.claude / "hooks" / "scan-secrets.log"
        return log.read_text() if log.exists() else ""


class ReportModeTests(ScanSecretsBase):
    def test_reports_strong_and_weak_hits_in_wings(self):
        (self.vault / "projects" / "alpha" / "CONTEXT.md").write_text(f"token {GITHUB}\n{WEAK}\n")
        r = self.run_scan()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "2 possible secret(s) found")
        self.assertIn("CONTEXT.md:1: github", self.log_text())
        self.assertIn("CONTEXT.md:2: api-key", self.log_text())

    def test_never_writes_the_secret_value(self):
        (self.vault / "projects" / "alpha" / "CONTEXT.md").write_text(f"{GITHUB}\n{WEAK}\n")
        r = self.run_scan()
        for value in (GITHUB, "hunter2"):
            self.assertNotIn(value, self.log_text())
            self.assertNotIn(value, r.stdout + r.stderr)

    def test_does_not_rewrite_wings(self):
        doc = self.vault / "projects" / "alpha" / "CONTEXT.md"
        doc.write_text(f"{GITHUB}\n")
        self.run_scan()
        self.assertIn(GITHUB, doc.read_text())

    def test_skips_env_placeholders(self):
        (self.vault / "projects" / "alpha" / "CONTEXT.md").write_text("api_key = ${API_KEY}\n")
        r = self.run_scan()
        self.assertEqual(r.stdout.strip().splitlines()[-1], "0 possible secret(s) found")

    def test_skips_empty_placeholder_and_reference_values(self):
        (self.vault / "projects" / "alpha" / "CONTEXT.md").write_text(
            "API_KEY=<key>\napi_key = ''\nAPI_KEY = \"\"\napi_key=settings.FOO_API_KEY,\n")
        r = self.run_scan()
        self.assertEqual(r.stdout.strip().splitlines()[-1], "0 possible secret(s) found")

    def test_missing_vault_fails_loudly(self):
        r = self.run_scan(vault=self.vault / "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("vault not found", r.stdout + r.stderr)


class RedactModeTests(ScanSecretsBase):
    def test_redacts_strong_patterns(self):
        f = self.sessions / "s.md"
        f.write_text(f"key {GITHUB} and {AWS}\n{PEM}\nafter\n")
        r = self.run_scan("--redact", str(self.sessions))
        self.assertEqual(r.returncode, 0, r.stderr)
        text = f.read_text()
        self.assertEqual(text, "key [REDACTED:github] and [REDACTED:aws]\n[REDACTED:private-key]\nafter\n")
        self.assertIn("3 secret(s) redacted in 1 file(s)", r.stdout)

    def test_ticket_slug_is_not_an_openai_key(self):
        f = self.sessions / "s.md"
        slug = "fix/sk-123-candidate-export-timeout-on-large-fairs\n"
        key = "sk-proj-" + "Ab3" * 16
        f.write_text(slug + key + "\n")
        self.run_scan("--redact", str(self.sessions))
        self.assertEqual(f.read_text(), slug + "[REDACTED:openai]\n")

    def test_leaves_weak_patterns_alone(self):
        f = self.sessions / "s.md"
        f.write_text(f"{WEAK}\n")
        self.run_scan("--redact", str(self.sessions))
        self.assertEqual(f.read_text(), f"{WEAK}\n")

    def test_is_idempotent(self):
        f = self.sessions / "s.md"
        f.write_text(f"{GITHUB}\n")
        self.run_scan("--redact", str(self.sessions))
        once = f.read_text()
        r = self.run_scan("--redact", str(self.sessions))
        self.assertEqual(f.read_text(), once)
        self.assertIn("0 secret(s) redacted", r.stdout)

    def test_days_skips_older_files(self):
        old = self.sessions / "old.md"
        old.write_text(f"{GITHUB}\n")
        stamp = old.stat().st_mtime - 10 * 86400
        os.utime(old, (stamp, stamp))
        self.run_scan("--redact", str(self.sessions), "--days", "3")
        self.assertIn(GITHUB, old.read_text())

    def test_log_carries_no_value(self):
        (self.sessions / "s.md").write_text(f"{GITHUB}\n")
        self.run_scan("--redact", str(self.sessions))
        self.assertIn("s.md: 1 redacted (github)", self.log_text())
        self.assertNotIn(GITHUB, self.log_text())

    def test_dry_run_counts_without_writing(self):
        f = self.sessions / "s.md"
        f.write_text(f"{GITHUB} {AWS}\n")
        r = self.run_scan("--redact", str(self.sessions), "--dry-run")
        self.assertEqual(f.read_text(), f"{GITHUB} {AWS}\n")
        self.assertIn("2 secret(s) would be redacted in 1 file(s)", r.stdout)
        self.assertIn("aws: 1", r.stdout)
        self.assertNotIn(GITHUB, r.stdout + self.log_text())

    def test_missing_dir_fails_loudly(self):
        r = self.run_scan("--redact", str(self.vault / "nope"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not found", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
