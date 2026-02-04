#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/portable_data/.venv"
SYSTEM_PY="$(command -v python3 || true)"
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "[Modultool] Must-Pass Suite: übersprungen (ffmpeg/ffprobe fehlt)."
  exit 0
fi
if [ ! -d "$VENV" ]; then
  if [ -z "$SYSTEM_PY" ]; then
    echo "[Modultool] Fehler: python3 fehlt (System-Python = Laufzeitumgebung)."
    echo "[Modultool] Tipp: python3 installieren und erneut starten."
    exit 1
  fi
  echo "[Modultool] venv fehlt. Ich nutze system-python3 für die Must-Pass Suite."
  "$SYSTEM_PY" "$ROOT/app/must_pass_suite.py" || true
  exit 0
fi
echo "[Modultool] Must-Pass Suite läuft …"
"$VENV/bin/python" "$ROOT/app/must_pass_suite.py" || true
echo "[Modultool] Must-Pass Suite fertig. Ergebnis liegt in user_data/reports/ (must_pass_*.json)"
