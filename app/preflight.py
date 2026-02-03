#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, os
from pathlib import Path
from datetime import datetime

def root() -> Path:
    return Path(__file__).resolve().parents[1]

def cfg_dir() -> Path:
    return root()/ "portable_data"/ "config"

def data_dir() -> Path:
    return root()/ "portable_data"/ "user_data"

def cache_dir() -> Path:
    return root()/ "portable_data"/ "cache"

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def writable_dir(p: Path) -> tuple[bool, str]:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p/".modultool_write_test.tmp"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, str(e)

def free_space_mb(p: Path) -> int:
    try:
        usage = shutil.disk_usage(str(p))
        return int(usage.free/1024/1024)
    except Exception:
        return -1

def find_font() -> str|None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None

def run(settings_path: Path|None = None) -> dict:
    if settings_path is None:
        settings_path = cfg_dir()/ "settings.json"
    settings = load_json(settings_path, {})
    paths = settings.get("paths", {})
    min_free_mb = int(settings.get("maintenance", {}).get("min_free_mb", 1024))

    watch = Path(paths.get("watch_folder", str(Path.home()/ "Downloads"))).expanduser()
    exports = data_dir()/paths.get("exports_dir","exports")
    reports = data_dir()/paths.get("reports_dir","reports")
    staging = data_dir()/paths.get("staging_dir","staging")
    trash = data_dir()/paths.get("trash_dir","trash")
    thumbs = cache_dir()/ "thumbs"
    temp_r = cache_dir()/ "temp_renders"

    ok_ffmpeg = have("ffmpeg") and have("ffprobe")
    ok_watch = watch.exists()

    writable = {}
    for key, p in [("exports", exports), ("reports", reports), ("staging", staging), ("trash", trash), ("thumbs", thumbs), ("temp_renders", temp_r)]:
        ok, err = writable_dir(p)
        writable[key] = {"ok": ok, "path": str(p), "error": err}

    free_mb = free_space_mb(data_dir())
    ok_space = (free_mb >= min_free_mb) if free_mb >= 0 else True

    font = find_font()
    ok_font = font is not None

    overall_ok = ok_ffmpeg and ok_watch and ok_space and all(v["ok"] for v in writable.values())

    rec = []
    if not ok_ffmpeg:
        rec.append("ffmpeg_install")
    if not ok_watch:
        rec.append("set_watchfolder")
    if not ok_space:
        rec.append("free_space")
    if not ok_font:
        rec.append("install_font")

    return {
        "at": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "overall_ok": overall_ok,
        "ffmpeg_ok": ok_ffmpeg,
        "watchfolder_ok": ok_watch,
        "watchfolder": str(watch),
        "free_mb": free_mb,
        "min_free_mb": min_free_mb,
        "space_ok": ok_space,
        "font_ok": ok_font,
        "font": font or "",
        "writable": writable,
        "recommendations": rec
    }

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
