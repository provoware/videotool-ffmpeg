#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[Modultool] Fehler: python3 fehlt."
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "[Modultool] Fehler: rsync fehlt."
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "[Modultool] Fehler: zip fehlt."
  exit 1
fi

VERSION="$(python3 - <<'PY'
import json
from pathlib import Path
manifest = Path("portable_data/config/manifest.json")
print(json.loads(manifest.read_text(encoding="utf-8"))["version"])
PY
)"

ZIP_NAME="modultool_portable_${VERSION}.zip"
DIST_DIR="$ROOT/dist"

rm -rf "$DIST_DIR/modultool_portable"
mkdir -p "$DIST_DIR/modultool_portable"

rsync -a --delete "$ROOT/" "$DIST_DIR/modultool_portable/" \
  --exclude ".git" \
  --exclude "dist" \
  --exclude ".github" \
  --exclude "deb_build"

(
  cd "$DIST_DIR"
  zip -r "$ROOT/$ZIP_NAME" "modultool_portable"
)

ls -lh "$ROOT/$ZIP_NAME"
