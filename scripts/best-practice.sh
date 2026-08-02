#!/usr/bin/env bash

# Best Practice level:
# - explicit authorization acknowledgement
# - domain or file input
# - strict scope filtering in domain mode
# - bounded concurrency and rate limiting
# - structured JSONL plus clean URL output
# - no redirect following and no repository dumping

set -Eeuo pipefail
IFS=$'\n\t'

usage() {
  cat <<'HELP'
Git Exposure Auditor — Best Practice workflow

Usage:
  Domain mode:
    ./scripts/best-practice.sh --domain example.com --authorized [options]

  Targets-file mode:
    ./scripts/best-practice.sh --targets targets.txt --authorized [options]

Required acknowledgement:
  --authorized        Confirm that you own the targets or have explicit permission.

Options:
  --output DIR        Output directory. Default: timestamped directory under results/
  --threads N         Worker count, 1-50. Default: 15
  --rate-limit N      Maximum requests per second, 1-50. Default: 8
  --ports VALUE       Explicit httpx port mapping. Domain-mode default: http:80,https:443.
                      In targets-file mode, ports are not expanded unless this is supplied.
  --history FILE      Append only newly observed candidate URLs with anew, if installed.
  -h, --help          Show this help text.

Examples:
  ./scripts/best-practice.sh --domain example.com --authorized
  ./scripts/best-practice.sh --targets authorized-targets.txt --authorized --rate-limit 5

This tool performs a non-destructive check of /.git/HEAD only. It does not dump repositories,
use exposed credentials, bypass access controls, or follow redirects.
HELP
}

DOMAIN=""
TARGETS_FILE=""
OUTDIR=""
THREADS=15
RATE_LIMIT=8
PORTS=""
PORTS_SET=0
HISTORY_FILE=""
AUTHORIZED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:-}"
      shift 2
      ;;
    --targets)
      TARGETS_FILE="${2:-}"
      shift 2
      ;;
    --output)
      OUTDIR="${2:-}"
      shift 2
      ;;
    --threads)
      THREADS="${2:-}"
      shift 2
      ;;
    --rate-limit)
      RATE_LIMIT="${2:-}"
      shift 2
      ;;
    --ports)
      PORTS="${2:-}"
      PORTS_SET=1
      shift 2
      ;;
    --history)
      HISTORY_FILE="${2:-}"
      shift 2
      ;;
    --authorized)
      AUTHORIZED=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[!] Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

[[ "$AUTHORIZED" -eq 1 ]] || {
  echo "[!] Refusing to run without --authorized." >&2
  echo "[!] Confirm ownership or explicit testing permission first." >&2
  exit 2
}

if [[ -n "$DOMAIN" && -n "$TARGETS_FILE" ]] || [[ -z "$DOMAIN" && -z "$TARGETS_FILE" ]]; then
  echo "[!] Choose exactly one input mode: --domain or --targets." >&2
  exit 2
fi

[[ "$THREADS" =~ ^[0-9]+$ ]] && (( THREADS >= 1 && THREADS <= 50 )) || {
  echo "[!] --threads must be an integer from 1 to 50." >&2
  exit 2
}

[[ "$RATE_LIMIT" =~ ^[0-9]+$ ]] && (( RATE_LIMIT >= 1 && RATE_LIMIT <= 50 )) || {
  echo "[!] --rate-limit must be an integer from 1 to 50." >&2
  exit 2
}

for cmd in jq; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "[!] Missing dependency: $cmd" >&2
    exit 2
  }
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"
resolve_projectdiscovery_httpx || exit 2

MODE="targets"
LABEL="targets"
if [[ -n "$DOMAIN" ]]; then
  MODE="domain"
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

  LABEL="$DOMAIN"
  if [[ "$PORTS_SET" -eq 0 ]]; then
    PORTS='http:80,https:443'
  fi
  for cmd in curl assetfinder; do
    command -v "$cmd" >/dev/null 2>&1 || {
      echo "[!] Missing dependency for domain mode: $cmd" >&2
      exit 2
    }
  done
else
  [[ -r "$TARGETS_FILE" ]] || {
    echo "[!] Cannot read targets file: $TARGETS_FILE" >&2
    exit 2
  }
  LABEL="$(basename "$TARGETS_FILE")"
