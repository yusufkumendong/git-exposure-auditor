#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${1:-}"
AUTH="${2:-}"
OUTPUT="${3:-}"

if [[ -z "$TARGETS" || "$AUTH" != "--authorized" ]]; then
  cat >&2 <<'HELP'
Usage:
  ./scripts/medium.sh <targets-file> --authorized [output-directory]

Example:
  ./scripts/medium.sh examples/targets.example.txt --authorized
HELP
  exit 2
fi

ARGS=(
  --targets "$TARGETS"
  --authorized
  --no-discovery
  --threads "${THREADS:-10}"
  --rate-limit "${RATE_LIMIT:-5}"
)
[[ -n "$OUTPUT" ]] && ARGS+=( --output "$OUTPUT" )
[[ -n "${PORTS:-}" ]] && ARGS+=( --ports "$PORTS" )

exec "$ROOT_DIR/bin/git-exposure-auditor" "${ARGS[@]}"
