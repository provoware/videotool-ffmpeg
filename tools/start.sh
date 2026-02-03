#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT/app"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"
AUTO_INSTALL="${MODULTOOL_AUTO_INSTALL:-0}"

echo "[Modultool] Start – Video-Werkstatt (Portable)"
if [ "$DEBUG_MODE" = "1" ]; then
  echo "[Modultool] Debug-Modus aktiv (mehr Details im Log)."
fi

echo "[Modultool] Abhängigkeiten prüfen …"
"$ROOT/tools/bootstrap_python_env.sh"
VENV_DIR="$ROOT/portable_data/.venv"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "[Modultool] Hinweis: FFmpeg fehlt (Video-Werkzeug)."
  if [ "$AUTO_INSTALL" = "1" ]; then
    echo "[Modultool] Starte Systemeinrichtung (kann Admin-Rechte brauchen) …"
    if ! "$ROOT/tools/setup_system.sh"; then
      echo "[Modultool] Fehler: FFmpeg-Installation fehlgeschlagen."
    fi
  else
    echo "[Modultool] Tipp: Starte \"tools/setup_system.sh\" oder setze MODULTOOL_AUTO_INSTALL=1."
  fi
fi

echo "[Modultool] Werkstatt-Check (Startprüfung) …"
if [ "$DEBUG_MODE" = "1" ]; then
  if PREFLIGHT_JSON=$("$VENV_DIR/bin/python" "$ROOT/app/preflight.py" --json); then
    :
  else
    PREFLIGHT_JSON=""
  fi
else
  if PREFLIGHT_JSON=$("$VENV_DIR/bin/python" "$ROOT/app/preflight.py" --json 2>/dev/null); then
    :
  else
    PREFLIGHT_JSON=""
  fi
fi
if [ -n "${PREFLIGHT_JSON:-}" ]; then
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
