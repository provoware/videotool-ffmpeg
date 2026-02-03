#!/usr/bin/env python3
import sys, json, subprocess, os, re, hashlib
from pathlib import Path
from preflight import run as preflight_run
from datetime import datetime

def portable_root() -> Path:
    return Path(__file__).resolve().parents[1]

def data_dir() -> Path:
    return portable_root() / "portable_data" / "user_data"

def config_dir() -> Path:
    return portable_root() / "portable_data" / "config"

def cache_dir() -> Path:
    return portable_root() / "portable_data" / "cache"

def logs_dir() -> Path:
    return portable_root() / "portable_data" / "logs"

def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def ensure_dirs():
    base = data_dir()
    for rel in [
        "exports","library/audio","library/images","quarantine","quarantine_jobs",
        "reports","trash","staging","projects","favorites"
    ]:
        (base/rel).mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
    (cache_dir()/ "thumbs").mkdir(parents=True, exist_ok=True)

def activity(msg: str):
    p = logs_dir() / "activity_log.jsonl"
    entry = {"at": datetime.utcnow().isoformat(timespec="seconds")+"Z", "msg": msg}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False)+"\n")

def have(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None

def open_path(p: Path):
    try:
        subprocess.Popen(["xdg-open", str(p)])
    except Exception:
        pass

def run_setup():
    script = portable_root()/"tools"/"setup_system.sh"
    subprocess.Popen(["bash", str(script)], cwd=str(portable_root()))

def run_timer_install():
    script = portable_root()/"tools"/"install_timer.sh"
    subprocess.Popen(["bash", str(script)], cwd=str(portable_root()))

def run_automation_now():
    script = portable_root()/"tools"/"run_automation.sh"
    subprocess.Popen(["bash", str(script)], cwd=str(portable_root()))

def run_quarantine_worker(job_id: str|None = None):
    venv = portable_root()/"portable_data"/".venv"
    py = venv/"bin"/"python"
    if not py.exists():
        py = Path(sys.executable)
    cmd = [str(py), str(portable_root()/"app"/"quarantine_worker.py")]
    if job_id:
        cmd += ["--job-id", job_id]
    subprocess.Popen(cmd, cwd=str(portable_root()))

def latest_report_file() -> Path|None:
    rdir = data_dir()/"reports"
    files = sorted(rdir.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def today_quarantine_jobs() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return data_dir()/"quarantine_jobs"/f"quarantine_jobs_{today}.json"

def load_today_quarantine_jobs():
    p = today_quarantine_jobs()
    if p.exists():
        return load_json(p, {})
    return {"schema_version":1,"date":datetime.now().strftime("%Y-%m-%d"),"items":[],"list_status":"offen","summary":{}}

def save_today_quarantine_jobs(doc: dict):
    p = today_quarantine_jobs()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

def update_quarantine_list_status(doc: dict) -> dict:
    items = doc.get("items", [])
    total = len(items)
    done = sum(1 for it in items if it.get("status")=="erledigt")
    postponed = sum(1 for it in items if it.get("status")=="zurueckgestellt")
    hard = sum(1 for it in items if it.get("status")=="fest")
    openish = sum(1 for it in items if it.get("status") in ("bereit","laeuft"))
    doc["summary"] = {"total": total, "done": done, "postponed": postponed, "hard_cases": hard, "open": openish}
    if hard == 0 and openish == 0:
        doc["list_status"] = "abgehakt"
        doc["closed_at"] = doc.get("closed_at") or datetime.utcnow().isoformat(timespec="seconds")+"Z"
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
    candidate = parent/(new_stem + ext)
    if candidate == old_path:
        return old_path
    i = 1
    while candidate.exists():
        candidate = parent/(f"{new_stem}_{i:03d}{ext}")
        i += 1
    old_path.rename(candidate)
    return candidate

# Qt UI
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTabWidget, QSplitter,
    QGroupBox, QMessageBox, QCheckBox, QTextEdit, QLineEdit, QFileDialog,
    QComboBox, QInputDialog, QFrame
)
from PySide6.QtCore import Qt, QSize, QProcess
from PySide6.QtGui import QPixmap, QIcon, QImageReader

SUPPORTED_AUDIO = {".mp3",".wav",".flac",".m4a",".aac",".ogg"}
SUPPORTED_IMG = {".jpg",".jpeg",".png",".webp",".bmp"}

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

def get_thumb_pixmap(p: Path, size: int = 96) -> QPixmap|None:
    if not p.exists() or not is_image_path(p):
        return None
    cache_file = cache_dir()/ "thumbs" / f"{thumb_cache_key(p, size)}.png"
    if cache_file.exists():
        pm = QPixmap(str(cache_file))
        if not pm.isNull():
            return pm
    reader = QImageReader(str(p))
    reader.setAutoTransform(True)
    img = reader.read()
    if img.isNull():
        return None
    pm = QPixmap.fromImage(img).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    try:
        pm.save(str(cache_file), "PNG")
    except Exception:
        pass
    return pm


# --- Favoriten (Werkzeugkasten) ---
def favorites_dir() -> Path:
    return data_dir() / "favorites"

def favorites_db_path() -> Path:
    return favorites_dir() / "favorites.json"

def load_favorites() -> dict:
    favorites_dir().mkdir(parents=True, exist_ok=True)
    if not favorites_db_path().exists():
        favorites_db_path().write_text(json.dumps({"schema_version":1,"updated_at":datetime.utcnow().isoformat(timespec="seconds")+"Z","items":[]}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return json.loads(favorites_db_path().read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version":1,"items":[]}

def save_favorites(doc: dict):
    doc["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")+"Z"
    favorites_db_path().write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

def fav_id_for_path(p: Path) -> str:
    try:
        raw = f"{p.resolve()}|{p.stat().st_size}|{int(p.stat().st_mtime)}"
    except Exception:
        raw = str(p)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def _safe_tag(s: str) -> str:
    import re
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
    seen=set(); out=[]
    for t in tags:
        if t not in seen:
            out.append(t); seen.add(t)
    return out

class FileDropListWidget(QListWidget):
    def __init__(self, on_paths, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_paths = on_paths
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DropOnly)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = []
        for u in urls:
            if u.isLocalFile():
                paths.append(Path(u.toLocalFile()))
        if paths:
            self.on_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


def _load_theme_qss(theme_name: str) -> str:
    try:
        themes = load_json(config_dir()/ "themes.json", {})
        return (themes.get("qss", {}) or {}).get(theme_name, "")
    except Exception:
        return ""

def _scale_font(app: QApplication, zoom_percent: int):
    try:
        f = app.font()
        base = f.pointSize()
        if base <= 0:
            base = 10
        f.setPointSize(max(8, int(round(base * (zoom_percent/100.0)))))
        app.setFont(f)
    except Exception:
        pass

class Main(QMainWindow):
    def apply_theme(self):
        theme = self.settings.get("ui", {}).get("theme", "hochkontrast_dunkel")
        qss = _load_theme_qss(theme)
        if qss:
            QApplication.instance().setStyleSheet(qss)
        # Button height and padding can be adjusted via stylesheet, but keep min heights coherent
        self._ui_button_height = int(self.settings.get("ui", {}).get("button_height", 38))


    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.texts = load_json(config_dir()/"texte_de.json", {"strings":{}, "tooltips":{}})
        self.settings = load_json(config_dir()/"settings.json", {})
        self.rules_path = config_dir()/"automation_rules.json"
        self.rules = load_json(self.rules_path, {})

        self.setWindowTitle(self.texts.get("strings", {}).get("app.titel", "Modultool"))
        self.setMinimumSize(1360, 820)
        self.statusBar().showMessage("Bereit. Gib mir Material.")
        activity("GUI gestartet.")

        # filters state
        self.material_search = ""
        self.material_type_filter = "alle"
        self.selection_search = ""
        self.selection_type_filter = "alle"
        self.q_search = ""
        self.done_search = ""

        splitter = QSplitter(Qt.Horizontal)
        self.left = QTabWidget()
        self.left.setMinimumWidth(380)

        # --- MATERIAL TAB (mit Suche/Filter) ---
        tab_material = QWidget(); lm = QVBoxLayout(tab_material)
        lm.addWidget(QLabel("Material (Checkboxen = Auswahl). Du kannst Dateien hier reinziehen."))

        row0 = QHBoxLayout()
        self.btn_add_files = QPushButton("Dateien holen")
        self.btn_add_folder = QPushButton("Ordner holen")
        row0.addWidget(self.btn_add_files)
        row0.addWidget(self.btn_add_folder)
        lm.addLayout(row0)

        row1 = QHBoxLayout()
        self.material_search_box = QLineEdit()
        self.material_search_box.setPlaceholderText("Suchen im Material …")
        self.material_type_combo = QComboBox()
        self.material_type_combo.addItems(["Typ: alle", "Typ: audio", "Typ: bilder"])
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Sortieren: Datum (neu zuerst)", "Sortieren: Name (A-Z)"])
        row1.addWidget(self.material_search_box, 2)
        row1.addWidget(self.material_type_combo)
        row1.addWidget(self.sort_combo)
        lm.addLayout(row1)

        material_split = QSplitter(Qt.Horizontal)
        self.material = FileDropListWidget(self.add_paths_to_material)
        self.material.setSelectionMode(QListWidget.ExtendedSelection)
        self.material.setIconSize(QSize(96,96))
        material_split.addWidget(self.material)

        preview = QWidget(); pv = QVBoxLayout(preview)
        title = QLabel("Bildvorschau"); title.setStyleSheet("font-weight:600;")
        self.preview_img = QLabel("Kein Bild ausgewählt.")
        self.preview_img.setAlignment(Qt.AlignCenter)
        self.preview_img.setMinimumWidth(280)
        self.preview_img.setMinimumHeight(240)
        self.preview_img.setFrameShape(QFrame.StyledPanel)
        self.preview_info = QLabel(""); self.preview_info.setWordWrap(True); self.preview_info.setStyleSheet("color:#666;")
        pv.addWidget(title)
        pv.addWidget(self.preview_img, 1)
        pv.addWidget(self.preview_info)
        pv.addStretch(1)
        material_split.addWidget(preview)
        material_split.setStretchFactor(0, 3)
        material_split.setStretchFactor(1, 2)

        lm.addWidget(material_split)
        hint = QLabel("Tipp: Bild anklicken = Vorschau. Checkboxen = Auswahlkorb. Suche/Filter oben.")
        hint.setStyleSheet("color:#777;")
        lm.addWidget(hint)

        self.left.addTab(tab_material, self.texts["strings"].get("sidebar.material","Material"))

        # Werkzeugkasten (Favoriten)
        tab_box = QWidget(); lb = QVBoxLayout(tab_box)
        lb.addWidget(QLabel(self.texts["strings"].get("favoriten.titel","Werkzeugkasten – Favoriten")))

        fav_row = QHBoxLayout()
        self.fav_search_box = QLineEdit()
        self.fav_search_box.setPlaceholderText(self.texts["strings"].get("favoriten.suchen","Suchen in Favoriten …"))
        self.fav_tag_combo = QComboBox()
        self.fav_tag_combo.addItems(["Tag: alle"])
        fav_row.addWidget(self.fav_search_box, 2)
        fav_row.addWidget(self.fav_tag_combo, 1)
        lb.addLayout(fav_row)

        self.fav_list = QListWidget()
        self.fav_list.setIconSize(QSize(64,64))
        lb.addWidget(self.fav_list, 1)

        fav_btns = QHBoxLayout()
        self.btn_fav_add = QPushButton(self.texts["strings"].get("favoriten.hinzufuegen","Favorit hinzufügen"))
        self.btn_fav_add.setToolTip(self.texts.get("tooltips",{}).get("favoriten.hinzufuegen",""))
        self.btn_fav_star = QPushButton(self.texts["strings"].get("favoriten.stern","Stern umschalten"))
        self.btn_fav_star.setToolTip(self.texts.get("tooltips",{}).get("favoriten.stern",""))
        self.btn_fav_tags = QPushButton(self.texts["strings"].get("favoriten.tags","Tags setzen"))
        self.btn_fav_tags.setToolTip(self.texts.get("tooltips",{}).get("favoriten.tags",""))
        self.btn_fav_remove = QPushButton(self.texts["strings"].get("favoriten.entfernen","Entfernen"))
        self.btn_fav_folder = QPushButton(self.texts["strings"].get("favoriten.ordner","Favoriten-Ordner öffnen"))
        fav_btns.addWidget(self.btn_fav_add)
        fav_btns.addWidget(self.btn_fav_star)
        fav_btns.addWidget(self.btn_fav_tags)
        fav_btns.addWidget(self.btn_fav_remove)
        fav_btns.addWidget(self.btn_fav_folder)
        lb.addLayout(fav_btns)

        hint = QLabel("Tipp: Favoriten sind Referenzen. Wenn die Datei fehlt, bleibt der Eintrag sichtbar.")
        hint.setStyleSheet("color:#777;")
        lb.addWidget(hint)

        self.left.addTab(tab_box, self.texts["strings"].get("sidebar.werkzeugkasten","Werkzeugkasten"))


        # Einstellungen-Tab (laienfest, alles deutsch, kein JSON-Gefummel)
        tab_settings = QWidget(); ls = QVBoxLayout(tab_settings)
        ls.addWidget(QLabel(self.texts["strings"].get("settings.titel","Einstellungen")))

        from PySide6.QtWidgets import QFormLayout, QGroupBox, QDoubleSpinBox, QSpinBox

        grp_paths = QGroupBox(self.texts["strings"].get("settings.speicherorte","Speicherorte"))
        form_p = QFormLayout(grp_paths)

        self.set_watch_folder = QLineEdit()
        self.set_watch_folder.setText(self.settings.get("paths",{}).get("watch_folder",""))
        btn_watch = QPushButton(self.texts["strings"].get("settings.folder_waehlen","Ordner wählen"))
        btn_watch.clicked.connect(lambda: self._pick_folder_into(self.set_watch_folder, "Downloads-Ordner"))
        row_watch = QWidget(); rw = QHBoxLayout(row_watch); rw.setContentsMargins(0,0,0,0)
        rw.addWidget(self.set_watch_folder, 1); rw.addWidget(btn_watch)
        form_p.addRow(self.texts["strings"].get("settings.watchfolder","Watchfolder"), row_watch)

        def add_rel_line(label_key, attr_name, default_val):
            le = QLineEdit()
            le.setText(self.settings.get("paths",{}).get(attr_name, default_val))
            le.setPlaceholderText(default_val)
            setattr(self, f"set_{attr_name}", le)
            form_p.addRow(self.texts["strings"].get(label_key, attr_name), le)

        add_rel_line("settings.exports", "exports_dir", "exports")
        add_rel_line("settings.library_audio", "library_audio_dir", "library/audio")
        add_rel_line("settings.library_images", "library_images_dir", "library/images")
        add_rel_line("settings.quarantine", "quarantine_dir", "quarantine")
        add_rel_line("settings.quarantine_jobs", "quarantine_jobs_dir", "quarantine_jobs")
        add_rel_line("settings.reports", "reports_dir", "reports")
        add_rel_line("settings.staging", "staging_dir", "staging")
        add_rel_line("settings.trash", "trash_dir", "trash")
        ls.addWidget(grp_paths)

        grp_audio = QGroupBox(self.texts["strings"].get("settings.audio","Audio"))
        form_a = QFormLayout(grp_audio)
        self.set_fade_in = QDoubleSpinBox(); self.set_fade_in.setRange(0.0, 30.0); self.set_fade_in.setSingleStep(0.1)
        self.set_fade_in.setValue(float(self.settings.get("audio",{}).get("fade_in_sec",0.5)))
        form_a.addRow(self.texts["strings"].get("settings.fade_in","Fade-In"), self.set_fade_in)
        self.set_fade_out = QDoubleSpinBox(); self.set_fade_out.setRange(0.0, 30.0); self.set_fade_out.setSingleStep(0.1)
        self.set_fade_out.setValue(float(self.settings.get("audio",{}).get("fade_out_sec",1.0)))
        form_a.addRow(self.texts["strings"].get("settings.fade_out","Fade-Out"), self.set_fade_out)
        self.set_min_br = QSpinBox(); self.set_min_br.setRange(0, 1024); self.set_min_br.setValue(int(self.settings.get("audio",{}).get("min_bitrate_kbps",192)))
        form_a.addRow(self.texts["strings"].get("settings.min_bitrate","Min Bitrate"), self.set_min_br)
        self.set_target_br = QSpinBox(); self.set_target_br.setRange(64, 1024); self.set_target_br.setValue(int(self.settings.get("audio",{}).get("target_bitrate_kbps",320)))
        form_a.addRow(self.texts["strings"].get("settings.target_bitrate","Ziel Bitrate"), self.set_target_br)
        self.set_sr = QSpinBox(); self.set_sr.setRange(8000, 192000); self.set_sr.setValue(int(self.settings.get("audio",{}).get("target_samplerate_hz",48000)))
        form_a.addRow(self.texts["strings"].get("settings.samplerate","Samplerate"), self.set_sr)
        ls.addWidget(grp_audio)

        grp_name = QGroupBox(self.texts["strings"].get("settings.dateinamen","Dateinamen"))
        form_n = QFormLayout(grp_name)
        self.set_tmpl_single = QLineEdit(); self.set_tmpl_single.setText(self.settings.get("naming",{}).get("template_single","{audio}_{vorlage}_{datum}_{uhrzeit}{sw}"))
        form_n.addRow(self.texts["strings"].get("settings.template_single","Vorlage Einzel"), self.set_tmpl_single)
        self.set_tmpl_batch = QLineEdit(); self.set_tmpl_batch.setText(self.settings.get("naming",{}).get("template_batch","{audio}_{vorlage}_{datum}_{nummer}{sw}"))
        form_n.addRow(self.texts["strings"].get("settings.template_batch","Vorlage Stapel"), self.set_tmpl_batch)
        self.set_append_label = QCheckBox(self.texts["strings"].get("settings.append_label","Etikett an Ausgabe anhängen"))
        self.set_append_label.setChecked(bool(self.settings.get("naming",{}).get("append_label_to_output", False)))
        form_n.addRow(self.set_append_label)
        self.set_append_mode = QComboBox(); self.set_append_mode.addItems(["only_quarantine","always","never"])
        mode = self.settings.get("naming",{}).get("append_label_mode","only_quarantine")
        ix = self.set_append_mode.findText(mode)
        if ix >= 0: self.set_append_mode.setCurrentIndex(ix)
        form_n.addRow(self.texts["strings"].get("settings.append_mode","Etikett-Modus"), self.set_append_mode)
        self.set_append_short = QCheckBox(self.texts["strings"].get("settings.append_short","Kurzform Etikett"))
        self.set_append_short.setChecked(bool(self.settings.get("naming",{}).get("append_label_shortform", True)))
        form_n.addRow(self.set_append_short)
        self.lbl_preview_name = QLabel("")
        form_n.addRow(self.texts["strings"].get("settings.preview_name","Vorschau Dateiname"), self.lbl_preview_name)
        ls.addWidget(grp_name)

        btn_row = QHBoxLayout()
        self.btn_settings_save = QPushButton(self.texts["strings"].get("settings.speichern","Speichern"))
        self.btn_settings_default = QPushButton(self.texts["strings"].get("settings.standard","Standard wiederherstellen"))
        self.btn_settings_test = QPushButton(self.texts["strings"].get("settings.testen","Pfade testen"))
        btn_row.addWidget(self.btn_settings_save); btn_row.addWidget(self.btn_settings_default); btn_row.addWidget(self.btn_settings_test)
        ls.addLayout(btn_row)
        ls.addStretch(1)

        self.left.addTab(tab_settings, self.texts["strings"].get("sidebar.einstellungen","Einstellungen"))
        # Vorlagen
        tab_presets = QWidget(); lp = QVBoxLayout(tab_presets)
        self.btn_p1 = QPushButton(self.texts["strings"].get("preset.youtube_hd_tonsafe","YouTube HD (Ton Safe)"))
        self.btn_p3 = QPushButton(self.texts["strings"].get("preset.shorts_9_16_tonsafe","Shorts 9:16 (Ton Safe)"))
        lp.addWidget(QLabel("Vorlagen (Ton Safe):"))
        lp.addWidget(self.btn_p1); lp.addWidget(self.btn_p3); lp.addStretch(1)
        self.left.addTab(tab_presets, self.texts["strings"].get("sidebar.vorlagen","Vorlagen"))

        # Automatik tab
        tab_auto = QWidget(); la = QVBoxLayout(tab_auto)
        self.chk_auto = QCheckBox("Automatik aktiv (global)")
        self.chk_auto.setChecked(bool(self.rules.get("enabled", False)))
        self.btn_timer = QPushButton("Zeitplan einrichten/aktualisieren")
        self.btn_run = QPushButton("Automatik jetzt starten (Test)")
        self.lbl_time = QLabel(f"Startzeit: {self.rules.get('start_time','22:00')}")
        la.addWidget(QLabel("Automatik: läuft erst zur Uhrzeit. Tagsüber einrichten, nachts Ruhe."))
        la.addWidget(self.lbl_time)
        la.addWidget(self.chk_auto); la.addWidget(self.btn_timer); la.addWidget(self.btn_run); la.addStretch(1)
        self.left.addTab(tab_auto, self.texts["strings"].get("sidebar.automatik","Automatik"))

        # Quarantäne-Tagesliste als UI-Tabelle (0.9.9)
        tab_quar = QWidget(); lq = QVBoxLayout(tab_quar)
        lq.addWidget(QLabel(self.texts["strings"].get("quar_tab.titel","Quarantäne-Aufträge (heute)")))
        hint = QLabel(self.texts["strings"].get("quar_tab.hinweis",""))
        hint.setStyleSheet("color:#777;")
        hint.setWordWrap(True)
        lq.addWidget(hint)

        # Controls row
        rowq = QHBoxLayout()
        self.btn_quar_refresh = QPushButton(self.texts["strings"].get("quar_tab.refresh","Aktualisieren"))
        self.btn_quar_open_json = QPushButton(self.texts["strings"].get("quar_tab.open_json","JSON öffnen"))
        self.btn_quar_open_folder = QPushButton(self.texts["strings"].get("quar_tab.open_folder","Quarantäne-Ordner"))
        self.btn_quar_all_rerun = QPushButton(self.texts["strings"].get("quar_tab.all_rerun","Alle bereit neu machen"))
        rowq.addWidget(self.btn_quar_refresh)
        rowq.addWidget(self.btn_quar_open_json)
        rowq.addWidget(self.btn_quar_open_folder)
        rowq.addWidget(self.btn_quar_all_rerun)
        lq.addLayout(rowq)

        # Table
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem
        self.quar_table = QTableWidget()
        self.quar_table.setColumnCount(6)
        self.quar_table.setHorizontalHeaderLabels([
            self.texts["strings"].get("quar_tab.status","Status"),
            self.texts["strings"].get("quar_tab.file","Datei"),
            self.texts["strings"].get("quar_tab.reason","Grund"),
            self.texts["strings"].get("quar_tab.tries","Versuche"),
            self.texts["strings"].get("quar_tab.action","Aktion"),
            "ID"
        ])
        self.quar_table.setColumnHidden(5, True)
        self.quar_table.setSelectionBehavior(self.quar_table.SelectRows)
        self.quar_table.setEditTriggers(self.quar_table.NoEditTriggers)
        lq.addWidget(self.quar_table, 1)

        # Action buttons for selected row
        rowa = QHBoxLayout()
        self.btn_quar_rerun = QPushButton(self.texts["strings"].get("quar_tab.rerun","Neu (Ton Safe)"))
        self.btn_quar_replace = QPushButton(self.texts["strings"].get("quar_tab.replace","Quelle ersetzen"))
        self.btn_quar_postpone = QPushButton(self.texts["strings"].get("quar_tab.postpone","Zurückstellen"))
        self.btn_quar_done = QPushButton(self.texts["strings"].get("quar_tab.mark_done","Erledigt"))
        rowa.addWidget(self.btn_quar_rerun)
        rowa.addWidget(self.btn_quar_replace)
        rowa.addWidget(self.btn_quar_postpone)
        rowa.addWidget(self.btn_quar_done)
        lq.addLayout(rowa)

        self.left.addTab(tab_quar, self.texts["strings"].get("quar_tab.titel","Quarantäne"))

        # Tests tab
        tab_tests = QWidget(); lt = QVBoxLayout(tab_tests)
        self.btn_selftest = QPushButton("Werkstatt-Prüfung (Selftest) – Volltest")
        self.btn_mustpass = QPushButton(self.texts["strings"].get("tests.mustpass","Must-Pass Suite"))
        self.lbl_mustpass = QLabel(self.texts["strings"].get("tests.mustpass_hint",""))
        self.lbl_mustpass.setStyleSheet("color:#777;")
        self.btn_open_reports = QPushButton("Arbeitsberichte öffnen")
        lt.addWidget(QLabel("Selftest: 1 Erfolg + 1 Quarantäne, danach wird 'Letzte Nacht' aktualisiert."))
        lt.addWidget(self.btn_selftest)
        lt.addWidget(self.btn_mustpass)
        lt.addWidget(self.lbl_mustpass)
        lt.addWidget(self.btn_open_reports)
        lt.addStretch(1)
        self.left.addTab(tab_tests, self.texts["strings"].get("sidebar.tests","Werkstatt-Prüfung"))

        # Entwicklerdoku tab
        tab_dev = QWidget(); ld = QVBoxLayout(tab_dev)
        ld.addWidget(QLabel("Entwicklerdoku (im Tool)"))
        self.dev_search = QLineEdit(); self.dev_search.setPlaceholderText("Suchen …")
        self.dev_view = QTextEdit(); self.dev_view.setReadOnly(True)
        dev_path = config_dir()/"DEVELOPER_MANUAL.md"
        self.dev_view.setPlainText(dev_path.read_text(encoding="utf-8") if dev_path.exists() else "DEVELOPER_MANUAL.md fehlt.")
        ld.addWidget(self.dev_search); ld.addWidget(self.dev_view)
        
        # Hilfe-Tab (Hilfe-Center)
        tab_help = QWidget(); lh = QVBoxLayout(tab_help)
        lh.addWidget(QLabel(self.texts["strings"].get("help.titel","Hilfe-Center")))
        self.help_search = QLineEdit()
        self.help_search.setPlaceholderText(self.texts["strings"].get("help.suchen","Suchen …"))
        self.help_view = QTextEdit()
        self.help_view.setReadOnly(True)
        help_path = config_dir()/"HELP_CENTER.md"
        self.help_view.setPlainText(help_path.read_text(encoding="utf-8") if help_path.exists() else "HELP_CENTER.md fehlt.")
        self.btn_help_open = QPushButton(self.texts["strings"].get("help.open_file","Hilfe-Datei öffnen"))
        lh.addWidget(self.help_search)
        lh.addWidget(self.help_view, 1)
        lh.addWidget(self.btn_help_open)

        self.left.addTab(tab_help, self.texts["strings"].get("sidebar.hilfe","Hilfe"))
        self.left.addTab(tab_dev, self.texts["strings"].get("sidebar.entwicklerdoku","Entwicklerdoku"))

        # --- MIDDLE DASHBOARD ---
        self.mid = QWidget(); md = QVBoxLayout(self.mid)
        header = QLabel("Schaltzentrale: Auswahl, letzte Nacht, nächste Schritte.")
        header.setStyleSheet("font-size:16px;font-weight:600;")
        md.addWidget(header)

        # Preflight Banner (Laien-Schutz)
        self.preflight_banner = QGroupBox("Werkstatt-Check")
        pb = QVBoxLayout(self.preflight_banner)
        self.lbl_preflight = QLabel("")
        self.lbl_preflight.setWordWrap(True)
        rowp = QHBoxLayout()
        self.btn_preflight_setup = QPushButton(self.texts["strings"].get("preflight.setup","Jetzt einrichten (FFmpeg)"))
        self.btn_preflight_details = QPushButton(self.texts["strings"].get("preflight.details","Details"))
        rowp.addWidget(self.btn_preflight_setup)
        rowp.addWidget(self.btn_preflight_details)
        pb.addWidget(self.lbl_preflight)
        pb.addLayout(rowp)
        md.addWidget(self.preflight_banner)

        self.grp_sel = QGroupBox("Deine Auswahl (0)")
        sll = QVBoxLayout(self.grp_sel)

        sel_filters = QHBoxLayout()
        self.selection_search_box = QLineEdit()
        self.selection_search_box.setPlaceholderText("Suchen in Auswahl …")
        self.selection_type_combo = QComboBox()
        self.selection_type_combo.addItems(["Typ: alle", "Typ: audio", "Typ: bilder"])
        sel_filters.addWidget(self.selection_search_box, 2)
        sel_filters.addWidget(self.selection_type_combo)
        sll.addLayout(sel_filters)

        sll.addWidget(QLabel("Hier liegt deine Auswahl. Du kannst Namen ändern oder aus der Auswahl werfen."))
        self.sel_list = QListWidget()
        self.sel_list.setIconSize(QSize(48,48))
        sll.addWidget(self.sel_list)

        row = QHBoxLayout()
        self.btn_queue = QPushButton(self.texts["strings"].get("buttons.in_warteschlange","In Warteschlange"))
        self.btn_prev = QPushButton(self.texts["strings"].get("buttons.vorschau_10s","Vorschau (zehn Sekunden)"))
        self.btn_clear = QPushButton("Auswahl leeren")
        row.addWidget(self.btn_queue); row.addWidget(self.btn_prev); row.addWidget(self.btn_clear)
        sll.addLayout(row)
        md.addWidget(self.grp_sel)

        # Werkbank: Standbild+Audio (Lauftext/Logo)
        self.grp_workbench = QGroupBox(self.texts["strings"].get("workbench.titel","Werkbank – Standbild + Audio"))
        wb = QVBoxLayout(self.grp_workbench)
        wb.addWidget(QLabel(self.texts["strings"].get("workbench.hinweis","")))

        wrow1 = QHBoxLayout()
        self.wb_preset = QComboBox()
        self.wb_preset.addItems([
            "youtube_hd_ton_safe",
            "shorts_9_16_ton_safe"
        ])
        wrow1.addWidget(QLabel(self.texts["strings"].get("workbench.preset","Vorlage")))
        wrow1.addWidget(self.wb_preset, 1)
        wb.addLayout(wrow1)


        # Bild-Zuweisung (Batch Pairing)
        wpair = QHBoxLayout()
        self.wb_pairing = QComboBox()
        self.wb_pairing.addItems(["one","seq","manual"])
        wpair.addWidget(QLabel(self.texts["strings"].get("workbench.pairing","Bild-Zuweisung")))
        wpair.addWidget(self.wb_pairing, 1)
        self.btn_wb_assign_open = QPushButton(self.texts["strings"].get("workbench.assign_open","Zuweisung öffnen"))
        wpair.addWidget(self.btn_wb_assign_open)
        wb.addLayout(wpair)

        pair_hint = QLabel(self.texts["strings"].get("workbench.pairing_hint",""))
        pair_hint.setStyleSheet("color:#777;")
        pair_hint.setWordWrap(True)
        wb.addWidget(pair_hint)

        self._wb_manual_map = []  # list of (audio_path, image_path)
        self.wb_text_on = QCheckBox(self.texts["strings"].get("workbench.text_on","Lauftext aktiv"))
        self.wb_text = QLineEdit()
        self.wb_text.setPlaceholderText(self.texts["strings"].get("workbench.text","Lauftext"))
        wrow2 = QHBoxLayout()
        self.wb_text_pos = QComboBox(); self.wb_text_pos.addItems(["bottom","top"])
        self.wb_text_speed = QComboBox(); self.wb_text_speed.addItems(["slow","medium","fast","auto"])
        self.wb_text_bg = QCheckBox(self.texts["strings"].get("workbench.text_bg","Balken hinter Text"))
        wrow2.addWidget(QLabel(self.texts["strings"].get("workbench.text_pos","Position")))
        wrow2.addWidget(self.wb_text_pos)
        wrow2.addWidget(QLabel(self.texts["strings"].get("workbench.text_speed","Tempo")))
        wrow2.addWidget(self.wb_text_speed)
        wrow2.addWidget(self.wb_text_bg)
        wb.addWidget(self.wb_text_on)
        wb.addWidget(self.wb_text)
        wb.addLayout(wrow2)

        self.wb_logo_on = QCheckBox(self.texts["strings"].get("workbench.logo_on","Logo aktiv"))
        wrow3 = QHBoxLayout()
        self.wb_logo_path = QLineEdit(); self.wb_logo_path.setPlaceholderText(self.texts["strings"].get("workbench.logo","Logo"))
        self.wb_logo_pick = QPushButton("…")
        self.wb_logo_pos = QComboBox(); self.wb_logo_pos.addItems(["bottom-right","bottom-left","top-right","top-left"])
        self.wb_logo_scale = QSpinBox(); self.wb_logo_scale.setRange(5, 50); self.wb_logo_scale.setValue(14)
        wrow3.addWidget(self.wb_logo_path, 2)
        wrow3.addWidget(self.wb_logo_pick)
        wrow3.addWidget(QLabel(self.texts["strings"].get("workbench.logo_pos","Position")))
        wrow3.addWidget(self.wb_logo_pos)
        wrow3.addWidget(QLabel(self.texts["strings"].get("workbench.logo_size","Größe (%)")))
        wrow3.addWidget(self.wb_logo_scale)
        wb.addWidget(self.wb_logo_on)
        wb.addLayout(wrow3)

        self.wb_gray = QCheckBox(self.texts["strings"].get("workbench.grayscale","Schwarz/Weiß (optional)"))
        self.wb_gray.setChecked(bool(self.settings.get("video",{}).get("grayscale_default", False)))
        wb.addWidget(self.wb_gray)

        wrow4 = QHBoxLayout()
        self.btn_wb_export = QPushButton(self.texts["strings"].get("workbench.export_now","Ausgabe bauen"))
        self.btn_wb_open_exports = QPushButton(self.texts["strings"].get("workbench.open_exports","Ausgaben öffnen"))
        wrow4.addWidget(self.btn_wb_export)
        wrow4.addWidget(self.btn_wb_open_exports)
        wb.addLayout(wrow4)

        md.addWidget(self.grp_workbench)

        self.grp_last = QGroupBox(self.texts["strings"].get("reports.karte_titel","Letzte Nacht"))
        lnl = QVBoxLayout(self.grp_last)
        self.lbl_last_summary = QLabel("Noch kein Lauf gefunden.")
        lnl.addWidget(self.lbl_last_summary)

        # Quarantine search
        qrow = QHBoxLayout()
        self.q_search_box = QLineEdit(); self.q_search_box.setPlaceholderText("Suchen in Quarantäne …")
        qrow.addWidget(self.q_search_box, 1)
        lnl.addLayout(qrow)

        lnl.addWidget(QLabel("Quarantäne (kurz):"))
        self.list_q = QListWidget()
        lnl.addWidget(self.list_q)

        qbtns = QHBoxLayout()
        self.btn_open_qjobs = QPushButton("Tagesliste öffnen")
        self.btn_rerun_all = QPushButton("Alle neu machen (Ton Safe)")
        qbtns.addWidget(self.btn_open_qjobs); qbtns.addWidget(self.btn_rerun_all)
        lnl.addLayout(qbtns)

        # Done search
        drow = QHBoxLayout()
        self.done_search_box = QLineEdit(); self.done_search_box.setPlaceholderText("Suchen in Ausgaben …")
        drow.addWidget(self.done_search_box, 1)
        lnl.addLayout(drow)

        lnl.addWidget(QLabel(self.texts["strings"].get("reports.block_fertig_kurz","Frisch aus der Werkbank") + " (letzte 3):"))
        self.list_done = QListWidget()
        lnl.addWidget(self.list_done)
        md.addWidget(self.grp_last)

        md.addStretch(1)

        # --- RIGHT PANEL ---
        self.right = QWidget(); rd = QVBoxLayout(self.right)
        rd.addWidget(QLabel("Einstellungen (Basic)"))
        self.btn_setup = QPushButton("Systemeinrichtung (FFmpeg) – tagsüber")
        self.btn_exports = QPushButton("Ausgaben-Ordner öffnen")
        self.btn_open_last_report = QPushButton("Letzten Arbeitsbericht öffnen")
        self.btn_refresh_last = QPushButton("Letzte Nacht aktualisieren")
        rd.addWidget(self.btn_setup); rd.addWidget(self.btn_exports); rd.addWidget(self.btn_open_last_report); rd.addWidget(self.btn_refresh_last)
        rd.addStretch(1)

        splitter.addWidget(self.left); splitter.addWidget(self.mid); splitter.addWidget(self.right)
        splitter.setStretchFactor(1, 3)

        rootw = QWidget(); rl = QVBoxLayout(rootw); rl.setContentsMargins(10,10,10,10); rl.setSpacing(10); rl.addWidget(splitter)
        self.setCentralWidget(rootw)

        # --- Signals ---
        self.material.itemChanged.connect(self.refresh_sel)
        self.material.currentItemChanged.connect(self.update_preview_from_current)
        self.btn_clear.clicked.connect(self.clear_sel)
        self.btn_setup.clicked.connect(self.setup_clicked)
        self.btn_preflight_setup.clicked.connect(self.setup_clicked)
        self.btn_preflight_details.clicked.connect(self._show_preflight_details)
        self.btn_exports.clicked.connect(self.open_exports)
        self.btn_timer.clicked.connect(self.install_timer)
        self.btn_run.clicked.connect(self.run_auto)
        self.btn_open_reports.clicked.connect(self.open_reports)
        self.btn_open_last_report.clicked.connect(self.open_last_report)
        self.btn_refresh_last.clicked.connect(self.refresh_last_night)

        # Werkbank
        self.wb_logo_pick.clicked.connect(self._wb_pick_logo)
        self.btn_wb_export.clicked.connect(self._wb_export)
        self.btn_wb_open_exports.clicked.connect(self._wb_open_exports)

        self.btn_wb_assign_open.clicked.connect(self._wb_open_assign)
        self.wb_pairing.currentIndexChanged.connect(lambda *_: None)
        self.btn_selftest.clicked.connect(self.selftest_full)

        self.btn_mustpass.clicked.connect(self.run_mustpass)
        self.btn_open_qjobs.clicked.connect(self.open_qjobs_today)
        self.btn_rerun_all.clicked.connect(self.rerun_all_quarantine_ready)

        # Quarantäne-Tab (Tabelle)
        self.btn_quar_refresh.clicked.connect(self._load_quarantine_table)
        self.btn_quar_open_json.clicked.connect(self.open_qjobs_today)
        self.btn_quar_open_folder.clicked.connect(self._quar_open_folder)
        self.btn_quar_all_rerun.clicked.connect(self.rerun_all_quarantine_ready)
        self.btn_quar_rerun.clicked.connect(lambda: (lambda jid=self._selected_quar_job_id(): run_quarantine_worker(jid) if jid else None)())
        self.btn_quar_replace.clicked.connect(lambda: (lambda jid=self._selected_quar_job_id(): self._quar_replace_source_simple(jid) if jid else None)())
        self.btn_quar_postpone.clicked.connect(lambda: (lambda jid=self._selected_quar_job_id(): self._update_quar_status(jid,'zurueckgestellt') and self._load_quarantine_table() if jid else None)())
        self.btn_quar_done.clicked.connect(lambda: (lambda jid=self._selected_quar_job_id(): self._update_quar_status(jid,'erledigt') and self._load_quarantine_table() if jid else None)())
        # Initial load
        self._load_quarantine_table()
        self.chk_auto.stateChanged.connect(self.toggle_automation_enabled)
        self.dev_search.textChanged.connect(self.dev_find)

        # Hilfe
        self.help_search.textChanged.connect(self.help_find)
        self.btn_help_open.clicked.connect(lambda: open_path(config_dir()/ "HELP_CENTER.md"))
        # Favoriten (Werkzeugkasten)
        self.fav_search_box.textChanged.connect(self.on_fav_search)
        self.fav_tag_combo.currentIndexChanged.connect(self.on_fav_tag)
        self.btn_fav_add.clicked.connect(self.fav_add_files)
        self.btn_fav_remove.clicked.connect(self.fav_remove_selected)
        self.btn_fav_star.clicked.connect(self.fav_toggle_star)
        self.btn_fav_tags.clicked.connect(self.fav_set_tags)
        self.btn_fav_folder.clicked.connect(lambda: open_path(favorites_dir()))

        # Einstellungen
        self.btn_settings_save.clicked.connect(self._settings_save)
        self.btn_settings_default.clicked.connect(self._settings_defaults)
        self.btn_settings_test.clicked.connect(self._settings_test_paths)
        self.set_tmpl_single.textChanged.connect(self._update_name_preview)
        self.set_tmpl_batch.textChanged.connect(self._update_name_preview)
        self.set_append_label.stateChanged.connect(self._update_name_preview)
        self.set_append_mode.currentIndexChanged.connect(self._update_name_preview)
        self.set_append_short.stateChanged.connect(self._update_name_preview)
        self._update_name_preview()
        self.fav_list.itemDoubleClicked.connect(self.fav_open_selected)

        self.btn_add_files.clicked.connect(self.pick_files)
        self.btn_add_folder.clicked.connect(self.pick_folder)
        self.sort_combo.currentIndexChanged.connect(self.apply_sort)
        self.material_search_box.textChanged.connect(self.on_material_search)
        self.material_type_combo.currentIndexChanged.connect(self.on_material_type)
        self.selection_search_box.textChanged.connect(self.on_selection_search)
        self.selection_type_combo.currentIndexChanged.connect(self.on_selection_type)
        self.q_search_box.textChanged.connect(self.on_q_search)
        self.done_search_box.textChanged.connect(self.on_done_search)

        self.refresh_sel()
        self.refresh_last_night()

        # Barriere-Labels (Screenreader / Tastatur)
        self._acc(self.material, "Materialliste", "Liste der importierten Dateien. Checkboxen wählen die Auswahl.")
        self._acc(self.preview_img, "Bildvorschau", "Große Vorschau des aktuell gewählten Bildes.")
        self._acc(self.sel_list, "Auswahlkorb", "Liste der ausgewählten Dateien, bearbeitbar.")
        self._acc(self.fav_list, "Favoritenliste", "Liste der Favoriten. Doppelklick öffnet Datei.")
        self._acc(self.btn_wb_export, "Ausgabe bauen", "Startet den Werkbank-Export für die aktuelle Auswahl.")
        self._acc(self.btn_quar_refresh, "Quarantäne aktualisieren", "Lädt die Quarantäne-Tagesliste neu.")
        self._acc(self.help_view, "Hilfeansicht", "Hilfe-Center Inhalt.")
        self._acc(self.dev_view, "Entwicklerdoku", "Entwickler-Handbuch im Tool.")
        self._acc(self.btn_settings_save, "Einstellungen speichern", "Speichert die aktuellen Einstellungen.")
        self._acc(self.btn_settings_test, "Pfade testen", "Prüft Schreibrechte und Pfade.")
        # Barriere-Labels gesetzt
        self.refresh_favorites()
        self.apply_material_filter()

        if not have("ffmpeg") or not have("ffprobe"):
            self.statusBar().showMessage("Hinweis: FFmpeg fehlt. Bitte tagsüber einrichten.")
            activity("Hinweis: ffmpeg/ffprobe fehlt (Setup empfohlen).")

    # --- Search/filter handlers ---
    def on_material_search(self, t: str):
        self.material_search = t.strip().lower()
        self.apply_material_filter()

    def on_material_type(self, idx: int):
        self.material_type_filter = ["alle","audio","bilder"][idx]
        self.apply_material_filter()

    def on_selection_search(self, t: str):
        self.selection_search = t.strip().lower()
        self.refresh_sel()

    def on_selection_type(self, idx: int):
        self.selection_type_filter = ["alle","audio","bilder"][idx]
        self.refresh_sel()

    def on_q_search(self, t: str):
        self.q_search = t.strip().lower()
        self.refresh_last_night()

    def on_done_search(self, t: str):
        self.done_search = t.strip().lower()
        self.refresh_last_night()

    def apply_material_filter(self):
        # hide/unhide items based on search and type
        for i in range(self.material.count()):
            it = self.material.item(i)
            path = it.data(Qt.UserRole)
            name = (it.text() or "").lower()
            show = True
            if self.material_search and self.material_search not in name:
                show = False
            if path:
                p = Path(path)
                if self.material_type_filter == "audio" and not is_audio_path(p):
                    show = False
                if self.material_type_filter == "bilder" and not is_image_path(p):
                    show = False
            else:
                # items without path: show only if no type filter
                if self.material_type_filter != "alle":
                    show = False
            it.setHidden(not show)

    # --- Developer docs search ---
    def dev_find(self, q: str):
        if not q.strip():
            return
        text = self.dev_view.toPlainText()
        idx = text.lower().find(q.lower())
        if idx >= 0:
            cursor = self.dev_view.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx+len(q), cursor.KeepAnchor)
            self.dev_view.setTextCursor(cursor)

    # --- Import ---
    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Dateien holen", str(Path.home()/ "Downloads"),
            "Audio/Bilder (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if files:
            self.add_paths_to_material([Path(f) for f in files])

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Ordner holen", str(Path.home()/ "Downloads"))
        if folder:
            p = Path(folder)
            paths = [x for x in p.iterdir() if x.is_file()]
            self.add_paths_to_material(paths)

    def add_paths_to_material(self, paths):
        added = 0
        for p in paths:
            if p.is_dir():
                for x in p.iterdir():
                    if x.is_file():
                        added += self._add_single_path(x)
            else:
                added += self._add_single_path(p)
        self.apply_sort()
        self.apply_material_filter()
        if added:
            self.statusBar().showMessage(f"{added} Datei(en) geholt. Jetzt: Checkboxen anklicken.")
            activity(f"Import: {added} Datei(en) hinzugefügt.")
        self.refresh_sel()

    def _add_single_path(self, p: Path) -> int:
        ext = p.suffix.lower()
        if ext not in SUPPORTED_AUDIO and ext not in SUPPORTED_IMG:
            return 0
        # avoid duplicates
        for i in range(self.material.count()):
            it = self.material.item(i)
            if it.data(Qt.UserRole) == str(p):
                return 0

        it = QListWidgetItem(p.name)
        it.setToolTip(str(p))
        it.setData(Qt.UserRole, str(p))
        it.setCheckState(Qt.Unchecked)

        if is_image_path(p):
            pm = get_thumb_pixmap(p, 96)
            if pm:
                it.setIcon(QIcon(pm))
        self.material.addItem(it)
        return 1

    def apply_sort(self):
        items = []
        for i in range(self.material.count()):
            it = self.material.item(i)
            path = it.data(Qt.UserRole)
            items.append((it.checkState(), it.text(), path, it.icon(), it.isHidden()))
        self.material.blockSignals(True)
        self.material.clear()
        mode = self.sort_combo.currentIndex()

        def key_fn(t):
            chk, name, path, _icon, _hidden = t
            if not path:
                return 0
            try:
                mt = Path(path).stat().st_mtime
            except Exception:
                mt = 0
            return -mt if mode == 0 else name.lower()

        for chk, name, path, icon, hidden in sorted(items, key=key_fn):
            it = QListWidgetItem(name)
            it.setToolTip(path or "")
            it.setData(Qt.UserRole, path)
            it.setCheckState(chk)
            it.setIcon(icon)
            it.setHidden(hidden)
            self.material.addItem(it)
        self.material.blockSignals(False)

    def update_preview_from_current(self, current, prev):
        if not current:
            self.preview_img.setText("Kein Bild ausgewählt.")
            self.preview_img.setPixmap(QPixmap())
            self.preview_info.setText("")
            return
        path = current.data(Qt.UserRole)
        if not path:
            self.preview_img.setText("Kein Bild ausgewählt.")
            self.preview_img.setPixmap(QPixmap())
            self.preview_info.setText("")
            return
        p = Path(path)
        if is_image_path(p) and p.exists():
            reader = QImageReader(str(p))
            reader.setAutoTransform(True)
            img = reader.read()
            pm = QPixmap.fromImage(img) if not img.isNull() else None
            if pm and not pm.isNull():
                pm2 = pm.scaled(self.preview_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.preview_img.setPixmap(pm2)
                self.preview_img.setText("")
                try:
                    st = p.stat()
                    self.preview_info.setText(f"{p.name}\n{p.parent}\nGröße: {st.st_size//1024} KB")
                except Exception:
                    self.preview_info.setText(f"{p.name}\n{p.parent}")
                return
        self.preview_img.setPixmap(QPixmap())
        self.preview_img.setText("Keine Bildvorschau.")
        self.preview_info.setText(p.name)

    # --- Selection basket ---
    def refresh_sel(self):
        checked = []
        self.sel_list.clear()

        for i in range(self.material.count()):
            it = self.material.item(i)
            if it.checkState() == Qt.Checked:
                path = it.data(Qt.UserRole) or ""
                name = (it.text() or "").lower()
                # apply selection filters
                if self.selection_search and self.selection_search not in name:
                    continue
                if path:
                    p = Path(path)
                    if self.selection_type_filter == "audio" and not is_audio_path(p):
                        continue
                    if self.selection_type_filter == "bilder" and not is_image_path(p):
                        continue
                else:
                    if self.selection_type_filter != "alle":
                        continue
                checked.append((it, path))

        self.grp_sel.setTitle(f"Deine Auswahl ({len(checked)})")
        for it, path in checked:
            self._add_selection_row(it, path)

        self.statusBar().showMessage("Auswahl aktualisiert. Nächster Schritt: Vorschau klicken.")

    def _add_selection_row(self, material_item: QListWidgetItem, path_str: str):
        from PySide6.QtWidgets import QWidget, QHBoxLayout

        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 2, 6, 2)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)

        if path_str:
            p = Path(path_str)
            if is_image_path(p):
                pm = get_thumb_pixmap(p, 48)
                if pm:
                    icon_lbl.setPixmap(pm)

        label = QLabel(material_item.text())
        label.setToolTip(path_str)

        btn_rename = QPushButton("Umbenennen"); btn_rename.setMaximumWidth(120)
        btn_remove = QPushButton("Entfernen"); btn_remove.setMaximumWidth(100)

        def do_remove():
            material_item.setCheckState(Qt.Unchecked)
            self.refresh_sel()
            activity(f"Auswahl entfernt: {material_item.text()}")

        def do_rename():
            if not path_str:
                QMessageBox.information(self, "Umbenennen", "Diese Auswahl hat keinen echten Pfad.")
                return
            p = Path(path_str)
            if not p.exists():
                QMessageBox.information(self, "Umbenennen", "Datei nicht gefunden. Pfad ist veraltet.")
                return
            new_name, ok = QInputDialog.getText(self, "Umbenennen", "Neuer Name (ohne Endung):", text=p.stem)
            if not ok or not new_name.strip():
                return
            try:
                new_path = rename_file_safe(p, new_name)
            except Exception as e:
                QMessageBox.critical(self, "Umbenennen", f"Konnte nicht umbenennen:\n{e}")
                return
            material_item.setText(new_path.name)
            material_item.setData(Qt.UserRole, str(new_path))
            material_item.setToolTip(str(new_path))
            if is_image_path(new_path):
                pm = get_thumb_pixmap(new_path, 96)
                if pm:
                    material_item.setIcon(QIcon(pm))
            activity(f"Umbenannt: {p.name} -> {new_path.name}")
            self.refresh_sel()
            self.apply_material_filter()

        btn_remove.clicked.connect(do_remove)
        btn_rename.clicked.connect(do_rename)

        layout.addWidget(icon_lbl)
        layout.addWidget(label, 1)
        layout.addWidget(btn_rename)
        layout.addWidget(btn_remove)

        item = QListWidgetItem()
        item.setSizeHint(QSize(10, 58))
        self.sel_list.addItem(item)
        self.sel_list.setItemWidget(item, w)

    def clear_sel(self):
        for i in range(self.material.count()):
            self.material.item(i).setCheckState(Qt.Unchecked)
        self.refresh_sel()

    # --- System & folders ---
    def setup_clicked(self):
        try:
            run_setup()
            QMessageBox.information(self, "Einrichtung", "Setup gestartet. Wenn fertig: Tool neu starten.")
            activity("Systemeinrichtung gestartet (sudo).")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Einrichtung konnte nicht gestartet werden:\n{e}")

    def open_exports(self):
        exports = data_dir()/self.settings.get("paths",{}).get("exports_dir","exports")
        open_path(exports)
        activity("Ausgaben-Ordner geöffnet.")

    def open_reports(self):
        open_path(data_dir()/self.settings.get("paths",{}).get("reports_dir","reports"))
        activity("Reports geöffnet.")

    def open_last_report(self):
        rf = latest_report_file()
        if rf:
            open_path(rf)
            activity("Letzten Arbeitsbericht geöffnet.")
        else:
            QMessageBox.information(self, "Arbeitsbericht", "Noch kein Arbeitsbericht vorhanden.")

    # --- Automation controls ---
    def install_timer(self):
        run_timer_install()
        activity("Zeitplan einrichten/aktualisieren gestartet.")

    def run_auto(self):
        run_automation_now()
        activity("Automatik manuell gestartet (Test).")

    def toggle_automation_enabled(self, state: int):
        self.rules["enabled"] = (state == Qt.Checked)
        self.rules_path.write_text(json.dumps(self.rules, ensure_ascii=False, indent=2), encoding="utf-8")
        activity(f"Automatik {'aktiviert' if self.rules['enabled'] else 'deaktiviert'}.")

    # --- Selftest (0.9.2) ---
    def selftest_full(self):
        script = portable_root()/"tools"/"run_selftest.sh"
        if not script.exists():
            QMessageBox.critical(self, "Selftest", "run_selftest.sh fehlt")
            return
        self.statusBar().showMessage("Selftest läuft…")
        self._selftest_proc = QProcess(self)
        self._selftest_proc.setProgram("bash")
        self._selftest_proc.setArguments([str(script)])
        def done(*args):
            self.statusBar().showMessage("Selftest fertig. Letzte Nacht aktualisiert.")
            activity("Selftest komplett ausgeführt.")
            self.refresh_last_night()
            QMessageBox.information(self, "Selftest", "Selftest fertig. Schau in 'Letzte Nacht' (inkl. Quarantäne-Aufträge).")
        self._selftest_proc.finished.connect(done)
        self._selftest_proc.start()

    # --- Quarantine daily jobs ---
    def open_qjobs_today(self):
        p = today_quarantine_jobs()
        if p.exists():
            open_path(p)
        else:
            QMessageBox.information(self, "Quarantäne", "Heute keine Quarantäne-Aufträge.")
        activity("Tagesliste Quarantäne geöffnet.")

    def rerun_all_quarantine_ready(self):
        doc = load_today_quarantine_jobs()
        n = 0
        for it in doc.get("items", []):
            if it.get("status") == "bereit":
                run_quarantine_worker(it.get("job_id"))
                n += 1
        QMessageBox.information(self, "Quarantäne", f"{n} Auftrag/ Aufträge gestartet.")
        activity(f"Quarantäne-Worker gestartet: {n} Jobs.")
        self.refresh_last_night()

    # --- Dashboard: Letzte Nacht ---
    def refresh_last_night(self):
        self.list_done.clear()
        self.list_q.clear()

        rf = latest_report_file()
        if not rf:
            self.lbl_last_summary.setText("Noch kein Lauf gefunden. Automatik einrichten oder Test starten.")
            self.list_q.addItem("Quarantäne heute: abgehakt ✅")
            return

        rep = load_json(rf, {})
        summ = rep.get("summary", {})
        self.lbl_last_summary.setText(f"Lauf {rep.get('run_id','?')}: fertig={summ.get('fertig',0)} | quarantäne={summ.get('quarantaene',0)} | gesamt={summ.get('gesamt',0)}")

        finished = [j for j in rep.get("jobs", []) if j.get("status") == "fertig" and j.get("output_final")]
        finished = finished[-3:] if len(finished) > 3 else finished
        for j in finished:
            p = Path(j["output_final"])
            if self.done_search and self.done_search not in p.name.lower():
                continue
            self.add_done_item(p)

        qdoc = None
        st = rep.get('selftest', {}) if isinstance(rep, dict) else {}
        qf = st.get('quarantine_jobs_file')
        if qf and Path(qf).exists():
            qdoc = load_json(Path(qf), {})
        else:
            qdoc = load_today_quarantine_jobs()

        qdoc = update_quarantine_list_status(qdoc)
        if not (qf and Path(qf).exists()):
            save_today_quarantine_jobs(qdoc)

        if qdoc.get("list_status") == "abgehakt":
            self.list_q.addItem("Quarantäne heute: abgehakt ✅")
        else:
            open_items = [it for it in qdoc.get("items", []) if it.get("status") in ("bereit","laeuft","fest")]
            # apply search filter
            if self.q_search:
                open_items = [it for it in open_items if self.q_search in (it.get("output_file","")+it.get("summary","")).lower()]
            show = open_items[:3]
            if not show:
                self.list_q.addItem("Quarantäne heute: abgehakt ✅")
            else:
                for it in show:
                    self.add_quarantine_item(it)
                if len(open_items) > 3:
                    self.list_q.addItem(f"+{len(open_items)-3} weitere … (Tagesliste öffnen)")
        self.statusBar().showMessage("Letzte Nacht aktualisiert.")

    def add_done_item(self, file_path: Path):
        from PySide6.QtWidgets import QWidget, QHBoxLayout
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 2, 6, 2)
        lbl = QLabel(file_path.name)
        lbl.setToolTip(str(file_path))
        btn_play = QPushButton("Abspielen"); btn_play.setMaximumWidth(110)
        btn_folder = QPushButton("Ordner"); btn_folder.setMaximumWidth(90)

        btn_play.clicked.connect(lambda: (open_path(file_path), activity(f"Abspielen: {file_path}")))
        btn_folder.clicked.connect(lambda: (open_path(file_path.parent), activity(f"Ordner öffnen: {file_path.parent}")))

        layout.addWidget(lbl, 1); layout.addWidget(btn_play); layout.addWidget(btn_folder)
        item = QListWidgetItem(); item.setSizeHint(QSize(10, 34))
        self.list_done.addItem(item); self.list_done.setItemWidget(item, w)

    def add_quarantine_item(self, it: dict):
        from PySide6.QtWidgets import QWidget, QHBoxLayout
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 2, 6, 2)

        qdir = it.get("paths", {}).get("quarantine_dir", "")
        qfile = it.get("output_file", "")
        qpath = Path(qdir)/qfile if qdir and qfile else None

        reason = it.get("summary","Quarantäne")
        title = qfile if qfile else it.get("job_id","?")
        lbl = QLabel(f"{title} | Grund: {reason}")
        lbl.setToolTip(json.dumps(it, ensure_ascii=False, indent=2))

        btn_play = QPushButton("Abspielen"); btn_play.setMaximumWidth(100)
        btn_rerun = QPushButton("Neu (Ton Safe)"); btn_rerun.setMaximumWidth(130)
        btn_details = QPushButton("Details"); btn_details.setMaximumWidth(90)

        def play():
            if qpath and qpath.exists():
                open_path(qpath); activity(f"Quarantäne abspielen: {qpath}")
            else:
                QMessageBox.information(self, "Abspielen", "Ausgabe nicht verfügbar. Quarantäne-Ordner öffnen.")
                if qdir:
                    open_path(Path(qdir))

        def rerun():
            run_quarantine_worker(it.get("job_id"))
            activity(f"Quarantäne neu machen: {it.get('job_id')}")
            QMessageBox.information(self, "Quarantäne", "Neu machen gestartet. Danach: Letzte Nacht aktualisieren.")

        btn_play.clicked.connect(play)
        btn_rerun.clicked.connect(rerun)
        btn_details.clicked.connect(self.open_qjobs_today)

        layout.addWidget(lbl, 1)
        layout.addWidget(btn_play)
        layout.addWidget(btn_rerun)
        layout.addWidget(btn_details)

        item = QListWidgetItem(); item.setSizeHint(QSize(10, 36))
        self.list_q.addItem(item); self.list_q.setItemWidget(item, w)



    # --- Favoriten (Werkzeugkasten) ---
    def on_fav_search(self, t: str):
        self.fav_search = t.strip().lower()
        self.refresh_favorites()

    def on_fav_tag(self, idx: int):
        t = self.fav_tag_combo.currentText()
        self.fav_tag_filter = "alle"
        if t.startswith("Tag: "):
            val = t[5:].strip()
            self.fav_tag_filter = val if val and val != "alle" else "alle"
        self.refresh_favorites()

    def refresh_favorites(self):
        doc = load_favorites()
        items = doc.get("items", [])
        # tags dropdown
        tags = set()
        for it in items:
            for tg in it.get("tags", []):
                tags.add(tg)

        current = self.fav_tag_combo.currentText() if self.fav_tag_combo.count() else "Tag: alle"
        self.fav_tag_combo.blockSignals(True)
        self.fav_tag_combo.clear()
        self.fav_tag_combo.addItem("Tag: alle")
        for tg in sorted(tags):
            self.fav_tag_combo.addItem(f"Tag: {tg}")
        if current:
            ix = self.fav_tag_combo.findText(current)
            if ix >= 0:
                self.fav_tag_combo.setCurrentIndex(ix)
        self.fav_tag_combo.blockSignals(False)

        self.fav_list.clear()
        for it in items:
            p = Path(it.get("path",""))
            name = it.get("name") or p.name or "unbekannt"
            starred = bool(it.get("starred", False))
            tgs = it.get("tags", [])
            if getattr(self, "fav_search", "") and self.fav_search not in name.lower():
                continue
            if getattr(self, "fav_tag_filter", "alle") != "alle":
                if self.fav_tag_filter not in tgs:
                    continue
            lw = QListWidgetItem(("⭐ " if starred else "") + name)
            lw.setData(Qt.UserRole, it.get("id"))
            lw.setToolTip(str(p))
            if p.exists() and is_image_path(p):
                pm = get_thumb_pixmap(p, 64)
                if pm:
                    lw.setIcon(QIcon(pm))
            else:
                lw.setForeground(Qt.gray)
                lw.setText(lw.text() + "  (fehlt)")
        self.fav_list.addItem(lw)

    def _selected_fav_ids(self):
        return [it.data(Qt.UserRole) for it in self.fav_list.selectedItems()]

    def fav_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Favorit hinzufügen", str(Path.home()/ "Downloads"),
            "Bilder/Logos (*.jpg *.jpeg *.png *.webp *.bmp)"
        )
        if not files:
            return
        doc = load_favorites()
        items = doc.get("items", [])
        existing = {it.get("id") for it in items}
        added = 0
        for f in files:
            p = Path(f)
            if not p.exists() or not is_image_path(p):
                continue
            fid = fav_id_for_path(p)
            if fid in existing:
                continue
            items.append({
                "id": fid,
                "path": str(p),
                "name": p.name,
                "type": "bild",
                "tags": [],
                "starred": False,
                "added_at": datetime.utcnow().isoformat(timespec="seconds")+"Z"
            })
            existing.add(fid)
            added += 1
        doc["items"] = items
        save_favorites(doc)
        QMessageBox.information(self, "Favoriten", f"{added} Favorit(en) hinzugefügt.")
        self.refresh_favorites()

    def fav_remove_selected(self):
        ids = set(self._selected_fav_ids())
        if not ids:
            return
        doc = load_favorites()
        before = len(doc.get("items", []))
        doc["items"] = [it for it in doc.get("items", []) if it.get("id") not in ids]
        save_favorites(doc)
        QMessageBox.information(self, "Favoriten", f"Entfernt: {before-len(doc['items'])}")
        self.refresh_favorites()

    def fav_toggle_star(self):
        ids = set(self._selected_fav_ids())
        if not ids:
            return
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") in ids:
                it["starred"] = not bool(it.get("starred", False))
        save_favorites(doc)
        self.refresh_favorites()

    def fav_set_tags(self):
        ids = set(self._selected_fav_ids())
        if not ids:
            return
        text, ok = QInputDialog.getText(self, "Tags setzen", "Tags (kommagetrennt):", text="logo, hell, transparent")
        if not ok:
            return
        tags = norm_tags(text)
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") in ids:
                it["tags"] = tags
        save_favorites(doc)
        self.refresh_favorites()

    def fav_open_selected(self, item: QListWidgetItem):
        fid = item.data(Qt.UserRole)
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") == fid:
                p = Path(it.get("path",""))
                if p.exists():
                    open_path(p)
                else:
                    QMessageBox.information(self, "Favorit", "Datei nicht gefunden. Pfad ist veraltet.")
                return


    # --- Einstellungen (0.9.7) ---
    def _pick_folder_into(self, line_edit, title):
        folder = QFileDialog.getExistingDirectory(self, title, str(Path.home()/ "Downloads"))
        if folder:
            line_edit.setText(folder)

    def _settings_defaults(self):
        self.set_watch_folder.setText(str(Path.home()/ "Downloads"))
        self.set_exports_dir.setText("exports")
        self.set_library_audio_dir.setText("library/audio")
        self.set_library_images_dir.setText("library/images")
        self.set_quarantine_dir.setText("quarantine")
        self.set_quarantine_jobs_dir.setText("quarantine_jobs")
        self.set_reports_dir.setText("reports")
        self.set_staging_dir.setText("staging")
        self.set_trash_dir.setText("trash")

        self.set_fade_in.setValue(0.5)
        self.set_fade_out.setValue(1.0)
        self.set_min_br.setValue(192)
        self.set_target_br.setValue(320)
        self.set_sr.setValue(48000)

        self.set_tmpl_single.setText("{audio}_{vorlage}_{datum}_{uhrzeit}{sw}")
        self.set_tmpl_batch.setText("{audio}_{vorlage}_{datum}_{nummer}{sw}")
        self.set_append_label.setChecked(False)
        ix = self.set_append_mode.findText("only_quarantine")
        if ix >= 0:
            self.set_append_mode.setCurrentIndex(ix)
        self.set_append_short.setChecked(True)
        self._update_name_preview()

    def _settings_save(self):
        self.settings.setdefault("paths", {})
        self.settings["paths"]["watch_folder"] = self.set_watch_folder.text().strip()
        for k in ["exports_dir","library_audio_dir","library_images_dir","quarantine_dir","quarantine_jobs_dir","reports_dir","staging_dir","trash_dir"]:
            le = getattr(self, f"set_{k}")
            self.settings["paths"][k] = le.text().strip() or self.settings["paths"].get(k,"")

        self.settings.setdefault("audio", {})
        self.settings["audio"]["fade_in_sec"] = float(self.set_fade_in.value())
        self.settings["audio"]["fade_out_sec"] = float(self.set_fade_out.value())
        self.settings["audio"]["min_bitrate_kbps"] = int(self.set_min_br.value())
        self.settings["audio"]["target_bitrate_kbps"] = int(self.set_target_br.value())
        self.settings["audio"]["target_samplerate_hz"] = int(self.set_sr.value())

        self.settings.setdefault("naming", {})
        self.settings["naming"]["template_single"] = self.set_tmpl_single.text().strip()
        self.settings["naming"]["template_batch"] = self.set_tmpl_batch.text().strip()
        self.settings["naming"]["append_label_to_output"] = bool(self.set_append_label.isChecked())
        self.settings["naming"]["append_label_mode"] = self.set_append_mode.currentText().strip()
        self.settings["naming"]["append_label_shortform"] = bool(self.set_append_short.isChecked())

        (config_dir()/ "settings.json").write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, self.texts["strings"].get("settings.ok","OK"), "Gespeichert. Werkstatt läuft weiter.")
        activity("Einstellungen gespeichert.")

    def _settings_test_paths(self):
        base_dir = data_dir()
        rels = {
            "exports": self.set_exports_dir.text().strip(),
            "library_audio": self.set_library_audio_dir.text().strip(),
            "library_images": self.set_library_images_dir.text().strip(),
            "quarantine": self.set_quarantine_dir.text().strip(),
            "quarantine_jobs": self.set_quarantine_jobs_dir.text().strip(),
            "reports": self.set_reports_dir.text().strip(),
            "staging": self.set_staging_dir.text().strip(),
            "trash": self.set_trash_dir.text().strip(),
        }
        errors = []
        for key, rel in rels.items():
            if not rel:
                errors.append(f"{key}: leer")
                continue
            p = base_dir / rel
            try:
                p.mkdir(parents=True, exist_ok=True)
                testfile = p / ".modultool_write_test.tmp"
                testfile.write_text("ok", encoding="utf-8")
                testfile.unlink(missing_ok=True)
            except Exception as e:
                errors.append(f"{key}: {e}")

        watch = Path(self.set_watch_folder.text().strip()).expanduser()
        if not watch.exists():
            errors.append(f"watch_folder fehlt: {watch}")

        if errors:
            QMessageBox.critical(self, self.texts["strings"].get("settings.fehler","Fehler"), "Pfade nicht ok:\n- " + "\n- ".join(errors))
        else:
            QMessageBox.information(self, self.texts["strings"].get("settings.ok","OK"), "Alle Pfade sind schreibbar. Nachtbetrieb ist safe.")
        activity("Pfade getestet.")

    def _update_name_preview(self):
        import datetime as _dt
        audio = "track_demo"
        vorlage = "youtube_hd_ton_safe"
        datum = _dt.datetime.now().strftime("%Y-%m-%d")
        uhrzeit = _dt.datetime.now().strftime("%H%M%S")
        nummer = "003"
        sw = ""
        try:
            example = self.set_tmpl_batch.text().format(audio=audio, vorlage=vorlage, datum=datum, uhrzeit=uhrzeit, nummer=nummer, sw=sw)
        except Exception:
            example = "(Vorlage hat Fehler)"
        self.lbl_preview_name.setText(example + ".mp4")


    # --- Quarantäne Tabelle (0.9.9) ---
    def _get_today_quar_doc(self):
        # reuse existing helper: load_today_quarantine_jobs
        try:
            return load_today_quarantine_jobs()
        except Exception:
            return {"items":[],"list_status":"offen"}

    def _load_quarantine_table(self):
        from PySide6.QtWidgets import QTableWidgetItem
        doc = self._get_today_quar_doc()
        doc = update_quarantine_list_status(doc)
        save_today_quarantine_jobs(doc)

        items = doc.get("items", [])
        self.quar_table.setRowCount(len(items))
        for r, it in enumerate(items):
            status = it.get("status","")
            out_file = it.get("output_file","")
            reason = it.get("summary","")
            tries = f"{it.get('tries',0)}/{it.get('max_tries',3)}"
            job_id = it.get("job_id","")

            self.quar_table.setItem(r, 0, QTableWidgetItem(status))
            self.quar_table.setItem(r, 1, QTableWidgetItem(out_file))
            self.quar_table.setItem(r, 2, QTableWidgetItem(reason))
            self.quar_table.setItem(r, 3, QTableWidgetItem(tries))
            self.quar_table.setItem(r, 4, QTableWidgetItem(it.get("recommended_action","")))
            self.quar_table.setItem(r, 5, QTableWidgetItem(job_id))

        # Visual hint: mark abgehakt in tab title
        idx = self.left.indexOf(self.quar_table.parentWidget().parentWidget())
        # cannot reliably locate tab widget by parent; keep as-is.

    def _selected_quar_job_id(self):
        sel = self.quar_table.selectionModel().selectedRows()
        if not sel:
            return None
        row = sel[0].row()
        item = self.quar_table.item(row, 5)
        return item.text() if item else None

    def _update_quar_status(self, job_id: str, new_status: str):
        doc = self._get_today_quar_doc()
        changed = False
        for it in doc.get("items", []):
            if it.get("job_id") == job_id:
                it["status"] = new_status
                changed = True
        if changed:
            doc = update_quarantine_list_status(doc)
            save_today_quarantine_jobs(doc)
        return changed

    def _quar_open_folder(self):
        # open today's quarantine folder, if exists
        qdir = data_dir()/self.settings.get("paths",{}).get("quarantine_dir","quarantine")/datetime.now().strftime("%Y-%m-%d")
        open_path(qdir)

    def _quar_replace_source_simple(self, job_id: str):
        # minimal: open JSON and let user use existing dashboard replace flow later
        # (full replace UI comes in later iteration)
        QMessageBox.information(self, "Quelle ersetzen", "Für jetzt: Öffne die Tagesliste (JSON) und ändere staging_audio/staging_image.\nDanach 'Neu (Ton Safe)'.")
        self.open_qjobs_today()



    # --- Werkbank Export (0.9.10) ---
    def _wb_pick_logo(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Logo wählen", str(Path.home()/ "Downloads"), "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)")
        if fp:
            self.wb_logo_path.setText(fp)
            self.wb_logo_on.setChecked(True)

    def _wb_collect_selection(self):
        # Find checked items and pick first audio + first image.
        audios = []
        images = []
        for i in range(self.material.count()):
            it = self.material.item(i)
            if it.checkState() == Qt.Checked:
                p = Path(it.data(Qt.UserRole) or "")
                if p.exists():
                    if is_audio_path(p):
                        audios.append(p)
                    elif is_image_path(p):
                        images.append(p)
        return audios, images

    def _wb_export(self):
        # Choose audio/image; batch if multiple audios.
        audios, images = self._wb_collect_selection()
        if not audios:
            QMessageBox.information(self, "Werkbank", "Keine Audio-Datei ausgewählt. Checkboxen setzen.")
            return
        if not images:
            QMessageBox.information(self, "Werkbank", "Kein Bild ausgewählt. Checkboxen setzen.")
            return

        preset = self.wb_preset.currentText().strip()
        # text options
        text = self.wb_text.text().strip() if self.wb_text_on.isChecked() else ""
        pos = self.wb_text_pos.currentText().strip()
        speed_mode = self.wb_text_speed.currentText().strip()
        speed = 160 if speed_mode=="slow" else (220 if speed_mode=="medium" else (320 if speed_mode=="fast" else 220))
        text_bg = bool(self.wb_text_bg.isChecked())

        logo = self.wb_logo_path.text().strip() if self.wb_logo_on.isChecked() else ""
        if logo and not Path(logo).exists():
            QMessageBox.information(self, "Werkbank", self.texts["strings"].get("edge.no_logo_file",""))
            logo = ""
            self.wb_logo_on.setChecked(False)
        logo_pos = self.wb_logo_pos.currentText().strip()
        logo_scale = int(self.wb_logo_scale.value())
        gray = bool(self.wb_gray.isChecked())

        # Output dir inside exports/YYYY-MM-DD
        day = datetime.now().strftime("%Y-%m-%d")
        outdir = data_dir()/self.settings.get("paths",{}).get("exports_dir","exports")/day
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            test = outdir/".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
        except Exception:
            QMessageBox.information(self, "Werkbank", self.texts["strings"].get("edge.outdir_fail",""))
            outdir = data_dir()/"exports"/day
            outdir.mkdir(parents=True, exist_ok=True)

        # Bild-Zuweisung (one/seq/manual)
        if hasattr(self, '_wb_build_jobs'):
            jobs = self._wb_build_jobs()
        else:
            jobs = [(a, images[0]) for a in audios]

        # Run jobs sequentially via QProcess calling tools/run_workbench_export.sh
        script = portable_root()/ "tools"/ "run_workbench_export.sh"
        if not script.exists():
            QMessageBox.critical(self, "Werkbank", "run_workbench_export.sh fehlt")
            return

        self.statusBar().showMessage(f"Werkbank: {len(jobs)} Auftrag/ Aufträge laufen …")
        self._wb_jobs = jobs
        self._wb_job_index = 0

        def run_next():
            if self._wb_job_index >= len(self._wb_jobs):
                self.statusBar().showMessage("Werkbank fertig. Ausgaben liegen im Export-Ordner.")
                QMessageBox.information(self, "Werkbank", "Fertig. Ausgaben sind gebaut.")
                self.refresh_last_night()
                return
            a, img = self._wb_jobs[self._wb_job_index]
            self._wb_job_index += 1

            args = ["--audio", str(a), "--image", str(img), "--outdir", str(outdir), "--preset", preset,
                    "--text", text, "--text_pos", pos, "--text_speed", str(speed)]
            if text_bg: args.append("--text_bg")
            if gray: args.append("--grayscale")
            if logo:
                args += ["--logo", logo, "--logo_pos", logo_pos, "--logo_scale", str(logo_scale)]

            self._wb_proc = QProcess(self)
            self._wb_proc.setProgram("bash")
            self._wb_proc.setArguments([str(script)] + args)

            def finished(*_):
                run_next()

            self._wb_proc.finished.connect(finished)
            self._wb_proc.start()

        run_next()

    def _wb_open_exports(self):
        day = datetime.now().strftime("%Y-%m-%d")
        outdir = data_dir()/self.settings.get("paths",{}).get("exports_dir","exports")/day
        open_path(outdir)


    def _wb_open_assign(self):
        """
        Manual pairing UI:
        - build a simple text editor list: one line per audio: audio_path | image_path
        - user can edit image paths
        """
        audios, images = self._wb_collect_selection()
        if not audios:
            QMessageBox.information(self, "Zuweisung", "Keine Audios ausgewählt.")
            return
        if not images:
            QMessageBox.information(self, "Zuweisung", "Keine Bilder ausgewählt.")
            return

        # Create default mapping: seq
        lines = []
        for idx, a in enumerate(audios, start=1):
            img = images[idx-1] if idx-1 < len(images) else images[0]
            lines.append(f"{a} | {img}")

        # Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Manuelle Zuweisung (Audio | Bild)")
        layout = QVBoxLayout(dlg)
        info = QLabel("Eine Zeile = ein Arbeitsgang. Du kannst Bildpfade ändern. Format: audio | bild")
        info.setWordWrap(True)
        layout.addWidget(info)
        edit = QTextEdit()
        edit.setPlainText("\n".join(lines))
        layout.addWidget(edit, 1)
        btns = QHBoxLayout()
        btn_ok = QPushButton(self.texts["strings"].get("workbench.assign_apply","Zuweisung übernehmen"))
        btn_cancel = QPushButton("Abbrechen")
        btns.addWidget(btn_ok); btns.addWidget(btn_cancel)
        layout.addLayout(btns)

        def apply():
            mapping = []
            for line in edit.toPlainText().splitlines():
                if "|" not in line:
                    continue
                a_s, i_s = [x.strip() for x in line.split("|", 1)]
                if not a_s or not i_s:
                    continue
                ap = Path(a_s)
                ip = Path(i_s)
                if ap.exists() and ip.exists():
                    mapping.append((ap, ip))
            self._wb_manual_map = mapping
            dlg.accept()

        btn_ok.clicked.connect(apply)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def _wb_build_jobs(self):
        # Returns list[(audio_path, image_path)]
        audios, images = self._wb_collect_selection()
        if not audios or not images:
            return []
        mode = self.wb_pairing.currentText().strip()
        if mode == "manual" and self._wb_manual_map:
            return self._wb_manual_map
        if mode == "seq":
            jobs = []
            for idx, a in enumerate(audios, start=1):
                img = images[idx-1] if idx-1 < len(images) else images[0]
                jobs.append((a, img))
            return jobs
        # default "one"
        img0 = images[0]
        return [(a, img0) for a in audios]


    def help_find(self, q: str):
        if not q.strip():
            return
        text = self.help_view.toPlainText()
        idx = text.lower().find(q.lower())
        if idx >= 0:
            cursor = self.help_view.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx+len(q), cursor.KeepAnchor)
            self.help_view.setTextCursor(cursor)


    # --- Barriere-Labels (0.9.13) ---
    def _acc(self, widget, name: str, desc: str = ""):
        try:
            widget.setAccessibleName(name)
            if desc:
                widget.setAccessibleDescription(desc)
        except Exception:
            pass


    def run_mustpass(self):
        script = portable_root()/"tools"/"run_must_pass.sh"
        if not script.exists():
            QMessageBox.critical(self, "Must-Pass", "run_must_pass.sh fehlt")
            return
        self.statusBar().showMessage("Must-Pass Suite läuft…")
        self._mp_proc = QProcess(self)
        self._mp_proc.setProgram("bash")
        self._mp_proc.setArguments([str(script)])
        def done(*args):
            self.statusBar().showMessage("Must-Pass Suite fertig. Report liegt in reports/.")
            QMessageBox.information(self, "Must-Pass", "Fertig. Öffne reports/ und schau must_pass_*.json.")
        self._mp_proc.finished.connect(done)
        self._mp_proc.start()


    def _run_preflight(self):
        self.preflight = preflight_run(config_dir()/ "settings.json")
        t = self.preflight
        msg_lines = []
        if not t.get("ffmpeg_ok", True):
            msg_lines.append(self.texts["strings"].get("preflight.missing_ffmpeg","FFmpeg fehlt."))
        if not t.get("watchfolder_ok", True):
            msg_lines.append(self.texts["strings"].get("preflight.watch_missing","Watchfolder fehlt."))
        if not t.get("space_ok", True):
            msg_lines.append(self.texts["strings"].get("preflight.space_low","Wenig Speicher frei.") + f" ({t.get('free_mb')} MB)")
        for k,v in (t.get("writable") or {}).items():
            if not v.get("ok", True):
                msg_lines.append(f"Ordner nicht schreibbar: {k} ({v.get('path')})")
        # Font-Check: wenn Font fehlt, Lauftext deaktivieren
        if not bool(t.get("font_ok", True)):
            if hasattr(self, "wb_text_on"):
                self.wb_text_on.setChecked(False)
                self.wb_text_on.setEnabled(False)
            if hasattr(self, "wb_text"):
                self.wb_text.setEnabled(False)
            msg_lines.append(self.texts["strings"].get("edge.font_missing","Schrift fehlt: Lauftext deaktiviert."))
        else:
            if hasattr(self, "wb_text_on"):
                self.wb_text_on.setEnabled(True)
            if hasattr(self, "wb_text"):
                self.wb_text.setEnabled(True)

        if not msg_lines:
            msg = self.texts["strings"].get("preflight.ok","Alles bereit.")
        else:
            msg = "- " + "\n- ".join(msg_lines)

        self.preflight_banner.setTitle("Werkstatt-Check ✅" if t.get("overall_ok") else "Werkstatt-Check ⚠️")
        self.lbl_preflight.setText(msg)

        ffok = bool(t.get("ffmpeg_ok", True))
        # Wenn Watchfolder fehlt: Setup-Button wird zum "Watchfolder wählen"
        if not bool(t.get("watchfolder_ok", True)):
            self.btn_preflight_setup.setText(self.texts["strings"].get("edge.pick_watch","Watchfolder wählen"))
            try:
                self.btn_preflight_setup.clicked.disconnect()
            except Exception:
                pass
            self.btn_preflight_setup.clicked.connect(self._pick_and_save_watchfolder)
        else:
            self.btn_preflight_setup.setText(self.texts["strings"].get("preflight.setup","Jetzt einrichten (FFmpeg)"))
            try:
                self.btn_preflight_setup.clicked.disconnect()
            except Exception:
                pass
            self.btn_preflight_setup.clicked.connect(self.setup_clicked)

        if hasattr(self, "btn_wb_export"):
            self.btn_wb_export.setEnabled(ffok)
        if hasattr(self, "btn_run"):
            self.btn_run.setEnabled(ffok)
        if hasattr(self, "btn_mustpass"):
            self.btn_mustpass.setEnabled(ffok)
        return t

    def _show_preflight_details(self):
        t = getattr(self, "preflight", None) or self._run_preflight()
        QMessageBox.information(self, "Werkstatt-Check Details", json.dumps(t, ensure_ascii=False, indent=2))


    def _pick_and_save_watchfolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Watchfolder wählen", str(Path.home()/ "Downloads"))
        if not folder:
            return
        # Update settings UI if present
        try:
            if hasattr(self, "set_watch_folder"):
                self.set_watch_folder.setText(folder)
            self.settings.setdefault("paths", {})
            self.settings["paths"]["watch_folder"] = folder
            (config_dir()/ "settings.json").write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Watchfolder", self.texts["strings"].get("edge.watch_set","Watchfolder gesetzt und gespeichert."))
        except Exception as e:
            QMessageBox.critical(self, "Watchfolder", f"Konnte nicht speichern:\n{e}")
        self._run_preflight()

def main():
    app = QApplication(sys.argv)
    win = Main()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
