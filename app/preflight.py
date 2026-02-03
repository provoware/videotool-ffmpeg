#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from paths import config_dir, data_dir, cache_dir, logs_dir


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def debug_enabled() -> bool:
    raw = os.getenv("MODULTOOL_DEBUG", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def log_debug(message: str, level: str = "DEBUG") -> None:
    try:
        logs_dir().mkdir(parents=True, exist_ok=True)
        payload = {
            "at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": level,
            "message": message,
        }
        log_path = logs_dir() / "preflight_debug.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def parse_min_free_mb(settings: dict) -> tuple[int, bool, str]:
    raw = settings.get("maintenance", {}).get("min_free_mb", 1024)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1024, False, str(raw)
    if value < 0:
        return 1024, False, str(raw)
    return value, True, str(raw)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def writable_dir(p: Path) -> tuple[bool, str]:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".modultool_write_test.tmp"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, str(e)


def free_space_mb(p: Path) -> int:
    try:
        usage = shutil.disk_usage(str(p))
        return int(usage.free / 1024 / 1024)
    except Exception:
        return -1


def find_font() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def run(settings_path: Path | None = None) -> dict:
    if settings_path is None:
        settings_path = config_dir() / "settings.json"
    if debug_enabled():
        log_debug(f"Preflight start (settings={settings_path})")
    settings = load_json(settings_path, {})
    paths = settings.get("paths", {})
    min_free_mb, min_free_ok, min_free_raw = parse_min_free_mb(settings)

    watch = Path(paths.get("watch_folder", str(Path.home() / "Downloads"))).expanduser()
    exports = data_dir() / paths.get("exports_dir", "exports")
    reports = data_dir() / paths.get("reports_dir", "reports")
    staging = data_dir() / paths.get("staging_dir", "staging")
    trash = data_dir() / paths.get("trash_dir", "trash")
    thumbs = cache_dir() / "thumbs"
    temp_r = cache_dir() / "temp_renders"

    ok_ffmpeg = have("ffmpeg") and have("ffprobe")
    ok_watch = watch.exists() and watch.is_dir()
    watch_writable_ok = True
    watch_writable_error = ""
    if ok_watch:
        watch_writable_ok, watch_writable_error = writable_dir(watch)

    writable = {}
    for key, p in [
        ("exports", exports),
        ("reports", reports),
        ("staging", staging),
        ("trash", trash),
        ("thumbs", thumbs),
        ("temp_renders", temp_r),
    ]:
        ok, err = writable_dir(p)
        writable[key] = {"ok": ok, "path": str(p), "error": err}

    free_mb = free_space_mb(data_dir())
    ok_space = (free_mb >= min_free_mb) if free_mb >= 0 else True

    font = find_font()
    ok_font = font is not None

    overall_ok = (
        ok_ffmpeg
        and ok_watch
        and ok_space
        and watch_writable_ok
        and all(v["ok"] for v in writable.values())
    )

    rec = []
    if not ok_ffmpeg:
        rec.append("ffmpeg_install")
    if not ok_watch:
        rec.append("set_watchfolder")
    if not ok_space:
        rec.append("free_space")
    if not ok_font:
        rec.append("install_font")
    if not min_free_ok:
        rec.append("min_free_mb_invalid")
    if ok_watch and not watch_writable_ok:
        rec.append("watchfolder_not_writable")

    result = {
        "at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "overall_ok": overall_ok,
        "ffmpeg_ok": ok_ffmpeg,
        "watchfolder_ok": ok_watch,
        "watchfolder": str(watch),
        "watchfolder_writable_ok": watch_writable_ok,
        "watchfolder_writable_error": watch_writable_error,
        "free_mb": free_mb,
        "min_free_mb_ok": min_free_ok,
        "min_free_mb_input": min_free_raw,
        "min_free_mb": min_free_mb,
        "space_ok": ok_space,
        "font_ok": ok_font,
        "font": font or "",
        "writable": writable,
        "recommendations": rec,
    }
    if debug_enabled():
        log_debug(f"Preflight result overall_ok={overall_ok} rec={rec}")
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = run()
    if args.json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        print(res)
