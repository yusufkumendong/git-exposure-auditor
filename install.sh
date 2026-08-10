#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for cmd in bash curl; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Dependency belum terpasang: $cmd" >&2
    echo "Debian/Kali/Ubuntu: sudo apt update && sudo apt install -y bash curl" >&2
    echo "RHEL/Alma: sudo dnf install -y bash curl" >&2
    echo "Rocky 9 minimal/container: sudo dnf install -y bash curl-minimal" >&2
    exit 1
  }
done

python_ok() {
  local candidate="$1"
  command -v "$candidate" >/dev/null 2>&1 || return 1
  "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

PYTHON_BIN=""
for candidate in "${GEA_PYTHON:-}" python3 python3.13 python3.12 python3.11 python3.10; do
  [[ -n "$candidate" ]] || continue
  if python_ok "$candidate"; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "Dependency belum terpenuhi: Python >= 3.10." >&2
  echo "Debian/Ubuntu/Kali: instal Python 3.10+ dari repository distro." >&2
  echo "Rocky Linux 9/RHEL 9: sudo dnf install -y python3.11" >&2
  exit 1
fi

chmod +x "$ROOT_DIR/bin/gea" "$ROOT_DIR/scripts/"*.sh "$ROOT_DIR/tests/"*.sh "$ROOT_DIR/tests/unit.py"
GEA_PYTHON="$PYTHON_BIN" "$ROOT_DIR/bin/gea" --version >/dev/null
"$PYTHON_BIN" -m py_compile "$ROOT_DIR"/gea/*.py

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  INSTALL_ROOT="${GEA_INSTALL_ROOT:-/usr/local/lib/git-exposure-auditor}"
  BIN_LINK="${GEA_BIN_LINK:-/usr/local/bin/gea}"

  mkdir -p "$INSTALL_ROOT" "$(dirname "$BIN_LINK")"
  rm -rf "$INSTALL_ROOT/gea" "$INSTALL_ROOT/bin"
  cp -a "$ROOT_DIR/gea" "$INSTALL_ROOT/gea"
  cp -a "$ROOT_DIR/bin" "$INSTALL_ROOT/bin"
  cp -a "$ROOT_DIR/VERSION" "$INSTALL_ROOT/VERSION"
  chmod +x "$INSTALL_ROOT/bin/gea"
  ln -sfn "$INSTALL_ROOT/bin/gea" "$BIN_LINK"

  GEA_PYTHON="$PYTHON_BIN" "$BIN_LINK" --version >/dev/null
  echo "Installed runtime: $INSTALL_ROOT"
  echo "Installed command: $BIN_LINK"
else
  echo "Dependencies OK (Python: $PYTHON_BIN). Jalankan: $ROOT_DIR/bin/gea"
  echo "Untuk instal global: sudo ./install.sh"
fi
