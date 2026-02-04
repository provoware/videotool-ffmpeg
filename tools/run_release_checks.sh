#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_BIN="$(command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "[Modultool] Fehler: python3 fehlt. Bitte Python 3.9+ installieren."
  exit 1
fi

echo "[Modultool] Release-Checks starten (vollautomatische Prüfung)."

echo "[Modultool] Schritt 1/5: Python-Compile (Syntax-Check) …"
"$PYTHON_BIN" -m py_compile "$ROOT"/app/*.py

echo "[Modultool] Schritt 2/5: Bash-Check (Shell-Skripte prüfen) …"
bash -n "$ROOT"/tools/*.sh

echo "[Modultool] Schritt 3/5: Qualitäts-Checks (Codequalität + Format) …"
"$ROOT"/tools/run_quality_checks.sh

echo "[Modultool] Schritt 4/5: Must-Pass Suite (Funktionsprüfung) …"
"$ROOT"/tools/run_must_pass.sh

echo "[Modultool] Schritt 5/5: Release-Builds (ZIP + .deb) …"
MODULTOOL_SKIP_MUST_PASS=1 "$ROOT"/tools/build_release.sh

echo "[Modultool] Release-Checks abgeschlossen."
