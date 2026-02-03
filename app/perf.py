#!/usr/bin/env python3
import json
from pathlib import Path

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def get_threads(settings_path: Path) -> int|None:
    s = load_json(settings_path, {})
    p = s.get("performance", {})
    eco_mode = bool(p.get("eco_mode", False))
    eco_threads = int(p.get("eco_threads", 2))
    normal_threads = int(p.get("normal_threads", 0))
    if eco_mode:
        return eco_threads if eco_threads > 0 else None
    return normal_threads if normal_threads > 0 else None
