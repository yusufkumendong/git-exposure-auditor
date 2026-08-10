#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
./tests/syntax.sh
PYTHONPATH="$ROOT_DIR" python3 ./tests/unit.py
./tests/integration.sh
echo "All tests: PASS"
