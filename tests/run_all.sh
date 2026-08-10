#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${GEA_PYTHON:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "Python runtime tidak ditemukan: $PYTHON_BIN" >&2
  exit 1
}
"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "Test suite membutuhkan Python >= 3.10 (runtime: $PYTHON_BIN)." >&2
  exit 1
}

GEA_PYTHON="$PYTHON_BIN" bash ./tests/syntax.sh
PYTHONPATH="$ROOT_DIR" "$PYTHON_BIN" ./tests/unit.py
GEA_PYTHON="$PYTHON_BIN" bash ./tests/integration.sh
echo "All tests: PASS"
