#!/usr/bin/env bash

# Shared helpers for Git Exposure Auditor v2.

gea_info() { printf '[*] %s\n' "$*"; }
gea_warn() { printf '[!] %s\n' "$*" >&2; }
gea_fail() { gea_warn "$*"; exit "${2:-2}"; }

gea_is_uint() {
  [[ "${1:-}" =~ ^[0-9]+$ ]]
}

gea_require_range() {
  local name="${1:-value}" value="${2:-}" minimum="${3:-1}" maximum="${4:-1}"
  gea_is_uint "$value" && (( value >= minimum && value <= maximum )) || {
    gea_fail "$name must be an integer from $minimum to $maximum."
  }
}

gea_is_projectdiscovery_httpx() {
  local binary="${1:-}" help_text
  [[ -n "$binary" && -x "$binary" ]] || return 1
  help_text="$("$binary" -h 2>&1 || true)"
  grep -q -- '-l, -list' <<< "$help_text" && \
    grep -Eq -- '(-j, -json|-json)' <<< "$help_text" && \
    grep -q -- '-path' <<< "$help_text"
}

gea_httpx_supports() {
  local binary="${1:-}" pattern="${2:-}" help_text
  [[ -n "$binary" && -n "$pattern" ]] || return 1
  help_text="$("$binary" -h 2>&1 || true)"
  grep -q -- "$pattern" <<< "$help_text"
}

gea_resolve_httpx() {
  local candidate resolved gobin gopath
  local -a candidates=()
  local -A seen=()

  [[ -n "${HTTPX_BIN:-}" ]] && candidates+=("$HTTPX_BIN")
  candidates+=("httpx-pd" "httpx-toolkit" "$HOME/go/bin/httpx")

  if command -v go >/dev/null 2>&1; then
    gobin="$(go env GOBIN 2>/dev/null || true)"
    gopath="$(go env GOPATH 2>/dev/null || true)"
    [[ -n "$gobin" ]] && candidates+=("$gobin/httpx")
    [[ -n "$gopath" ]] && candidates+=("$gopath/bin/httpx")
  fi

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

    if gea_is_projectdiscovery_httpx "$resolved"; then
      HTTPX_BIN="$resolved"
      export HTTPX_BIN
      gea_info "Using ProjectDiscovery httpx: $HTTPX_BIN"
      return 0
    fi
  done

  cat >&2 <<'MESSAGE'
[!] ProjectDiscovery httpx was not found.
[!] The unrelated Python HTTPX CLI may be installed as /usr/bin/httpx.

Kali Linux:
  sudo apt update
  sudo apt install -y httpx-toolkit
  httpx-toolkit -version

Generic Go installation:
  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
  export PATH="$(go env GOPATH)/bin:$PATH"
  hash -r

Explicit selection:
  HTTPX_BIN=/usr/bin/httpx-toolkit ./bin/git-exposure-auditor ...
MESSAGE
  return 1
}

gea_fetch_crtsh_names() {
  local domain="${1:-}" output_file="${2:-}" error_log="${3:-/dev/null}"
  local response_file max_time retries

  [[ -n "$domain" && -n "$output_file" ]] || return 2
  response_file="$(mktemp)"
  max_time="${CRT_MAX_TIME:-90}"
  retries="${CRT_RETRIES:-1}"
  : > "$output_file"
  : > "$error_log"

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
    --user-agent 'git-exposure-auditor/2.0.0' \
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

gea_sha256_file() {
  local file="${1:-}"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  else
    shasum -a 256 "$file" | awk '{print $1}'
  fi
}

gea_join_by() {
  local delimiter="${1:-}"; shift || true
  local first=1 item
  for item in "$@"; do
    if (( first )); then
      printf '%s' "$item"
      first=0
    else
      printf '%s%s' "$delimiter" "$item"
    fi
  done
}
