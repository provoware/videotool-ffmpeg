#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from io_utils import load_json
from logging_utils import log_message
from paths import config_dir, data_dir, cache_dir
from validation_utils import validate_settings_paths, validate_settings_schema


def debug_enabled() -> bool:
    raw = os.getenv("MODULTOOL_DEBUG", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def log_debug(message: str, level: str = "DEBUG") -> None:
    log_message(message, level=level, context="preflight")


def parse_min_free_mb(settings: dict) -> tuple[int, bool, str]:
    raw = settings.get("maintenance", {}).get("min_free_mb", 1024)
    try:
        if isinstance(raw, bool):
            raise ValueError("bool is not a valid min_free_mb")
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
        test = p / f".modultool_write_test_{uuid4().hex}.tmp"
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


def load_theme_names() -> set[str]:
    data = load_json(config_dir() / "themes.json", {})
    names: set[str] = set()
    themes = data.get("themes")
    if isinstance(themes, dict):
        names.update(k for k in themes.keys() if isinstance(k, str) and k.strip())
    qss = data.get("qss")
    if isinstance(qss, dict):
        names.update(k for k in qss.keys() if isinstance(k, str) and k.strip())
    return names


def run(settings_path: Path | None = None) -> dict:
    if settings_path is None:
        settings_path = config_dir() / "settings.json"
    debug = debug_enabled()
    if debug:
        log_debug(f"Preflight start (settings={settings_path})")
    settings = load_json(settings_path, {})
    paths = settings.get("paths", {})
    ui = settings.get("ui", {})
    schema_errors = validate_settings_schema(settings)
    path_errors = validate_settings_paths(settings)
    min_free_mb, min_free_ok, min_free_raw = parse_min_free_mb(settings)
    default_theme = "hochkontrast_dunkel"
    theme_input = ui.get("theme", default_theme)
    theme_names = load_theme_names()
    theme_ok = True
    theme = default_theme
    if isinstance(theme_input, str) and theme_input.strip():
        candidate = theme_input.strip()
        if theme_names and candidate not in theme_names:
            theme_ok = False
            theme = default_theme
            if debug:
                log_debug(
                    f"Theme ungültig: {candidate} -> {default_theme}",
                    level="WARN",
                )
        else:
            theme = candidate
    else:
        if theme_names:
            theme_ok = False
            if debug:
                log_debug("Theme fehlt oder leer, Standard wird genutzt.", level="WARN")
        theme = default_theme

    raw_watch = paths.get("watch_folder")
    watch_invalid = False
    if isinstance(raw_watch, Path):
        watch_value = raw_watch
    elif isinstance(raw_watch, str) and raw_watch.strip():
        watch_value = raw_watch.strip()
    else:
        watch_value = str(Path.home() / "Downloads")
        if raw_watch is not None and raw_watch != "":
            watch_invalid = True
        if raw_watch == "":
            watch_invalid = True

    watch = Path(watch_value).expanduser()
    watch_created = False
    if not watch.exists():
        try:
            watch.mkdir(parents=True, exist_ok=True)
            watch_created = True
            if debug:
                log_debug(f"Watchfolder created: {watch}")
        except Exception as exc:
            if debug:
                log_debug(f"Watchfolder create failed: {watch} ({exc})", level="WARN")
    base_raw = paths.get("base_data_dir")
    base_input = "" if base_raw is None else str(base_raw)
    base_dir = data_dir()
    base_ok = True
    base_writable_ok = True
    base_writable_error = ""
    if isinstance(base_raw, str) and base_raw.strip():
        base_dir = Path(base_raw).expanduser()
        base_writable_ok, base_writable_error = writable_dir(base_dir)
    else:
        base_ok = False
        base_writable_ok = False
        base_writable_error = "base_data_dir_missing_or_invalid"

    exports = base_dir / paths.get("exports_dir", "exports")
    reports = base_dir / paths.get("reports_dir", "reports")
    staging = base_dir / paths.get("staging_dir", "staging")
    trash = base_dir / paths.get("trash_dir", "trash")
    thumbs = cache_dir() / "thumbs"
    temp_r = cache_dir() / "temp_renders"

    ok_ffmpeg = have("ffmpeg") and have("ffprobe")
    ok_watch = watch.exists() and watch.is_dir()
    watch_writable_ok = True
    watch_writable_error = ""
    if ok_watch:
        watch_writable_ok, watch_writable_error = writable_dir(watch)
    else:
        watch_writable_ok = False
        watch_writable_error = "watchfolder_missing_or_invalid"

    config_root = config_dir()
    config_writable_ok, config_writable_error = writable_dir(config_root)

    writable = {
        "base_data_dir": {
            "ok": base_writable_ok,
            "path": str(base_dir),
            "error": base_writable_error,
        }
    }
    if not base_ok:
        path_errors.append("paths.base_data_dir:missing_or_invalid")
    elif not base_writable_ok:
        path_errors.append("paths.base_data_dir:not_writable")

    for key, p in [
        ("config", config_root),
        ("exports", exports),
        ("reports", reports),
        ("staging", staging),
        ("trash", trash),
        ("thumbs", thumbs),
        ("temp_renders", temp_r),
    ]:
        ok, err = writable_dir(p)
        writable[key] = {"ok": ok, "path": str(p), "error": err}
        if not ok:
            if key == "config":
                path_errors.append("config_dir:not_writable")
            else:
                path_errors.append(f"paths.{key}:not_writable")

    free_mb = free_space_mb(data_dir())
    ok_space = (free_mb >= min_free_mb) if free_mb >= 0 else True

    font = find_font()
    ok_font = font is not None

    settings_ok = min_free_ok and not schema_errors and not path_errors
    overall_ok = (
        ok_ffmpeg
        and ok_watch
        and ok_space
        and watch_writable_ok
        and all(v["ok"] for v in writable.values())
        and settings_ok
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
    if not base_ok:
        rec.append("base_data_dir_invalid")
    if base_ok and not base_writable_ok:
        rec.append("base_data_dir_not_writable")
    if not config_writable_ok:
        rec.append("config_not_writable")
    if not min_free_ok:
        rec.append("min_free_mb_invalid")
    if not theme_ok:
        rec.append("theme_invalid")
    if ok_watch and not watch_writable_ok:
        rec.append("watchfolder_not_writable")
    if watch_invalid:
        rec.append("watchfolder_invalid")
    if not ok_watch:
        path_errors.append("paths.watch_folder:not_found")
    if ok_watch and not watch_writable_ok:
        path_errors.append("paths.watch_folder:not_writable")
    if schema_errors:
        rec.append("settings_schema_invalid")
    if path_errors:
        rec.append("settings_paths_invalid")

    result = {
        "at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "overall_ok": overall_ok,
        "ffmpeg_ok": ok_ffmpeg,
        "watchfolder_ok": ok_watch,
        "watchfolder": str(watch),
        "watchfolder_input": "" if raw_watch is None else str(raw_watch),
        "watchfolder_created": watch_created,
        "watchfolder_writable_ok": watch_writable_ok,
        "watchfolder_writable_error": watch_writable_error,
        "base_data_dir": str(base_dir),
        "base_data_dir_input": base_input,
        "base_data_dir_ok": base_ok,
        "base_data_dir_writable_ok": base_writable_ok,
        "base_data_dir_writable_error": base_writable_error,
        "free_mb": free_mb,
        "min_free_mb_ok": min_free_ok,
        "min_free_mb_input": min_free_raw,
        "min_free_mb": min_free_mb,
        "theme_ok": theme_ok,
        "theme": theme,
        "theme_input": "" if theme_input is None else str(theme_input),
        "settings_ok": settings_ok,
        "space_ok": ok_space,
        "font_ok": ok_font,
        "font": font or "",
        "writable": writable,
        "recommendations": rec,
        "settings_schema_errors": schema_errors,
        "settings_path_errors": path_errors,
    }
    if debug:
        log_debug(
            "Preflight summary "
            f"overall_ok={overall_ok} ffmpeg_ok={ok_ffmpeg} "
            f"watchfolder_ok={ok_watch} watchfolder='{watch}' "
            f"watch_writable_ok={watch_writable_ok} base_ok={base_ok} "
            f"base_writable_ok={base_writable_ok} config_writable_ok={config_writable_ok} "
            f"theme='{theme}' theme_ok={theme_ok} free_mb={free_mb} "
            f"min_free_mb={min_free_mb} settings_ok={settings_ok} rec={rec}"
        )
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
