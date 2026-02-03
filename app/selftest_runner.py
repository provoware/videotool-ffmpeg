#!/usr/bin/env python3
"""
Selftest (Iteration 1.0.46):
- erzeugt einen internen Test-Ordner
- führt vier Läufe aus:
  A) Erfolgs-Lauf (Ton Safe) → 1 fertige Ausgabe
  B) Quarantäne-Lauf (absichtlich niedrige Audio-Bitrate) → 1 Quarantäne-Auftrag
  C) Mittel-Bitrate-Lauf (weitere Bitraten-Variante) → 1 fertige Ausgabe
  D) Fehler/Größe-Lauf (defekte + große Datei) → robuste Prüfung
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


def require_setting(settings: dict, *keys: str) -> None:
    cur = settings
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            raise ValueError(f"Selftest-Config unvollständig: {'.'.join(keys)} fehlt.")
        cur = cur[key]


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


def add_corrupt_audio(folder: Path) -> Path:
    corrupt = folder / "corrupt_audio.wav"
    corrupt.write_bytes(b"")
    return corrupt


def add_large_audio(source: Path, folder: Path, target_size_bytes: int) -> Path:
    if target_size_bytes <= 0:
        raise ValueError(
            "Selftest-Config unvollständig: target_size_bytes muss > 0 sein."
        )
    large = folder / "large_audio.wav"
    shutil.copy(source, large)
    current = large.stat().st_size
    if current < target_size_bytes:
        extra = target_size_bytes - current
        with large.open("ab") as handle:
            handle.write(b"\0" * extra)
    return large


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
    try:
        require_setting(settings_base, "paths", "quarantine_jobs_dir")
    except ValueError as exc:
        print(f"Selftest abgebrochen: {exc}")
        return 1

    # sandbox base dir
    sandbox = data_dir() / "selftest"
    base_ok = sandbox / "ok"
    base_bad = sandbox / "quarantine"
    base_mid = sandbox / "mid"
    base_edge = sandbox / "edge"
    watch_ok = base_ok / "watch"
    watch_bad = base_bad / "watch"
    watch_mid = base_mid / "watch"
    watch_edge = base_edge / "watch"

    # Prepare watch folders
    try:
        prepare_watch(watch_ok)
        prepare_watch(watch_bad)
        prepare_watch(watch_mid)
        prepare_watch(watch_edge)
    except FileNotFoundError as exc:
        print(f"Selftest abgebrochen: {exc}")
        return 1

    add_corrupt_audio(watch_edge)
    add_large_audio(
        assets_dir() / "default_assets" / "test_audio_10s.wav",
        watch_edge,
        5 * 1024 * 1024,
    )

    scenarios = [
        {
            "name": "ok",
            "base": base_ok,
            "watch": watch_ok,
            "target_bitrate": 320,
            "min_bitrate": 192,
        },
        {
            "name": "quarantine",
            "base": base_bad,
            "watch": watch_bad,
            "target_bitrate": 96,
            "min_bitrate": 192,
        },
        {
            "name": "mid_bitrate",
            "base": base_mid,
            "watch": watch_mid,
            "target_bitrate": 160,
            "min_bitrate": 128,
        },
        {
            "name": "edge_files",
            "base": base_edge,
            "watch": watch_edge,
            "target_bitrate": 320,
            "min_bitrate": 192,
        },
    ]

    main_reports = data_dir() / "reports"
    main_reports.mkdir(parents=True, exist_ok=True)
    report_map: dict[str, str] = {}
    sandbox_map: dict[str, str] = {}

    for scenario in scenarios:
        base_dir = scenario["base"]
        watch_dir = scenario["watch"]
        sandbox_map[scenario["name"]] = str(base_dir)
        s_path, r_path = make_overrides(
            base_dir,
            watch_dir,
            settings_base,
            rules_base,
            target_bitrate=int(scenario["target_bitrate"]),
            min_bitrate=int(scenario["min_bitrate"]),
        )
        report_path = run_runner(s_path, r_path)
        report_copy = main_reports / f"run_selftest_{ts}_{scenario['name']}.json"
        shutil.copy(report_path, report_copy)
        report_map[scenario["name"]] = str(report_copy)

        qjobs = (
            base_dir
            / settings_base["paths"]["quarantine_jobs_dir"]
            / f"quarantine_jobs_{today}.json"
        )
        if qjobs.exists():
            qjobs_copy = (
                main_reports / f"selftest_quarantine_jobs_{ts}_{scenario['name']}.json"
            )
            shutil.copy(qjobs, qjobs_copy)
            report_doc = load_json(report_copy, {})
            report_doc["selftest"] = {"quarantine_jobs_file": str(qjobs_copy)}
            save_json(report_copy, report_doc)

    summary = {
        "schema_version": 1,
        "selftest_id": ts,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "reports": report_map,
        "sandbox": sandbox_map,
    }
    summary_path = main_reports / f"selftest_summary_{ts}.json"
    save_json(summary_path, summary)

    print(str(summary_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
