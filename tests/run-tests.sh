#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
PORT="${GEA_TEST_PORT:-18080}"
SERVER_PID=""
cleanup() {
  [[ -z "$SERVER_PID" ]] || kill "$SERVER_PID" 2>/dev/null || true
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

python3 "$ROOT_DIR/tests/mock_server.py" --port "$PORT" > "$TMPDIR/server.log" 2>&1 &
SERVER_PID="$!"
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/.git/HEAD" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

cat > "$TMPDIR/scope.json" <<JSON
{
  "program": "local-test",
  "authorized": true,
  "include": ["127.0.0.1"],
  "exclude": [],
  "allowed_ports": ["http:$PORT"],
  "application_paths": ["/", "/soft", "/blocked"],
  "max_threads": 10,
  "max_rate_limit": 20,
  "max_tasks": 100,
  "max_response_bytes": 65536
}
JSON

printf 'http://127.0.0.1:%s\n' "$PORT" > "$TMPDIR/urls.txt"
printf '/\n/soft\n/blocked\n' > "$TMPDIR/paths.txt"

python3 "$ROOT_DIR/lib/scope.py" validate --scope "$TMPDIR/scope.json" >/dev/null
python3 "$ROOT_DIR/lib/validator.py" \
  --urls "$TMPDIR/urls.txt" \
  --paths "$TMPDIR/paths.txt" \
  --scope "$TMPDIR/scope.json" \
  --output "$TMPDIR/findings.jsonl" \
  --threads 3 \
  --rate-limit 20 \
  --timeout 3 \
  --confirm >/dev/null

jq -e 'select(.application_path == "/" and .classification == "CONFIRMED" and .score >= 90)' "$TMPDIR/findings.jsonl" >/dev/null
jq -e 'select(.application_path == "/soft" and .classification == "SOFT_404")' "$TMPDIR/findings.jsonl" >/dev/null
jq -e 'select(.application_path == "/blocked" and .classification == "BLOCKED")' "$TMPDIR/findings.jsonl" >/dev/null

cat > "$TMPDIR/metadata.json" <<JSON
{
  "tool_version": "2.0.0",
  "started_at": "2026-08-02T00:00:00Z",
  "finished_at": "2026-08-02T00:00:01Z",
  "input_mode": "test",
  "output_directory": "$TMPDIR",
  "safe_confirmation": true
}
JSON

python3 "$ROOT_DIR/lib/report.py" \
  --findings "$TMPDIR/findings.jsonl" \
  --metadata "$TMPDIR/metadata.json" \
  --live-urls "$TMPDIR/urls.txt" \
  --output-dir "$TMPDIR/report" >/dev/null

test -s "$TMPDIR/report/summary.md"
test -s "$TMPDIR/report/report-draft.md"
grep -q 'http://127.0.0.1' "$TMPDIR/report/confirmed.txt"

printf 'http://127.0.0.1:%s\n' "$PORT" > "$TMPDIR/main-targets.txt"
HTTPX_BIN="$ROOT_DIR/tests/mock_httpx.sh" \
  "$ROOT_DIR/bin/git-exposure-auditor" \
  --targets "$TMPDIR/main-targets.txt" \
  --authorized \
  --confirm \
  --threads 2 \
  --rate-limit 10 \
  --timeout 3 \
  --output "$TMPDIR/main-output" >/dev/null

jq -e '.confirmed_count == 1 and .guarantees_bounty == false' \
  "$TMPDIR/main-output/scan-summary.json" >/dev/null
jq -e '.safe_confirmation == true and .filter_stats.accepted == 1' \
  "$TMPDIR/main-output/metadata.json" >/dev/null

echo "All tests passed."
