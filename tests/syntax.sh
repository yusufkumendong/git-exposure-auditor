#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while IFS= read -r file; do bash -n "$file"; done < <(find "$ROOT_DIR" -type f \( -name '*.sh' -o -path "$ROOT_DIR/bin/gea" \))
PYTHON_BIN="${GEA_PYTHON:-python3}"
"$PYTHON_BIN" -m py_compile "$ROOT_DIR"/gea/*.py "$ROOT_DIR/tests/mock_server.py"
echo "Syntax test: PASS"
