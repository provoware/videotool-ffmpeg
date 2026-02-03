import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from io_utils import atomic_write_json, load_json
from logging_utils import log_exception
from paths import (
    app_dir,
    repo_root,
    data_dir,
    config_dir,
    cache_dir,
    logs_dir,
    venv_dir,
)
from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QPixmap, QImageReader
from PySide6.QtWidgets import QMessageBox, QWidget


def normalize_report_doc(doc: dict) -> dict:
    if not isinstance(doc, dict):
        return {}
    if not isinstance(doc.get("schema_version"), int):
        doc["schema_version"] = 1
    if not isinstance(doc.get("jobs"), list):
        doc["jobs"] = []
    if not isinstance(doc.get("repairs"), list):
        doc["repairs"] = []
    if not isinstance(doc.get("errors"), list):
        doc["errors"] = []
    summary = doc.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    summary.setdefault("fertig", 0)
    summary.setdefault("quarantaene", 0)
    summary.setdefault("gesamt", 0)
    doc["summary"] = summary
    return doc


def ensure_dirs():
    base = data_dir()
    for rel in [
        "exports",
        "library/audio",
        "library/images",
        "quarantine",
        "quarantine_jobs",
        "reports",
        "trash",
        "staging",
        "projects",
        "favorites",
    ]:
        (base / rel).mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
    (cache_dir() / "thumbs").mkdir(parents=True, exist_ok=True)


def activity(msg: str):
    p = logs_dir() / "activity_log.jsonl"
    entry = {"at": datetime.utcnow().isoformat(timespec="seconds") + "Z", "msg": msg}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def have(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def open_path(p: Path, parent: QWidget | None = None):
    try:
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(p)])
        elif os.name == "nt":
            os.startfile(p)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(p)])
    except Exception as exc:
        log_exception("open_path", exc, extra={"path": str(p)})
        _show_process_message(
            parent,
            "Öffnen fehlgeschlagen",
            "Der Pfad konnte nicht geöffnet werden.",
            details=str(p),
            icon=QMessageBox.Warning,
        )


def run_quarantine_worker(job_id: str | None = None):
    venv = venv_dir()
    py = venv / "bin" / "python"
    if not py.exists():
        py = Path(sys.executable)
    cmd = [str(py), str(app_dir() / "quarantine_worker.py")]
    if job_id:
        cmd += ["--job-id", job_id]
    subprocess.Popen(cmd, cwd=str(repo_root()))


def latest_report_file() -> Path | None:
    rdir = data_dir() / "reports"
    files = sorted(
        rdir.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return files[0] if files else None


def today_quarantine_jobs() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return data_dir() / "quarantine_jobs" / f"quarantine_jobs_{today}.json"


def normalize_quarantine_doc(doc: dict, day: str) -> dict:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if not isinstance(doc, dict):
        doc = {}
    if not isinstance(doc.get("items"), list):
        doc["items"] = []
    if not isinstance(doc.get("summary"), dict):
        doc["summary"] = {}
    if not isinstance(doc.get("schema_version"), int):
        doc["schema_version"] = 1
    if not doc.get("date"):
        doc["date"] = day
    if not doc.get("title"):
        doc["title"] = f"Quarantäne-Aufträge – {doc['date']}"
    if not doc.get("created_at"):
        doc["created_at"] = now
    if "list_status" not in doc:
        doc["list_status"] = "offen"
    if "closed_at" not in doc:
        doc["closed_at"] = None
    return update_quarantine_list_status(doc)


def load_today_quarantine_jobs():
    day = datetime.now().strftime("%Y-%m-%d")
    p = today_quarantine_jobs()
    if p.exists():
        doc = load_json(p, {})
        return normalize_quarantine_doc(doc, day)
    return normalize_quarantine_doc({}, day)


def save_today_quarantine_jobs(doc: dict):
    p = today_quarantine_jobs()
    ok = atomic_write_json(p, doc, context="save_today_quarantine_jobs")
    if not ok:
        log_exception(
            "save_today_quarantine_jobs",
            RuntimeError("Quarantäne-Liste konnte nicht gespeichert werden."),
            extra={"path": str(p)},
        )


def update_quarantine_list_status(doc: dict) -> dict:
    items = doc.get("items", [])
    total = len(items)
    done = sum(1 for it in items if it.get("status") == "erledigt")
    postponed = sum(1 for it in items if it.get("status") == "zurueckgestellt")
    hard = sum(1 for it in items if it.get("status") == "fest")
    openish = sum(1 for it in items if it.get("status") in ("bereit", "laeuft"))
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


def safe_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9._-]+", "", name)
    name = name.strip("._-")
    return name or "datei"


def rename_file_safe(old_path: Path, new_stem: str) -> Path:
    new_stem = safe_filename(new_stem)
    ext = old_path.suffix
    parent = old_path.parent
    candidate = parent / (new_stem + ext)
    if candidate == old_path:
        return old_path
    i = 1
    while candidate.exists():
        candidate = parent / (f"{new_stem}_{i:03d}{ext}")
        i += 1
    old_path.rename(candidate)
    return candidate


SUPPORTED_AUDIO = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
SUPPORTED_IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _show_process_message(
    parent: QWidget | None,
    title: str,
    text: str,
    details: str | None = None,
    icon=QMessageBox.Information,
):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setIcon(icon)
    msg.setText(text)
    if details:
        msg.setDetailedText(details)
    msg.exec()


