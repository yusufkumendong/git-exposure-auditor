#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for cmd in bash curl jq python3; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Dependency belum terpasang: $cmd" >&2
    echo "Debian/Kali/Ubuntu: sudo apt update && sudo apt install -y bash curl jq python3" >&2
    echo "RHEL/Alma/Rocky: sudo dnf install -y bash curl jq python3" >&2
    exit 1
  }
done

chmod +x \
  "$ROOT_DIR/bin/gea" \
  "$ROOT_DIR/scripts/"*.sh \
  "$ROOT_DIR/tests/"*.sh \
  "$ROOT_DIR/lib/analyzer.py"

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  cat > /usr/local/bin/gea <<EOF_WRAPPER
#!/usr/bin/env bash
exec "$ROOT_DIR/bin/gea" "\$@"
EOF_WRAPPER

  chmod +x /usr/local/bin/gea
  echo "Installed: /usr/local/bin/gea"
else
  echo "Dependencies OK."
  echo "Jalankan langsung: $ROOT_DIR/bin/gea"
  echo "Untuk instalasi global, jalankan: sudo ./install.sh"
fi