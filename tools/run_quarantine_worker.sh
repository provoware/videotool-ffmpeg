#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/portable_data/.venv"
JOB_ID="${1:-}"
if [ ! -d "$VENV" ]; then
  echo "[Modultool] venv fehlt. Bitte zuerst tools/start.sh einmal ausführen."
  exit 1
fi
echo "[Modultool] Quarantäne-Worker startet …"
if [ -n "$JOB_ID" ]; then
  "$VENV/bin/python" "$ROOT/app/quarantine_worker.py" --job-id "$JOB_ID"
else
  "$VENV/bin/python" "$ROOT/app/quarantine_worker.py"
fi
echo "[Modultool] Quarantäne-Worker beendet."
