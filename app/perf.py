#!/usr/bin/env python3
import json
import os
from pathlib import Path


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cpu_threads() -> int:
    return max(1, os.cpu_count() or 1)


def get_threads(settings_path: Path) -> int | None:
    s = load_json(settings_path, {})
    p = s.get("performance", {})
    eco_mode = bool(p.get("eco_mode", False))
    eco_threads = _safe_int(p.get("eco_threads", 2), 2)
    normal_threads = _safe_int(p.get("normal_threads", 0), 0)
    cpu_threads = _cpu_threads()
    if eco_mode:
        if eco_threads > 0:
            return eco_threads
        return max(1, cpu_threads // 2)
    if normal_threads > 0:
        return normal_threads
    return cpu_threads
