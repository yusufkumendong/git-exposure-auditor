#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: $0 domain|subdomain|'*.example.com' [opsi tambahan]"; exit 1; }
INPUT="$1"; shift
if [[ "$INPUT" == \*.* ]]; then
  exec "$ROOT_DIR/bin/gea" --mode best-practice --wildcard "$INPUT" --authorized "$@"
elif [[ "$INPUT" == http://* || "$INPUT" == https://* ]]; then
  exec "$ROOT_DIR/bin/gea" --mode best-practice --target "$INPUT" --authorized "$@"
else
  exec "$ROOT_DIR/bin/gea" --mode best-practice --domain "$INPUT" --authorized "$@"
fi
