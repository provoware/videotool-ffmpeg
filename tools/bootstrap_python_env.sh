#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT/app"
VENV_DIR="$ROOT/portable_data/.venv"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"
WITH_DEV=0
REPAIR_ATTEMPTED=0

for arg in "$@"; do
  case "$arg" in
    --dev)
      WITH_DEV=1
      ;;
    *)
      ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "[Modultool] Fehler: python3 fehlt. Bitte installieren." >&2
  exit 1
fi

recreate_venv() {
  echo "[Modultool] Self-Repair: Python-Umgebung wird neu erstellt …"
  rm -rf "$VENV_DIR"
  python3 -m venv "$VENV_DIR"
}

ensure_venv() {
  if [ ! -d "$VENV_DIR" ]; then
    echo "[Modultool] Python-Umgebung wird erstellt …"
    python3 -m venv "$VENV_DIR"
  fi
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "[Modultool] Hinweis: Python-Umgebung defekt. Reparatur läuft …"
    recreate_venv
  fi
}

ensure_venv

if [ ! -f "$APP_DIR/requirements.txt" ]; then
  echo "[Modultool] Fehler: requirements.txt fehlt." >&2
  echo "[Modultool] Tipp: Prüfe das Installationspaket oder stelle die Datei wieder her." >&2
  exit 1
fi

PIP_CMD=("$VENV_DIR/bin/python" -m pip)

upgrade_pip() {
  if [ "$DEBUG_MODE" = "1" ]; then
    "${PIP_CMD[@]}" install --upgrade pip
  else
    "${PIP_CMD[@]}" install --upgrade pip >/dev/null
  fi
}

install_requirements() {
  if [ "$DEBUG_MODE" = "1" ]; then
    "${PIP_CMD[@]}" install -r "$APP_DIR/requirements.txt"
  else
    "${PIP_CMD[@]}" install -r "$APP_DIR/requirements.txt" >/dev/null
  fi
}

install_dev_requirements() {
  if [ "$WITH_DEV" = "1" ] && [ -f "$APP_DIR/requirements-dev.txt" ]; then
    if [ "$DEBUG_MODE" = "1" ]; then
      "${PIP_CMD[@]}" install -r "$APP_DIR/requirements-dev.txt"
    else
      "${PIP_CMD[@]}" install -r "$APP_DIR/requirements-dev.txt" >/dev/null
    fi
  fi
}

run_pip_check() {
  if [ "$DEBUG_MODE" = "1" ]; then
    "${PIP_CMD[@]}" check
  else
    "${PIP_CMD[@]}" check >/dev/null
  fi
}

run_with_repair() {
  local label="$1"
  shift
  if "$@"; then
    return 0
  fi
  if [ "$REPAIR_ATTEMPTED" = "0" ]; then
    REPAIR_ATTEMPTED=1
    echo "[Modultool] Hinweis: $label fehlgeschlagen. Self-Repair startet …"
    recreate_venv
    PIP_CMD=("$VENV_DIR/bin/python" -m pip)
    "$@"
    return $?
  fi
  return 1
}

if ! run_with_repair "pip-Upgrade" upgrade_pip; then
  echo "[Modultool] Fehler: pip-Upgrade fehlgeschlagen." >&2
  echo "[Modultool] Tipp: Internet prüfen, dann erneut starten." >&2
  exit 1
fi

if ! run_with_repair "Dependencies-Installation" install_requirements; then
  echo "[Modultool] Fehler: Abhängigkeiten (Dependencies = Zusatzpakete) konnten nicht installiert werden." >&2
  echo "[Modultool] Tipp: Internet prüfen, dann erneut starten." >&2
  exit 1
fi

if ! run_with_repair "Dev-Dependencies-Installation" install_dev_requirements; then
  echo "[Modultool] Fehler: Dev-Abhängigkeiten konnten nicht installiert werden." >&2
  exit 1
fi

if ! run_with_repair "pip-Check" run_pip_check; then
  echo "[Modultool] Fehler: Python-Abhängigkeiten sind inkonsistent." >&2
  echo "[Modultool] Tipp: MODULTOOL_DEBUG=1 tools/start.sh zeigt Details." >&2
  exit 1
fi

if ! "$VENV_DIR/bin/python" - <<'PY'
import importlib.util
import sys

missing = []
for pkg in ("PySide6",):
    if importlib.util.find_spec(pkg) is None:
        missing.append(pkg)

if missing:
    print(f"[Modultool] Fehler: Pflichtpakete fehlen: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)
PY
then
  exit 1
fi
