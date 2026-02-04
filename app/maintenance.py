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
import argparse
import json
import time
from pathlib import Path
from datetime import datetime
from paths import config_dir, data_dir, logs_dir, cache_dir


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_json(p: Path, default=None):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}
    if not isinstance(data, dict):
        return default if default is not None else {}
    return data


def parse_int(value, default: int, field: str, warnings: list[dict]) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not a valid int")
        return int(value)
    except Exception:
        warnings.append(
            {
                "field": field,
                "value": value,
                "default": default,
                "message": f"Invalid int for {field}; using default {default}.",
            }
        )
        return default


def parse_non_negative_int(
    value, default: int, field: str, warnings: list[dict]
) -> int:
    parsed = parse_int(value, default, field, warnings)
    if parsed < 0:
        warnings.append(
            {
                "field": field,
                "value": value,
                "default": default,
                "message": f"Value for {field} must be >= 0; using default {default}.",
            }
        )
        return default
    return parsed


def bytes_from_mb(mb: int | float) -> int:
    return max(0, int(float(mb) * 1024 * 1024))


def list_files_recursive(folder: Path):
    for p in folder.rglob("*"):
        if p.is_file():
            yield p


def record_warning(warnings: list[dict], action: str, path: Path, error: Exception):
    warnings.append({"action": action, "path": str(path), "error": str(error)})


def folder_size_bytes(folder: Path, warnings: list[dict]) -> int:
    total = 0
    if not folder.exists():
        return 0
    for f in list_files_recursive(folder):
        try:
            total += f.stat().st_size
        except Exception as exc:
            record_warning(warnings, "stat_size", f, exc)
    return total


def rotate_file(path: Path, max_bytes: int, keep: int, warnings: list[dict]):
    if not path.exists():
        return
    try:
        size = path.stat().st_size
    except Exception as exc:
        record_warning(warnings, "stat_size", path, exc)
        return
    if size <= max_bytes:
        return
    if keep <= 0:
        try:
            path.write_text("", encoding="utf-8")
        except Exception as exc:
            record_warning(warnings, "truncate_log", path, exc)
        return
    # rotate: file -> file.1, .1 -> .2, ... up to keep
    for i in range(keep, 0, -1):
        older = path.with_name(path.name + f".{i}")
        newer = path.with_name(path.name + f".{i + 1}")
        if i == keep:
            # drop the last
            if older.exists():
                try:
                    older.unlink()
                except Exception as exc:
                    record_warning(warnings, "unlink_old_rotation", older, exc)
        if older.exists():
            try:
                older.rename(newer)
            except Exception as exc:
                record_warning(warnings, "rename_rotation", older, exc)
    # move current to .1
    try:
        path.rename(path.with_name(path.name + ".1"))
    except Exception as exc:
        record_warning(warnings, "rename_rotation", path, exc)
        return
    # create new empty file
    try:
        path.write_text("", encoding="utf-8")
    except Exception as exc:
        record_warning(warnings, "write_rotated_log", path, exc)


def prune_by_age(folder: Path, max_age_days: int, warnings: list[dict]):
    if not folder.exists():
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    for f in list_files_recursive(folder):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception as exc:
            record_warning(warnings, "prune_by_age", f, exc)
    return removed


def prune_to_size(folder: Path, max_bytes: int, warnings: list[dict]):
    if not folder.exists():
        return 0
    # delete oldest files until under limit
    files = []
    for f in list_files_recursive(folder):
        try:
            st = f.stat()
            files.append((st.st_mtime, st.st_size, f))
        except Exception as exc:
            record_warning(warnings, "stat_prune_candidate", f, exc)
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
        except Exception as exc:
            record_warning(warnings, "prune_to_size", f, exc)
    return removed


