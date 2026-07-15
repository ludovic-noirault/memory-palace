#!/usr/bin/env python3
"""Scan the Obsidian vault for cred-shaped strings that shouldn't sit there in plaintext.

Scoped to projects/ (hand-maintained wings) and top-level vault docs — NOT llmwiki/
(generated site + raw session dumps) or claude-sessions/ (historical transcripts full of
pasted code examples). Those are noisy and low-actionability; this targets where a stray
credentials file like the bucket-credentials.md incident actually showed up.

Silent if clean. On a hit: macOS notification + details appended to scan-secrets.log.
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path

VAULT = Path.home() / "theTribe" / "obsidian"
LOG = Path.home() / ".claude" / "hooks" / "scan-secrets.log"

SCAN_ROOTS = [VAULT / "projects"] + list(VAULT.glob("*.md"))
SKIP_DIR_NAMES = {"_backups", ".template"}

PATTERNS = [
    re.compile(r"auth-password=\S+"),
    re.compile(r"auth-username=\S+"),
    re.compile(r'api[_-]?key["\']?\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r'secret[_-]?key["\']?\s*[:=]\s*\S+', re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]+"),
]

# Known false-positive shapes: env-var placeholders, not literal secrets
FALSE_POSITIVE_MARKERS = ("%env(", "${", "process.env.", "os.environ")


def iter_files():
    for root in SCAN_ROOTS:
        if root.is_file():
            yield root
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in path.parts):
                continue
            yield path


def scan() -> list[str]:
    hits = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.split("\n"), 1):
            if any(marker in line for marker in FALSE_POSITIVE_MARKERS):
                continue
            for pat in PATTERNS:
                if pat.search(line):
                    hits.append(f"{path}:{lineno}: {line.strip()[:200]}")
                    break
    return hits


def notify(count: int):
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{count} possible secret(s) found in the vault — see {LOG}" '
             f'with title "Vault secrets scan"'],
            timeout=5, capture_output=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def main():
    hits = scan()
    print(f"{len(hits)} possible secret(s) found")
    if not hits:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"=== {timestamp} ===\n")
        f.write("\n".join(hits))
        f.write("\n\n")
    notify(len(hits))


if __name__ == "__main__":
    main()
