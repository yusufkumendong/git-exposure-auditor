#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 3 ]] || {
  echo "Usage: $0 TARGET SCOPE_FILE POLICY_JSON [opsi tambahan]" >&2
  exit 1
}
TARGET="$1"; SCOPE_FILE="$2"; POLICY_FILE="$3"; shift 3
exec "$ROOT_DIR/bin/gea" \
  --mode authorized-advanced \
  --target "$TARGET" \
  --scope "$SCOPE_FILE" \
  --policy-file "$POLICY_FILE" \
  --authorized \
  --bypass-permitted \
  "$@"
