#!/usr/bin/env bash
set -euo pipefail
echo "[Modultool] Systemeinrichtung – tagsüber (sudo)"
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  echo "[Modultool] FFmpeg/ffprobe vorhanden."
  exit 0
fi

echo "[Modultool] FFmpeg fehlt. Installation startet …"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y ffmpeg
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -S --noconfirm ffmpeg
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg
else
  echo "[Modultool] Fehler: Kein Paketmanager (Installationswerkzeug) gefunden."
  echo "[Modultool] Tipp: Installiere FFmpeg manuell und starte das Tool erneut."
  exit 1
fi

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  echo "[Modultool] Fertig. Tool neu starten, dann Automatik einrichten."
  exit 0
fi
echo "[Modultool] Fehler: FFmpeg/ffprobe ist nach der Installation nicht verfügbar."
echo "[Modultool] Tipp: Prüfe die Systeminstallation und starte erneut."
exit 1
