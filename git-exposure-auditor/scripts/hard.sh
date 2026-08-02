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

Only use this script where passive discovery and automated probing are permitted by scope.
HELP
}

DOMAIN="${1:-}"
OUTDIR="${2:-results/${DOMAIN:-unknown}-hard-$(date +%Y%m%d-%H%M%S)}"
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

for cmd in curl jq assetfinder httpx; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "[!] Missing dependency: $cmd" >&2
    exit 2
  }
done

mkdir -p "$OUTDIR"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
RAW="$TMPDIR/raw.txt"
printf '%s\n' "$DOMAIN" > "$RAW"

echo "[*] Querying Certificate Transparency data."
if ! curl \
  --fail \
  --silent \
  --show-error \
  --get \
  --connect-timeout 10 \
  --max-time 45 \
  --retry 2 \
  --retry-delay 1 \
  --data-urlencode "q=%.$DOMAIN" \
  --data-urlencode 'output=json' \
  'https://crt.sh/' \
  | jq -r '.[].name_value? // empty | split("\n")[]' \
  >> "$RAW"; then
  echo "[!] crt.sh did not return usable data; continuing with other sources." >&2
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

MATCHER='status_code == 200 && (contains(body, "ref: refs/heads/") || regex("^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", trim_space(body)))'

httpx \
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
