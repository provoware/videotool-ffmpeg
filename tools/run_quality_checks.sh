#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT/portable_data/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[Modultool] Fehler: python3 fehlt."
  exit 1
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "[Modultool] Fehler: rg (ripgrep) fehlt."
  exit 1
fi

echo "[Modultool] Qualitäts-Checks starten …"

if [ ! -d "$VENV_DIR" ]; then
  echo "[Modultool] Python-Umgebung fehlt. Erstelle venv …"
  python3 -m venv "$VENV_DIR"
fi

echo "[Modultool] Abhängigkeiten für Checks installieren …"
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
"$PYTHON_BIN" -m pip install -r "$ROOT/app/requirements.txt" >/dev/null
if [ -f "$ROOT/app/requirements-dev.txt" ]; then
  "$PYTHON_BIN" -m pip install -r "$ROOT/app/requirements-dev.txt" >/dev/null
fi

"$PYTHON_BIN" -m py_compile "$ROOT"/app/*.py

bash -n "$ROOT"/tools/*.sh

echo "[Modultool] Marker-Scan (keine Markerwörter) …"
marker_regex='TO'"DO|FI"'XME|place'"holder|Platz"'halter'
if rg -n --glob 'app/*.py' --glob 'tools/*.sh' -e "$marker_regex" "$ROOT"; then
  echo "[Modultool] Fehler: Marker gefunden."
  exit 1
fi

echo "[Modultool] Marker-Scan: ok"

echo "[Modultool] Format-Check (Formatprüfung) …"
"$PYTHON_BIN" -m ruff check "$ROOT/app"
"$PYTHON_BIN" -m ruff format --check "$ROOT/app"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[Modultool] Must-Pass Suite …"
  "$ROOT"/tools/run_must_pass.sh
else
  echo "[Modultool] Must-Pass Suite: übersprungen (ffmpeg fehlt)."
fi

echo "[Modultool] Qualitäts-Checks abgeschlossen."
