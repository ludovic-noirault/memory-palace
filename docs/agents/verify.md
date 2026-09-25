# Verify

Commands `~/.claude/hooks/verify-gate.py` runs before it lets a `git push` through.
Every 4-space-indented line is one command, run from the repo root; a non-zero exit
denies the push.

## Test suite

57 stdlib unittest cases over the resolver, validate, render, staleness, archive,
doctor, secret-scan and harvest-template paths. Runs in about 3 seconds, so there is no reason to push around it.

    bash skills/palace-tests/run.sh

## Hooks deployed into ~/.claude

`install.sh` copies these onto the machine, where a syntax error costs every session
until someone notices. Parsed rather than compiled, so no `__pycache__` lands in the
tree.

    python3 -c "import ast,sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]" hooks/scan-secrets.py hooks/spine-palace-link.py
    bash -n hooks/index-sessions.sh
    bash -n hooks/palace-sync-sessions.sh
    bash -n hooks/palace-context.sh
    bash -n hooks/palace-install.sh
    bash -n install.sh
