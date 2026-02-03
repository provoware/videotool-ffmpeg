import json
from datetime import datetime
from pathlib import Path

from i18n_utils import load_texts
from io_utils import atomic_write_json
from preflight import run as preflight_run
from logging_utils import log_exception, log_message
from paths import config_dir, data_dir, repo_root
from validation_utils import (
    ensure_existing_dir,
    ensure_existing_file,
    PathValidationError,
)
from PySide6.QtCore import Qt, QSize, QProcess
from PySide6.QtGui import QPixmap, QIcon, QImageReader
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidgetItem,
    QMessageBox,
    QTextEdit,
    QFileDialog,
    QInputDialog,
    QDialog,
)
from ui_main_layout import build_main_layout
from quarantine_table_controller import QuarantineTableController

from app_services import (
    activity,
    ensure_dirs,
    fav_id_for_path,
    favorites_dir,
    get_thumb_pixmap,
    have,
    is_audio_path,
    is_image_path,
    latest_report_file,
    load_favorites,
    load_json,
    load_today_quarantine_jobs,
    normalize_report_doc,
    norm_tags,
    open_path,
    rename_file_safe,
    run_automation_now,
    run_quarantine_worker,
    run_setup,
    run_timer_install,
    save_favorites,
    save_today_quarantine_jobs,
    today_quarantine_jobs,
    update_quarantine_list_status,
    _load_theme_qss,
)


