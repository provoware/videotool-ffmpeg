#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ZIP_SCRIPT="$ROOT/tools/build_portable_zip.sh"
DEB_SCRIPT="$ROOT/tools/build_deb_package.sh"
MUST_PASS_SCRIPT="$ROOT/tools/run_must_pass.sh"
INSTALL_SCRIPT="$ROOT/tools/install_portable_template.sh"

if [ ! -x "$ZIP_SCRIPT" ]; then
  echo "[Modultool] Fehler: ZIP-Build-Skript fehlt."
  exit 1
fi

if [ ! -x "$DEB_SCRIPT" ]; then
  echo "[Modultool] Fehler: .deb-Build-Skript fehlt."
  exit 1
fi

echo "[Modultool] Release-Build: ZIP-Archiv …"
"$ZIP_SCRIPT"

echo "[Modultool] Release-Build: .deb-Paket …"
"$DEB_SCRIPT"

if [ -x "$INSTALL_SCRIPT" ]; then
  echo "[Modultool] Release-Test: Template-Installer …"
  "$INSTALL_SCRIPT"
fi

if [ -x "$MUST_PASS_SCRIPT" ]; then
  echo "[Modultool] Release-Test: Must-Pass Suite …"
  "$MUST_PASS_SCRIPT"
fi

echo "[Modultool] Release-Build abgeschlossen."
