#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

TARGET="${1:-}"
AUTH="${2:-}"
OUTPUT="${3:-}"

if [[ -z "$TARGET" || "$AUTH" != "--authorized" ]]; then
  cat >&2 <<'HELP'
Usage:
  ./scripts/easy.sh <URL-or-host> --authorized [output-directory]

Example:
  ./scripts/easy.sh https://example.com --authorized
HELP
  exit 2
fi

TMP_TARGETS="$(mktemp)"
trap 'rm -f "$TMP_TARGETS"' EXIT
printf '%s\n' "$TARGET" > "$TMP_TARGETS"

ARGS=(
  --targets "$TMP_TARGETS"
  --authorized
  --no-discovery
  --threads 1
  --rate-limit 1
  --max-tasks 10
)
[[ -n "$OUTPUT" ]] && ARGS+=( --output "$OUTPUT" )

exec "$ROOT_DIR/bin/git-exposure-auditor" "${ARGS[@]}"
