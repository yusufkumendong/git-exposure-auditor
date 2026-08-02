#!/usr/bin/env bash

set -Eeuo pipefail

info() { printf '[*] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }
fail() { warn "$*"; exit 1; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/scripts/common.sh"

command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v jq >/dev/null 2>&1 || fail "jq is required."
command -v go >/dev/null 2>&1 || fail "Go is required to install assetfinder and anew."

GOBIN_PATH="$(go env GOBIN 2>/dev/null || true)"
[[ -n "$GOBIN_PATH" ]] || GOBIN_PATH="$(go env GOPATH)/bin"
mkdir -p "$GOBIN_PATH"

if resolve_projectdiscovery_httpx --quiet; then
  info "Existing ProjectDiscovery httpx detected: $HTTPX_BIN"
else
  info "Installing ProjectDiscovery httpx into: $GOBIN_PATH"
  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
  [[ -x "$GOBIN_PATH/httpx" ]] || fail "ProjectDiscovery httpx was not created in $GOBIN_PATH."
  ln -sfn "$GOBIN_PATH/httpx" "$GOBIN_PATH/httpx-pd"
fi

if command -v assetfinder >/dev/null 2>&1; then
  info "Existing assetfinder detected: $(command -v assetfinder)"
else
  info "Installing assetfinder into: $GOBIN_PATH"
  go install -v github.com/tomnomnom/assetfinder@latest
fi

if command -v anew >/dev/null 2>&1; then
  info "Existing anew detected: $(command -v anew)"
else
  info "Installing anew into: $GOBIN_PATH"
  go install -v github.com/tomnomnom/anew@latest
fi

cat <<MESSAGE

Installation completed.

Kali Linux note:
  ProjectDiscovery httpx may be installed as /usr/bin/httpx-toolkit.
  Version 1.0.2 detects httpx-toolkit automatically; no symlink is required.

If Go-installed commands are not found, prepend the Go binary directory:
  export PATH="$GOBIN_PATH:\$PATH"
  hash -r

Kali normally uses Zsh. To persist the path:
  echo 'export PATH="$GOBIN_PATH:\$PATH"' >> ~/.zshrc
  source ~/.zshrc

Verify:
  httpx-toolkit -version  # Kali package, when installed
  "$GOBIN_PATH/httpx" -version  # Go installation, when installed
  assetfinder --help
  anew -h

Run with an explicit binary when needed:
  HTTPX_BIN=/usr/bin/httpx-toolkit ./scripts/hard.sh example.com
MESSAGE
