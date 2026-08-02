#!/usr/bin/env bash

# Easy level: validate one base URL with curl only.
# Exit codes:
#   0 = high-confidence Git HEAD signature found
#   1 = not confirmed
#   2 = input, dependency, or network error

set -Eeuo pipefail

usage() {
  cat <<'HELP'
Usage:
  ./scripts/easy.sh <base-url-or-host>

Examples:
  ./scripts/easy.sh https://example.com
  ./scripts/easy.sh app.example.com

Only test systems you own or are explicitly authorized to assess.
HELP
}

TARGET="${1:-}"
[[ -n "$TARGET" ]] || { usage; exit 2; }
command -v curl >/dev/null 2>&1 || { echo "[!] Missing dependency: curl" >&2; exit 2; }

if [[ ! "$TARGET" =~ ^https?:// ]]; then
  TARGET="https://$TARGET"
fi

TARGET="${TARGET%/}/.git/HEAD"
TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

HTTP_CODE="$(
  curl \
    --silent \
    --show-error \
    --path-as-is \
    --connect-timeout 5 \
    --max-time 10 \
    --output "$TMP_BODY" \
    --write-out '%{http_code}' \
    "$TARGET"
)" || {
  echo "[!] Request failed: $TARGET" >&2
  exit 2
}

BODY="$(tr -d '\r' < "$TMP_BODY")"
TRIMMED="$(printf '%s' "$BODY" | awk '{$1=$1};1')"

printf '[*] URL: %s\n' "$TARGET"
printf '[*] HTTP status: %s\n' "$HTTP_CODE"

if [[ "$HTTP_CODE" == "200" ]] && {
  [[ "$TRIMMED" =~ ^ref:[[:space:]]refs/heads/[A-Za-z0-9._/-]+$ ]] ||
  [[ "$TRIMMED" =~ ^[0-9a-fA-F]{40}$ ]] ||
  [[ "$TRIMMED" =~ ^[0-9a-fA-F]{64}$ ]]
}; then
  echo "[+] High-confidence candidate: Git HEAD metadata is publicly readable."
  printf '[+] Response signature: %s\n' "$TRIMMED"
  echo "[!] Stop here and verify scope before performing any additional request."
  exit 0
fi

echo "[-] Git HEAD exposure was not confirmed."
exit 1
