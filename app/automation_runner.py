#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from perf import get_threads
from paths import config_dir, logs_dir, cache_dir, repo_root
from logging_utils import log_exception


def default_settings_path() -> Path:
    return config_dir() / "settings.json"


def default_rules_path() -> Path:
    return config_dir() / "automation_rules.json"


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def log_line(logs_dir: Path, msg: str):
    logs_dir.mkdir(parents=True, exist_ok=True)
    p = logs_dir / "activity_log.jsonl"
    entry = {"at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "msg": msg}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def validate_settings(settings: dict, logs_dir: Path) -> dict:
    if not isinstance(settings, dict):
        log_line(
            logs_dir,
            "Automatik abgebrochen: Einstellungen sind unlesbar. Aktion: Einstellungen reparieren.",
        )
        raise SystemExit(1)
    paths = settings.get("paths")
    if not isinstance(paths, dict):
        log_line(
            logs_dir,
            "Automatik abgebrochen: Pfad-Einstellungen fehlen. Aktion: Einstellungen reparieren.",
        )
        raise SystemExit(1)
    required = [
        "watch_folder",
        "base_data_dir",
        "exports_dir",
        "library_audio_dir",
        "library_images_dir",
        "quarantine_dir",
        "quarantine_jobs_dir",
        "reports_dir",
        "trash_dir",
        "staging_dir",
    ]
    missing = [key for key in required if not paths.get(key)]
    if missing:
        missing_list = ", ".join(missing)
        log_line(
            logs_dir,
            "Automatik abgebrochen: fehlende Pfade in Einstellungen "
            f"({missing_list}). Aktion: Einstellungen reparieren.",
        )
        raise SystemExit(1)
    return settings


def have(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def stable_file(p: Path, seconds: int = 8) -> bool:
    try:
        s1 = p.stat().st_size
        time.sleep(seconds)
        s2 = p.stat().st_size
        return s1 == s2 and s2 > 0
    except Exception:
        return False


def safe_slug(s: str, maxlen: int = 120) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    s = s.strip("._-")
    return s[:maxlen] if len(s) > maxlen else s


def ffprobe_json(path: Path) -> dict:
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


def build_output_name(
    audio_path: Path, preset: str, sw: bool, idx: int, settings: dict
) -> str:
    tmpl = settings["naming"]["template_batch"]
    dt = datetime.now().strftime("%Y-%m-%d")
    tm = datetime.now().strftime("%H%M%S")
    audio = safe_slug(audio_path.stem)
    nummer = f"{idx:03d}"
    sws = "_sw" if sw else ""
    name = tmpl.format(
        audio=audio,
        vorlage=safe_slug(preset),
        datum=dt,
        uhrzeit=tm,
        nummer=nummer,
        sw=sws,
    )
    return safe_slug(name) + ".mp4"


def ensure_structure(base: Path, settings):
    for rel in [
        settings["paths"]["exports_dir"],
        settings["paths"]["library_audio_dir"],
        settings["paths"]["library_images_dir"],
        settings["paths"]["quarantine_dir"],
        settings["paths"]["quarantine_jobs_dir"],
        settings["paths"]["reports_dir"],
        settings["paths"]["trash_dir"],
        settings["paths"]["staging_dir"],
    ]:
        (base / rel).mkdir(parents=True, exist_ok=True)


def load_or_create_quarantine_list(base: Path, qjobs_rel: str, day: str) -> Path:
    qdir = base / qjobs_rel
    qdir.mkdir(parents=True, exist_ok=True)
    qfile = qdir / f"quarantine_jobs_{day}.json"
    if not qfile.exists():
        doc = {
            "schema_version": 1,
            "date": day,
            "title": f"Quarantäne-Aufträge – {day}",
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "list_status": "offen",
            "closed_at": None,
            "summary": {
                "total": 0,
                "done": 0,
                "postponed": 0,
                "hard_cases": 0,
                "open": 0,
            },
            "items": [],
        }
        save_json(qfile, doc)
    return qfile


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


def append_quarantine_job(
    qfile: Path,
    run_id: str,
    nr: int,
    preset: str,
    output_quarantine: Path,
    staging_audio: Path,
    staging_image: Path | None,
    reason: str,
    validation: dict,
):
    doc = load_json(qfile, default={})
    items = doc.get("items", [])
    job_id = f"q_{run_id}_{nr:04d}"
    item = {
        "job_id": job_id,
        "source_run_id": run_id,
        "status": "bereit",
        "label": "quarantaene",
        "summary": reason,
        "recommended_action": "neu_machen_ton_safe",
        "tries": 0,
        "max_tries": 3,
        "preset": preset,
        "output_file": output_quarantine.name,
        "paths": {
            "quarantine_dir": str(output_quarantine.parent),
            "staging_audio": str(staging_audio),
            "staging_image": str(staging_image) if staging_image else "",
        },
        "validation": validation or {},
    }
    items.append(item)
    doc["items"] = items
    save_json(qfile, update_list_status(doc))


def run(settings_path: Path, rules_path: Path) -> Path:
    settings = load_json(settings_path, {})
    threads = get_threads(settings_path)
    rules = load_json(rules_path, {})

    logs_dir_path = logs_dir()
    validate_settings(settings, logs_dir_path)

    base = Path(settings["paths"]["base_data_dir"])
    ensure_structure(base, settings)

    if not have("ffmpeg") or not have("ffprobe"):
        log_line(
            logs_dir_path, "Automatik abgebrochen: ffmpeg/ffprobe fehlt (Setup nötig)."
        )
        raise SystemExit(2)

    watch = Path(settings["paths"]["watch_folder"]).expanduser()
    if not watch.exists():
        log_line(logs_dir_path, f"Automatik abgebrochen: Watchfolder fehlt: {watch}")
        raise SystemExit(1)

    day = datetime.now().strftime("%Y-%m-%d")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    lock = base / settings["paths"]["staging_dir"] / "automation.lock"
    if lock.exists():
        log_line(logs_dir_path, "Lock vorhanden: Automatik läuft schon. Abbruch.")
        raise SystemExit(0)
    lock.write_text(run_id, encoding="utf-8")

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "watch_folder": str(watch),
        "settings_path": str(settings_path),
        "rules_path": str(rules_path),
        "jobs": [],
        "repairs": [],
        "summary": {},
    }

    report_path: Path | None = None

    try:
        audio_exts = set(
            [
                e.lower()
                for e in rules.get("scan", {}).get(
                    "audio_extensions", [".mp3", ".wav", ".flac", ".m4a"]
                )
            ]
        )
        img_exts = set(
            [
                e.lower()
                for e in rules.get("scan", {}).get(
                    "image_extensions", [".jpg", ".jpeg", ".png", ".webp"]
                )
            ]
        )
        audios = [
            p for p in watch.iterdir() if p.is_file() and p.suffix.lower() in audio_exts
        ]
        images = [
            p for p in watch.iterdir() if p.is_file() and p.suffix.lower() in img_exts
        ]

        audios.sort(key=lambda p: p.stat().st_mtime)
        images.sort(key=lambda p: p.stat().st_mtime)

        fallback_img = (
            repo_root()
            / rules.get("pairing", {}).get(
                "fallback_image", "assets/default_assets/preset_cover.jpg"
            )
        ).resolve()
        preset_id = rules.get("presets", {}).get(
            "default_preset_id", "youtube_hd_ton_safe"
        )

        import os as _os

        fast = _os.getenv("MODULTOOL_FAST", "") == "1"
        if fast:
            W, H, FPS = (640, 360, 24)
        else:
            W, H, FPS = (1920, 1080, 30)

        staging_day = base / settings["paths"]["staging_dir"] / day
        (staging_day / "audio").mkdir(parents=True, exist_ok=True)
        (staging_day / "images").mkdir(parents=True, exist_ok=True)

        exports_day = base / settings["paths"]["exports_dir"] / day
        exports_day.mkdir(parents=True, exist_ok=True)
        quarantine_day = base / settings["paths"]["quarantine_dir"] / day
        quarantine_day.mkdir(parents=True, exist_ok=True)
        lib_a = base / settings["paths"]["library_audio_dir"] / day
        lib_i = base / settings["paths"]["library_images_dir"] / day
        lib_a.mkdir(parents=True, exist_ok=True)
        lib_i.mkdir(parents=True, exist_ok=True)

        qfile = load_or_create_quarantine_list(
            base, settings["paths"]["quarantine_jobs_dir"], day
        )

        staged_images = []
        for img in images:
            if not stable_file(img):
                report["repairs"].append(
                    {"type": "skip_unstable_image", "file": str(img)}
                )
                continue
            dst = (
                staging_day
                / "images"
                / (safe_slug(img.stem) + f"_in_work_{run_id}" + img.suffix.lower())
            )
            try:
                shutil.move(str(img), str(dst))
                staged_images.append(dst)
            except Exception as e:
                report["repairs"].append(
                    {"type": "move_fail_image", "file": str(img), "error": str(e)}
                )

        ok = 0
        qn = 0

        for idx, aud in enumerate(audios, start=1):
            job = {"nr": idx, "preset": preset_id, "status": "bereit"}
            if not stable_file(aud):
                job.update(
                    {
                        "status": "uebersprungen",
                        "reason": "download_nicht_stabil",
                        "audio": str(aud),
                    }
                )
                report["jobs"].append(job)
                continue

            aud_dst = (
                staging_day
                / "audio"
                / (safe_slug(aud.stem) + f"_in_work_{run_id}" + aud.suffix.lower())
            )
            try:
                shutil.move(str(aud), str(aud_dst))
            except Exception as e:
                job.update(
                    {
                        "status": "quarantaene",
                        "reason": "move_fail_audio",
                        "audio": str(aud),
                        "error": str(e),
                    }
                )
                report["jobs"].append(job)
                qn += 1
                continue

            img_use = (
                staged_images[idx - 1]
                if (idx - 1) < len(staged_images)
                else fallback_img
            )

            out_name = build_output_name(aud_dst, preset_id, False, idx, settings)
            out_tmp = cache_dir() / "temp_renders" / out_name
            out_tmp.parent.mkdir(parents=True, exist_ok=True)
            out_final = exports_day / out_name

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
            ]
            if threads:
                cmd += ["-threads", str(threads)]
            cmd += [
                "-loop",
                "1",
                "-i",
                str(img_use),
                "-i",
                str(aud_dst),
                "-vf",
                f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
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
                str(FPS),
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

            job.update(
                {
                    "audio": str(aud_dst),
                    "image": str(img_use),
                    "output_tmp": str(out_tmp),
                }
            )
            try:
                subprocess.check_call(cmd)
            except Exception as e:
                qn += 1
                job.update(
                    {"status": "quarantaene", "reason": "ffmpeg_fail", "error": str(e)}
                )
                # Create a small marker file so quarantine jobs always have an output_file
                marker = quarantine_day / (Path(out_name).stem + "_quarantaene.txt")
                marker.write_text(
                    "FFmpeg Fehler beim Export. Siehe Report.\n", encoding="utf-8"
                )
                append_quarantine_job(
                    qfile,
                    run_id,
                    idx,
                    preset_id,
                    marker,
                    aud_dst,
                    img_use if img_use != fallback_img else None,
                    "ffmpeg_fail",
                    {},
                )
                report["jobs"].append(job)
                continue

            # Validate audio with deterministic rule:
            # If bitrate cannot be determined, treat as FAIL when a minimum is configured.
            ok_audio = False
            bitrate_kbps = None
            samplerate = None
            validation = {}
            try:
                info = ffprobe_json(out_tmp)
                astreams = [
                    s for s in info.get("streams", []) if s.get("codec_type") == "audio"
                ]
                if astreams:
                    samplerate = int(astreams[0].get("sample_rate") or 0)
                    br = astreams[0].get("bit_rate") or info.get("format", {}).get(
                        "bit_rate"
                    )
                    if br:
                        bitrate_kbps = int(int(br) / 1000)
                min_br = int(settings["audio"]["min_bitrate_kbps"])
                ok_bitrate = (
                    (bitrate_kbps is not None and bitrate_kbps >= min_br)
                    if min_br > 0
                    else True
                )
                ok_sr = samplerate == int(settings["audio"]["target_samplerate_hz"])
                ok_audio = ok_bitrate and ok_sr
                validation = {
                    "audio_bitrate_kbps": bitrate_kbps,
                    "audio_samplerate_hz": samplerate,
                    "ok": bool(ok_audio),
                }
                job["validation"] = validation
            except Exception as e:
                job["validation"] = {"ok": False, "error": str(e)}
                ok_audio = False

            if not ok_audio:
                qn += 1
                q_out = quarantine_day / (out_tmp.stem + "_quarantaene.mp4")
                shutil.move(str(out_tmp), str(q_out))
                job.update(
                    {
                        "status": "quarantaene",
                        "reason": "audio_check_fail",
                        "output_quarantine": str(q_out),
                    }
                )
                append_quarantine_job(
                    qfile,
                    run_id,
                    idx,
                    preset_id,
                    q_out,
                    aud_dst,
                    img_use if img_use != fallback_img else None,
                    "audio_check_fail",
                    validation,
                )
                report["jobs"].append(job)
                continue

            # Commit output
            shutil.move(str(out_tmp), str(out_final))

            # Commit inputs
            used_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            aud_final = lib_a / (
                safe_slug(aud_dst.stem) + f"_used_{used_ts}" + aud_dst.suffix.lower()
            )
            shutil.move(str(aud_dst), str(aud_final))

            img_final = ""
            if img_use != fallback_img and Path(img_use).exists():
                img_p = Path(img_use)
                img_final_path = lib_i / (
                    safe_slug(img_p.stem) + f"_used_{used_ts}" + img_p.suffix.lower()
                )
                shutil.move(str(img_p), str(img_final_path))
                img_final = str(img_final_path)

            job.update(
                {
                    "status": "fertig",
                    "output_final": str(out_final),
                    "inputs_final": {"audio": str(aud_final), "image": img_final},
                }
            )
            report["jobs"].append(job)
            ok += 1

        report["finished_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        report["summary"] = {"fertig": ok, "quarantaene": qn, "gesamt": len(audios)}
        rdir = base / settings["paths"]["reports_dir"]
        rdir.mkdir(parents=True, exist_ok=True)
        report_path = rdir / f"run_{run_id}.json"
        save_json(report_path, report)
        log_line(
            logs_dir_path,
            f"Automatik Lauf {run_id}: fertig={ok} quarantaene={qn} gesamt={len(audios)}",
        )
        return report_path

    finally:
        try:
            lock.unlink()
        except Exception as exc:
            log_exception(
                "automation_runner.lock_cleanup",
                exc,
                logs_path=logs_dir_path,
                extra={"lock_path": str(lock)},
            )
            log_line(
                logs_dir_path,
                f"Automatik: Lock konnte nicht entfernt werden ({lock}). Bitte prüfen.",
            )
            if report_path and report_path.exists():
                try:
                    report_doc = load_json(report_path, {})
                    repairs = report_doc.get("repairs", [])
                    repairs.append(
                        {
                            "type": "lock_cleanup_failed",
                            "lock_path": str(lock),
                            "error": str(exc),
                        }
                    )
                    report_doc["repairs"] = repairs
                    save_json(report_path, report_doc)
                except Exception as report_exc:
                    log_exception(
                        "automation_runner.report_update",
                        report_exc,
                        logs_path=logs_dir_path,
                        extra={"report_path": str(report_path)},
                    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default=str(default_settings_path()))
    ap.add_argument("--rules", default=str(default_rules_path()))
    args = ap.parse_args()
    rp = run(Path(args.settings), Path(args.rules))
    # Print report path for callers (selftest)
    print(str(rp))


if __name__ == "__main__":
    main()
