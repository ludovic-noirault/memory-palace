#!/usr/bin/env python3
"""Find cred-shaped strings in the Obsidian vault.

Two modes:

  scan-secrets.py                        report: wings (projects/) + top-level vault docs.
                                         Strong and weak patterns, never rewrites a file.
  scan-secrets.py --redact DIR [--days N] [--dry-run]
                                         redact: strong patterns only, rewritten in place as
                                         [REDACTED:<rule>]. For transcripts regenerated from
                                         JSONL, never for hand-curated wings. --dry-run counts
                                         per rule and writes nothing.

Neither mode prints or logs a matched value: the log gets `path:line: rule` only.
"""

import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path


def _load_env_file():
    """Parse palace.env the way palace-map does: $PALACE_ENV, else $PALACE_CLAUDE_DIR/palace.env."""
    path = os.environ.get("PALACE_ENV") or os.path.join(
        os.environ.get("PALACE_CLAUDE_DIR", os.path.expanduser("~/.claude")), "palace.env")
    vals = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    except OSError:
        pass
    return vals


_ENV_FILE = _load_env_file()


def _cfg(key, default):
    """Real env var > palace.env > built-in default."""
    return os.environ.get(key) or _ENV_FILE.get(key) or default


VAULT = Path(os.path.expanduser(_cfg("VAULT_DIR", "~/obsidian")))
LOG = Path(os.path.expanduser(_cfg("PALACE_CLAUDE_DIR", "~/.claude"))) / "hooks" / "scan-secrets.log"
SKIP_DIR_NAMES = {"_backups", ".template"}

# Token shapes with a vendor prefix: near-zero false positives, safe to rewrite in place.
# sk-ant precedes the generic sk- rule so Anthropic keys get the right label.
STRONG = [
    ("private-key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----)?", re.DOTALL)),
    ("github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("github", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("gitlab", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}")),
    ("anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    # Length + an uppercase letter: ticket slugs like sk-123-some-branch are lowercase words.
    ("openai", re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{40,}")),
    ("slack", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
    ("aws", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]

# Generic assignments: often a code example, so reported for a human, never rewritten.
# The value must be an 8+ char literal: skips '', <key> and settings.FOO references.
LITERAL = r"""["']?[A-Za-z0-9_\-+/=]{8,}(?![\w.(])"""
WEAK = [
    ("auth-password", re.compile(r"auth-password=\S+")),
    ("auth-username", re.compile(r"auth-username=\S+")),
    ("api-key", re.compile(r'api[_-]?key["\']?\s*[:=]\s*' + LITERAL, re.IGNORECASE)),
    ("secret-key", re.compile(r'secret[_-]?key["\']?\s*[:=]\s*' + LITERAL, re.IGNORECASE)),
]

# Known false-positive shapes: env-var placeholders, not literal secrets
FALSE_POSITIVE_MARKERS = ("%env(", "${", "process.env.", "os.environ")


def iter_md(root: Path):
    for path in root.rglob("*.md"):
        if path.is_file() and not any(part in SKIP_DIR_NAMES for part in path.parts):
            yield path


def read(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def line_hits(text: str):
    """(lineno, rule) for every strong or weak match, placeholder lines skipped."""
    lines = text.split("\n")
    skip = {i for i, line in enumerate(lines, 1) if any(m in line for m in FALSE_POSITIVE_MARKERS)}
    hits = []
    for rule, pat in STRONG:
        for m in pat.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            if lineno not in skip:
                hits.append((lineno, rule))
    for lineno, line in enumerate(lines, 1):
        if lineno in skip:
            continue
        for rule, pat in WEAK:
            if pat.search(line):
                hits.append((lineno, rule))
                break
    return sorted(set(hits))


def log(lines):
    if not lines:
        return
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"=== {datetime.now():%Y-%m-%d %H:%M:%S} ===\n" + "\n".join(lines) + "\n\n")


def report():
    if not (VAULT / "projects").is_dir():
        print(f"scan-secrets: vault not found: {VAULT / 'projects'}", file=sys.stderr)
        print(f"vault not found: {VAULT}")
        return 2
    files = list(iter_md(VAULT / "projects")) + sorted(p for p in VAULT.glob("*.md") if p.is_file())
    entries = []
    for path in files:
        text = read(path)
        if text is not None:
            entries += [f"{path}:{lineno}: {rule}" for lineno, rule in line_hits(text)]
    log(entries)
    print(f"{len(entries)} possible secret(s) found")
    return 0


def redact(root: Path, days, dry_run=False):
    if not root.is_dir():
        print(f"scan-secrets: redact dir not found: {root}", file=sys.stderr)
        return 2
    cutoff = time.time() - days * 86400 if days is not None else None
    by_rule, touched, entries = Counter(), 0, []
    for path in iter_md(root):
        if cutoff is not None and path.stat().st_mtime < cutoff:
            continue
        text = read(path)
        if text is None:
            continue
        rules = []
        for rule, pat in STRONG:
            text, n = pat.subn(f"[REDACTED:{rule}]", text)
            rules += [rule] * n
        if rules:
            by_rule.update(rules)
            touched += 1
            if not dry_run:
                path.write_text(text, encoding="utf-8")
                entries.append(f"{path}: {len(rules)} redacted ({', '.join(sorted(set(rules)))})")
    total = sum(by_rule.values())
    if dry_run:
        print(f"{total} secret(s) would be redacted in {touched} file(s)")
        for rule, n in sorted(by_rule.items()):
            print(f"  {rule}: {n}")
        return 0
    log(entries)
    print(f"{total} secret(s) redacted in {touched} file(s)")
    return 0


def main(argv):
    if "--redact" not in argv:
        return report()
    i = argv.index("--redact")
    if i + 1 >= len(argv):
        print("usage: scan-secrets.py --redact DIR [--days N] [--dry-run]", file=sys.stderr)
        return 2
    days = float(argv[argv.index("--days") + 1]) if "--days" in argv else None
    return redact(Path(os.path.expanduser(argv[i + 1])), days, "--dry-run" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