fi

OUTDIR="${OUTDIR:-results/${LABEL}-best-practice-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUTDIR"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

INPUT_FILE="$OUTDIR/targets.txt"

if [[ "$MODE" == "domain" ]]; then
  RAW="$TMPDIR/raw.txt"
  printf '%s\n' "$DOMAIN" > "$RAW"

  echo "[*] Collecting passive hostnames for: $DOMAIN"

  CRT_NAMES="$TMPDIR/crtsh-names.txt"
  if fetch_crtsh_names "$DOMAIN" "$CRT_NAMES" "$OUTDIR/crtsh-errors.log"; then
    cat "$CRT_NAMES" >> "$RAW"
    printf '[*] crt.sh names collected: %s\n' "$(wc -l < "$CRT_NAMES" | tr -d ' ')"
  else
    echo "[!] crt.sh did not return usable data; continuing." >&2
    echo "[!] Details: $OUTDIR/crtsh-errors.log" >&2
  fi

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
  }' "$RAW" | sort -u > "$INPUT_FILE"
else
  awk '
  {
    gsub(/\r/, "", $0)
    sub(/^[[:space:]]+/, "", $0)
    sub(/[[:space:]]+$/, "", $0)
    if ($0 != "" && $0 !~ /^#/) print $0
  }' "$TARGETS_FILE" | sort -u > "$INPUT_FILE"
fi

TARGET_COUNT="$(wc -l < "$INPUT_FILE" | tr -d ' ')"
if [[ "$TARGET_COUNT" -eq 0 ]]; then
  echo "[!] No usable targets were produced." >&2
  exit 1
fi

printf '[*] Authorized targets prepared: %s\n' "$TARGET_COUNT"
PORT_DISPLAY="${PORTS:-input-defined/default httpx behavior}"
printf '[*] Threads: %s | Rate limit: %s req/s | Ports: %s\n' "$THREADS" "$RATE_LIMIT" "$PORT_DISPLAY"

MATCHER='status_code == 200 && (contains(body, "ref: refs/heads/") || regex("^([0-9a-fA-F]{40}|[0-9a-fA-F]{64})$", trim_space(body)))'
JSONL="$OUTDIR/candidates.jsonl"
TXT="$OUTDIR/candidates.txt"

: > "$JSONL"

HTTPX_ARGS=(
  -l "$INPUT_FILE"
  -silent
  -nc
  -path '/.git/HEAD'
  -mdc "$MATCHER"
  -sc
  -cl
  -server
  -threads "$THREADS"
  -rate-limit "$RATE_LIMIT"
  -timeout 8
  -retries 1
  -json
  -o "$JSONL"
)

if [[ -n "$PORTS" ]]; then
  HTTPX_ARGS+=( -ports "$PORTS" )
fi

"$HTTPX_BIN" "${HTTPX_ARGS[@]}"

if [[ -s "$JSONL" ]]; then
  jq -r '.url // empty' "$JSONL" | sort -u > "$TXT"
else
  : > "$TXT"
fi

CANDIDATE_COUNT="$(wc -l < "$TXT" | tr -d ' ')"
printf '[*] High-confidence candidates: %s\n' "$CANDIDATE_COUNT"
printf '[*] JSONL evidence: %s\n' "$JSONL"
printf '[*] URL list: %s\n' "$TXT"

if [[ -n "$HISTORY_FILE" ]]; then
  mkdir -p "$(dirname "$HISTORY_FILE")"
  if command -v anew >/dev/null 2>&1; then
    NEW_FILE="$OUTDIR/new-candidates.txt"
    anew "$HISTORY_FILE" < "$TXT" > "$NEW_FILE"
    printf '[*] Newly observed candidates: %s\n' "$(wc -l < "$NEW_FILE" | tr -d ' ')"
    printf '[*] New-only output: %s\n' "$NEW_FILE"
  else
    echo "[!] --history was requested, but anew is not installed." >&2
  fi
fi

cat <<'MESSAGE'

Next steps:
1. Verify that every result is still in scope.
2. Manually reproduce the minimal request once.
3. Do not dump the repository or use any exposed secret without explicit permission.
4. Report only the minimum evidence required to demonstrate impact.
MESSAGE
