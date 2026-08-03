#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d -t gea-test.XXXXXX)"
SERVER_PID=""
cleanup() { [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null || true; rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

python3 "$ROOT_DIR/tests/mock_server.py" &
SERVER_PID=$!
for _ in {1..20}; do curl -s http://127.0.0.1:18765/ >/dev/null && break; sleep 0.1; done

"$ROOT_DIR/bin/gea" \
  --mode best-practice \
  --target http://127.0.0.1:18765 \
  --authorized --allow-private \
  --concurrency 2 --rate 5 --retries 1 \
  --report-dir "$TMP_DIR/report" --no-color >/dev/null

JSON="$TMP_DIR/report/results.jsonl"
jq -e 'select(.endpoint=="/.git/HEAD" and .status=="200" and .classification=="confirmed_exposure" and .confidence>=90)' "$JSON" >/dev/null
jq -e 'select(.endpoint=="/.git/config" and .classification=="spa_fallback")' "$JSON" >/dev/null
jq -e 'select(.endpoint=="/.git/packed-refs" and .classification=="upstream_error" and .retries==1)' "$JSON" >/dev/null
jq -e 'select(.endpoint=="/.git/logs/HEAD" and .classification=="waf_challenge")' "$JSON" >/dev/null
jq -e 'select(.endpoint=="/.git/objects/info/packs" and .classification=="rate_limited")' "$JSON" >/dev/null
grep -q 'HTTP 200: 4 respons' "$TMP_DIR/report/summary.txt"
grep -q 'confirmed_exposure: 3 respons' "$TMP_DIR/report/summary.txt"
grep -q 'No repository dumping' "$TMP_DIR/report/hackerone-findings.md"
echo "Integration test: PASS"
