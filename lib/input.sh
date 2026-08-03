#!/usr/bin/env bash

TARGET_INPUTS=()
DOMAIN_INPUTS=()
SUBDOMAIN_INPUTS=()
WILDCARD_INPUTS=()
DISCOVERED_HOSTS=()

add_csv_values() {
  local destination="$1" raw="$2" value
  local -n destination_ref="$destination"
  IFS=',' read -r -a _values <<< "$raw"
  for value in "${_values[@]}"; do
    value="$(trim "$value")"
    [[ -n "$value" ]] || continue
    destination_ref+=("$value")
  done
}

sanitize_host_input() {
  local raw="$1"
  raw="$(trim "$raw")"
  raw="${raw#http://}"; raw="${raw#https://}"; raw="${raw%%/*}"
  printf '%s' "${raw,,}"
}

wildcard_root() {
  local raw
  raw="$(sanitize_host_input "$1")"
  raw="${raw#*.}"
  printf '%s' "$raw"
}

discover_with_subfinder() {
  local root="$1"
  subfinder -silent -d "$root" 2>/dev/null || true
}

discover_with_crtsh() {
  local root="$1"
  curl --silent --show-error --fail --compressed --max-time 30 \
    --user-agent "$USER_AGENT" \
    "https://crt.sh/?q=%25.${root}&output=json" 2>/dev/null |
    jq -r '.[].name_value? // empty' 2>/dev/null |
    tr '\r' '\n' |
    sed 's/^\*\.//' |
    awk 'NF'
}

discover_wildcard_hosts() {
  local wildcard="$1" root method="$ENUMERATOR"
  root="$(wildcard_root "$wildcard")"
  [[ -n "$root" ]] || return 0

  printf '%s\n' "$root"
  case "$method" in
    auto)
      if command -v subfinder >/dev/null 2>&1; then
        debug "Enumerasi pasif wildcard $root menggunakan subfinder"
        discover_with_subfinder "$root"
      else
        debug "subfinder tidak tersedia; fallback ke crt.sh untuk $root"
        discover_with_crtsh "$root"
      fi
      ;;
    subfinder)
      require_cmd subfinder
      discover_with_subfinder "$root"
      ;;
    crtsh)
      discover_with_crtsh "$root"
      ;;
    none)
      ;;
    *) die "Enumerator tidak valid: $method" ;;
  esac
}

build_target_urls() {
  local raw normalized host wildcard discovered count=0
  local -a candidates=()

  candidates+=("${TARGET_INPUTS[@]}")

  for raw in "${DOMAIN_INPUTS[@]}"; do
    raw="$(sanitize_host_input "$raw")"
    [[ -n "$raw" ]] || continue
    add_scope_rule "$raw"
    candidates+=("$raw")
  done

  for raw in "${SUBDOMAIN_INPUTS[@]}"; do
    raw="$(sanitize_host_input "$raw")"
    [[ -n "$raw" ]] || continue
    add_scope_rule "$raw"
    candidates+=("$raw")
  done

  for wildcard in "${WILDCARD_INPUTS[@]}"; do
    wildcard="$(sanitize_host_input "$wildcard")"
    wildcard="*.${wildcard#*.}"
    add_scope_rule "$wildcard"
    if [[ "$DISCOVER_WILDCARDS" == "true" ]]; then
      while IFS= read -r discovered; do
        discovered="$(sanitize_host_input "$discovered")"
        [[ -n "$discovered" ]] || continue
        host_in_scope "$discovered" || continue
        candidates+=("$discovered")
        count=$((count + 1))
        ((count >= MAX_DISCOVERED)) && break
      done < <(discover_wildcard_hosts "$wildcard")
    else
      candidates+=("$(wildcard_root "$wildcard")")
    fi
  done

  for raw in "${TARGET_INPUTS[@]}"; do
    normalized="$(normalize_url "$raw")" || continue
    host="$(extract_host "$normalized")"
    [[ -n "$host" ]] && add_scope_rule "$host"
  done

  if [[ -n "${TARGET_LIST:-}" ]]; then
    [[ -f "$TARGET_LIST" ]] || die "File target tidak ditemukan: $TARGET_LIST"
    while IFS= read -r raw; do
      raw="$(trim "$raw")"
      [[ -z "$raw" || "$raw" == \#* ]] && continue
      candidates+=("$raw")
    done < "$TARGET_LIST"
  fi

  TARGETS=()
  declare -A seen=()
  for raw in "${candidates[@]}"; do
    if [[ "$raw" != http://* && "$raw" != https://* ]]; then
      case "$SCHEME_MODE" in
        http) raw="http://$raw" ;;
        https|both) raw="https://$raw" ;;
      esac
    fi
    normalized="$(normalize_url "$raw")" || { log_warn "Input target tidak valid: $raw"; continue; }
    host="$(extract_host "$normalized")"
    [[ -n "$host" ]] || continue

    if ((${#SCOPE_RULES[@]} > 0)) && ! host_in_scope "$host"; then
      log_warn "Di luar scope, dilewati: $normalized"
      continue
    fi

    if is_private_host "$host" && [[ "$ALLOW_PRIVATE" != "true" ]]; then
      log_warn "Target private/localhost dilewati: $normalized"
      continue
    fi

    if [[ "$SCHEME_MODE" == "both" && "$normalized" != *"://"* ]]; then
      :
    fi

    if [[ -z "${seen[$normalized]+x}" ]]; then
      TARGETS+=("$normalized")
      seen[$normalized]=1
    fi

    if [[ "$SCHEME_MODE" == "both" && "$normalized" == https://* ]]; then
      local_http="http://${normalized#https://}"
      if [[ -z "${seen[$local_http]+x}" ]]; then
        TARGETS+=("$local_http")
        seen[$local_http]=1
      fi
    fi
  done
}
