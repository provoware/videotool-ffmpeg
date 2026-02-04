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


def get_parallel_audio_workers(settings: dict) -> int:
    if not isinstance(settings, dict):
        return 1
    performance = settings.get("performance", {})
    if not isinstance(performance, dict):
        return 1
    cpu_threads = _cpu_threads()
    eco_mode = bool(performance.get("eco_mode", False))
    default_workers = 1 if eco_mode else max(1, min(4, cpu_threads))
    raw = _safe_int(performance.get("parallel_audio_workers", default_workers), 1)
    if raw < 1:
        return 1
    return min(raw, cpu_threads)
