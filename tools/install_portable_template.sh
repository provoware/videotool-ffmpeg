#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT"
USER_BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET_DIR="$USER_BASE/modultool_portable"

if ! command -v rsync >/dev/null 2>&1; then
  echo "[Modultool] Fehler: rsync fehlt."
  exit 1
fi

if [ -d "$TARGET_DIR" ]; then
  echo "[Modultool] Ziel existiert bereits: $TARGET_DIR"
  echo "[Modultool] Kein Überschreiben vorgenommen."
  exit 0
fi

mkdir -p "$USER_BASE"
rsync -a --delete "$TEMPLATE_DIR/" "$TARGET_DIR/" \
  --exclude ".git" \
  --exclude "deb_build" \
  --exclude "dist" \
  --exclude ".github"

chmod +x "$TARGET_DIR/tools/"*.sh || true

echo "[Modultool] Template kopiert nach $TARGET_DIR"
