#!/usr/bin/env bash

set -o pipefail

GEA_VERSION="3.1.0-rc1"
GEA_NAME="Git Exposure Auditor"

if [[ -t 1 && "${NO_COLOR:-false}" != "true" ]]; then
  C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'
  C_BLUE='\033[0;34m'; C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_RESET='\033[0m'
else
  C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

log_info()  { [[ "${QUIET:-false}" == "true" ]] || printf "%b[INFO]%b %s\n" "$C_BLUE" "$C_RESET" "$*"; }
log_ok()    { [[ "${QUIET:-false}" == "true" ]] || printf "%b[OK]%b %s\n" "$C_GREEN" "$C_RESET" "$*"; }
log_warn()  { printf "%b[WARN]%b %s\n" "$C_YELLOW" "$C_RESET" "$*" >&2; }
log_error() { printf "%b[ERROR]%b %s\n" "$C_RED" "$C_RESET" "$*" >&2; }
debug()     { [[ "${VERBOSE:-false}" == "true" ]] && printf "%b[DEBUG]%b %s\n" "$C_CYAN" "$C_RESET" "$*" >&2 || true; }
die()       { log_error "$*"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Dependency tidak ditemukan: $1"
}

trim() {
  local value="$*"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

normalize_url() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit, urlunsplit
raw = sys.argv[1].strip()
if not raw:
    raise SystemExit(1)
if not raw.lower().startswith(("http://", "https://")):
    raw = "https://" + raw
p = urlsplit(raw)
if p.scheme not in {"http", "https"} or not p.hostname:
    raise SystemExit(1)
host = p.hostname.encode("idna").decode("ascii").lower()
port = f":{p.port}" if p.port else ""
userinfo = ""
if p.username or p.password:
    raise SystemExit(1)
path = p.path.rstrip("/")
print(urlunsplit((p.scheme.lower(), host + port, path, "", "")))
PY
}

extract_host() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit
raw = sys.argv[1]
if not raw.startswith(("http://", "https://")):
    raw = "https://" + raw
p = urlsplit(raw)
print((p.hostname or "").lower())
PY
}

extract_port() {
  python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit
raw = sys.argv[1]
if not raw.startswith(("http://", "https://")):
    raw = "https://" + raw
p = urlsplit(raw)
print(p.port or "")
PY
}

host_is_ip_literal() {
  python3 - "$1" <<'PY'
import ipaddress, sys
try:
    ipaddress.ip_address(sys.argv[1])
except ValueError:
    raise SystemExit(1)
PY
}

is_private_host() {
  python3 - "$1" <<'PY'
import ipaddress, socket, sys
host = sys.argv[1].strip().strip("[]")
if host == "localhost" or host.endswith(".localhost"):
    raise SystemExit(0)
try:
    ips = [ipaddress.ip_address(host)]
except ValueError:
    try:
        ips = {ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(host, None)}
    except OSError:
        raise SystemExit(1)
for ip in ips:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
        raise SystemExit(0)
raise SystemExit(1)
PY
}

safe_filename() {
  printf '%s' "$1" | sed -E 's#^https?://##; s#[^A-Za-z0-9._-]+#_#g; s#_+$##'
}

random_hex() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(8))
PY
}

print_banner() {
  [[ "${QUIET:-false}" == "true" ]] && return 0
  cat <<EOF_BANNER
${C_CYAN}${C_BOLD}${GEA_NAME} v${GEA_VERSION}${C_RESET}
Safe, signature-aware .git exposure validation
EOF_BANNER
}

legal_notice() {
  [[ "${QUIET:-false}" == "true" ]] && return 0
  cat <<'EOF_NOTICE'
Gunakan hanya pada aset yang tercantum dalam scope program dan mengizinkan pengujian.
Tool tidak melakukan repository dumping, credential testing, bypass autentikasi/WAF,
brute force, eksploitasi, maupun perubahan pada target.
EOF_NOTICE
}
