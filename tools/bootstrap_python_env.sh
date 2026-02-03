#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT/app"
VENV_DIR="$ROOT/portable_data/.venv"
DEBUG_MODE="${MODULTOOL_DEBUG:-0}"
WITH_DEV=0

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

if [ ! -d "$VENV_DIR" ]; then
  echo "[Modultool] Python-Umgebung wird erstellt …"
  python3 -m venv "$VENV_DIR"
fi

if [ ! -f "$APP_DIR/requirements.txt" ]; then
  echo "[Modultool] Fehler: requirements.txt fehlt." >&2
  echo "[Modultool] Tipp: Prüfe das Installationspaket oder stelle die Datei wieder her." >&2
  exit 1
fi

PIP_CMD=("$VENV_DIR/bin/python" -m pip)

if [ "$DEBUG_MODE" = "1" ]; then
  "${PIP_CMD[@]}" install --upgrade pip
else
  "${PIP_CMD[@]}" install --upgrade pip >/dev/null
fi

if [ "$DEBUG_MODE" = "1" ]; then
  if ! "${PIP_CMD[@]}" install -r "$APP_DIR/requirements.txt"; then
    echo "[Modultool] Fehler: Abhängigkeiten (Dependencies = Zusatzpakete) konnten nicht installiert werden." >&2
    echo "[Modultool] Tipp: Internet prüfen, dann erneut starten." >&2
    exit 1
  fi
else
  if ! "${PIP_CMD[@]}" install -r "$APP_DIR/requirements.txt" >/dev/null; then
    echo "[Modultool] Fehler: Abhängigkeiten (Dependencies = Zusatzpakete) konnten nicht installiert werden." >&2
    echo "[Modultool] Tipp: Internet prüfen, dann erneut starten." >&2
    exit 1
  fi
fi

if [ "$WITH_DEV" = "1" ] && [ -f "$APP_DIR/requirements-dev.txt" ]; then
  if [ "$DEBUG_MODE" = "1" ]; then
    if ! "${PIP_CMD[@]}" install -r "$APP_DIR/requirements-dev.txt"; then
      echo "[Modultool] Fehler: Dev-Abhängigkeiten konnten nicht installiert werden." >&2
      exit 1
    fi
  else
    if ! "${PIP_CMD[@]}" install -r "$APP_DIR/requirements-dev.txt" >/dev/null; then
      echo "[Modultool] Fehler: Dev-Abhängigkeiten konnten nicht installiert werden." >&2
      exit 1
    fi
  fi
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
