#!/usr/bin/env bash

header_last_value() {
  local file="$1" name="$2"
  awk -v key="${name,,}" '
    BEGIN{IGNORECASE=1}
    index(tolower($0), key ":")==1 {
      sub(/^[^:]+:[[:space:]]*/, "", $0); sub(/\r$/, "", $0); value=$0
    }
    END{print value}
  ' "$file"
}

http_request() {
  local url="$1" body_file="$2" headers_file="$3" error_file="$4" meta_file="$5"
  local attempt=0 delay="$RETRY_DELAY" meta curl_rc status retry_after sleep_for
  local -a args=(
    --silent --show-error --compressed --path-as-is --max-redirs 0
    --connect-timeout "$CONNECT_TIMEOUT" --max-time "$MAX_TIME"
    --max-filesize "$MAX_BODY_BYTES"
    --user-agent "$USER_AGENT"
    --dump-header "$headers_file" --output "$body_file"
    --write-out $'%{http_code}\t%{url_effective}\t%{content_type}\t%{size_download}\t%{time_total}\t%{remote_ip}\t%{http_version}'
    --proto '=http,https'
  )

  [[ "$INSECURE" == "true" ]] && args+=(--insecure)
  [[ -n "$PROXY_URL" ]] && args+=(--proxy "$PROXY_URL")
  case "$HTTP_VERSION" in
    auto) ;;
    1.1) args+=(--http1.1) ;;
    2) args+=(--http2) ;;
  esac
  local h
  for h in "${CUSTOM_HEADERS[@]}"; do args+=(--header "$h"); done

  while :; do
    : > "$body_file"; : > "$headers_file"; : > "$error_file"
    set +e
    meta="$(curl "${args[@]}" "$url" 2>"$error_file")"
    curl_rc=$?
    set -e
    status="${meta%%$'\t'*}"
    status="${status:-000}"

    if ((attempt >= RETRIES)); then break; fi
    if [[ "$status" != "000" && ! "$status" =~ ^(429|502|503|504)$ ]]; then break; fi

    retry_after="$(header_last_value "$headers_file" "Retry-After")"
    sleep_for="$delay"
    if [[ "$RESPECT_RETRY_AFTER" == "true" && "$retry_after" =~ ^[0-9]+$ ]]; then
      ((retry_after <= RETRY_MAX_DELAY)) && sleep_for="$retry_after"
    fi
    debug "Retry $((attempt + 1))/$RETRIES untuk $url setelah ${sleep_for}s (HTTP $status, curl $curl_rc)"
    python3 - "$sleep_for" <<'PY'
import sys,time
time.sleep(max(0.0, float(sys.argv[1])))
PY
    attempt=$((attempt + 1))
    delay="$(python3 - "$delay" "$RETRY_MAX_DELAY" <<'PY'
import sys
print(min(float(sys.argv[1]) * 2, float(sys.argv[2])))
PY
)"
  done

  printf '%s\t%s\t%s\n' "$meta" "$curl_rc" "$attempt" > "$meta_file"
}
