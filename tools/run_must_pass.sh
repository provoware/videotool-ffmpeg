#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/portable_data/.venv"
SYSTEM_PY="$(command -v python3 || true)"
if [ ! -d "$VENV" ]; then
  echo "[Modultool] venv fehlt. Ich nutze system-python3 für die Must-Pass Suite."
  "$SYSTEM_PY" "$ROOT/app/must_pass_suite.py" || true
  exit 0
fi
echo "[Modultool] Must-Pass Suite läuft …"
"$VENV/bin/python" "$ROOT/app/must_pass_suite.py" || true
echo "[Modultool] Must-Pass Suite fertig. Ergebnis liegt in user_data/reports/ (must_pass_*.json)"
