#!/usr/bin/env bash

# Hard level: passive subdomain discovery plus a controlled Git HEAD check.

set -Eeuo pipefail
IFS=$'\n\t'

usage() {
  cat <<'HELP'
Usage:
  ./scripts/hard.sh <root-domain> [output-directory]

Example:
  ./scripts/hard.sh example.com results/example.com-hard

Environment overrides:
  THREADS=20 RATE_LIMIT=10 PORTS='http:80,https:443' ./scripts/hard.sh example.com
  CRT_MAX_TIME=120 CRT_RETRIES=1 ./scripts/hard.sh example.com
  HTTPX_BIN=/usr/bin/httpx-toolkit ./scripts/hard.sh example.com

Only use this script where passive discovery and automated probing are permitted by scope.
HELP
}

DOMAIN="${1:-}"
OUTDIR="${2:-}"
THREADS="${THREADS:-20}"
RATE_LIMIT="${RATE_LIMIT:-10}"
PORTS="${PORTS:-http:80,https:443}"

[[ -n "$DOMAIN" ]] || { usage; exit 2; }
DOMAIN="${DOMAIN#http://}"
DOMAIN="${DOMAIN#https://}"
DOMAIN="${DOMAIN%%/*}"
DOMAIN="${DOMAIN%%:*}"
DOMAIN="${DOMAIN%.}"
DOMAIN="${DOMAIN,,}"

if [[ ! "$DOMAIN" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$ ]]; then
  echo "[!] Invalid root domain: $DOMAIN" >&2
  exit 2
fi

[[ "$THREADS" =~ ^[0-9]+$ ]] && (( THREADS >= 1 && THREADS <= 50 )) || {
  echo "[!] THREADS must be an integer from 1 to 50." >&2
  exit 2
}

[[ "$RATE_LIMIT" =~ ^[0-9]+$ ]] && (( RATE_LIMIT >= 1 && RATE_LIMIT <= 50 )) || {
  echo "[!] RATE_LIMIT must be an integer from 1 to 50." >&2
  exit 2
}

OUTDIR="${OUTDIR:-results/${DOMAIN}-hard-$(date +%Y%m%d-%H%M%S)}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

for cmd in curl jq assetfinder; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "[!] Missing dependency: $cmd" >&2
    exit 2
  }
done

resolve_projectdiscovery_httpx || exit 2

mkdir -p "$OUTDIR"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
RAW="$TMPDIR/raw.txt"
CRT_NAMES="$TMPDIR/crtsh-names.txt"
printf '%s\n' "$DOMAIN" > "$RAW"

echo "[*] Querying Certificate Transparency data."
if fetch_crtsh_names "$DOMAIN" "$CRT_NAMES" "$OUTDIR/crtsh-errors.log"; then
  cat "$CRT_NAMES" >> "$RAW"
  printf '[*] crt.sh names collected: %s\n' "$(wc -l < "$CRT_NAMES" | tr -d ' ')"
else
  echo "[!] crt.sh did not return usable data; continuing with other sources." >&2
  echo "[!] Details: $OUTDIR/crtsh-errors.log" >&2
fi

echo "[*] Running assetfinder."
if ! assetfinder --subs-only "$DOMAIN" >> "$RAW" 2>"$OUTDIR/assetfinder-errors.log"; then
  echo "[!] assetfinder returned an error; see assetfinder-errors.log." >&2
fi

awk -v d="$DOMAIN" '
{
  gsub(/\r/, "", $0)
  sub(/^\*\./, "", $0)
  x = tolower($0)
  if (x == d || (length(x) > length(d) && substr(x, length(x)-length(d), length(d)+1) == "." d)) {
    print x
  }
}' "$RAW" | sort -u > "$OUTDIR/subdomains.txt"

HOST_COUNT="$(wc -l < "$OUTDIR/subdomains.txt" | tr -d ' ')"
printf '[*] In-scope unique hosts: %s\n' "$HOST_COUNT"

if [[ "$HOST_COUNT" -eq 0 ]]; then
  echo "[!] No in-scope hosts were produced." >&2
  exit 1
fi

: > "$OUTDIR/candidates.txt"

MATCHER='status_code == 200 && (contains(body, "ref: refs/heads/") || regex("^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", trim_space(body)))'

"$HTTPX_BIN" \
  -l "$OUTDIR/subdomains.txt" \
  -silent \
  -nc \
  -path '/.git/HEAD' \
  -ports "$PORTS" \
  -mdc "$MATCHER" \
  -sc \
  -cl \
  -server \
  -threads "$THREADS" \
  -rate-limit "$RATE_LIMIT" \
  -timeout 8 \
  -retries 1 \
  -o "$OUTDIR/candidates.txt"

CANDIDATE_COUNT="$(wc -l < "$OUTDIR/candidates.txt" | tr -d ' ')"
printf '[*] High-confidence candidates: %s\n' "$CANDIDATE_COUNT"
printf '[*] Output directory: %s\n' "$OUTDIR"
