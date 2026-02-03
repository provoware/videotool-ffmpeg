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

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "[Modultool] Fehler: dpkg-deb fehlt."
  exit 1
fi

VERSION="$(python3 - <<'PY'
import json
from pathlib import Path
manifest = Path("portable_data/config/manifest.json")
print(json.loads(manifest.read_text(encoding="utf-8"))["version"])
PY
)"

PKG="modultool-video-werkstatt"
ARCH="all"
ROOTDIR="$ROOT/deb_build/${PKG}_${VERSION}_${ARCH}"

rm -rf "$ROOT/deb_build"
mkdir -p "$ROOTDIR/DEBIAN"
mkdir -p "$ROOTDIR/usr/share/modultool_portable_template"
mkdir -p "$ROOTDIR/usr/bin"
mkdir -p "$ROOTDIR/usr/share/applications"
mkdir -p "$ROOTDIR/usr/share/icons/hicolor/256x256/apps"

rsync -a --delete "$ROOT/" "$ROOTDIR/usr/share/modultool_portable_template/" \
  --exclude ".git" \
  --exclude "deb_build" \
  --exclude ".github" \
  --exclude "dist"

chmod +x "$ROOTDIR/usr/share/modultool_portable_template/tools/"*.sh || true

if [ -f "$ROOTDIR/usr/share/modultool_portable_template/assets/default_assets/default_logo.png" ]; then
  cp "$ROOTDIR/usr/share/modultool_portable_template/assets/default_assets/default_logo.png" \
     "$ROOTDIR/usr/share/icons/hicolor/256x256/apps/modultool-video-werkstatt.png"
fi

cat > "$ROOTDIR/usr/bin/modultool-video-werkstatt" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
TEMPLATE_DIR="/usr/share/modultool_portable_template"
USER_BASE="${XDG_DATA_HOME:-$HOME/.local/share}"
TARGET_DIR="$USER_BASE/modultool_portable"

if [ ! -d "$TARGET_DIR" ]; then
  mkdir -p "$USER_BASE"
  cp -a "$TEMPLATE_DIR" "$TARGET_DIR"
  chmod +x "$TARGET_DIR/tools/"*.sh || true
fi

exec "$TARGET_DIR/tools/start.sh"
SH
chmod +x "$ROOTDIR/usr/bin/modultool-video-werkstatt"

cat > "$ROOTDIR/usr/share/applications/modultool-video-werkstatt.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Modultool – Video-Werkstatt
Comment=Standbild+Audio Videos bauen (Ton Safe), Automatik, Quarantäne, Werkbank
Exec=modultool-video-werkstatt
Icon=modultool-video-werkstatt
Terminal=false
Categories=AudioVideo;Utility;
StartupNotify=true
DESKTOP

cat > "$ROOTDIR/DEBIAN/control" <<CONTROL
Package: $PKG
Version: $VERSION
Section: video
Priority: optional
Architecture: $ARCH
Maintainer: Modultool Builder <noreply@local>
Depends: python3, python3-venv, ffmpeg
Description: Modultool – Video-Werkstatt (Template + Launcher)
 Installiert eine Vorlage nach /usr/share und startet beim ersten Run eine Nutzerkopie.
CONTROL

cat > "$ROOTDIR/DEBIAN/postinst" <<'POST'
#!/usr/bin/env bash
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
POST
chmod 755 "$ROOTDIR/DEBIAN/postinst"

dpkg-deb --build "$ROOTDIR" "$ROOT/${PKG}_${VERSION}_${ARCH}.deb"
ls -lh "$ROOT/${PKG}_${VERSION}_${ARCH}.deb"
