#!/usr/bin/env bash

set -Eeuo pipefail

info() { printf '[*] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }
fail() { warn "$*"; exit 1; }

command -v go >/dev/null 2>&1 || fail "Go is required. Install Go, then run this script again."
command -v curl >/dev/null 2>&1 || fail "curl is required."
command -v jq >/dev/null 2>&1 || fail "jq is required."

info "Installing Go-based dependencies into: $(go env GOPATH)/bin"
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/tomnomnom/anew@latest

GOBIN_PATH="$(go env GOPATH)/bin"

cat <<MESSAGE

Installation completed.

Add the Go binary directory to your PATH when necessary:

  export PATH="\$PATH:$GOBIN_PATH"

To make it persistent in Bash:

  echo 'export PATH="\$PATH:$GOBIN_PATH"' >> ~/.bashrc
  source ~/.bashrc

Verify the installation:

  httpx -version
  assetfinder --help
  anew -h
MESSAGE