def prune_reports(reports_dir: Path, keep_days: int, warnings: list[dict]):
    if not reports_dir.exists():
        return 0
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for f in reports_dir.glob("*.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except Exception as exc:
            record_warning(warnings, "prune_reports", f, exc)
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--auto", action="store_true", help="Run maintenance with settings.json rules"
    )
    args = ap.parse_args()
    if not args.auto:
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "Bitte mit --auto starten (Auto = automatische Regeln).",
                    "next_step": "Beispiel: app/maintenance.py --auto",
                },
                ensure_ascii=False,
            )
        )
        return 0
    settings = load_json(settings_path(), {})
    m = settings.get("maintenance", {})
    warnings: list[dict] = []
    if not isinstance(m, dict):
        warnings.append(
            {
                "field": "maintenance",
                "value": type(m).__name__,
                "default": "dict",
                "message": "maintenance muss ein Objekt sein; Standardwerte aktiv.",
            }
        )
        m = {}
    logs_max_mb = parse_non_negative_int(
        m.get("logs_max_mb", 5), 5, "logs_max_mb", warnings
    )
    logs_keep = parse_non_negative_int(m.get("logs_keep", 5), 5, "logs_keep", warnings)
    cache_max_mb = parse_non_negative_int(
        m.get("cache_max_mb", 200), 200, "cache_max_mb", warnings
    )
    thumbs_max_mb = parse_non_negative_int(
        m.get("thumbs_max_mb", 150), 150, "thumbs_max_mb", warnings
    )
    temp_age = parse_non_negative_int(
        m.get("temp_max_age_days", 3), 3, "temp_max_age_days", warnings
    )
    reports_keep_days = parse_non_negative_int(
        m.get("reports_keep_days", 30), 30, "reports_keep_days", warnings
    )
    logs_max = bytes_from_mb(logs_max_mb)
    cache_max = bytes_from_mb(cache_max_mb)
    thumbs_max = bytes_from_mb(thumbs_max_mb)

    logs_dir().mkdir(parents=True, exist_ok=True)
    cache_dir().mkdir(parents=True, exist_ok=True)
    (cache_dir() / "thumbs").mkdir(parents=True, exist_ok=True)
    (cache_dir() / "temp_renders").mkdir(parents=True, exist_ok=True)

    summary = {
        "at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "warnings": warnings,
        "rotated": [],
        "pruned": {},
        "sizes_before": {},
        "sizes_after": {},
    }

    # sizes before
    summary["sizes_before"]["logs"] = folder_size_bytes(logs_dir(), warnings)
    summary["sizes_before"]["cache"] = folder_size_bytes(cache_dir(), warnings)
    summary["sizes_before"]["thumbs"] = folder_size_bytes(
        cache_dir() / "thumbs", warnings
    )
    summary["sizes_before"]["temp_renders"] = folder_size_bytes(
        cache_dir() / "temp_renders", warnings
    )

    # rotate key logs
    for fn in ["activity_log.jsonl", "debug.log"]:
        p = logs_dir() / fn
        rotate_file(p, logs_max, logs_keep, warnings)
        if p.with_name(p.name + ".1").exists():
            summary["rotated"].append(fn)

    # prune temp by age
    removed_temp = prune_by_age(cache_dir() / "temp_renders", temp_age, warnings)
    summary["pruned"]["temp_renders_by_age"] = removed_temp

    # prune thumbs to size
    removed_thumbs = prune_to_size(cache_dir() / "thumbs", thumbs_max, warnings)
    summary["pruned"]["thumbs_to_size"] = removed_thumbs

    # prune total cache to max (after temp/thumbs)
    removed_cache = prune_to_size(cache_dir(), cache_max, warnings)
    summary["pruned"]["cache_to_size"] = removed_cache

    # prune reports
    removed_reports = prune_reports(data_dir() / "reports", reports_keep_days, warnings)
    summary["pruned"]["reports_by_age"] = removed_reports

    # sizes after
    summary["sizes_after"]["logs"] = folder_size_bytes(logs_dir(), warnings)
    summary["sizes_after"]["cache"] = folder_size_bytes(cache_dir(), warnings)
    summary["sizes_after"]["thumbs"] = folder_size_bytes(
        cache_dir() / "thumbs", warnings
    )
    summary["sizes_after"]["temp_renders"] = folder_size_bytes(
        cache_dir() / "temp_renders", warnings
    )

    # write summary to logs
    out = logs_dir() / "maintenance_last.json"
    try:
        out.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        record_warning(warnings, "write_summary", out, exc)

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    main()
