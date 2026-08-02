#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$ROOT_DIR/lib/common.sh"

MODE="check"
CREATE_LINK=0

usage() {
  cat <<'HELP'
Usage:
  ./install.sh [--check] [--install] [--link]

Options:
  --check     Verify dependencies only. This is the default.
  --install   Install missing packages when supported.
  --link      Create /usr/local/bin/git-exposure-auditor.

Kali Linux uses the package and command name httpx-toolkit for
ProjectDiscovery httpx. The unrelated Python HTTPX CLI is not compatible.
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check"; shift ;;
    --install) MODE="install"; shift ;;
    --link) CREATE_LINK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) gea_fail "Unknown option: $1" ;;
  esac
done

install_core_apt() {
  local sudo_cmd=()
  if [[ "$(id -u)" -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 || gea_fail "sudo is required for apt installation."
    sudo_cmd=(sudo)
  fi
  "${sudo_cmd[@]}" apt-get update
  "${sudo_cmd[@]}" apt-get install -y bash curl jq python3 git unzip ca-certificates golang-go httpx-toolkit
}

missing=()
for command_name in bash curl jq python3; do
  command -v "$command_name" >/dev/null 2>&1 || missing+=("$command_name")
done

if (( ${#missing[@]} > 0 )); then
  if [[ "$MODE" == "install" ]] && command -v apt-get >/dev/null 2>&1; then
    gea_info "Installing core dependencies with apt."
    install_core_apt
  else
    gea_warn "Missing core dependencies: ${missing[*]}"
    gea_warn "Kali/Debian: sudo apt install -y bash curl jq python3 git unzip ca-certificates"
  fi
fi

if ! gea_resolve_httpx; then
  if [[ "$MODE" == "install" ]] && command -v apt-get >/dev/null 2>&1; then
    gea_info "Installing Kali/Debian ProjectDiscovery package: httpx-toolkit"
    install_core_apt
    gea_resolve_httpx || gea_fail "ProjectDiscovery httpx is still unavailable."
  else
    exit 2
  fi
fi

if ! command -v assetfinder >/dev/null 2>&1; then
  if [[ "$MODE" == "install" ]] && command -v go >/dev/null 2>&1; then
    gea_info "Installing assetfinder with Go."
    go install -v github.com/tomnomnom/assetfinder@latest
  else
    gea_warn "assetfinder is optional but recommended for domain discovery."
    gea_warn 'Install: go install -v github.com/tomnomnom/assetfinder@latest'
  fi
fi

if ! command -v anew >/dev/null 2>&1; then
  if [[ "$MODE" == "install" ]] && command -v go >/dev/null 2>&1; then
    gea_info "Installing optional anew utility with Go."
    go install -v github.com/tomnomnom/anew@latest
  else
    gea_warn "anew is optional; v2 has a built-in history workflow."
  fi
fi

chmod +x "$ROOT_DIR/bin/git-exposure-auditor" "$ROOT_DIR/scripts"/*.sh "$ROOT_DIR/lib"/*.py "$ROOT_DIR/tests"/*.sh "$ROOT_DIR/tests"/*.py

if (( CREATE_LINK == 1 )); then
  if [[ "$(id -u)" -eq 0 ]]; then
    ln -sfn "$ROOT_DIR/bin/git-exposure-auditor" /usr/local/bin/git-exposure-auditor
  elif command -v sudo >/dev/null 2>&1; then
    sudo ln -sfn "$ROOT_DIR/bin/git-exposure-auditor" /usr/local/bin/git-exposure-auditor
  else
    gea_fail "Root or sudo is required to create /usr/local/bin/git-exposure-auditor."
  fi
  gea_info "Installed command: /usr/local/bin/git-exposure-auditor"
fi

gea_info "Dependency check completed."
gea_info "Run: ./bin/git-exposure-auditor --help"
