#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "${1:-}" == "-h" ]]; then
  cat <<'HELP'
-l, -list string
-j, -json
-path string
-o, -output string
-nf, -no-fallback
-rstr, -response-size-to-read int
-duc, -disable-update-check
HELP
  exit 0
fi
if [[ "${1:-}" == "-version" ]]; then
  echo '[INF] Current Version: mock-v2'
  exit 0
fi
INPUT=""
OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -l|-list) INPUT="$2"; shift 2 ;;
    -o|-output) OUTPUT="$2"; shift 2 ;;
    -threads|-rate-limit|-timeout|-retries|-ports|-hash|-response-size-to-read) shift 2 ;;
    *) shift ;;
  esac
done
[[ -n "$INPUT" && -n "$OUTPUT" ]]
: > "$OUTPUT"
while IFS= read -r target; do
  [[ -n "$target" ]] || continue
  if [[ "$target" != http://* && "$target" != https://* ]]; then
    target="http://$target"
  fi
  printf '{"url":"%s","status_code":200,"probe_status":true}\n' "$target" >> "$OUTPUT"
done < "$INPUT"
