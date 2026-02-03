#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT/app"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"
AUTO_INSTALL="${MODULTOOL_AUTO_INSTALL:-0}"
RUN_CHECKS="${MODULTOOL_RUN_CHECKS:-0}"
LOG_DIR="$ROOT/portable_data/logs"
LOG_FILE=""

if mkdir -p "$LOG_DIR" 2>/dev/null; then
  LOG_FILE="$LOG_DIR/start_last.log"
fi

if [ -n "$LOG_FILE" ]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

echo "[Modultool] Start – Video-Werkstatt (Portable)"
if [ "$DEBUG_MODE" = "1" ]; then
  echo "[Modultool] Debug-Modus aktiv (mehr Details im Log)."
fi
if [ -n "$LOG_FILE" ]; then
  echo "[Modultool] Start-Log: $LOG_FILE"
fi

echo "[Modultool] Abhängigkeiten prüfen …"
"$ROOT/tools/bootstrap_python_env.sh"
VENV_DIR="$ROOT/portable_data/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[Modultool] Fehler: Python-Umgebung fehlt oder ist defekt."
  echo "[Modultool] Tipp: Lösche $VENV_DIR und starte erneut."
  echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
  exit 1
fi

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

if [ "$RUN_CHECKS" = "1" ]; then
  echo "[Modultool] Release-Checks (automatische Prüfung) …"
  if "$ROOT/tools/run_quality_checks.sh"; then
    echo "[Modultool] Release-Checks: ok."
  else
    echo "[Modultool] Release-Checks: Fehler."
    echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
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
if [ -n "${PREFLIGHT_JSON:-}" ] && [ -n "${PREFLIGHT_JSON//[[:space:]]/}" ]; then
  echo "$PREFLIGHT_JSON" | "$VENV_DIR/bin/python" - <<'PY'
import json
import sys

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print("[Modultool] Werkstatt-Check: Ergebnis unlesbar (JSON = strukturierte Textdaten).")
    print("[Modultool] Tipp: Befehl: MODULTOOL_DEBUG=1 tools/start.sh")
    print("[Modultool] Tipp: Befehl: ./portable_data/.venv/bin/python app/preflight.py --json")
    sys.exit(0)
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
        "install_font": "Schrift (Font) installieren, z.B. DejaVuSans.",
        "watchfolder_not_writable": "Watchfolder (Eingangsordner) braucht Schreibrechte (Rechte prüfen).",
        "watchfolder_invalid": "Watchfolder-Eingabe prüfen und gültigen Ordner wählen.",
        "min_free_mb_invalid": "Mindest-Speicher (min_free_mb) als Zahl setzen (z.B. 2048).",
        "settings_schema_invalid": "Einstellungen prüfen (Eingaben müssen zum Schema passen).",
        "settings_paths_invalid": "Einstellungen prüfen (Pfade müssen gültig sein).",
        "theme_invalid": "Theme prüfen und ein verfügbares Theme auswählen."
    }
    if recs:
        print("[Modultool] Nächste Schritte:")
        for rec in recs:
            print(f" - {rec_map.get(rec, rec)}")
PY
else
  echo "[Modultool] Werkstatt-Check: fehlgeschlagen (weiter mit Standardstart)."
  echo "[Modultool] Tipp: Befehl: MODULTOOL_DEBUG=1 tools/start.sh"
  echo "[Modultool] Tipp: Befehl: ./portable_data/.venv/bin/python app/preflight.py --json"
fi

echo "[Modultool] Werkstatt-Aufräumen …"
# Maintenance (Logs/Cache/Temp) – best effort
"$VENV_DIR/bin/python" "$ROOT/app/maintenance.py" --auto >/dev/null 2>&1 || true

echo "[Modultool] GUI startet …"
exec "$VENV_DIR/bin/python" "$APP_DIR/main.py"
