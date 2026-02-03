#!/usr/bin/env python3
"""
Selftest (Iteration 0.9.2):
- erzeugt einen internen Test-Ordner
- führt zwei Läufe aus:
  A) Erfolgs-Lauf (Ton Safe) → 1 fertige Ausgabe
  B) Quarantäne-Lauf (absichtlich niedrige Audio-Bitrate) → 1 Quarantäne-Auftrag
- kopiert die erzeugten Reports in den normalen Reports-Ordner, damit die GUI sofort "Letzte Nacht" aktualisieren kann.
- schreibt eine Selftest-Zusammenfassung als JSON.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from paths import app_dir, assets_dir, config_dir, data_dir


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def require_asset(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} fehlt: {path}")


def run_runner(settings_path: Path, rules_path: Path) -> Path:
    # returns report path printed by automation_runner
    cmd = [
        str(app_dir() / "automation_runner.py"),
        "--settings",
        str(settings_path),
        "--rules",
        str(rules_path),
    ]
    out = subprocess.check_output([sys.executable] + cmd, text=True).strip()
    return Path(out)


def prepare_watch(folder: Path):
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)

    assets = assets_dir() / "default_assets"
    image_asset = assets / "test_image.jpg"
    audio_asset = assets / "test_audio_10s.wav"
    require_asset(image_asset, "Testbild")
    require_asset(audio_asset, "Testaudio")
    # Copy one image
    shutil.copy(image_asset, folder / "test_image.jpg")
    # Copy audio (wav)
    shutil.copy(audio_asset, folder / "test_audio_10s.wav")


def make_overrides(
    base_data_dir: Path,
    watch_folder: Path,
    settings_base: dict,
    rules_base: dict,
    target_bitrate: int,
    min_bitrate: int,
) -> tuple[Path, Path]:
    o = base_data_dir / "overrides"
    o.mkdir(parents=True, exist_ok=True)
    s = json.loads(json.dumps(settings_base))
    s["paths"]["base_data_dir"] = str(base_data_dir)
    s["paths"]["watch_folder"] = str(watch_folder)
    s["audio"]["target_bitrate_kbps"] = target_bitrate
    s["audio"]["min_bitrate_kbps"] = min_bitrate
    s_path = o / f"settings_{target_bitrate}k.json"
    save_json(s_path, s)

    r = json.loads(json.dumps(rules_base))
    r["scan"]["audio_extensions"] = [".wav", ".mp3", ".flac", ".m4a"]
    r["scan"]["image_extensions"] = [".jpg", ".jpeg", ".png", ".webp"]
    # fallback image path remains as in project
    r_path = o / f"rules_{target_bitrate}k.json"
    save_json(r_path, r)
    return s_path, r_path


def main():
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    today = datetime.now().strftime("%Y-%m-%d")

    settings_base = load_json(config_dir() / "settings.json", {})
    rules_base = load_json(config_dir() / "automation_rules.json", {})

    # sandbox base dir
    sandbox = data_dir() / "selftest"
    base_ok = sandbox / "ok"
    base_bad = sandbox / "quarantine"
    watch_ok = base_ok / "watch"
    watch_bad = base_bad / "watch"

    # Prepare watch folders
    try:
        prepare_watch(watch_ok)
        prepare_watch(watch_bad)
    except FileNotFoundError as exc:
        print(f"Selftest abgebrochen: {exc}")
        return 1

    # Create overrides:
    # A) OK: target 320, min 192
    s_ok, r_ok = make_overrides(
        base_ok,
        watch_ok,
        settings_base,
        rules_base,
        target_bitrate=320,
        min_bitrate=192,
    )
    # B) BAD: target 96, min 192 -> should fail validation and create quarantine job
    s_bad, r_bad = make_overrides(
        base_bad,
        watch_bad,
        settings_base,
        rules_base,
        target_bitrate=96,
        min_bitrate=192,
    )

    # Run A
    rep_ok = run_runner(s_ok, r_ok)
    # Run B
    rep_bad = run_runner(s_bad, r_bad)

    # Copy reports to main reports folder (so GUI sees them)
    main_reports = data_dir() / "reports"
    main_reports.mkdir(parents=True, exist_ok=True)
    rep_ok_copy = main_reports / f"run_selftest_{ts}_ok.json"
    rep_bad_copy = main_reports / f"run_selftest_{ts}_quarantine.json"
    shutil.copy(rep_ok, rep_ok_copy)
    shutil.copy(rep_bad, rep_bad_copy)

    # Also copy quarantine jobs list from bad run into a selftest-namespaced file inside reports
    qjobs = (
        base_bad
        / settings_base["paths"]["quarantine_jobs_dir"]
        / f"quarantine_jobs_{today}.json"
    )
    qjobs_copy = main_reports / f"selftest_quarantine_jobs_{ts}.json"
    if qjobs.exists():
        shutil.copy(qjobs, qjobs_copy)
        # Patch the copied bad report to point to this file
        bad_doc = load_json(rep_bad_copy, {})
        bad_doc["selftest"] = {"quarantine_jobs_file": str(qjobs_copy)}
        save_json(rep_bad_copy, bad_doc)

    summary = {
        "schema_version": 1,
        "selftest_id": ts,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "reports": {"ok": str(rep_ok_copy), "quarantine": str(rep_bad_copy)},
        "sandbox": {"ok": str(base_ok), "quarantine": str(base_bad)},
    }
    save_json(main_reports / f"selftest_summary_{ts}.json", summary)

    print(str(rep_bad_copy))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
