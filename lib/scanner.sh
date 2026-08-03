#!/usr/bin/env bash

select_endpoints() {
  local mode="$1"
  case "$mode" in
    easy) ENDPOINTS=("/.git/HEAD") ;;
    medium) ENDPOINTS=("/.git/HEAD" "/.git/config" "/.git/packed-refs") ;;
    hard|best-practice)
      ENDPOINTS=(
        "/.git/HEAD" "/.git/config" "/.git/packed-refs"
        "/.git/refs/heads/main" "/.git/refs/heads/master"
        "/.git/logs/HEAD" "/.git/index" "/.git/objects/info/packs"
      )
      ;;
    *) die "Mode tidak valid: $mode" ;;
  esac
}

rate_sleep() {
  [[ "$RATE_LIMIT" == "0" || "$RATE_LIMIT" == "0.0" ]] && return 0
  python3 - "$RATE_LIMIT" <<'PY'
import sys,time
rate=float(sys.argv[1])
if rate > 0: time.sleep(1.0/rate)
PY
}

prepare_baseline() {
  local target="$1" dir="$2" token
  token="$(random_hex)"
  BASELINE_ENDPOINT="/.gea-baseline-${token}"
  BASELINE_BODY="$dir/baseline.body"
  BASELINE_HEADERS="$dir/baseline.headers"
  BASELINE_ERROR="$dir/baseline.error"
  BASELINE_META="$dir/baseline.meta"
  http_request "${target}${BASELINE_ENDPOINT}" "$BASELINE_BODY" "$BASELINE_HEADERS" "$BASELINE_ERROR" "$BASELINE_META"
  BASELINE_STATUS="$(cut -f1 "$BASELINE_META")"
  BASELINE_STATUS="${BASELINE_STATUS:-000}"
}

scan_one_to_file() {
  local target="$1" endpoint="$2" baseline_body="$3" baseline_status="$4" result_file="$5"
  local body_file headers_file error_file meta_file line status effective content_type size duration remote_ip http_version curl_rc retries timestamp analysis curl_error
  body_file="$(mktemp "$WORK_DIR/body.XXXXXX")"
  headers_file="$(mktemp "$WORK_DIR/headers.XXXXXX")"
  error_file="$(mktemp "$WORK_DIR/error.XXXXXX")"
  meta_file="$(mktemp "$WORK_DIR/meta.XXXXXX")"

  http_request "${target}${endpoint}" "$body_file" "$headers_file" "$error_file" "$meta_file"
  line="$(cat "$meta_file")"
  IFS=$'\t' read -r status effective content_type size duration remote_ip http_version curl_rc retries <<< "$line"
  status="${status:-000}"; effective="${effective:-${target}${endpoint}}"; content_type="${content_type:-unknown}"
  size="${size:-0}"; duration="${duration:-0}"; remote_ip="${remote_ip:-}"; http_version="${http_version:-}"
  curl_rc="${curl_rc:-0}"; retries="${retries:-0}"; timestamp="$(date -Iseconds)"
  curl_error="$(tr '\n' ' ' < "$error_file" | sed 's/[[:space:]]\+/ /g' | cut -c1-300)"

  local -a scope_args=()
  local rule
  for rule in "${SCOPE_RULES[@]}"; do scope_args+=(--scope "$rule"); done
  analysis="$(python3 "$ROOT_DIR/lib/analyzer.py" \
    --endpoint "$endpoint" --body "$body_file" --headers "$headers_file" \
    --status "$status" --content-type "$content_type" --target "$target" \
    --baseline-body "$baseline_body" --baseline-status "$baseline_status" \
    "${scope_args[@]}")"

  jq -cn \
    --arg timestamp "$timestamp" --arg target "$target" --arg endpoint "$endpoint" \
    --arg status "$status" --arg effective_url "$effective" --arg content_type "$content_type" \
    --arg size_bytes "$size" --arg time_seconds "$duration" --arg remote_ip "$remote_ip" \
    --arg http_version "$http_version" --arg curl_rc "$curl_rc" --arg retries "$retries" \
    --arg curl_error "$curl_error" --arg baseline_status "$baseline_status" \
    --argjson analysis "$analysis" \
    '{timestamp:$timestamp,target:$target,endpoint:$endpoint,status:$status,effective_url:$effective_url,
      content_type:$content_type,size_bytes:($size_bytes|tonumber? // 0),time_seconds:($time_seconds|tonumber? // 0),
      remote_ip:$remote_ip,http_version:$http_version,curl_rc:($curl_rc|tonumber? // 0),retries:($retries|tonumber? // 0),
      curl_error:$curl_error,baseline_status:$baseline_status} + $analysis' > "$result_file"

  rm -f "$body_file" "$headers_file" "$error_file" "$meta_file"
}

run_scan_jobs() {
  local -a targets=("$@")
  local target endpoint job_id=0 running=0 target_dir
  mkdir -p "$WORK_DIR/results" "$WORK_DIR/targets"

  for target in "${targets[@]}"; do
    target_dir="$WORK_DIR/targets/$(safe_filename "$target")-$(random_hex)"
    mkdir -p "$target_dir"
    prepare_baseline "$target" "$target_dir"
    debug "Baseline $target: HTTP $BASELINE_STATUS ($BASELINE_ENDPOINT)"
    rate_sleep

    for endpoint in "${ENDPOINTS[@]}"; do
      job_id=$((job_id + 1))
      scan_one_to_file "$target" "$endpoint" "$BASELINE_BODY" "$BASELINE_STATUS" \
        "$WORK_DIR/results/$(printf '%06d' "$job_id").json" &
      running=$((running + 1))
      if ((running >= CONCURRENCY)); then
        wait -n || true
        running=$((running - 1))
      fi
      rate_sleep
    done
  done
  wait || true
}

consume_results() {
  local idx=0 file
  shopt -s nullglob
  for file in "$WORK_DIR"/results/*.json; do
    idx=$((idx + 1))
    append_json_result "$file"
    [[ "$QUIET" == "true" ]] || print_result_line "$idx" "$file"
  done
  shopt -u nullglob
}