def _run_tool_script(
    parent: QWidget | None,
    script: Path,
    title: str,
    success_next: str,
    failure_next: str,
) -> QProcess | None:
    if not script.exists() or not script.is_file():
        text = f"{script.name} fehlt.\nNächster Schritt: Script wiederherstellen oder Neuinstallation starten."
        _show_process_message(parent, title, text, icon=QMessageBox.Critical)
        activity(f"{title} fehlgeschlagen: Script fehlt ({script.name}).")
        return None
    proc = QProcess(parent)
    proc.setProgram("bash")
    proc.setArguments([str(script)])
    proc.setWorkingDirectory(str(repo_root()))
    proc.setProcessChannelMode(QProcess.MergedChannels)
    activity(f"{title} gestartet ({script.name}).")

    def on_error(error):
        output = bytes(proc.readAllStandardOutput()).decode("utf-8", "ignore").strip()
        text = (
            f"{title} konnte nicht gestartet werden.\nNächster Schritt: {failure_next}"
        )
        _show_process_message(
            parent, title, text, details=output or str(error), icon=QMessageBox.Critical
        )
        activity(f"{title} Startfehler: {error}.")

    def on_finished(exit_code, exit_status):
        output = bytes(proc.readAllStandardOutput()).decode("utf-8", "ignore").strip()
        if exit_status == QProcess.NormalExit and exit_code == 0:
            text = f"{title} abgeschlossen.\nNächster Schritt: {success_next}"
            _show_process_message(
                parent,
                title,
                text,
                details=output or None,
                icon=QMessageBox.Information,
            )
            activity(f"{title} abgeschlossen: exit=0.")
        else:
            text = (
                f"{title} fehlgeschlagen (Exit-Code/Beendigungszahl: {exit_code}).\n"
                f"Nächster Schritt: {failure_next}"
            )
            _show_process_message(
                parent, title, text, details=output or None, icon=QMessageBox.Critical
            )
            activity(
                f"{title} fehlgeschlagen: exit={exit_code}, status={int(exit_status)}."
            )

    proc.errorOccurred.connect(on_error)
    proc.finished.connect(on_finished)
    proc.start()
    return proc


def run_setup(parent: QWidget | None = None) -> QProcess | None:
    script = repo_root() / "tools" / "setup_system.sh"
    return _run_tool_script(
        parent,
        script,
        "Einrichtung",
        "Tool neu starten und Werkstatt-Check laufen lassen.",
        "Setup manuell starten oder Hilfe-Center öffnen.",
    )


def run_timer_install(parent: QWidget | None = None) -> QProcess | None:
    script = repo_root() / "tools" / "install_timer.sh"
    return _run_tool_script(
        parent,
        script,
        "Zeitplan",
        "Automatik ist eingerichtet. Optional: Automatik aktivieren.",
        "Automatik-Status prüfen und Script erneut ausführen.",
    )


def run_automation_now(parent: QWidget | None = None) -> QProcess | None:
    script = repo_root() / "tools" / "run_automation.sh"
    return _run_tool_script(
        parent,
        script,
        "Automatik-Test",
        "Reports und Quarantäne prüfen.",
        "Logdatei öffnen und Fehler beheben.",
    )


def is_image_path(p: Path) -> bool:
    return p.suffix.lower() in SUPPORTED_IMG


def is_audio_path(p: Path) -> bool:
    return p.suffix.lower() in SUPPORTED_AUDIO


def thumb_cache_key(p: Path, size: int) -> str:
    try:
        st = p.stat()
        raw = f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}|{size}"
    except Exception:
        raw = f"{p}|{size}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def get_thumb_pixmap(p: Path, size: int = 96) -> QPixmap | None:
    if not p.exists() or not is_image_path(p):
        return None
    cache_file = cache_dir() / "thumbs" / f"{thumb_cache_key(p, size)}.png"
    if cache_file.exists():
        pm = QPixmap(str(cache_file))
        if not pm.isNull():
            return pm
    reader = QImageReader(str(p))
    reader.setAutoTransform(True)
    img = reader.read()
    if img.isNull():
        return None
    pm = QPixmap.fromImage(img).scaled(
        size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    try:
        pm.save(str(cache_file), "PNG")
    except Exception as exc:
        log_exception("thumb_cache.save", exc, extra={"path": str(cache_file)})
    return pm


# --- Favoriten (Werkzeugkasten) ---


def favorites_dir() -> Path:
    return data_dir() / "favorites"


def favorites_db_path() -> Path:
    return favorites_dir() / "favorites.json"


def load_favorites() -> dict:
    favorites_dir().mkdir(parents=True, exist_ok=True)
    if not favorites_db_path().exists():
        favorites_db_path().write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "items": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    try:
        return json.loads(favorites_db_path().read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "items": []}


def save_favorites(doc: dict):
    doc["updated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    favorites_db_path().write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fav_id_for_path(p: Path) -> str:
    try:
        raw = f"{p.resolve()}|{p.stat().st_size}|{int(p.stat().st_mtime)}"
    except Exception:
        raw = str(p)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _safe_tag(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9._-]+", "", s)
    return s.strip("._-")


def norm_tags(s: str) -> list[str]:
    tags = []
    for t in s.split(","):
        t = _safe_tag(t)
        if t:
            tags.append(t)
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _load_theme_qss(theme_name: str) -> str:
    try:
        themes = load_json(config_dir() / "themes.json", {})
        return (themes.get("qss", {}) or {}).get(theme_name, "")
    except Exception:
        return ""


def _scale_font(app, zoom_percent: int):
    try:
        f = app.font()
        base = f.pointSize()
        if base <= 0:
            base = 10
        f.setPointSize(max(8, int(round(base * (zoom_percent / 100.0)))))
        app.setFont(f)
    except Exception as exc:
        log_exception(
            "scale_font",
            exc,
            extra={"zoom_percent": zoom_percent},
        )
