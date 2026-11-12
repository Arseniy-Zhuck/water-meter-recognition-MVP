#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
usage() {
  cat <<'HELP'
Usage: ./start.sh [--host ADDRESS] [--port PORT] [--cert CERT.pem --key KEY.pem]
  --host, --address ADDRESS  Bind address (default: 0.0.0.0)
  --port PORT                Listen port (default: 8011)
  --cert PATH                TLS certificate with chain (PEM)
  --key PATH                 TLS private key (PEM, no password)
  -h, --help                 Show help
Example:
  ./start.sh --host 0.0.0.0 --port 8443 --cert /etc/ssl/meter/fullchain.pem --key /etc/ssl/meter/privkey.pem
HELP
}
args=()
while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --host|--address|--port|--cert|--key)
      option="$1"
      if (($# < 2)) || [[ -z "$2" || "$2" == --* ]]; then
        echo "Missing value for $option" >&2; exit 2
      fi
      [[ "$option" == --address ]] && option=--host
      args+=("$option" "$2"); shift 2 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
if command -v python3 >/dev/null 2>&1; then
  python=python3
elif command -v python >/dev/null 2>&1; then
  python=python
else
  echo 'Install Python 3.10+ with pip and venv.' >&2; exit 1
fi
exec "$python" "$ROOT/start.py" "${args[@]}"
