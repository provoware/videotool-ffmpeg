#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/portable_data/.venv"
if [ ! -d "$VENV" ]; then
  echo "[Modultool] venv fehlt. Bitte zuerst tools/start.sh einmal ausführen."
  exit 1
fi
echo "[Modultool] Selftest startet (0.9.2) …"
"$VENV/bin/python" "$ROOT/app/selftest_runner.py"
echo "[Modultool] Selftest beendet."
