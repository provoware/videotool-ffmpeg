#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SCRIPT="$ROOT/tools/start.sh"
LOG_DIR="$ROOT/portable_data/logs"
LOG_FILE="$LOG_DIR/click_and_start_last.log"
TEXTS_DIR="$ROOT/portable_data/config"
TEXTS_LANG_RAW="${MODULTOOL_LANG:-${LANG%%_*}}"
TEXTS_LANG="de"
FALLBACK_LANG="de"
TOTAL_STEPS=5
STEP=0

case "${TEXTS_LANG_RAW,,}" in
  de|en)
    TEXTS_LANG="${TEXTS_LANG_RAW,,}"
    ;;
esac

TEXTS_PATH="$TEXTS_DIR/texte_${TEXTS_LANG}.json"
FALLBACK_TEXTS_PATH="$TEXTS_DIR/texte_${FALLBACK_LANG}.json"

format_text() {
  local text="$1"
  shift
  while [ "$#" -gt 1 ]; do
    local key="$1"
    local value="$2"
    text="${text//\{$key\}/$value}"
    shift 2
  done
  printf '%s' "$text"
}

get_text() {
  local key="$1"
  local default="$2"
  python3 - "$TEXTS_PATH" "$FALLBACK_TEXTS_PATH" "$key" "$default" <<'PY'
import json
import os
import sys

primary_path = sys.argv[1]
fallback_path = sys.argv[2]
key = sys.argv[3]
default = sys.argv[4]


def load_texts(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


texts = load_texts(fallback_path)
texts.update(load_texts(primary_path))
strings = texts.get("strings", {})
print(strings.get(key, default))
PY
}

normalize_flag() {
  local name="$1"
  local value="${2:-}"
  local default="$3"
  local normalized

  case "${value,,}" in
    1|true|yes|on)
      normalized="1"
      ;;
    0|false|no|off)
      normalized="0"
      ;;
    "")
      normalized="$default"
      ;;
    *)
      normalized="$default"
      local warn_template
      warn_template="$(get_text "click_start.invalid_flag" \
        "Ungültiger Wert für {name}: '{value}'. Nutze Standard {default}.")"
      echo "[Modultool] $(format_text "$warn_template" name "$name" value "$value" default "$default")"
      ;;
  esac

  echo "$normalized"
}

progress_step() {
  STEP=$((STEP + 1))
  if [ -z "${1:-}" ]; then
    echo "[Modultool] $(get_text "click_start.step_missing" "Warnung: Fortschritts-Text fehlt.")"
    return
  fi
  echo "[Modultool] $(format_text "$(get_text "click_start.step" "Schritt {step}/{total}: {text}")" \
    step "$STEP" total "$TOTAL_STEPS" text "$1")"
}

explain_next_steps() {
  echo "[Modultool] $(get_text "click_start.options" \
    "Optionen: Jetzt reparieren, Sicherer Standard, Details.")"
  echo "[Modultool] $(get_text "click_start.tip_debug" \
    "Tipp: MODULTOOL_DEBUG=1 tools/click_and_start_on_GUI.sh")"
  echo "[Modultool] $(get_text "click_start.tip_auto_install" \
    "Tipp: MODULTOOL_AUTO_INSTALL=1 tools/click_and_start_on_GUI.sh")"
  echo "[Modultool] $(get_text "click_start.tip_self_repair" \
    "Tipp: MODULTOOL_SELF_REPAIR=1 tools/click_and_start_on_GUI.sh")"
}

mkdir -p "$LOG_DIR" 2>/dev/null || true
if [ -d "$LOG_DIR" ]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
fi

if [ ! -f "$TEXTS_PATH" ] && [ -f "$FALLBACK_TEXTS_PATH" ]; then
  echo "[Modultool] $(get_text "click_start.lang_fallback" \
    "Hinweis: Sprachdatei fehlt, nutze Standard.")"
  TEXTS_PATH="$FALLBACK_TEXTS_PATH"
fi

echo "[Modultool] $(get_text "click_start.intro" \
  "Klick-Start: automatische Start-Routine (Start = Autostart).")"
if [ -f "$LOG_FILE" ]; then
  echo "[Modultool] $(format_text "$(get_text "click_start.log_path" "Klick-Start-Log: {path}")" \
    path "$LOG_FILE")"
fi

progress_step "$(get_text "click_start.step_check_script" \
  "Start-Skript prüfen (Skript = ausführbare Datei) …")"
if [ ! -x "$START_SCRIPT" ]; then
  echo "[Modultool] $(get_text "click_start.error_start_missing" \
    "Fehler: tools/start.sh fehlt oder ist nicht ausführbar.")"
  echo "[Modultool] $(get_text "click_start.tip_fix_permissions" \
    "Tipp: Prüfe die Dateirechte mit: chmod +x tools/start.sh")"
  explain_next_steps
  exit 1
fi

progress_step "$(get_text "click_start.step_prepare_autostart" \
  "Autostart vorbereiten (Auto-Install + Self-Repair) …")"
AUTO_INSTALL="$(normalize_flag "MODULTOOL_AUTO_INSTALL" "${MODULTOOL_AUTO_INSTALL:-1}" "1")"
SELF_REPAIR="$(normalize_flag "MODULTOOL_SELF_REPAIR" "${MODULTOOL_SELF_REPAIR:-1}" "1")"
RUN_CHECKS="$(normalize_flag "MODULTOOL_RUN_CHECKS" "${MODULTOOL_RUN_CHECKS:-1}" "1")"
DEBUG_MODE="$(normalize_flag "MODULTOOL_DEBUG" "${MODULTOOL_DEBUG:-0}" "0")"

progress_step "$(get_text "click_start.step_run_autostart" \
  "Autostart ausführen (vollautomatisch) …")"
if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" \
  MODULTOOL_SELF_REPAIR="$SELF_REPAIR" \
  MODULTOOL_RUN_CHECKS="$RUN_CHECKS" \
  MODULTOOL_DEBUG="$DEBUG_MODE" \
  MODULTOOL_PROGRESS="1" \
  "$START_SCRIPT"; then
  progress_step "$(get_text "click_start.step_gui_running" \
    "GUI läuft (grafische Oberfläche) …")"
  echo "[Modultool] $(get_text "click_start.success" "Klick-Start abgeschlossen.")"
  exit 0
fi

progress_step "$(get_text "click_start.step_repair_attempt" \
  "Reparatur versuchen (Self-Repair) …")"
if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" MODULTOOL_DEBUG="$DEBUG_MODE" \
  "$ROOT/tools/self_repair.sh"; then
  echo "[Modultool] $(get_text "click_start.repair_done" \
    "Reparatur abgeschlossen. Starte erneut …")"
  if MODULTOOL_AUTO_INSTALL="$AUTO_INSTALL" \
    MODULTOOL_SELF_REPAIR="$SELF_REPAIR" \
    MODULTOOL_RUN_CHECKS="$RUN_CHECKS" \
    MODULTOOL_DEBUG="$DEBUG_MODE" \
    MODULTOOL_PROGRESS="1" \
    "$START_SCRIPT"; then
    echo "[Modultool] $(get_text "click_start.success" "Klick-Start abgeschlossen.")"
    exit 0
  fi
fi

echo "[Modultool] $(get_text "click_start.error_failed" \
  "Fehler: Klick-Start konnte nicht abgeschlossen werden.")"
explain_next_steps
exit 1
