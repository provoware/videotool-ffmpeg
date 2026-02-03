#!/usr/bin/env python3
"""
Manual Export (Werkbank) – Standbild + Audio + optional Lauftext + optional Logo.

Input:
- audio_path, image_path
- output_dir
- preset: youtube_hd_ton_safe | shorts_9_16_ton_safe
- text (optional), text_speed (px/s), text_position (bottom/top), text_bg (bool)
- logo_path (optional), logo_pos (top-left/top-right/bottom-left/bottom-right), logo_scale_percent
- grayscale (bool)

Safety:
- Uses temp file then renames to final (atomic).
- Always applies audio settings (AAC, samplerate, bitrate) from settings.json.
- Never overwrites: adds _001 suffix if needed.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from perf import get_threads
from datetime import datetime
from paths import config_dir
from validation_utils import (
    PathValidationError,
    ensure_existing_dir,
    ensure_existing_file,
    ensure_output_path,
)


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def safe_slug(s: str, maxlen: int = 120, fallback: str = "unbenannt") -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    s = s.strip("._-")
    if not s:
        s = fallback
    return s[:maxlen] if len(s) > maxlen else s


def parse_int(value, default: int, label: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not a valid int")
        return int(value)
    except Exception:
        print(f"WARNUNG: {label} ungültig ({value}), nutze Standard {default}.")
        return default


def parse_positive_int(value, default: int, label: str) -> int:
    parsed = parse_int(value, default, label)
    if parsed <= 0:
        print(f"WARNUNG: {label} ungültig ({value}), nutze Standard {default}.")
        return default
    return parsed


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    stem = p.stem
    ext = p.suffix
    i = 1
    while True:
        cand = p.with_name(f"{stem}_{i:03d}{ext}")
        if not cand.exists():
            return cand
        i += 1


def find_font() -> str | None:
    # best-effort common paths
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


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def escape_drawtext_text(t: str) -> str:
    # FFmpeg drawtext escaping (basic, safe)
    t = t.replace("\\", "\\\\")  # escape backslash
    t = t.replace(":", "\\:")
    t = t.replace("'", "\\'")
    t = t.replace("%", "\\%")
    t = t.replace("\n", " ")
    return t


def build_filters(
    preset: str,
    grayscale: bool,
    text: str | None,
    text_speed: int,
    text_pos: str,
    text_bg: bool,
    logo_path: Path | None,
    logo_pos: str,
    logo_scale_percent: int,
) -> tuple[str, str, int, int, int]:
    # returns filter_complex, out_label, WxH, fps
    if preset == "shorts_9_16_ton_safe":
        W, H, FPS = 1080, 1920, 30
    else:
        W, H, FPS = 1920, 1080, 30

    # Fast-Test Modus (nur für interne Tests, Qualität der Audio-Checks bleibt)
    import os as _os

    if _os.getenv("MODULTOOL_FAST", "") == "1":
        if preset == "shorts_9_16_ton_safe":
            W, H, FPS = 360, 640, 24
        else:
            W, H, FPS = 640, 360, 24

    filters = []
    filters.append(
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},format=yuv420p[bg]"
    )
    v_in = "[bg]"
    out_label = v_in

    if grayscale:
        filters.append(f"{v_in}format=gray[bg2]")
        v_in = "[bg2]"
        out_label = v_in

    if text and text.strip():
        font = find_font()
        if font:
            fontsize = 48 if H == 1080 else 52
            y = "h-th-30" if text_pos == "bottom" else "30"
            xexpr = f"w - mod(t*{text_speed}, w+tw)"
            box = "1" if text_bg else "0"
            boxcolor = "black@0.55"
            escaped = escape_drawtext_text(text)
            filters.append(
                f"{v_in}drawtext=fontfile='{font}':text='{escaped}':"
                f"fontcolor=white:fontsize={fontsize}:x='{xexpr}':y='{y}':"
                f"box={box}:boxcolor={boxcolor}:boxborderw=16[txt]"
            )
            v_in = "[txt]"
            out_label = v_in
        else:
            print(
                "WARNUNG: Kein Font gefunden, Lauftext wird übersprungen. "
                "Aktion: Schriftart installieren (z. B. DejaVuSans)."
            )

    if logo_path and logo_path.exists():
        scale = max(5, min(100, int(logo_scale_percent)))
        target_h = int(H * (scale / 100.0))
        filters.append(f"[2:v]scale=-1:{target_h}:flags=lanczos[logo]")
        pad = 30
        if logo_pos == "top-left":
            x, y = pad, pad
        elif logo_pos == "top-right":
            x, y = f"main_w-overlay_w-{pad}", pad
        elif logo_pos == "bottom-left":
            x, y = pad, f"main_h-overlay_h-{pad}"
        else:
            x, y = f"main_w-overlay_w-{pad}", f"main_h-overlay_h-{pad}"
        filters.append(f"{v_in}[logo]overlay=x={x}:y={y}[vout]")
        v_in = "[vout]"
        out_label = v_in

    return ";".join(filters), out_label, W, H, FPS


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--preset", default="youtube_hd_ton_safe")
    ap.add_argument("--text", default="")
    ap.add_argument("--text_speed", type=int, default=220)
    ap.add_argument("--text_pos", choices=["bottom", "top"], default="bottom")
    ap.add_argument("--text_bg", action="store_true")
    ap.add_argument("--logo", default="")
    ap.add_argument(
        "--logo_pos",
        choices=["top-left", "top-right", "bottom-left", "bottom-right"],
        default="bottom-right",
    )
    ap.add_argument("--logo_scale", type=int, default=14)
    ap.add_argument("--grayscale", action="store_true")
    ap.add_argument("--settings", default=str(config_dir() / "settings.json"))
    args = ap.parse_args()

    try:
        audio = ensure_existing_file(Path(args.audio), "Audio-Datei")
        image = ensure_existing_file(Path(args.image), "Bild-Datei")
        outdir = ensure_existing_dir(Path(args.outdir), "Ausgabe-Ordner", create=True)
        logo_path = (
            ensure_existing_file(Path(args.logo), "Logo-Datei") if args.logo else None
        )
    except PathValidationError as exc:
        print(f"Fehler: {exc}")
        return 2

    settings = load_json(Path(args.settings), {})
    threads = get_threads(Path(args.settings))
    a_cfg = settings.get("audio", {})
    a_bitrate = parse_positive_int(
        a_cfg.get("target_bitrate_kbps", 320), 320, "Audio-Bitrate"
    )
    a_sr = parse_positive_int(
        a_cfg.get("target_samplerate_hz", 48000), 48000, "Audio-Samplerate"
    )

    filter_complex, out_label, W, H, FPS = build_filters(
        args.preset,
        args.grayscale,
        args.text,
        args.text_speed,
        args.text_pos,
        args.text_bg,
        logo_path,
        args.logo_pos,
        args.logo_scale,
    )

    # name using templates if present
    n_cfg = settings.get("naming", {})
    tmpl = n_cfg.get("template_single", "{audio}_{vorlage}_{datum}_{uhrzeit}{sw}")
    dt = datetime.now().strftime("%Y-%m-%d")
    tm = datetime.now().strftime("%H%M%S")
    sw = "_sw" if args.grayscale else ""
    name_stem = tmpl.format(
        audio=safe_slug(audio.stem),
        vorlage=safe_slug(args.preset),
        datum=dt,
        uhrzeit=tm,
        nummer="001",
        sw=sw,
    )
    name_stem = safe_slug(name_stem)
    out_final = unique_path(outdir / f"{name_stem}.mp4")
    out_tmp = ensure_output_path(out_final.with_suffix(".tmp.mp4"), "Zwischenausgabe")

    if not have("ffmpeg"):
        print("Fehler: ffmpeg nicht gefunden. Aktion: ffmpeg installieren.")
        return 2

    # Inputs: 0=image, 1=audio, 2=logo (optional)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if threads:
        cmd += ["-threads", str(threads)]
    cmd += ["-loop", "1", "-i", str(image), "-i", str(audio)]
    if logo_path and logo_path.exists():
        cmd += ["-i", str(logo_path)]
    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        out_label,
        "-map",
        "1:a:0",
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        ("ultrafast" if os.getenv("MODULTOOL_FAST", "") == "1" else "medium"),
        "-crf",
        ("28" if os.getenv("MODULTOOL_FAST", "") == "1" else "19"),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        f"{a_bitrate}k",
        "-ar",
        str(a_sr),
        "-shortest",
        "-movflags",
        "+faststart",
        str(out_tmp),
    ]

    # Run ffmpeg
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        out_tmp.unlink(missing_ok=True)
        print(f"Fehler: FFmpeg fehlgeschlagen (Exit {exc.returncode}).")
        return exc.returncode or 1
    except Exception as exc:
        out_tmp.unlink(missing_ok=True)
        print(f"Fehler: Export abgebrochen ({exc}).")
        return 1

    # Atomic move to final
    out_tmp.replace(out_final)
    print(str(out_final))
    return 0


if __name__ == "__main__":
    main()
