#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${1:-}"
AUTH="${2:-}"
OUTPUT="${3:-}"

if [[ -z "$DOMAIN" || "$AUTH" != "--authorized" ]]; then
  cat >&2 <<'HELP'
Usage:
  ./scripts/hard.sh <root-domain> --authorized [output-directory]

Example:
  ./scripts/hard.sh example.com --authorized

Environment overrides:
  THREADS=10 RATE_LIMIT=5 PORTS='http:80,https:443' \
    ./scripts/hard.sh example.com --authorized
HELP
  exit 2
fi

ARGS=(
  --domain "$DOMAIN"
  --authorized
  --threads "${THREADS:-15}"
  --rate-limit "${RATE_LIMIT:-10}"
)
[[ -n "$OUTPUT" ]] && ARGS+=( --output "$OUTPUT" )
[[ -n "${PORTS:-}" ]] && ARGS+=( --ports "$PORTS" )
[[ "${SAFE_CONFIRM:-0}" == "1" ]] && ARGS+=( --confirm )

exec "$ROOT_DIR/bin/git-exposure-auditor" "${ARGS[@]}"
