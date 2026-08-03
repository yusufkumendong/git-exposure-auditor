#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: $0 domain-or-url [opsi tambahan]"; exit 1; }
INPUT="$1"; shift
if [[ "$INPUT" == http://* || "$INPUT" == https://* ]]; then
  exec "$ROOT_DIR/bin/gea" --mode easy --target "$INPUT" "$@"
else
  exec "$ROOT_DIR/bin/gea" --mode easy --domain "$INPUT" "$@"
fi
