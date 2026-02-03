#!/usr/bin/env bash
set -euo pipefail
echo "[Modultool] Systemeinrichtung – tagsüber (sudo)"
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  echo "[Modultool] FFmpeg/ffprobe vorhanden."
else
  echo "[Modultool] FFmpeg fehlt. Installation startet …"
  sudo apt-get update
  sudo apt-get install -y ffmpeg
fi
echo "[Modultool] Fertig. Tool neu starten, dann Automatik einrichten."
