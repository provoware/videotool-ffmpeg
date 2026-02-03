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
if ! "$VENV_DIR/bin/python" -m pip install -r "$APP_DIR/requirements.txt"; then
  echo "[Modultool] Fehler: Abhängigkeiten (Dependencies = Zusatzpakete) konnten nicht installiert werden."
  echo "[Modultool] Tipp: Internet prüfen, dann erneut starten."
  exit 1
fi

echo "[Modultool] Werkstatt-Check (Startprüfung) …"
if PREFLIGHT_JSON=$("$VENV_DIR/bin/python" "$ROOT/app/preflight.py" --json 2>/dev/null); then
  echo "$PREFLIGHT_JSON" | "$VENV_DIR/bin/python" - <<'PY'
import json
import sys

data = json.load(sys.stdin)
overall_ok = bool(data.get("overall_ok", False))
if overall_ok:
    print("[Modultool] Werkstatt-Check: Alles bereit.")
else:
    print("[Modultool] Werkstatt-Check: Bitte prüfen.")
    recs = data.get("recommendations") or []
    rec_map = {
        "ffmpeg_install": "FFmpeg (Video-Werkzeug) installieren.",
        "set_watchfolder": "Watchfolder (Eingangsordner) wählen.",
        "free_space": "Speicher frei machen (nicht benötigte Dateien löschen).",
        "install_font": "Schrift (Font) installieren, z.B. DejaVuSans."
    }
    if recs:
        print("[Modultool] Nächste Schritte:")
        for rec in recs:
            print(f" - {rec_map.get(rec, rec)}")
PY
else
  echo "[Modultool] Werkstatt-Check: fehlgeschlagen (weiter mit Standardstart)."
fi

echo "[Modultool] Werkstatt-Aufräumen …"
# Maintenance (Logs/Cache/Temp) – best effort
"$VENV_DIR/bin/python" "$ROOT/app/maintenance.py" --auto >/dev/null 2>&1 || true

echo "[Modultool] GUI startet …"
exec "$VENV_DIR/bin/python" "$APP_DIR/main.py"
