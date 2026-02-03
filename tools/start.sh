#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT/app"
VENV_DIR="$ROOT/portable_data/.venv"

echo "[Modultool] Start – Video-Werkstatt (Portable)"

command -v python3 >/dev/null 2>&1 || { echo "Python3 fehlt. Bitte installieren."; exit 1; }

if [ ! -d "$VENV_DIR" ]; then
  echo "[Modultool] Python-Umgebung wird erstellt …"
  python3 -m venv "$VENV_DIR"
fi

echo "[Modultool] Abhängigkeiten prüfen …"
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

echo "[Modultool] Werkstatt-Aufräumen …"
# Maintenance (Logs/Cache/Temp) – best effort
"$VENV_DIR/bin/python" "$ROOT/app/maintenance.py" --auto >/dev/null 2>&1 || true

echo "[Modultool] GUI startet …"
exec "$VENV_DIR/bin/python" "$APP_DIR/main.py"
