#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SCRIPT="$ROOT/tools/start.sh"
LOG_DIR="$ROOT/portable_data/logs"
LOG_FILE="$LOG_DIR/click_and_start_last.log"
TOTAL_STEPS=5
STEP=0

progress_step() {
  STEP=$((STEP + 1))
  echo "[Modultool] Schritt $STEP/$TOTAL_STEPS: $1"
}

explain_next_steps() {
  echo "[Modultool] Optionen: Jetzt reparieren, Sicherer Standard, Details."
  echo "[Modultool] Tipp: MODULTOOL_DEBUG=1 tools/click_and_start_on_GUI.sh"
  echo "[Modultool] Tipp: MODULTOOL_AUTO_INSTALL=1 tools/click_and_start_on_GUI.sh"
  echo "[Modultool] Tipp: MODULTOOL_SELF_REPAIR=1 tools/click_and_start_on_GUI.sh"
}

mkdir -p "$LOG_DIR" 2>/dev/null || true
if [ -d "$LOG_DIR" ]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

echo "[Modultool] Klick-Start: automatische Start-Routine (Start = Autostart)."
if [ -f "$LOG_FILE" ]; then
  echo "[Modultool] Klick-Start-Log: $LOG_FILE"
fi

progress_step "Start-Skript prüfen (Skript = ausführbare Datei) …"
if [ ! -x "$START_SCRIPT" ]; then
  echo "[Modultool] Fehler: tools/start.sh fehlt oder ist nicht ausführbar."
  echo "[Modultool] Tipp: Prüfe die Dateirechte mit: chmod +x tools/start.sh"
  explain_next_steps
  exit 1
fi

progress_step "Autostart vorbereiten (Auto-Install + Self-Repair) …"
AUTO_INSTALL="${MODULTOOL_AUTO_INSTALL:-1}"
SELF_REPAIR="${MODULTOOL_SELF_REPAIR:-1}"
RUN_CHECKS="${MODULTOOL_RUN_CHECKS:-1}"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"

progress_step "Autostart ausführen (vollautomatisch) …"
if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" \
  MODULTOOL_SELF_REPAIR="$SELF_REPAIR" \
  MODULTOOL_RUN_CHECKS="$RUN_CHECKS" \
  MODULTOOL_DEBUG="$DEBUG_MODE" \
  MODULTOOL_PROGRESS="1" \
  "$START_SCRIPT"; then
  progress_step "GUI läuft (grafische Oberfläche) …"
  echo "[Modultool] Klick-Start abgeschlossen."
  exit 0
fi

progress_step "Reparatur versuchen (Self-Repair) …"
if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" MODULTOOL_DEBUG="$DEBUG_MODE" \
  "$ROOT/tools/self_repair.sh"; then
  echo "[Modultool] Reparatur abgeschlossen. Starte erneut …"
  if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" \
    MODULTOOL_SELF_REPAIR="$SELF_REPAIR" \
    MODULTOOL_RUN_CHECKS="$RUN_CHECKS" \
    MODULTOOL_DEBUG="$DEBUG_MODE" \
    MODULTOOL_PROGRESS="1" \
    "$START_SCRIPT"; then
    echo "[Modultool] Klick-Start abgeschlossen."
    exit 0
  fi
fi

echo "[Modultool] Fehler: Klick-Start konnte nicht abgeschlossen werden."
explain_next_steps
exit 1
