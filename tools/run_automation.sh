#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/portable_data/.venv"
if [ ! -d "$VENV" ]; then
  echo "[Modultool] venv fehlt. Bitte zuerst tools/start.sh einmal ausführen."
  exit 1
fi
echo "[Modultool] Automatik startet (CLI) …"
"$VENV/bin/python" "$ROOT/app/automation_runner.py"
echo "[Modultool] Automatik beendet."

# Maintenance (best effort)
"$VENV/bin/python" "$ROOT/app/maintenance.py" --auto >/dev/null 2>&1 || true
