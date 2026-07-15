#!/bin/bash
VAULT_DIR=$HOME/theTribe/obsidian
python3 ~/.claude/skills/recall/scripts/extract-sessions.py --days 3
qmd update
