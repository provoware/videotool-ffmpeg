#!/usr/bin/env python3
"""
Quarantäne-Worker: bearbeitet einen Quarantäne-Auftrag erneut.
- liest Tagesliste quarantine_jobs_YYYY-MM-DD.json
- nimmt job_id oder nimmt den ersten 'bereit' Job
- rendert neu (Ton Safe)
- validiert
- wenn ok: export + commit, setzt status=erledigt
- wenn fail: tries++ und ggf. status=fost (fest) bei max_tries
- aktualisiert list_status: abgehakt/offen
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from paths import assets_dir, config_dir, cache_dir
from logging_utils import log_exception
from validation_utils import (
    PathValidationError,
    ensure_existing_file,
    ensure_output_path,
)


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_slug(s: str, maxlen: int = 120, fallback: str = "unbenannt") -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    s = s.strip("._-")
    if not s:
        s = fallback
    return s[:maxlen] if len(s) > maxlen else s


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def ffprobe_json(path: Path) -> dict:
    path = ensure_existing_file(path, "FFprobe-Eingabe")
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def update_list_status(doc: dict) -> dict:
    total = len(doc.get("items", []))
    done = sum(1 for it in doc.get("items", []) if it.get("status") == "erledigt")
    postponed = sum(
        1 for it in doc.get("items", []) if it.get("status") == "zurueckgestellt"
    )
    hard = sum(1 for it in doc.get("items", []) if it.get("status") == "fest")
    openish = sum(
        1 for it in doc.get("items", []) if it.get("status") in ("bereit", "laeuft")
    )
    doc["summary"] = {
        "total": total,
        "done": done,
        "postponed": postponed,
        "hard_cases": hard,
        "open": openish,
    }
    if hard == 0 and openish == 0:
        doc["list_status"] = "abgehakt"
        doc["closed_at"] = (
            doc.get("closed_at")
            or datetime.utcnow().isoformat(timespec="seconds") + "Z"
        )
    else:
        doc["list_status"] = "offen"
        doc["closed_at"] = None
    return doc


def pick_job(doc: dict, job_id: str | None):
    if job_id:
        for it in doc.get("items", []):
            if it.get("job_id") == job_id:
                return it
        return None
    # first ready
    for it in doc.get("items", []):
        if it.get("status") == "bereit":
            return it
    return None


def validate_settings(settings: dict) -> tuple[bool, str]:
    if not isinstance(settings, dict):
        return False, "Einstellungen unlesbar. Aktion: Einstellungen reparieren."
    paths = settings.get("paths")
    if not isinstance(paths, dict):
        return False, "Pfad-Einstellungen fehlen. Aktion: Einstellungen reparieren."
    required = [
        "base_data_dir",
        "exports_dir",
        "quarantine_dir",
        "quarantine_jobs_dir",
        "library_audio_dir",
        "library_images_dir",
    ]
    missing = [key for key in required if not paths.get(key)]
    if missing:
        missing_list = ", ".join(missing)
        return (
            False,
            "Fehlende Pfade in Einstellungen "
            f"({missing_list}). Aktion: Einstellungen reparieren.",
        )
    audio = settings.get("audio")
    if not isinstance(audio, dict):
        return False, "Audio-Einstellungen fehlen. Aktion: Einstellungen reparieren."
    for key in ["target_bitrate_kbps", "target_samplerate_hz", "min_bitrate_kbps"]:
        if audio.get(key) is None:
            return (
                False,
                f"Audio-Einstellung fehlt ({key}). Aktion: Einstellungen reparieren.",
            )
    return True, ""


def run(job_id: str | None = None) -> int:
    settings = load_json(config_dir() / "settings.json", {})
    ok, message = validate_settings(settings)
    if not ok:
        log_exception(
            "quarantine_worker.settings_invalid",
            ValueError(message),
            extra={"settings_path": str(config_dir() / "settings.json")},
        )
        return 1
    base = Path(settings["paths"]["base_data_dir"])
    today = datetime.now().strftime("%Y-%m-%d")
    qjobs = (
        base
        / settings["paths"]["quarantine_jobs_dir"]
        / f"quarantine_jobs_{today}.json"
    )
    doc = load_json(
        qjobs,
        default={
            "schema_version": 1,
            "date": today,
            "items": [],
            "list_status": "offen",
            "closed_at": None,
        },
    )
    job = pick_job(doc, job_id)
    if not job:
        return 0

    if not (have("ffmpeg") and have("ffprobe")):
        job["status"] = "fest"
        job["summary"] = "FFmpeg fehlt"
        job["error"] = "ffmpeg oder ffprobe nicht gefunden. Aktion: ffmpeg installieren."
        save_json(qjobs, update_list_status(doc))
        return 1

    job["status"] = "laeuft"
    job["tries"] = int(job.get("tries", 0)) + 1
    save_json(qjobs, update_list_status(doc))

    audio_target = Path(job["paths"].get("staging_audio", ""))
    image_target = (
        Path(job["paths"].get("staging_image", "")) if job.get("paths") else Path()
    )
    try:
        audio_target = ensure_existing_file(audio_target, "Audio-Quelle")
    except PathValidationError as exc:
        job["status"] = "fest"
        job["summary"] = "Quelle fehlt (Audio nicht gefunden)"
        job["error"] = str(exc)
        save_json(qjobs, update_list_status(doc))
        return 1

    try:
        image_target = ensure_existing_file(image_target, "Bild-Quelle")
    except PathValidationError:
        # fallback preset cover
        image_target = assets_dir() / "default_assets" / "preset_cover.jpg"

    day = today
    exports_day = base / settings["paths"]["exports_dir"] / day
    exports_day.mkdir(parents=True, exist_ok=True)
    quarantine_day = base / settings["paths"]["quarantine_dir"] / day
    quarantine_day.mkdir(parents=True, exist_ok=True)
    lib_a = base / settings["paths"]["library_audio_dir"] / day
    lib_i = base / settings["paths"]["library_images_dir"] / day
    lib_a.mkdir(parents=True, exist_ok=True)
    lib_i.mkdir(parents=True, exist_ok=True)

    out_name = (
        safe_slug(Path(job.get("output_file", "")).stem or f"rework_{job['job_id']}")
        + ".mp4"
    )
    try:
        image_target = ensure_existing_file(image_target, "Bild-Quelle")
    except PathValidationError as exc:
        job["status"] = "fest"
        job["summary"] = "Bildquelle ungültig"
        job["error"] = str(exc)
        save_json(qjobs, update_list_status(doc))
        return 1
    out_tmp = ensure_output_path(
        cache_dir() / "temp_renders" / out_name, "Zwischenausgabe"
    )
    out_final = exports_day / out_name

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_target),
        "-i",
        str(audio_target),
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        f"{settings['audio']['target_bitrate_kbps']}k",
        "-ar",
        str(settings["audio"]["target_samplerate_hz"]),
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_tmp),
    ]

    try:
        subprocess.check_call(cmd)
    except Exception as e:
        job["status"] = (
            "bereit" if job["tries"] < int(job.get("max_tries", 3)) else "fest"
        )
        job["summary"] = "Neu machen fehlgeschlagen"
        job["error"] = str(e)
        # keep last output in quarantine
        if out_tmp.exists():
            q_out = quarantine_day / (out_tmp.stem + "_quarantaene.mp4")
            shutil.move(str(out_tmp), str(q_out))
            job["output_file"] = q_out.name
            job.setdefault("paths", {})["quarantine_dir"] = str(quarantine_day)
        save_json(qjobs, update_list_status(doc))
        return 2

    # validate audio
    ok_audio = False
    bitrate_kbps = None
    samplerate = None
    try:
        info = ffprobe_json(out_tmp)
        astreams = [
            s for s in info.get("streams", []) if s.get("codec_type") == "audio"
        ]
        if astreams:
            samplerate = int(astreams[0].get("sample_rate") or 0)
            br = astreams[0].get("bit_rate") or info.get("format", {}).get("bit_rate")
            if br:
                bitrate_kbps = int(int(br) / 1000)
        ok_audio = (samplerate == settings["audio"]["target_samplerate_hz"]) and (
            bitrate_kbps is None
            or bitrate_kbps >= settings["audio"]["min_bitrate_kbps"]
        )
        job["validation"] = {
            "audio_bitrate_kbps": bitrate_kbps,
            "audio_samplerate_hz": samplerate,
            "ok": bool(ok_audio),
        }
    except Exception as e:
        job["validation"] = {"ok": False, "error": str(e)}
        ok_audio = False

    if not ok_audio:
        q_out = quarantine_day / (out_tmp.stem + "_quarantaene.mp4")
        shutil.move(str(out_tmp), str(q_out))
        job["status"] = (
            "bereit" if job["tries"] < int(job.get("max_tries", 3)) else "fest"
        )
        job["summary"] = "Tonprüfung fehlgeschlagen"
        job["output_file"] = q_out.name
        job.setdefault("paths", {})["quarantine_dir"] = str(quarantine_day)
        save_json(qjobs, update_list_status(doc))
        return 3

    # commit output
    shutil.move(str(out_tmp), str(out_final))
    job["status"] = "erledigt"
    job["output_final"] = str(out_final)
    save_json(qjobs, update_list_status(doc))
    return 0


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--job-id", default=None)
    args = ap.parse_args()
    run(args.job_id)
