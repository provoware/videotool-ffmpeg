#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SET="$ROOT/portable_data/config/settings.json"
python3 - <<'PY'
import json
from pathlib import Path
p = Path("/mnt/data/_w914/modultool_portable/portable_data/config/settings.json")
s = json.loads(p.read_text(encoding="utf-8"))
perf = s.setdefault("performance", {})
perf["eco_mode"] = not bool(perf.get("eco_mode", False))
p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
print("eco_mode =", perf["eco_mode"])
PY
