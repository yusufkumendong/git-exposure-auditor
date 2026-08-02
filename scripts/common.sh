#!/usr/bin/env bash

# Shared dependency and passive-source helpers for Git Exposure Auditor.

is_projectdiscovery_httpx() {
  local binary="${1:-}"
  local help_text

  [[ -n "$binary" && -x "$binary" ]] || return 1

  help_text="$("$binary" -h 2>&1 || true)"
  grep -q -- '-l, -list' <<< "$help_text" && \
    grep -q -- '-mdc, -match-condition' <<< "$help_text"
}

resolve_projectdiscovery_httpx() {
  local mode="${1:-}"
  local candidate resolved gobin gopath
  local -a candidates=()
  local -A seen=()

  # Explicit operator choice always receives the highest priority.
  [[ -n "${HTTPX_BIN:-}" ]] && candidates+=("$HTTPX_BIN")

  # Distinct names avoid the common collision with the Python HTTPX CLI.
  candidates+=("httpx-pd" "httpx-toolkit")

  # Common Go installation locations.
  candidates+=("$HOME/go/bin/httpx")
  if command -v go >/dev/null 2>&1; then
    gobin="$(go env GOBIN 2>/dev/null || true)"
    gopath="$(go env GOPATH 2>/dev/null || true)"
    [[ -n "$gobin" ]] && candidates+=("$gobin/httpx")
    [[ -n "$gopath" ]] && candidates+=("$gopath/bin/httpx")
  fi

  # Last fallback: a command literally named httpx. It is accepted only
  # after its flags prove that it is ProjectDiscovery httpx.
  candidates+=("httpx")

  for candidate in "${candidates[@]}"; do
    [[ -n "$candidate" ]] || continue
    [[ -z "${seen[$candidate]:-}" ]] || continue
    seen["$candidate"]=1

    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      resolved="$candidate"
    else
      resolved="$(command -v "$candidate" 2>/dev/null || true)"
      [[ -n "$resolved" ]] || continue
    fi

    if is_projectdiscovery_httpx "$resolved"; then
      HTTPX_BIN="$resolved"
      export HTTPX_BIN
      if [[ "$mode" != "--quiet" ]]; then
        printf '[*] Using ProjectDiscovery httpx: %s\n' "$HTTPX_BIN"
      fi
      return 0
    fi
  done

  if [[ "$mode" != "--quiet" ]]; then
    cat >&2 <<'MESSAGE'
[!] ProjectDiscovery httpx was not found.
[!] A different program named "httpx" may be installed, commonly Python HTTPX.

Kali Linux:
  sudo apt update
  sudo apt install -y httpx-toolkit
  httpx-toolkit -version

Generic Go installation:
  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
  export PATH="$(go env GOPATH)/bin:$PATH"
  hash -r

The toolkit automatically checks these names and locations:
  HTTPX_BIN, httpx-pd, httpx-toolkit, Go bin directories, then httpx

You may also select the binary explicitly:
  HTTPX_BIN="$(command -v httpx-toolkit)" ./scripts/hard.sh example.com
MESSAGE
  fi
  return 1
}

fetch_crtsh_names() {
  local domain="${1:-}"
  local output_file="${2:-}"
  local error_log="${3:-/dev/null}"
  local response_file max_time retries

  [[ -n "$domain" && -n "$output_file" ]] || return 2

  response_file="$(mktemp)"
  max_time="${CRT_MAX_TIME:-90}"
  retries="${CRT_RETRIES:-1}"
  : > "$output_file"
  : > "$error_log"

  # Download first, parse second. This prevents a timed-out or truncated JSON
  # response from being streamed into jq and producing misleading parse errors.
  if ! curl \
    --fail \
    --silent \
    --show-error \
    --compressed \
    --get \
    --connect-timeout 10 \
    --max-time "$max_time" \
    --retry "$retries" \
    --retry-delay 2 \
    --retry-connrefused \
    --user-agent 'git-exposure-auditor/1.0.2' \
    --data-urlencode "q=%.$domain" \
    --data-urlencode 'output=json' \
    --output "$response_file" \
    'https://crt.sh/' \
    2>"$error_log"; then
    rm -f "$response_file"
    return 1
  fi

  if ! jq -e 'type == "array"' "$response_file" >/dev/null 2>>"$error_log"; then
    printf '%s\n' 'crt.sh returned data that was not a valid JSON array.' >> "$error_log"
    rm -f "$response_file"
    return 1
  fi

  if ! jq -r '.[].name_value? // empty | split("\n")[]' \
    "$response_file" > "$output_file" 2>>"$error_log"; then
    rm -f "$response_file"
    return 1
  fi

  rm -f "$response_file"
  return 0
}
