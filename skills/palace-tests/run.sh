#!/bin/bash
# Palace engine test suite — stdlib unittest, zero install. Run: bash run.sh
cd "$(dirname "$0")" || exit 1
exec python3 -m unittest -v
