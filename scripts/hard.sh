#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || { echo "Usage: $0 domain-or-subdomain [opsi tambahan]"; exit 1; }
INPUT="$1"; shift
exec "$ROOT_DIR/bin/gea" --mode hard --target "$INPUT" "$@"
