#!/usr/bin/env python3
"""
Must-Pass Suite (0.9.15)
Runs a set of deterministic checks to validate:
- Python modules compile
- Workbench export works (with and without eco_mode), and output audio meets minimum bitrate/samplerate
- Automation runner works in sandbox (staging/temp/commit)
- Quarantine jobs are created when forcing low bitrate in sandbox
Outputs:
- user_data/reports/must_pass_<timestamp>.json
Exit code 0 = pass, 1 = fail
"""
from __future__ import annotations
import json, subprocess, shutil, time, os, py_compile, wave, struct, math, hashlib, re
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader

def root() -> Path:
    return Path(__file__).resolve().parents[1]

def cfg_dir() -> Path:
    return root()/"portable_data"/"config"

def user_data() -> Path:
    return root()/"portable_data"/"user_data"

def cache_dir() -> Path:
    return root()/"portable_data"/"cache"

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def have(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None

def make_test_assets(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    # simple 5s wav 48k stereo
    sr = 48000
    dur = 1
    t = [i/sr for i in range(sr*dur)]
    freq = 440.0
    data = [0.2*math.sin(2*math.pi*freq*x) for x in t]
    wav_path = folder/"tone_5s.wav"
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for s in data:
            v = int(max(-1,min(1,s))*32767)
            wf.writeframes(struct.pack("<hh", v, v))
    # image: use existing preset_cover if available
    preset = root()/"assets"/"default_assets"/"test_image.jpg"
    img_path = folder/"img.jpg"
    if preset.exists():
        shutil.copy(preset, img_path)
    else:
        # minimal fallback using ImageMagick isn't allowed; just touch
        img_path.write_bytes(b"")
    return wav_path, img_path

def make_thumbnail(image_path: Path, size: int = 96) -> Path|None:
    if not image_path.exists():
        return None
    cache = cache_dir()/ "thumbs"
    cache.mkdir(parents=True, exist_ok=True)
    raw = image_path.read_bytes()
    digest = hashlib.sha1(raw).hexdigest()
    out = cache / f"mustpass_{digest}_{size}.png"
    reader = QImageReader(str(image_path))
    reader.setAutoTransform(True)
    img = reader.read()
    if img.isNull():
        return None
    scaled = img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if not scaled.save(str(out), "PNG"):
        return None
    return out if out.exists() else None

def ffprobe_audio_ok(file: Path, min_kbps: int, sr_target: int) -> tuple[bool, dict]:
    cmd = ["ffprobe","-v","error","-print_format","json","-show_streams","-show_format",str(file)]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    info = json.loads(out)
    astreams = [s for s in info.get("streams", []) if s.get("codec_type")=="audio"]
    bitrate_kbps = None
    samplerate = None
    if astreams:
        samplerate = int(astreams[0].get("sample_rate") or 0)
        br = astreams[0].get("bit_rate") or info.get("format",{}).get("bit_rate")
        if br:
            bitrate_kbps = int(int(br)/1000)
    ok = (samplerate == sr_target) and (bitrate_kbps is not None and bitrate_kbps >= min_kbps)
    return ok, {"audio_bitrate_kbps": bitrate_kbps, "audio_samplerate_hz": samplerate}

def run_workbench(settings_path: Path, eco_mode: bool) -> dict:
    settings = load_json(settings_path, {})
    settings.setdefault("performance", {})
    settings["performance"]["eco_mode"] = eco_mode
    settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")

    outdir = user_data()/"exports"/"mustpass"
    outdir.mkdir(parents=True, exist_ok=True)
    sandbox = user_data()/"mustpass"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True, exist_ok=True)
    wav, img = make_test_assets(sandbox)

    script = root()/"app"/"manual_export.py"
    import sys
    cmd = [sys.executable, str(script),
           "--audio", str(wav), "--image", str(img), "--outdir", str(outdir),
           "--preset", "youtube_hd_ton_safe",
           "--settings", str(settings_path)]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ, MODULTOOL_FAST='1'))
    # newest mp4 in outdir
    files = sorted(outdir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    mp4 = files[0] if files else None
    ok_audio, meta = ffprobe_audio_ok(mp4, int(settings.get("audio",{}).get("min_bitrate_kbps",192)), int(settings.get("audio",{}).get("target_samplerate_hz",48000)))
    return {"eco_mode": eco_mode, "output": str(mp4) if mp4 else "", "audio_ok": ok_audio, "audio_meta": meta}

def run_automation_sandbox(settings_base: Path, rules_base: Path, force_bad_bitrate: bool) -> dict:
    sb = user_data()/"mustpass_auto"
    if sb.exists():
        shutil.rmtree(sb)
    sb.mkdir(parents=True, exist_ok=True)
    watch = sb/"watch"
    watch.mkdir(parents=True, exist_ok=True)
    wav, img = make_test_assets(watch)

    settings = load_json(settings_base, {})
    settings["paths"]["base_data_dir"] = str(sb/"data")
    settings["paths"]["watch_folder"] = str(watch)
    settings.setdefault("audio", {})
    if force_bad_bitrate:
        # force low bitrate output but keep min high to trigger quarantine
        settings["audio"]["target_bitrate_kbps"] = 96
        settings["audio"]["min_bitrate_kbps"] = 192
    else:
        settings["audio"]["target_bitrate_kbps"] = 320
        settings["audio"]["min_bitrate_kbps"] = 192
    s_path = sb/"settings.json"
    save_json(s_path, settings)

    rules = load_json(rules_base, {})
    r_path = sb/"rules.json"
    save_json(r_path, rules)

    runner = root()/"app"/"automation_runner.py"
    import sys
    out = subprocess.check_output([sys.executable, str(runner), "--settings", str(s_path), "--rules", str(r_path)], text=True, env=dict(os.environ, MODULTOOL_FAST='1')).strip()
    rep = Path(out)
    rep_doc = load_json(rep, {})
    q_count = rep_doc.get("summary", {}).get("quarantaene", 0)
    f_count = rep_doc.get("summary", {}).get("fertig", 0)
    return {"force_bad_bitrate": force_bad_bitrate, "report": str(rep), "fertig": f_count, "quarantaene": q_count}

def compile_all() -> list:
    errs = []
    for p in (root()/"app").rglob("*.py"):
        try:
            py_compile.compile(str(p), doraise=True)
        except Exception as e:
            errs.append({"file": str(p), "error": str(e)})
    return errs

def _hex_to_rgb(value: str) -> tuple[float, float, float] | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.match(r"^#[0-9a-fA-F]{6}$", value):
        return None
    r = int(value[1:3], 16) / 255.0
    g = int(value[3:5], 16) / 255.0
    b = int(value[5:7], 16) / 255.0
    return r, g, b

def _relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

def _contrast_ratio(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter, darker = (l1, l2) if l1 >= l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)

def _extract_widget_colors(qss: str) -> dict:
    if not isinstance(qss, str):
        return {}
    widget = re.search(r"QWidget\\s*\\{([^}]*)\\}", qss, re.DOTALL)
    if not widget:
        return {}
    block = widget.group(1)
    bg_match = re.search(r"background\\s*:\\s*(#[0-9a-fA-F]{6})", block)
    fg_match = re.search(r"color\\s*:\\s*(#[0-9a-fA-F]{6})", block)
    return {"background": bg_match.group(1) if bg_match else "", "color": fg_match.group(1) if fg_match else ""}

def _extract_role_colors(qss: str, role: str) -> dict:
    if not isinstance(qss, str) or not isinstance(role, str) or not role:
        return {}
    role_block = re.search(rf"QLabel\\[role=\\\"{re.escape(role)}\\\"\\]\\s*\\{{([^}}]*)\\}}", qss, re.DOTALL)
    if not role_block:
        return {}
    block = role_block.group(1)
    fg_match = re.search(r"color\\s*:\\s*(#[0-9a-fA-F]{6})", block)
    return {"color": fg_match.group(1) if fg_match else ""}

def check_theme_contrast(themes_path: Path, min_ratio: float = 4.5) -> dict:
    doc = load_json(themes_path, {})
    qss_map = doc.get("qss", {}) or {}
    results = {"min_ratio": min_ratio, "themes": {}, "ok": True}
    for name, qss in qss_map.items():
        colors = _extract_widget_colors(qss)
        fg = _hex_to_rgb(colors.get("color", ""))
        bg = _hex_to_rgb(colors.get("background", ""))
        if fg is None or bg is None:
            results["themes"][name] = {"ok": False, "ratio": None, "colors": colors, "roles": {}}
            results["ok"] = False
            continue
        ratio = _contrast_ratio(fg, bg)
        ok = ratio >= min_ratio
        role_results = {}
        for role in ("hint", "muted"):
            role_colors = _extract_role_colors(qss, role)
            role_fg = _hex_to_rgb(role_colors.get("color", ""))
            if role_fg is None:
                role_results[role] = {"ok": False, "ratio": None, "colors": role_colors}
                ok = False
                continue
            role_ratio = _contrast_ratio(role_fg, bg)
            role_ok = role_ratio >= min_ratio
            role_results[role] = {"ok": role_ok, "ratio": round(role_ratio, 2), "colors": role_colors}
            if not role_ok:
                ok = False
        results["themes"][name] = {"ok": ok, "ratio": round(ratio, 2), "colors": colors, "roles": role_results}
        if not ok:
            results["ok"] = False
    return results

def main():
    results = {"at": datetime.utcnow().isoformat(timespec="seconds")+"Z", "pass": True, "checks": {}}

    # Prereqs
    prereq = {"ffmpeg": have("ffmpeg"), "ffprobe": have("ffprobe")}
    results["checks"]["prereq"] = prereq
    if not prereq["ffmpeg"] or not prereq["ffprobe"]:
        results["pass"] = False

    # Compile
    comp_errs = compile_all()
    results["checks"]["compile"] = {"errors": comp_errs, "ok": len(comp_errs)==0}
    if comp_errs:
        results["pass"] = False

    # Workbench normal + eco
    settings_path = cfg_dir()/"settings.json"
    try:
        wb_norm = run_workbench(settings_path, eco_mode=False)
        wb_eco = run_workbench(settings_path, eco_mode=True)
        results["checks"]["workbench"] = {"normal": wb_norm, "eco": wb_eco}
        if not (wb_norm["audio_ok"] and wb_eco["audio_ok"]):
            results["pass"] = False
    except Exception as e:
        results["checks"]["workbench"] = {"error": str(e)}
        results["pass"] = False

    # Thumbnail regression (load image and ensure thumb exists)
    try:
        thumb_sandbox = user_data()/"mustpass_thumbs"
        if thumb_sandbox.exists():
            shutil.rmtree(thumb_sandbox)
        thumb_sandbox.mkdir(parents=True, exist_ok=True)
        _, img = make_test_assets(thumb_sandbox)
        thumb = make_thumbnail(img, 96)
        thumb_ok = bool(thumb and thumb.exists() and thumb.stat().st_size > 0)
        results["checks"]["thumbnail"] = {"ok": thumb_ok, "thumb": str(thumb) if thumb else "", "source": str(img)}
        if not thumb_ok:
            results["pass"] = False
    except Exception as e:
        results["checks"]["thumbnail"] = {"error": str(e)}
        results["pass"] = False

    # Automation sandbox pass + quarantine
    try:
        auto_ok = run_automation_sandbox(settings_path, cfg_dir()/"automation_rules.json", force_bad_bitrate=False)
        auto_bad = run_automation_sandbox(settings_path, cfg_dir()/"automation_rules.json", force_bad_bitrate=True)
        results["checks"]["automation"] = {"ok": auto_ok, "bad": auto_bad}
        if not (auto_ok["fertig"] >= 1 and auto_ok["quarantaene"] == 0):
            results["pass"] = False
        if not (auto_bad["quarantaene"] >= 1):
            results["pass"] = False
    except Exception as e:
        results["checks"]["automation"] = {"error": str(e)}
        results["pass"] = False

    # Theme contrast check (accessibility)
    try:
        contrast = check_theme_contrast(cfg_dir()/"themes.json")
        results["checks"]["theme_contrast"] = contrast
        if not contrast["ok"]:
            results["pass"] = False
    except Exception as e:
        results["checks"]["theme_contrast"] = {"error": str(e)}
        results["pass"] = False

    out = user_data()/"reports"/f"must_pass_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    save_json(out, results)
    print(str(out))
    return 0 if results["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
