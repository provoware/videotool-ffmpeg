#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT/portable_data/.venv"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"
AUTO_INSTALL="${MODULTOOL_AUTO_INSTALL:-0}"
LOG_DIR="$ROOT/portable_data/logs"
LOG_FILE=""
PORTABLE_FFMPEG_DIR="$ROOT/portable_data/bin"

if mkdir -p "$LOG_DIR" 2>/dev/null; then
  LOG_FILE="$LOG_DIR/self_repair_last.log"
else
  echo "[Modultool] Hinweis: Self-Repair-Log nicht möglich (Log = Protokoll)."
  echo "[Modultool] Tipp: Prüfe Schreibrechte für $LOG_DIR."
fi

if [ -n "$LOG_FILE" ]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

if [ -d "$PORTABLE_FFMPEG_DIR" ]; then
  export PATH="$PORTABLE_FFMPEG_DIR:$PATH"
  if [ -x "$PORTABLE_FFMPEG_DIR/ffmpeg" ] || [ -x "$PORTABLE_FFMPEG_DIR/ffprobe" ]; then
    echo "[Modultool] Hinweis: Portables FFmpeg gefunden (offline nutzbar)."
  fi
fi

echo "[Modultool] Self-Repair startet (Selbstreparatur)."
if [ "$DEBUG_MODE" = "1" ]; then
  echo "[Modultool] Debug-Modus aktiv (mehr Details im Log)."
fi
if [ -n "$LOG_FILE" ]; then
  echo "[Modultool] Self-Repair-Log: $LOG_FILE"
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[Modultool] Fehler: python3 fehlt. Bitte installieren."
  echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
  exit 1
fi

if [ -d "$VENV_DIR" ] && [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[Modultool] Hinweis: Python-Umgebung defekt. Setze sie neu auf …"
  rm -rf "$VENV_DIR"
fi

echo "[Modultool] Abhängigkeiten prüfen und reparieren …"
if ! "$ROOT/tools/bootstrap_python_env.sh"; then
  echo "[Modultool] Fehler: Python-Umgebung konnte nicht repariert werden."
  echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
  exit 1
fi
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[Modultool] Fehler: Python-Umgebung fehlt oder ist defekt."
  echo "[Modultool] Tipp: Lösche $VENV_DIR und starte erneut."
  echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "[Modultool] Hinweis: FFmpeg/ffprobe fehlt (Video-Werkzeug)."
  if [ "$AUTO_INSTALL" = "1" ]; then
    echo "[Modultool] Starte Systemeinrichtung (kann Admin-Rechte brauchen) …"
    if ! "$ROOT/tools/setup_system.sh"; then
      echo "[Modultool] Fehler: FFmpeg-Installation fehlgeschlagen."
      echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
      exit 1
    fi
  else
    echo "[Modultool] Tipp: Starte \"tools/setup_system.sh\" oder setze MODULTOOL_AUTO_INSTALL=1."
  fi
  if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo "[Modultool] Fehler: FFmpeg/ffprobe fehlt weiterhin."
    echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
    exit 1
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
  printf '%s' "$PREFLIGHT_JSON" | "$VENV_DIR/bin/python" - <<'PY'
import json
import sys

raw = sys.stdin.read()
candidate = raw.strip()

def parse_payload(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None

data = parse_payload(candidate)
if data is None:
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        data = parse_payload(candidate[start : end + 1])

if not isinstance(data, dict):
    print("[Modultool] Werkstatt-Check: Ergebnis unlesbar (JSON = strukturierte Textdaten).")
    print("[Modultool] Tipp: Befehl: MODULTOOL_DEBUG=1 tools/self_repair.sh")
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
        "config_not_writable": "Config-Ordner (Konfiguration) braucht Schreibrechte.",
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
  echo "[Modultool] Werkstatt-Check: fehlgeschlagen (Details im Log)."
  echo "[Modultool] Tipp: Befehl: MODULTOOL_DEBUG=1 tools/self_repair.sh"
  echo "[Modultool] Tipp: Befehl: ./portable_data/.venv/bin/python app/preflight.py --json"
fi

echo "[Modultool] Self-Repair abgeschlossen."
