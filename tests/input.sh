#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/lib/common.sh"
source "$ROOT_DIR/lib/scope.sh"
source "$ROOT_DIR/lib/input.sh"
USER_AGENT="test"; ENUMERATOR=none; DISCOVER_WILDCARDS=false; MAX_DISCOVERED=10; ALLOW_PRIVATE=true; TARGET_LIST=""; SCHEME_MODE=https
add_csv_values DOMAIN_INPUTS "example.com,example.org"
add_csv_values SUBDOMAIN_INPUTS "api.example.com"
add_csv_values WILDCARD_INPUTS "*.example.net"
build_target_urls
[[ " ${TARGETS[*]} " == *" https://example.com "* ]]
[[ " ${TARGETS[*]} " == *" https://api.example.com "* ]]
host_in_scope "foo.example.net"
echo "Input test: PASS"
