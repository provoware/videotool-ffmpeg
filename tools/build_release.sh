#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ZIP_SCRIPT="$ROOT/tools/build_portable_zip.sh"
DEB_SCRIPT="$ROOT/tools/build_deb_package.sh"
MUST_PASS_SCRIPT="$ROOT/tools/run_must_pass.sh"
INSTALL_SCRIPT="$ROOT/tools/install_portable_template.sh"
MANIFEST="$ROOT/portable_data/config/manifest.json"

if [ ! -f "$MANIFEST" ]; then
  echo "[Modultool] Fehler: manifest.json fehlt."
  exit 1
fi

VERSION="$(python3 - <<'PY'
import json
from pathlib import Path

manifest = Path("portable_data/config/manifest.json")
data = json.loads(manifest.read_text(encoding="utf-8"))
print(data.get("version", ""))
PY
)"

if [ -z "$VERSION" ]; then
  echo "[Modultool] Fehler: Version in manifest.json fehlt."
  exit 1
fi

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

ZIP_FILE="$ROOT/modultool_portable_${VERSION}.zip"
DEB_FILE="$ROOT/modultool-video-werkstatt_${VERSION}_all.deb"

if [ ! -s "$ZIP_FILE" ]; then
  echo "[Modultool] Fehler: ZIP-Archiv fehlt oder ist leer."
  echo "[Modultool] Tipp: Prüfe $ZIP_FILE und die vorherigen Build-Schritte."
  exit 1
fi

if [ ! -s "$DEB_FILE" ]; then
  echo "[Modultool] Fehler: .deb-Paket fehlt oder ist leer."
  echo "[Modultool] Tipp: Prüfe $DEB_FILE und die vorherigen Build-Schritte."
  exit 1
fi

echo "[Modultool] Release-Build: Artefakte ok (ZIP + .deb)."

if [ -x "$INSTALL_SCRIPT" ]; then
  echo "[Modultool] Release-Test: Template-Installer …"
  "$INSTALL_SCRIPT"
fi

if [ -x "$MUST_PASS_SCRIPT" ]; then
  if [ "${MODULTOOL_SKIP_MUST_PASS:-0}" = "1" ]; then
    echo "[Modultool] Release-Test: Must-Pass Suite übersprungen (bereits geprüft)."
  else
    echo "[Modultool] Release-Test: Must-Pass Suite …"
    "$MUST_PASS_SCRIPT"
  fi
fi

echo "[Modultool] Release-Build abgeschlossen."
