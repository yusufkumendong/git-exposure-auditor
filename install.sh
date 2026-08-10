#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for cmd in bash curl python3; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Dependency belum terpasang: $cmd" >&2
    echo "Debian/Kali/Ubuntu: sudo apt update && sudo apt install -y bash curl python3" >&2
    echo "RHEL/Alma/Rocky: sudo dnf install -y bash curl python3" >&2
    exit 1
  }
done
chmod +x "$ROOT_DIR/bin/gea" "$ROOT_DIR/scripts/"*.sh "$ROOT_DIR/tests/"*.sh "$ROOT_DIR/tests/unit.py"
python3 -m py_compile "$ROOT_DIR"/gea/*.py
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  ln -sfn "$ROOT_DIR/bin/gea" /usr/local/bin/gea
  echo "Installed: /usr/local/bin/gea"
else
  echo "Dependencies OK. Jalankan: $ROOT_DIR/bin/gea"
  echo "Opsional: sudo ln -sfn '$ROOT_DIR/bin/gea' /usr/local/bin/gea"
fi
