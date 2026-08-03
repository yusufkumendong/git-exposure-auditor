#!/usr/bin/env bash

SCOPE_RULES=()

add_scope_rule() {
  local rule
  rule="$(python3 - "$1" <<'PY'
import sys
from urllib.parse import urlsplit
raw=sys.argv[1].strip().lower()
if not raw:
    raise SystemExit(0)
if raw.startswith("*."):
    print("*." + raw[2:].split("/",1)[0].split(":",1)[0])
elif raw.startswith(("http://","https://")):
    print((urlsplit(raw).hostname or "").lower())
elif raw.startswith("[") and "]" in raw:
    print(raw[1:raw.index("]")])
elif raw.count(":") > 1:
    print(raw)
else:
    print(raw.split("/",1)[0].split(":",1)[0])
PY
)"
  [[ -n "$rule" ]] || return 0
  SCOPE_RULES+=("$rule")
}

load_scope_rules() {
  local file="$1" line
  [[ -f "$file" ]] || die "File scope tidak ditemukan: $file"
  while IFS= read -r line; do
    line="$(trim "$line")"
    [[ -z "$line" || "$line" == \#* ]] && continue
    add_scope_rule "$line"
  done < "$file"
}

host_in_scope() {
  local host="${1,,}" rule suffix
  for rule in "${SCOPE_RULES[@]}"; do
    if [[ "$rule" == \*.* ]]; then
      suffix="${rule#*.}"
      [[ "$host" == "$suffix" || "$host" == *."$suffix" ]] && return 0
    elif [[ "$host" == "$rule" ]]; then
      return 0
    fi
  done
  return 1
}

scope_summary() {
  printf '%s\n' "${SCOPE_RULES[@]}" | awk 'NF && !seen[$0]++'
}
