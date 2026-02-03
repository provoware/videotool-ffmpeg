#!/usr/bin/env python3
"""
Maintenance (0.9.8):
- Log rotation for portable_data/logs/*.log and activity_log.jsonl
- Cache cleanup for portable_data/cache/thumbs and temp_renders
- Report retention (optional) for user_data/reports (keep last N days)
Safety rules:
- Never delete exports/, library/, projects/, favorites/ content
- Only operates on cache/, logs/, reports/ by age/size rules from config/settings.json
"""
from __future__ import annotations
import argparse, json, os, shutil, time
from pathlib import Path
from datetime import datetime, timedelta

def root() -> Path:
    return Path(__file__).resolve().parents[1]

def cfg_dir() -> Path:
    return root() / "portable_data" / "config"

def settings_path() -> Path:
    return cfg_dir() / "settings.json"

def data_dir() -> Path:
    return root() / "portable_data" / "user_data"

def logs_dir() -> Path:
    return root() / "portable_data" / "logs"

def cache_dir() -> Path:
    return root() / "portable_data" / "cache"

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def bytes_from_mb(mb: int|float) -> int:
    return int(float(mb) * 1024 * 1024)

def list_files_recursive(folder: Path):
    for p in folder.rglob("*"):
        if p.is_file():
            yield p

def folder_size_bytes(folder: Path) -> int:
    total = 0
    if not folder.exists():
        return 0
    for f in list_files_recursive(folder):
        try:
            total += f.stat().st_size
        except Exception:
            pass
    return total

def rotate_file(path: Path, max_bytes: int, keep: int):
    if not path.exists():
        return
    try:
        size = path.stat().st_size
    except Exception:
        return
    if size <= max_bytes:
        return
    # rotate: file -> file.1, .1 -> .2, ... up to keep
    for i in range(keep, 0, -1):
        older = path.with_name(path.name + f".{i}")
        newer = path.with_name(path.name + f".{i+1}")
        if i == keep:
            # drop the last
            if older.exists():
                try:
                    older.unlink()
                except Exception:
                    pass
        if older.exists():
            try:
                older.rename(newer)
            except Exception:
                pass
    # move current to .1
    try:
        path.rename(path.with_name(path.name + ".1"))
    except Exception:
        return
    # create new empty file
    try:
        path.write_text("", encoding="utf-8")
    except Exception:
        pass

def prune_by_age(folder: Path, max_age_days: int):
    if not folder.exists():
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for f in list_files_recursive(folder):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass
    return removed

def prune_to_size(folder: Path, max_bytes: int):
    if not folder.exists():
        return 0
    # delete oldest files until under limit
    files = []
    for f in list_files_recursive(folder):
        try:
            st = f.stat()
            files.append((st.st_mtime, st.st_size, f))
        except Exception:
            pass
    files.sort(key=lambda x: x[0])  # oldest first
    removed = 0
    total = sum(s for _, s, _ in files)
    for _mt, sz, f in files:
        if total <= max_bytes:
            break
        try:
            f.unlink()
            total -= sz
            removed += 1
        except Exception:
            pass
    return removed

def prune_reports(reports_dir: Path, keep_days: int):
    if not reports_dir.exists():
        return 0
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for f in reports_dir.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception:
            pass
    return removed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="Run maintenance with settings.json rules")
    args = ap.parse_args()

    settings = load_json(settings_path(), {})
    m = settings.get("maintenance", {})
    logs_max = bytes_from_mb(m.get("logs_max_mb", 5))
    logs_keep = int(m.get("logs_keep", 5))
    cache_max = bytes_from_mb(m.get("cache_max_mb", 200))
    thumbs_max = bytes_from_mb(m.get("thumbs_max_mb", 150))
    temp_age = int(m.get("temp_max_age_days", 3))
    reports_keep_days = int(m.get("reports_keep_days", 30))

    logs_dir().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
    (cache_dir()/ "thumbs").mkdir(parents=True, exist_ok=True)
    (cache_dir()/ "temp_renders").mkdir(parents=True, exist_ok=True)

    summary = {
        "at": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "rotated": [],
        "pruned": {},
        "sizes_before": {},
        "sizes_after": {}
    }

    # sizes before
    summary["sizes_before"]["logs"] = folder_size_bytes(logs_dir())
    summary["sizes_before"]["cache"] = folder_size_bytes(cache_dir())
    summary["sizes_before"]["thumbs"] = folder_size_bytes(cache_dir()/ "thumbs")
    summary["sizes_before"]["temp_renders"] = folder_size_bytes(cache_dir()/ "temp_renders")

    # rotate key logs
    for fn in ["activity_log.jsonl", "debug.log"]:
        p = logs_dir()/fn
        rotate_file(p, logs_max, logs_keep)
        if p.with_name(p.name + ".1").exists():
            summary["rotated"].append(fn)

    # prune temp by age
    removed_temp = prune_by_age(cache_dir()/ "temp_renders", temp_age)
    summary["pruned"]["temp_renders_by_age"] = removed_temp

    # prune thumbs to size
    removed_thumbs = prune_to_size(cache_dir()/ "thumbs", thumbs_max)
    summary["pruned"]["thumbs_to_size"] = removed_thumbs

    # prune total cache to max (after temp/thumbs)
    removed_cache = prune_to_size(cache_dir(), cache_max)
    summary["pruned"]["cache_to_size"] = removed_cache

    # prune reports
    removed_reports = prune_reports(data_dir()/ "reports", reports_keep_days)
    summary["pruned"]["reports_by_age"] = removed_reports

    # sizes after
    summary["sizes_after"]["logs"] = folder_size_bytes(logs_dir())
    summary["sizes_after"]["cache"] = folder_size_bytes(cache_dir())
    summary["sizes_after"]["thumbs"] = folder_size_bytes(cache_dir()/ "thumbs")
    summary["sizes_after"]["temp_renders"] = folder_size_bytes(cache_dir()/ "temp_renders")

    # write summary to logs
    out = logs_dir()/ "maintenance_last.json"
    try:
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(json.dumps(summary, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