class Main(QMainWindow):
    def apply_theme(self):
        theme = self.settings.get("ui", {}).get("theme", "hochkontrast_dunkel")
        qss = _load_theme_qss(theme)
        if not qss:
            fallback = "hochkontrast_dunkel"
            if theme != fallback:
                log_message(
                    "Theme fehlt, Standard wird genutzt.",
                    level="WARN",
                    context="ui",
                    extra={"theme": theme, "fallback": fallback},
                )
            theme = fallback
            qss = _load_theme_qss(theme)
        if qss:
            QApplication.instance().setStyleSheet(qss)
        # Button height and padding can be adjusted via stylesheet, but keep min heights coherent
        self._ui_button_height = int(
            self.settings.get("ui", {}).get("button_height", 38)
        )

    def __init__(self):
        super().__init__()
        ensure_dirs()
        self.settings = load_json(config_dir() / "settings.json", {})
        self.texts = load_texts(self.settings)
        self.rules_path = config_dir() / "automation_rules.json"
        self.rules = load_json(self.rules_path, {})
        self._tool_procs = []

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

        self._init_ui()
        self._load_help_center()
        self._quar_controller = QuarantineTableController(
            self.quar_table,
            self.statusBar(),
            load_today_quarantine_jobs,
            save_today_quarantine_jobs,
            update_quarantine_list_status,
        )

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
        self.btn_quar_rerun.clicked.connect(
            lambda: (
                lambda jid=self._selected_quar_job_id(): run_quarantine_worker(jid)
                if jid
                else None
            )()
        )
        self.btn_quar_replace.clicked.connect(
            lambda: (
                lambda jid=self._selected_quar_job_id(): self._quar_replace_source_simple(
                    jid
                )
                if jid
                else None
            )()
        )
        self.btn_quar_postpone.clicked.connect(
            lambda: (
                lambda jid=self._selected_quar_job_id(): self._update_quar_status(
                    jid, "zurueckgestellt"
                )
                and self._load_quarantine_table()
                if jid
                else None
            )()
        )
        self.btn_quar_done.clicked.connect(
            lambda: (
                lambda jid=self._selected_quar_job_id(): self._update_quar_status(
                    jid, "erledigt"
                )
                and self._load_quarantine_table()
                if jid
                else None
            )()
        )
        # Initial load
        self._load_quarantine_table()
        self.quar_table.itemChanged.connect(self._quar_controller.on_item_changed)
        self.chk_auto.stateChanged.connect(self.toggle_automation_enabled)
        self.dev_search.textChanged.connect(self.dev_find)

        # Hilfe
        self.help_search.textChanged.connect(self.help_find)
        self.help_topics.itemActivated.connect(self._jump_help_topic)
        self.help_topics.itemClicked.connect(self._jump_help_topic)
        self.btn_help_open.clicked.connect(
            lambda: open_path(config_dir() / "HELP_CENTER.md")
        )
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
        self._acc(
            self.material,
            "Materialliste",
            "Liste der importierten Dateien. Checkboxen wählen die Auswahl.",
        )
        self._acc(
            self.preview_img,
            "Bildvorschau",
            "Große Vorschau des aktuell gewählten Bildes.",
        )
        self._acc(
            self.sel_list, "Auswahlkorb", "Liste der ausgewählten Dateien, bearbeitbar."
        )
        self._acc(
            self.fav_list,
            "Favoritenliste",
            "Liste der Favoriten. Doppelklick öffnet Datei.",
        )
        self._acc(
            self.btn_wb_export,
            "Ausgabe bauen",
            "Startet den Werkbank-Export für die aktuelle Auswahl.",
        )
        self._acc(
            self.btn_quar_refresh,
            "Quarantäne aktualisieren",
            "Lädt die Quarantäne-Tagesliste neu.",
        )
        self._acc(self.help_view, "Hilfeansicht", "Hilfe-Center Inhalt.")
        self._acc(self.dev_view, "Entwicklerdoku", "Entwickler-Handbuch im Tool.")
        self._acc(
            self.btn_settings_save,
            "Einstellungen speichern",
            "Speichert die aktuellen Einstellungen.",
        )
        self._acc(
            self.btn_settings_test, "Pfade testen", "Prüft Schreibrechte und Pfade."
        )
        # Barriere-Labels gesetzt
        self.refresh_favorites()
        self.apply_material_filter()

        if not have("ffmpeg") or not have("ffprobe"):
            self.statusBar().showMessage(
                "Hinweis: FFmpeg fehlt. Bitte tagsüber einrichten."
            )
            activity("Hinweis: ffmpeg/ffprobe fehlt (Setup empfohlen).")

    def _init_ui(self):
        build_main_layout(self)

    # --- Search/filter handlers ---
    def on_material_search(self, t: str):
        self.material_search = t.strip().lower()
        self.apply_material_filter()

    def on_material_type(self, idx: int):
        self.material_type_filter = ["alle", "audio", "bilder"][idx]
        self.apply_material_filter()

    def on_selection_search(self, t: str):
        self.selection_search = t.strip().lower()
        self.refresh_sel()

    def on_selection_type(self, idx: int):
        self.selection_type_filter = ["alle", "audio", "bilder"][idx]
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
        self._find_in_text_view(
            self.dev_view,
            q,
            "Entwicklerdoku-Suche",
            "Suche in Entwicklerdoku abgeschlossen.",
        )

    # --- Import ---
    def pick_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien holen",
            str(Path.home() / "Downloads"),
            "Audio/Bilder (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if files:
            self.add_paths_to_material([Path(f) for f in files])

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Ordner holen", str(Path.home() / "Downloads")
        )
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
            self.statusBar().showMessage(
                f"{added} Datei(en) geholt. Jetzt: Checkboxen anklicken."
            )
            activity(f"Import: {added} Datei(en) hinzugefügt.")
        self.refresh_sel()

    def _add_single_path(self, p: Path) -> int:
        if not is_audio_path(p) and not is_image_path(p):
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
                pm2 = pm.scaled(
                    self.preview_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.preview_img.setPixmap(pm2)
                self.preview_img.setText("")
                try:
                    st = p.stat()
                    self.preview_info.setText(
                        f"{p.name}\n{p.parent}\nGröße: {st.st_size // 1024} KB"
                    )
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

        self.statusBar().showMessage(
            "Auswahl aktualisiert. Nächster Schritt: Vorschau klicken."
        )

    def _add_selection_row(self, material_item: QListWidgetItem, path_str: str):
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

        btn_rename = QPushButton("Umbenennen")
        btn_rename.setMaximumWidth(120)
        btn_remove = QPushButton("Entfernen")
        btn_remove.setMaximumWidth(100)

        def do_remove():
            material_item.setCheckState(Qt.Unchecked)
            self.refresh_sel()
            activity(f"Auswahl entfernt: {material_item.text()}")

        def do_rename():
            if not path_str:
                QMessageBox.information(
                    self, "Umbenennen", "Diese Auswahl hat keinen echten Pfad."
                )
                return
            p = Path(path_str)
            if not p.exists():
                QMessageBox.information(
                    self, "Umbenennen", "Datei nicht gefunden. Pfad ist veraltet."
                )
                return
            new_name, ok = QInputDialog.getText(
                self, "Umbenennen", "Neuer Name (ohne Endung):", text=p.stem
            )
            if not ok or not new_name.strip():
                return
            try:
                new_path = rename_file_safe(p, new_name)
            except Exception as e:
                QMessageBox.critical(
                    self, "Umbenennen", f"Konnte nicht umbenennen:\n{e}"
                )
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
        proc = run_setup(self)
        if proc:
            self._tool_procs.append(proc)

    def open_exports(self):
        exports = data_dir() / self.settings.get("paths", {}).get(
            "exports_dir", "exports"
        )
        self._open_dir_with_feedback(exports, "Ausgaben-Ordner")

    def open_reports(self):
        reports = data_dir() / self.settings.get("paths", {}).get(
            "reports_dir", "reports"
        )
        self._open_dir_with_feedback(reports, "Reports")

    def open_last_report(self):
        rf = latest_report_file()
        if rf:
            self._open_file_with_feedback(rf, "Arbeitsbericht")
        else:
            QMessageBox.information(
                self, "Arbeitsbericht", "Noch kein Arbeitsbericht vorhanden."
            )

    # --- Automation controls ---
    def install_timer(self):
        proc = run_timer_install(self)
        if proc:
            self._tool_procs.append(proc)

    def run_auto(self):
        proc = run_automation_now(self)
        if proc:
            self._tool_procs.append(proc)

    def toggle_automation_enabled(self, state: int):
        self.rules["enabled"] = state == Qt.Checked
        ok = atomic_write_json(
            self.rules_path,
            self.rules,
            context="ui.rules_save",
        )
        if ok:
            activity(
                f"Automatik {'aktiviert' if self.rules['enabled'] else 'deaktiviert'}."
            )
        else:
            QMessageBox.critical(
                self,
                "Automatik",
                "Speichern der Automatik-Regeln fehlgeschlagen.",
            )

    # --- Selftest (0.9.2) ---
    def selftest_full(self):
        script = repo_root() / "tools" / "run_selftest.sh"
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
            QMessageBox.information(
                self,
                "Selftest",
                "Selftest fertig. Schau in 'Letzte Nacht' (inkl. Quarantäne-Aufträge).",
            )

        self._selftest_proc.finished.connect(done)
        self._selftest_proc.start()

    # --- Quarantine daily jobs ---
    def open_qjobs_today(self):
        p = today_quarantine_jobs()
        if p.exists():
            open_path(p)
        else:
            QMessageBox.information(
                self, "Quarantäne", "Heute keine Quarantäne-Aufträge."
            )
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
            self.lbl_last_summary.setText(
                "Noch kein Lauf gefunden. Automatik einrichten oder Test starten."
            )
            self.list_q.addItem("Quarantäne heute: abgehakt ✅")
            return

        rep = normalize_report_doc(load_json(rf, {}))
        summ = rep.get("summary", {})
        errors = rep.get("errors", []) if isinstance(rep, dict) else []
        summary_text = (
            f"Lauf {rep.get('run_id', '?')}: fertig={summ.get('fertig', 0)} | "
            f"quarantäne={summ.get('quarantaene', 0)} | gesamt={summ.get('gesamt', 0)}"
        )
        if errors:
            summary_text += f" | Fehler={len(errors)}"
        self.lbl_last_summary.setText(summary_text)

        for err in errors[:3]:
            msg = err.get("message", "Unbekannter Fehler")
            detail = err.get("details", "")
            if detail:
                self.list_q.addItem(f"Fehler: {msg} ({detail})")
            else:
                self.list_q.addItem(f"Fehler: {msg}")

        finished = [
            j
            for j in rep.get("jobs", [])
            if j.get("status") == "fertig" and j.get("output_final")
        ]
        finished = finished[-3:] if len(finished) > 3 else finished
        for j in finished:
            p = Path(j["output_final"])
            if self.done_search and self.done_search not in p.name.lower():
                continue
            self.add_done_item(p)

        qdoc = None
        st = rep.get("selftest", {}) if isinstance(rep, dict) else {}
        qf = st.get("quarantine_jobs_file")
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
            open_items = [
                it
                for it in qdoc.get("items", [])
                if it.get("status") in ("bereit", "laeuft", "fest")
            ]
            # apply search filter
            if self.q_search:
                open_items = [
                    it
                    for it in open_items
                    if self.q_search
                    in (it.get("output_file", "") + it.get("summary", "")).lower()
                ]
            show = open_items[:3]
            if not show:
                self.list_q.addItem("Quarantäne heute: abgehakt ✅")
            else:
                for it in show:
                    self.add_quarantine_item(it)
                if len(open_items) > 3:
                    self.list_q.addItem(
                        f"+{len(open_items) - 3} weitere … (Tagesliste öffnen)"
                    )
        self.statusBar().showMessage("Letzte Nacht aktualisiert.")

    def add_done_item(self, file_path: Path):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 2, 6, 2)
        lbl = QLabel(file_path.name)
        lbl.setToolTip(str(file_path))
        btn_play = QPushButton("Abspielen")
        btn_play.setMaximumWidth(110)
        btn_folder = QPushButton("Ordner")
        btn_folder.setMaximumWidth(90)

        btn_play.clicked.connect(
            lambda: (open_path(file_path), activity(f"Abspielen: {file_path}"))
        )
        btn_folder.clicked.connect(
            lambda: (
                open_path(file_path.parent),
                activity(f"Ordner öffnen: {file_path.parent}"),
            )
        )

        layout.addWidget(lbl, 1)
        layout.addWidget(btn_play)
        layout.addWidget(btn_folder)
        item = QListWidgetItem()
        item.setSizeHint(QSize(10, 34))
        self.list_done.addItem(item)
        self.list_done.setItemWidget(item, w)

    def add_quarantine_item(self, it: dict):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(6, 2, 6, 2)

        qdir = it.get("paths", {}).get("quarantine_dir", "")
        qfile = it.get("output_file", "")
        qpath = Path(qdir) / qfile if qdir and qfile else None

        reason = it.get("summary", "Quarantäne")
        title = qfile if qfile else it.get("job_id", "?")
        lbl = QLabel(f"{title} | Grund: {reason}")
        lbl.setToolTip(json.dumps(it, ensure_ascii=False, indent=2))

        btn_play = QPushButton("Abspielen")
        btn_play.setMaximumWidth(100)
        btn_rerun = QPushButton("Neu (Ton Safe)")
        btn_rerun.setMaximumWidth(130)
        btn_details = QPushButton("Details")
        btn_details.setMaximumWidth(90)

        def play():
            if qpath and qpath.exists():
                open_path(qpath)
                activity(f"Quarantäne abspielen: {qpath}")
            else:
                QMessageBox.information(
                    self,
                    "Abspielen",
                    "Ausgabe nicht verfügbar. Quarantäne-Ordner öffnen.",
                )
                if qdir:
                    open_path(Path(qdir))

        def rerun():
            run_quarantine_worker(it.get("job_id"))
            activity(f"Quarantäne neu machen: {it.get('job_id')}")
            QMessageBox.information(
                self,
                "Quarantäne",
                "Neu machen gestartet. Danach: Letzte Nacht aktualisieren.",
            )

        btn_play.clicked.connect(play)
        btn_rerun.clicked.connect(rerun)
        btn_details.clicked.connect(self.open_qjobs_today)

        layout.addWidget(lbl, 1)
        layout.addWidget(btn_play)
        layout.addWidget(btn_rerun)
        layout.addWidget(btn_details)

        item = QListWidgetItem()
        item.setSizeHint(QSize(10, 36))
        self.list_q.addItem(item)
        self.list_q.setItemWidget(item, w)

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

        current = (
            self.fav_tag_combo.currentText()
            if self.fav_tag_combo.count()
            else "Tag: alle"
        )
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
            p = Path(it.get("path", ""))
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
            self,
            "Favorit hinzufügen",
            str(Path.home() / "Downloads"),
            "Bilder/Logos (*.jpg *.jpeg *.png *.webp *.bmp)",
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
            items.append(
                {
                    "id": fid,
                    "path": str(p),
                    "name": p.name,
                    "type": "bild",
                    "tags": [],
                    "starred": False,
                    "added_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                }
            )
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
        QMessageBox.information(
            self, "Favoriten", f"Entfernt: {before - len(doc['items'])}"
        )
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
        text, ok = QInputDialog.getText(
            self, "Tags setzen", "Tags (kommagetrennt):", text="logo, hell, transparent"
        )
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
                p = Path(it.get("path", ""))
                if p.exists():
                    open_path(p)
                else:
                    QMessageBox.information(
                        self, "Favorit", "Datei nicht gefunden. Pfad ist veraltet."
                    )
                return

    # --- Einstellungen (0.9.7) ---
    def _pick_folder_into(self, line_edit, title):
        folder = QFileDialog.getExistingDirectory(
            self, title, str(Path.home() / "Downloads")
        )
        if folder:
            line_edit.setText(folder)

    def _settings_defaults(self):
        self.set_watch_folder.setText(str(Path.home() / "Downloads"))
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
        for k in [
            "exports_dir",
            "library_audio_dir",
            "library_images_dir",
            "quarantine_dir",
            "quarantine_jobs_dir",
            "reports_dir",
            "staging_dir",
            "trash_dir",
        ]:
            le = getattr(self, f"set_{k}")
            self.settings["paths"][k] = le.text().strip() or self.settings["paths"].get(
                k, ""
            )

        self.settings.setdefault("audio", {})
        self.settings["audio"]["fade_in_sec"] = float(self.set_fade_in.value())
        self.settings["audio"]["fade_out_sec"] = float(self.set_fade_out.value())
        self.settings["audio"]["min_bitrate_kbps"] = int(self.set_min_br.value())
        self.settings["audio"]["target_bitrate_kbps"] = int(self.set_target_br.value())
        self.settings["audio"]["target_samplerate_hz"] = int(self.set_sr.value())

        self.settings.setdefault("naming", {})
        self.settings["naming"]["template_single"] = self.set_tmpl_single.text().strip()
        self.settings["naming"]["template_batch"] = self.set_tmpl_batch.text().strip()
        self.settings["naming"]["append_label_to_output"] = bool(
            self.set_append_label.isChecked()
        )
        self.settings["naming"]["append_label_mode"] = (
            self.set_append_mode.currentText().strip()
        )
        self.settings["naming"]["append_label_shortform"] = bool(
            self.set_append_short.isChecked()
        )

        settings_path = config_dir() / "settings.json"
        ok = atomic_write_json(
            settings_path,
            self.settings,
            context="ui.settings_save",
        )
        if ok:
            QMessageBox.information(
                self,
                self.texts["strings"].get("settings.ok", "OK"),
                "Gespeichert. Werkstatt läuft weiter.",
            )
            activity("Einstellungen gespeichert.")
        else:
            QMessageBox.critical(
                self,
                "Einstellungen",
                "Speichern fehlgeschlagen. Bitte erneut versuchen.",
            )

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
            QMessageBox.critical(
                self,
                self.texts["strings"].get("settings.fehler", "Fehler"),
                "Pfade nicht ok:\n- " + "\n- ".join(errors),
            )
        else:
            QMessageBox.information(
                self,
                self.texts["strings"].get("settings.ok", "OK"),
                "Alle Pfade sind schreibbar. Nachtbetrieb ist safe.",
            )
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
            example = self.set_tmpl_batch.text().format(
                audio=audio,
                vorlage=vorlage,
                datum=datum,
                uhrzeit=uhrzeit,
                nummer=nummer,
                sw=sw,
            )
        except Exception:
            example = "(Vorlage hat Fehler)"
        self.lbl_preview_name.setText(example + ".mp4")

    # --- Quarantäne Tabelle (0.9.9) ---
    def _load_quarantine_table(self):
        self._quar_controller.load_table()

        # Visual hint: mark abgehakt in tab title (derzeit deaktiviert, Parent-Pfad ist nicht stabil).

    def _selected_quar_job_id(self):
        return self._quar_controller.selected_job_id()

    def _update_quar_status(self, job_id: str, new_status: str):
        return self._quar_controller.update_job_status(job_id, new_status)

    def _quar_open_folder(self):
        # open today's quarantine folder, if exists
        qdir = (
            data_dir()
            / self.settings.get("paths", {}).get("quarantine_dir", "quarantine")
            / datetime.now().strftime("%Y-%m-%d")
        )
        open_path(qdir)

    def _quar_replace_source_simple(self, job_id: str):
        # minimal: open JSON and let user use existing dashboard replace flow later
        # (full replace UI comes in later iteration)
        QMessageBox.information(
            self,
            "Quelle ersetzen",
            "Für jetzt: Öffne die Tagesliste (JSON) und ändere staging_audio/staging_image.\nDanach 'Neu (Ton Safe)'.",
        )
        self.open_qjobs_today()

    # --- Werkbank Export (0.9.10) ---
    def _wb_pick_logo(self):
        fp, _ = QFileDialog.getOpenFileName(
            self,
            "Logo wählen",
            str(Path.home() / "Downloads"),
            "Bilder (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
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
            QMessageBox.information(
                self, "Werkbank", "Keine Audio-Datei ausgewählt. Checkboxen setzen."
            )
            return
        if not images:
            QMessageBox.information(
                self, "Werkbank", "Kein Bild ausgewählt. Checkboxen setzen."
            )
            return

        preset = self.wb_preset.currentText().strip()
        # text options
        text = self.wb_text.text().strip() if self.wb_text_on.isChecked() else ""
        pos = self.wb_text_pos.currentText().strip()
        speed_mode = self.wb_text_speed.currentText().strip()
        speed = (
            160
            if speed_mode == "slow"
            else (
                220
                if speed_mode == "medium"
                else (320 if speed_mode == "fast" else 220)
            )
        )
        text_bg = bool(self.wb_text_bg.isChecked())

        logo = self.wb_logo_path.text().strip() if self.wb_logo_on.isChecked() else ""
        if logo and not Path(logo).exists():
            QMessageBox.information(
                self, "Werkbank", self.texts["strings"].get("edge.no_logo_file", "")
            )
            logo = ""
            self.wb_logo_on.setChecked(False)
        logo_pos = self.wb_logo_pos.currentText().strip()
        logo_scale = int(self.wb_logo_scale.value())
        gray = bool(self.wb_gray.isChecked())

        # Output dir inside exports/YYYY-MM-DD
        day = datetime.now().strftime("%Y-%m-%d")
        outdir = (
            data_dir()
            / self.settings.get("paths", {}).get("exports_dir", "exports")
            / day
        )
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            test = outdir / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
        except Exception:
            QMessageBox.information(
                self, "Werkbank", self.texts["strings"].get("edge.outdir_fail", "")
            )
            outdir = data_dir() / "exports" / day
            outdir.mkdir(parents=True, exist_ok=True)

        # Bild-Zuweisung (one/seq/manual)
        if hasattr(self, "_wb_build_jobs"):
            jobs = self._wb_build_jobs()
        else:
            jobs = [(a, images[0]) for a in audios]

        # Run jobs sequentially via QProcess calling tools/run_workbench_export.sh
        script = repo_root() / "tools" / "run_workbench_export.sh"
        if not script.exists():
            QMessageBox.critical(self, "Werkbank", "run_workbench_export.sh fehlt")
            return

        self.statusBar().showMessage(
            f"Werkbank: {len(jobs)} Auftrag/ Aufträge laufen …"
        )
        self._wb_jobs = jobs
        self._wb_job_index = 0

        def run_next():
            if self._wb_job_index >= len(self._wb_jobs):
                self.statusBar().showMessage(
                    "Werkbank fertig. Ausgaben liegen im Export-Ordner."
                )
                QMessageBox.information(
                    self, "Werkbank", "Fertig. Ausgaben sind gebaut."
                )
                self.refresh_last_night()
                return
            a, img = self._wb_jobs[self._wb_job_index]
            self._wb_job_index += 1

            args = [
                "--audio",
                str(a),
                "--image",
                str(img),
                "--outdir",
                str(outdir),
                "--preset",
                preset,
                "--text",
                text,
                "--text_pos",
                pos,
                "--text_speed",
                str(speed),
            ]
            if text_bg:
                args.append("--text_bg")
            if gray:
                args.append("--grayscale")
            if logo:
                args += [
                    "--logo",
                    logo,
                    "--logo_pos",
                    logo_pos,
                    "--logo_scale",
                    str(logo_scale),
                ]

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
        outdir = (
            data_dir()
            / self.settings.get("paths", {}).get("exports_dir", "exports")
            / day
        )
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
            img = images[idx - 1] if idx - 1 < len(images) else images[0]
            lines.append(f"{a} | {img}")

        # Dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Manuelle Zuweisung (Audio | Bild)")
        layout = QVBoxLayout(dlg)
        info = QLabel(
            "Eine Zeile = ein Arbeitsgang. Du kannst Bildpfade ändern. Format: audio | bild"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        edit = QTextEdit()
        edit.setPlainText("\n".join(lines))
        layout.addWidget(edit, 1)
        btns = QHBoxLayout()
        btn_ok = QPushButton(
            self.texts["strings"].get("workbench.assign_apply", "Zuweisung übernehmen")
        )
        btn_cancel = QPushButton("Abbrechen")
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
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
                img = images[idx - 1] if idx - 1 < len(images) else images[0]
                jobs.append((a, img))
            return jobs
        # default "one"
        img0 = images[0]
        return [(a, img0) for a in audios]

    def help_find(self, q: str):
        self._find_in_text_view(
            self.help_view,
            q,
            "Hilfe-Suche",
            "Suche im Hilfe-Center abgeschlossen.",
        )

    def _find_in_text_view(
        self,
        view: QTextEdit,
        query: str,
        label: str,
        success_msg: str,
    ) -> None:
        if not query.strip():
            self.statusBar().showMessage(
                f"{label}: Bitte Suchbegriff eingeben (Query = Suchtext)."
            )
            return
        text = view.toPlainText()
        idx = text.lower().find(query.lower())
        if idx >= 0:
            cursor = view.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(query), cursor.KeepAnchor)
            view.setTextCursor(cursor)
            self.statusBar().showMessage(success_msg)
        else:
            self.statusBar().showMessage(
                f"{label}: Kein Treffer gefunden. Nächster Schritt: Begriff prüfen."
            )

    def _open_dir_with_feedback(self, path: Path, label: str) -> None:
        try:
            resolved = ensure_existing_dir(path, label, create=True)
        except PathValidationError as exc:
            QMessageBox.warning(
                self,
                label,
                f"{label} konnte nicht geöffnet werden.\nNächster Schritt: Pfad prüfen.",
            )
            log_exception(
                "open_dir_with_feedback",
                exc,
                extra={"path": str(path), "label": label},
            )
            return
        open_path(resolved, self)
        self.statusBar().showMessage(f"{label} geöffnet.")
        activity(f"{label} geöffnet.")

    def _open_file_with_feedback(self, path: Path, label: str) -> None:
        try:
            resolved = ensure_existing_file(path, label)
        except PathValidationError as exc:
            QMessageBox.warning(
                self,
                label,
                f"{label} konnte nicht geöffnet werden.\nNächster Schritt: Datei prüfen.",
            )
            log_exception(
                "open_file_with_feedback",
                exc,
                extra={"path": str(path), "label": label},
            )
            return
        open_path(resolved, self)
        self.statusBar().showMessage(f"{label} geöffnet.")
        activity(f"{label} geöffnet.")

    def _load_help_center(self) -> None:
        help_path = config_dir() / "HELP_CENTER.md"
        if help_path.exists():
            content = help_path.read_text(encoding="utf-8")
        else:
            content = "HELP_CENTER.md fehlt."
        self.help_view.setPlainText(content)
        self._help_index = self._build_help_index(content)
        self.help_topics.clear()
        for title in self._help_index:
            self.help_topics.addItem(title)
        self.statusBar().showMessage("Hilfe-Center geladen.")

    def _build_help_index(self, content: str) -> dict[str, int]:
        index: dict[str, int] = {}
        offset = 0
        for line in content.splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("## "):
                title = stripped.replace("## ", "", 1).strip()
                if title:
                    index[title] = offset
            offset += len(line)
        return index

    def _jump_help_topic(self, item: QListWidgetItem) -> None:
        if not item:
            return
        title = item.text()
        pos = self._help_index.get(title)
        if pos is None:
            return
        cursor = self.help_view.textCursor()
        cursor.setPosition(pos)
        self.help_view.setTextCursor(cursor)
        self.statusBar().showMessage("Hilfe-Thema geöffnet.")

    # --- Barriere-Labels (0.9.13) ---
    def _acc(self, widget, name: str, desc: str = ""):
        try:
            widget.setAccessibleName(name)
            if desc:
                widget.setAccessibleDescription(desc)
        except Exception as exc:
            log_exception(
                "accessibility.set",
                exc,
                extra={
                    "name": name,
                    "desc": desc,
                    "widget_type": type(widget).__name__,
                },
            )

    def run_mustpass(self):
        script = repo_root() / "tools" / "run_must_pass.sh"
        if not script.exists():
            QMessageBox.critical(self, "Must-Pass", "run_must_pass.sh fehlt")
            return
        self.statusBar().showMessage("Must-Pass Suite läuft…")
        self._mp_proc = QProcess(self)
        self._mp_proc.setProgram("bash")
        self._mp_proc.setArguments([str(script)])

        def done(*args):
            self.statusBar().showMessage(
                "Must-Pass Suite fertig. Report liegt in reports/."
            )
            QMessageBox.information(
                self, "Must-Pass", "Fertig. Öffne reports/ und schau must_pass_*.json."
            )

        self._mp_proc.finished.connect(done)
        self._mp_proc.start()

    def _run_preflight(self):
        self.preflight = preflight_run(config_dir() / "settings.json")
        t = self.preflight
        msg_lines = []
        if not t.get("ffmpeg_ok", True):
            msg_lines.append(
                self.texts["strings"].get("preflight.missing_ffmpeg", "FFmpeg fehlt.")
            )
        if not t.get("watchfolder_ok", True):
            msg_lines.append(
                self.texts["strings"].get(
                    "preflight.watch_missing", "Watchfolder fehlt."
                )
            )
        if not t.get("watchfolder_writable_ok", True):
            msg_lines.append(
                self.texts["strings"].get(
                    "preflight.watch_not_writable", "Watchfolder ist nicht schreibbar."
                )
            )
        if not t.get("space_ok", True):
            msg_lines.append(
                self.texts["strings"].get("preflight.space_low", "Wenig Speicher frei.")
                + f" ({t.get('free_mb')} MB)"
            )
        if not t.get("min_free_mb_ok", True):
            msg_lines.append(
                self.texts["strings"].get(
                    "preflight.min_free_invalid",
                    "Mindest-Speicher (min_free_mb) ist ungültig. Standard 1024 MB wird genutzt.",
                )
                + f" (Eingabe: {t.get('min_free_mb_input')})"
            )
        if not t.get("theme_ok", True):
            msg_lines.append(
                self.texts["strings"].get(
                    "preflight.theme_invalid",
                    "Theme ist unbekannt. Standard wird genutzt.",
                )
                + f" (Eingabe: {t.get('theme_input')})"
            )
        for k, v in (t.get("writable") or {}).items():
            if not v.get("ok", True):
                msg_lines.append(f"Ordner nicht schreibbar: {k} ({v.get('path')})")
        # Font-Check: wenn Font fehlt, Lauftext deaktivieren
        if not bool(t.get("font_ok", True)):
            if hasattr(self, "wb_text_on"):
                self.wb_text_on.setChecked(False)
                self.wb_text_on.setEnabled(False)
            if hasattr(self, "wb_text"):
                self.wb_text.setEnabled(False)
            msg_lines.append(
                self.texts["strings"].get(
                    "edge.font_missing", "Schrift fehlt: Lauftext deaktiviert."
                )
            )
        else:
            if hasattr(self, "wb_text_on"):
                self.wb_text_on.setEnabled(True)
            if hasattr(self, "wb_text"):
                self.wb_text.setEnabled(True)

        if not msg_lines:
            msg = self.texts["strings"].get("preflight.ok", "Alles bereit.")
        else:
            msg = "- " + "\n- ".join(msg_lines)

        self.preflight_banner.setTitle(
            "Werkstatt-Check ✅" if t.get("overall_ok") else "Werkstatt-Check ⚠️"
        )
        self.lbl_preflight.setText(msg)

        ffok = bool(t.get("ffmpeg_ok", True))
        # Wenn Watchfolder fehlt: Setup-Button wird zum "Watchfolder wählen"
        if not bool(t.get("watchfolder_ok", True)):
            self.btn_preflight_setup.setText(
                self.texts["strings"].get("edge.pick_watch", "Watchfolder wählen")
            )
            try:
                self.btn_preflight_setup.clicked.disconnect()
            except Exception:
                pass
            self.btn_preflight_setup.clicked.connect(self._pick_and_save_watchfolder)
        else:
            self.btn_preflight_setup.setText(
                self.texts["strings"].get(
                    "preflight.setup", "Jetzt einrichten (FFmpeg)"
                )
            )
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
        if not isinstance(t, dict):
            QMessageBox.critical(
                self,
                "Werkstatt-Check Details",
                "Unerwartete Daten vom Werkstatt-Check.",
            )
            return

        lines = [
            self.texts["strings"].get(
                "preflight.details_header", "Werkstatt-Check – klar erklärt."
            )
        ]
        lines.append("")

        if t.get("ffmpeg_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_ffmpeg_ok", "✅ FFmpeg (Video-Werkzeug) ist da."
                )
            )
        else:
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_ffmpeg_bad",
                    "⚠️ FFmpeg (Video-Werkzeug) fehlt. Bitte einrichten.",
                )
            )

        watchfolder = t.get("watchfolder", "") or "–"
        if t.get("watchfolder_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_watch_ok",
                    "✅ Watchfolder (Eingangsordner) ist gesetzt.",
                )
                + f"\n   {watchfolder}"
            )
        else:
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_watch_bad",
                    "⚠️ Watchfolder (Eingangsordner) fehlt. Bitte wählen.",
                )
                + f"\n   {watchfolder}"
            )
        if t.get("watchfolder_ok", True) and not t.get("watchfolder_writable_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_watch_not_writable",
                    "⚠️ Watchfolder (Eingangsordner) ist nicht schreibbar. Bitte Rechte prüfen.",
                )
            )

        free_mb = t.get("free_mb", -1)
        min_mb = t.get("min_free_mb", 0)
        if free_mb >= 0:
            space_info = f"{free_mb} MB frei (Ziel: {min_mb} MB)"
        else:
            space_info = self.texts["strings"].get(
                "preflight.details_space_unknown", "Speicher frei: nicht messbar."
            )
        if t.get("space_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_space_ok", "✅ Genug Speicher frei."
                )
                + f" {space_info}"
            )
        else:
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_space_bad",
                    "⚠️ Speicher knapp. Export kann scheitern.",
                )
                + f" {space_info}"
            )
        if not t.get("min_free_mb_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_min_free_invalid",
                    "⚠️ Mindest-Speicher (min_free_mb) ist ungültig. Standard 1024 MB wird genutzt.",
                )
                + f" (Eingabe: {t.get('min_free_mb_input')})"
            )

        if t.get("font_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_font_ok",
                    "✅ Schrift (Font) verfügbar. Lauftext möglich.",
                )
            )
        else:
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_font_bad",
                    "⚠️ Schrift (Font) fehlt. Lauftext bleibt aus.",
                )
            )

        theme_name = t.get("theme", "") or "–"
        if t.get("theme_ok", True):
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_theme_ok",
                    "✅ Theme ist verfügbar.",
                )
                + f" {theme_name}"
            )
        else:
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_theme_bad",
                    "⚠️ Theme ist unbekannt. Standard wird genutzt.",
                )
                + f" {theme_name}"
            )

        writable = t.get("writable") or {}
        if writable:
            lines.append("")
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_write_header", "Ordner-Zugriff (Schreibrecht):"
                )
            )
            for key, info in writable.items():
                ok = info.get("ok", True)
                path = info.get("path", "") or "–"
                err = info.get("error", "") or ""
                if ok:
                    lines.append(f"✅ {key}: {path}")
                else:
                    extra = f" – {err}" if err else ""
                    lines.append(f"⚠️ {key}: {path}{extra}")

        recs = t.get("recommendations") or []
        if recs:
            lines.append("")
            lines.append(
                self.texts["strings"].get(
                    "preflight.details_next_header", "Nächste Schritte (einfach):"
                )
            )
            rec_map = {
                "ffmpeg_install": self.texts["strings"].get(
                    "preflight.details_rec_ffmpeg",
                    "• FFmpeg (Video-Werkzeug) installieren.",
                ),
                "set_watchfolder": self.texts["strings"].get(
                    "preflight.details_rec_watch",
                    "• Watchfolder (Eingangsordner) wählen.",
                ),
                "watchfolder_not_writable": self.texts["strings"].get(
                    "preflight.details_rec_watch_write",
                    "• Watchfolder (Eingangsordner) braucht Schreibrechte (Rechte prüfen).",
                ),
                "free_space": self.texts["strings"].get(
                    "preflight.details_rec_space",
                    "• Speicher frei machen (nicht benötigte Dateien löschen).",
                ),
                "install_font": self.texts["strings"].get(
                    "preflight.details_rec_font",
                    "• Schrift (Font) installieren, z.B. DejaVuSans.",
                ),
                "min_free_mb_invalid": self.texts["strings"].get(
                    "preflight.details_rec_min_free",
                    "• Mindest-Speicher (min_free_mb) als Zahl eintragen (z.B. 2048).",
                ),
                "theme_invalid": self.texts["strings"].get(
                    "preflight.details_rec_theme",
                    "• Theme auswählen, das in den Einstellungen verfügbar ist.",
                ),
            }
            for rec in recs:
                lines.append(rec_map.get(rec, f"• {rec}"))

        QMessageBox.information(self, "Werkstatt-Check Details", "\n".join(lines))

    def _pick_and_save_watchfolder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Watchfolder wählen", str(Path.home() / "Downloads")
        )
        if not folder:
            return
        # Update settings UI if present
        try:
            if hasattr(self, "set_watch_folder"):
                self.set_watch_folder.setText(folder)
            self.settings.setdefault("paths", {})
            self.settings["paths"]["watch_folder"] = folder
            settings_path = config_dir() / "settings.json"
            ok = atomic_write_json(
                settings_path,
                self.settings,
                context="ui.watchfolder_save",
            )
            if ok:
                QMessageBox.information(
                    self,
                    "Watchfolder",
                    self.texts["strings"].get(
                        "edge.watch_set", "Watchfolder gesetzt und gespeichert."
                    ),
                )
            else:
                QMessageBox.critical(
                    self,
                    "Watchfolder",
                    "Speichern fehlgeschlagen. Bitte erneut versuchen.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Watchfolder", f"Konnte nicht speichern:\n{e}")
        self._run_preflight()
