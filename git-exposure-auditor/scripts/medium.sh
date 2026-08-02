#!/usr/bin/env bash

# Medium level: test a user-supplied list of hosts or URLs with httpx.

set -Eeuo pipefail

usage() {
  cat <<'HELP'
Usage:
  ./scripts/medium.sh <targets-file> [output-file]

Example:
  ./scripts/medium.sh examples/targets.example.txt results/medium.txt

The targets file must contain only systems you own or are explicitly authorized to test.
HELP
}

INPUT="${1:-}"
OUTPUT="${2:-results/medium-$(date +%Y%m%d-%H%M%S).txt}"

[[ -n "$INPUT" ]] || { usage; exit 2; }
[[ -r "$INPUT" ]] || { echo "[!] Cannot read input file: $INPUT" >&2; exit 2; }
command -v httpx >/dev/null 2>&1 || { echo "[!] Missing dependency: httpx" >&2; exit 2; }

mkdir -p "$(dirname "$OUTPUT")"

MATCHER='status_code == 200 && (contains(body, "ref: refs/heads/") || regex("^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", trim_space(body)))'

echo "[*] Running a low-rate metadata check against the supplied targets."

httpx \
  -l "$INPUT" \
  -silent \
  -nc \
  -path '/.git/HEAD' \
  -mdc "$MATCHER" \
  -sc \
  -cl \
  -server \
  -threads 10 \
  -rate-limit 5 \
  -timeout 8 \
  -retries 1 \
  -o "$OUTPUT"

COUNT="$(wc -l < "$OUTPUT" | tr -d ' ')"
printf '[*] High-confidence candidates: %s\n' "$COUNT"
printf '[*] Output: %s\n' "$OUTPUT"
