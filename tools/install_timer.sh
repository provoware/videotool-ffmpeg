#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$ROOT/portable_data/config/automation_rules.json"
RUNNER="$ROOT/tools/run_automation.sh"

TIME="$(python3 -c "import json;print(json.load(open('$CFG'))['start_time'])")"
HOUR="${TIME%:*}"
MIN="${TIME#*:}"

UNIT_DIR="$HOME/.config/systemd/user"
SERVICE="modultool-automation.service"
TIMER="modultool-automation.timer"
mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/$SERVICE" <<EOF
[Unit]
Description=Modultool Automatik (Portable)
[Service]
Type=oneshot
ExecStart=$RUNNER
EOF

cat > "$UNIT_DIR/$TIMER" <<EOF
[Unit]
Description=Modultool Automatik Zeitplan
[Timer]
OnCalendar=*-*-* $HOUR:$MIN:00
Persistent=false
Unit=$SERVICE
[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "$TIMER"
echo "[Modultool] Zeitplan gesetzt: täglich $TIME"
