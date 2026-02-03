from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QTabWidget,
    QSplitter,
    QGroupBox,
    QCheckBox,
    QTextEdit,
    QLineEdit,
    QComboBox,
    QFrame,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QTableWidget,
)

from logging_utils import log_exception
from paths import config_dir


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


def _apply_label_role(label: QLabel, role: str):
    if not isinstance(role, str) or not role:
        return
    label.setProperty("role", role)
    try:
        label.style().unpolish(label)
        label.style().polish(label)
    except Exception as exc:
        log_exception(
            "apply_label_role",
            exc,
            extra={"role": role, "label": label.objectName()},
        )


def build_main_layout(main) -> None:
    splitter = QSplitter(Qt.Horizontal)
    main.left = QTabWidget()
    main.left.setMinimumWidth(380)

    # --- MATERIAL TAB (mit Suche/Filter) ---
    tab_material = QWidget()
    lm = QVBoxLayout(tab_material)
    lm.addWidget(
        QLabel("Material (Checkboxen = Auswahl). Du kannst Dateien hier reinziehen.")
    )

    row0 = QHBoxLayout()
    main.btn_add_files = QPushButton("Dateien holen")
    main.btn_add_folder = QPushButton("Ordner holen")
    row0.addWidget(main.btn_add_files)
    row0.addWidget(main.btn_add_folder)
    lm.addLayout(row0)

    row1 = QHBoxLayout()
    main.material_search_box = QLineEdit()
    main.material_search_box.setPlaceholderText("Suchen im Material …")
    main.material_type_combo = QComboBox()
    main.material_type_combo.addItems(["Typ: alle", "Typ: audio", "Typ: bilder"])
    main.sort_combo = QComboBox()
    main.sort_combo.addItems(["Sortieren: Datum (neu zuerst)", "Sortieren: Name (A-Z)"])
    row1.addWidget(main.material_search_box, 2)
    row1.addWidget(main.material_type_combo)
    row1.addWidget(main.sort_combo)
    lm.addLayout(row1)

    material_split = QSplitter(Qt.Horizontal)
    main.material = FileDropListWidget(main.add_paths_to_material)
    main.material.setSelectionMode(QListWidget.ExtendedSelection)
    main.material.setIconSize(QSize(96, 96))
    material_split.addWidget(main.material)

    preview = QWidget()
    pv = QVBoxLayout(preview)
    title = QLabel("Bildvorschau")
    title.setStyleSheet("font-weight:600;")
    main.preview_img = QLabel("Kein Bild ausgewählt.")
    main.preview_img.setAlignment(Qt.AlignCenter)
    main.preview_img.setMinimumWidth(280)
    main.preview_img.setMinimumHeight(240)
    main.preview_img.setFrameShape(QFrame.StyledPanel)
    main.preview_info = QLabel("")
    main.preview_info.setWordWrap(True)
    _apply_label_role(main.preview_info, "muted")
    pv.addWidget(title)
    pv.addWidget(main.preview_img, 1)
    pv.addWidget(main.preview_info)
    pv.addStretch(1)
    material_split.addWidget(preview)
    material_split.setStretchFactor(0, 3)
    material_split.setStretchFactor(1, 2)

    lm.addWidget(material_split)
    hint = QLabel(
        "Tipp: Bild anklicken = Vorschau. Checkboxen = Auswahlkorb. Suche/Filter oben."
    )
    _apply_label_role(hint, "hint")
    lm.addWidget(hint)

    main.left.addTab(
        tab_material, main.texts["strings"].get("sidebar.material", "Material")
    )

    # Werkzeugkasten (Favoriten)
    tab_box = QWidget()
    lb = QVBoxLayout(tab_box)
    lb.addWidget(
        QLabel(
            main.texts["strings"].get("favoriten.titel", "Werkzeugkasten – Favoriten")
        )
    )

    fav_row = QHBoxLayout()
    main.fav_search_box = QLineEdit()
    main.fav_search_box.setPlaceholderText(
        main.texts["strings"].get("favoriten.suchen", "Suchen in Favoriten …")
    )
    main.fav_tag_combo = QComboBox()
    main.fav_tag_combo.addItems(["Tag: alle"])
    fav_row.addWidget(main.fav_search_box, 2)
    fav_row.addWidget(main.fav_tag_combo, 1)
    lb.addLayout(fav_row)

    main.fav_list = QListWidget()
    main.fav_list.setIconSize(QSize(64, 64))
    lb.addWidget(main.fav_list, 1)

    fav_btns = QHBoxLayout()
    main.btn_fav_add = QPushButton(
        main.texts["strings"].get("favoriten.hinzufuegen", "Favorit hinzufügen")
    )
    main.btn_fav_add.setToolTip(
        main.texts.get("tooltips", {}).get("favoriten.hinzufuegen", "")
    )
    main.btn_fav_star = QPushButton(
        main.texts["strings"].get("favoriten.stern", "Stern umschalten")
    )
    main.btn_fav_star.setToolTip(
        main.texts.get("tooltips", {}).get("favoriten.stern", "")
    )
    main.btn_fav_tags = QPushButton(
        main.texts["strings"].get("favoriten.tags", "Tags setzen")
    )
    main.btn_fav_tags.setToolTip(
        main.texts.get("tooltips", {}).get("favoriten.tags", "")
    )
    main.btn_fav_remove = QPushButton(
        main.texts["strings"].get("favoriten.entfernen", "Entfernen")
    )
    main.btn_fav_folder = QPushButton(
        main.texts["strings"].get("favoriten.ordner", "Favoriten-Ordner öffnen")
    )
    fav_btns.addWidget(main.btn_fav_add)
    fav_btns.addWidget(main.btn_fav_star)
    fav_btns.addWidget(main.btn_fav_tags)
    fav_btns.addWidget(main.btn_fav_remove)
    fav_btns.addWidget(main.btn_fav_folder)
    lb.addLayout(fav_btns)

    hint = QLabel(
        "Tipp: Favoriten sind Referenzen. Wenn die Datei fehlt, bleibt der Eintrag sichtbar."
    )
    _apply_label_role(hint, "hint")
    lb.addWidget(hint)

    main.left.addTab(
        tab_box,
        main.texts["strings"].get("sidebar.werkzeugkasten", "Werkzeugkasten"),
    )

    # Einstellungen-Tab (laienfest, alles deutsch, kein JSON-Gefummel)
    tab_settings = QWidget()
    ls = QVBoxLayout(tab_settings)
    ls.addWidget(QLabel(main.texts["strings"].get("settings.titel", "Einstellungen")))

    grp_paths = QGroupBox(
        main.texts["strings"].get("settings.speicherorte", "Speicherorte")
    )
    form_p = QFormLayout(grp_paths)

    main.set_watch_folder = QLineEdit()
    main.set_watch_folder.setText(
        main.settings.get("paths", {}).get("watch_folder", "")
    )
    btn_watch = QPushButton(
        main.texts["strings"].get("settings.folder_waehlen", "Ordner wählen")
    )
    btn_watch.clicked.connect(
        lambda: main._pick_folder_into(main.set_watch_folder, "Downloads-Ordner")
    )
    row_watch = QWidget()
    rw = QHBoxLayout(row_watch)
    rw.setContentsMargins(0, 0, 0, 0)
    rw.addWidget(main.set_watch_folder, 1)
    rw.addWidget(btn_watch)
    form_p.addRow(
        main.texts["strings"].get("settings.watchfolder", "Watchfolder"), row_watch
    )

    def add_rel_line(label_key, attr_name, default_val):
        le = QLineEdit()
        le.setText(main.settings.get("paths", {}).get(attr_name, default_val))
        le.setPlaceholderText(default_val)
        setattr(main, f"set_{attr_name}", le)
        form_p.addRow(main.texts["strings"].get(label_key, attr_name), le)

    add_rel_line("settings.exports", "exports_dir", "exports")
    add_rel_line("settings.library_audio", "library_audio_dir", "library/audio")
    add_rel_line("settings.library_images", "library_images_dir", "library/images")
    add_rel_line("settings.quarantine", "quarantine_dir", "quarantine")
    add_rel_line("settings.quarantine_jobs", "quarantine_jobs_dir", "quarantine_jobs")
    add_rel_line("settings.reports", "reports_dir", "reports")
    add_rel_line("settings.staging", "staging_dir", "staging")
    add_rel_line("settings.trash", "trash_dir", "trash")
    ls.addWidget(grp_paths)

    grp_audio = QGroupBox(main.texts["strings"].get("settings.audio", "Audio"))
    form_a = QFormLayout(grp_audio)
    main.set_fade_in = QDoubleSpinBox()
    main.set_fade_in.setRange(0.0, 30.0)
    main.set_fade_in.setSingleStep(0.1)
    main.set_fade_in.setValue(
        float(main.settings.get("audio", {}).get("fade_in_sec", 0.5))
    )
    form_a.addRow(
        main.texts["strings"].get("settings.fade_in", "Fade-In"), main.set_fade_in
    )
    main.set_fade_out = QDoubleSpinBox()
    main.set_fade_out.setRange(0.0, 30.0)
    main.set_fade_out.setSingleStep(0.1)
    main.set_fade_out.setValue(
        float(main.settings.get("audio", {}).get("fade_out_sec", 1.0))
    )
    form_a.addRow(
        main.texts["strings"].get("settings.fade_out", "Fade-Out"), main.set_fade_out
    )
    main.set_min_br = QSpinBox()
    main.set_min_br.setRange(0, 1024)
    main.set_min_br.setValue(
        int(main.settings.get("audio", {}).get("min_bitrate_kbps", 192))
    )
    form_a.addRow(
        main.texts["strings"].get("settings.min_bitrate", "Min Bitrate"),
        main.set_min_br,
    )
    main.set_target_br = QSpinBox()
    main.set_target_br.setRange(64, 1024)
    main.set_target_br.setValue(
        int(main.settings.get("audio", {}).get("target_bitrate_kbps", 320))
    )
    form_a.addRow(
        main.texts["strings"].get("settings.target_bitrate", "Ziel Bitrate"),
        main.set_target_br,
    )
    main.set_sr = QSpinBox()
    main.set_sr.setRange(8000, 192000)
    main.set_sr.setValue(
        int(main.settings.get("audio", {}).get("target_samplerate_hz", 48000))
    )
    form_a.addRow(
        main.texts["strings"].get("settings.samplerate", "Samplerate"), main.set_sr
    )
    ls.addWidget(grp_audio)

    grp_name = QGroupBox(main.texts["strings"].get("settings.dateinamen", "Dateinamen"))
    form_n = QFormLayout(grp_name)
    main.set_tmpl_single = QLineEdit()
    main.set_tmpl_single.setText(
        main.settings.get("naming", {}).get(
            "template_single", "{audio}_{vorlage}_{datum}_{uhrzeit}{sw}"
        )
    )
    form_n.addRow(
        main.texts["strings"].get("settings.template_single", "Vorlage Einzel"),
        main.set_tmpl_single,
    )
    main.set_tmpl_batch = QLineEdit()
    main.set_tmpl_batch.setText(
        main.settings.get("naming", {}).get(
            "template_batch", "{audio}_{vorlage}_{datum}_{nummer}{sw}"
        )
    )
    form_n.addRow(
        main.texts["strings"].get("settings.template_batch", "Vorlage Stapel"),
        main.set_tmpl_batch,
    )
    main.set_append_label = QCheckBox(
        main.texts["strings"].get(
            "settings.append_label", "Etikett an Ausgabe anhängen"
        )
    )
    main.set_append_label.setChecked(
        bool(main.settings.get("naming", {}).get("append_label_to_output", False))
    )
    form_n.addRow(main.set_append_label)
    main.set_append_mode = QComboBox()
    main.set_append_mode.addItems(["only_quarantine", "always", "never"])
    mode = main.settings.get("naming", {}).get("append_label_mode", "only_quarantine")
    ix = main.set_append_mode.findText(mode)
    if ix >= 0:
        main.set_append_mode.setCurrentIndex(ix)
    form_n.addRow(
        main.texts["strings"].get("settings.append_mode", "Etikett-Modus"),
        main.set_append_mode,
    )
    main.set_append_short = QCheckBox(
        main.texts["strings"].get("settings.append_short", "Kurzform Etikett")
    )
    main.set_append_short.setChecked(
        bool(main.settings.get("naming", {}).get("append_label_shortform", True))
    )
    form_n.addRow(main.set_append_short)
    main.lbl_preview_name = QLabel("")
    form_n.addRow(
        main.texts["strings"].get("settings.preview_name", "Vorschau Dateiname"),
        main.lbl_preview_name,
    )
    ls.addWidget(grp_name)

    btn_row = QHBoxLayout()
    main.btn_settings_save = QPushButton(
        main.texts["strings"].get("settings.speichern", "Speichern")
    )
    main.btn_settings_default = QPushButton(
        main.texts["strings"].get("settings.standard", "Standard wiederherstellen")
    )
    main.btn_settings_test = QPushButton(
        main.texts["strings"].get("settings.testen", "Pfade testen")
    )
    btn_row.addWidget(main.btn_settings_save)
    btn_row.addWidget(main.btn_settings_default)
    btn_row.addWidget(main.btn_settings_test)
    ls.addLayout(btn_row)
    ls.addStretch(1)

    main.left.addTab(
        tab_settings,
        main.texts["strings"].get("sidebar.einstellungen", "Einstellungen"),
    )
    # Vorlagen
    tab_presets = QWidget()
    lp = QVBoxLayout(tab_presets)
    main.btn_p1 = QPushButton(
        main.texts["strings"].get("preset.youtube_hd_tonsafe", "YouTube HD (Ton Safe)")
    )
    main.btn_p3 = QPushButton(
        main.texts["strings"].get(
            "preset.shorts_9_16_tonsafe", "Shorts 9:16 (Ton Safe)"
        )
    )
    lp.addWidget(QLabel("Vorlagen (Ton Safe):"))
    lp.addWidget(main.btn_p1)
    lp.addWidget(main.btn_p3)
    lp.addStretch(1)
    main.left.addTab(
        tab_presets, main.texts["strings"].get("sidebar.vorlagen", "Vorlagen")
    )

    # Automatik tab
    tab_auto = QWidget()
    la = QVBoxLayout(tab_auto)
    main.chk_auto = QCheckBox("Automatik aktiv (global)")
    main.chk_auto.setChecked(bool(main.rules.get("enabled", False)))
    main.btn_timer = QPushButton("Zeitplan einrichten/aktualisieren")
    main.btn_run = QPushButton("Automatik jetzt starten (Test)")
    main.lbl_time = QLabel(f"Startzeit: {main.rules.get('start_time', '22:00')}")
    la.addWidget(
        QLabel("Automatik: läuft erst zur Uhrzeit. Tagsüber einrichten, nachts Ruhe.")
    )
    la.addWidget(main.lbl_time)
    la.addWidget(main.chk_auto)
    la.addWidget(main.btn_timer)
    la.addWidget(main.btn_run)
    la.addStretch(1)
    main.left.addTab(
        tab_auto, main.texts["strings"].get("sidebar.automatik", "Automatik")
    )

    # Quarantäne-Tagesliste als UI-Tabelle (0.9.9)
    tab_quar = QWidget()
    lq = QVBoxLayout(tab_quar)
    lq.addWidget(
        QLabel(
            main.texts["strings"].get("quar_tab.titel", "Quarantäne-Aufträge (heute)")
        )
    )
    hint = QLabel(main.texts["strings"].get("quar_tab.hinweis", ""))
    _apply_label_role(hint, "hint")
    hint.setWordWrap(True)
    lq.addWidget(hint)

    # Controls row
    rowq = QHBoxLayout()
    main.btn_quar_refresh = QPushButton(
        main.texts["strings"].get("quar_tab.refresh", "Aktualisieren")
    )
    main.btn_quar_open_json = QPushButton(
        main.texts["strings"].get("quar_tab.open_json", "JSON öffnen")
    )
    main.btn_quar_open_folder = QPushButton(
        main.texts["strings"].get("quar_tab.open_folder", "Quarantäne-Ordner")
    )
    main.btn_quar_all_rerun = QPushButton(
        main.texts["strings"].get("quar_tab.all_rerun", "Alle bereit neu machen")
    )
    rowq.addWidget(main.btn_quar_refresh)
    rowq.addWidget(main.btn_quar_open_json)
    rowq.addWidget(main.btn_quar_open_folder)
    rowq.addWidget(main.btn_quar_all_rerun)
    lq.addLayout(rowq)

    # Table
    main.quar_table = QTableWidget()
    main.quar_table.setColumnCount(6)
    main.quar_table.setHorizontalHeaderLabels(
        [
            main.texts["strings"].get("quar_tab.status", "Status"),
            main.texts["strings"].get("quar_tab.file", "Datei"),
            main.texts["strings"].get("quar_tab.reason", "Grund"),
            main.texts["strings"].get("quar_tab.tries", "Versuche"),
            main.texts["strings"].get("quar_tab.action", "Aktion"),
            "ID",
        ]
    )
    main.quar_table.setColumnHidden(5, True)
    main.quar_table.setSelectionBehavior(main.quar_table.SelectRows)
    main.quar_table.setEditTriggers(main.quar_table.NoEditTriggers)
    lq.addWidget(main.quar_table, 1)

    # Action buttons for selected row
    rowa = QHBoxLayout()
    main.btn_quar_rerun = QPushButton(
        main.texts["strings"].get("quar_tab.rerun", "Neu (Ton Safe)")
    )
    main.btn_quar_replace = QPushButton(
        main.texts["strings"].get("quar_tab.replace", "Quelle ersetzen")
    )
    main.btn_quar_postpone = QPushButton(
        main.texts["strings"].get("quar_tab.postpone", "Zurückstellen")
    )
    main.btn_quar_done = QPushButton(
        main.texts["strings"].get("quar_tab.mark_done", "Erledigt")
    )
    rowa.addWidget(main.btn_quar_rerun)
    rowa.addWidget(main.btn_quar_replace)
    rowa.addWidget(main.btn_quar_postpone)
    rowa.addWidget(main.btn_quar_done)
    lq.addLayout(rowa)

    main.left.addTab(
        tab_quar, main.texts["strings"].get("quar_tab.titel", "Quarantäne")
    )

    # Tests tab
    tab_tests = QWidget()
    lt = QVBoxLayout(tab_tests)
    main.btn_selftest = QPushButton("Werkstatt-Prüfung (Selftest) – Volltest")
    main.btn_mustpass = QPushButton(
        main.texts["strings"].get("tests.mustpass", "Must-Pass Suite")
    )
    main.lbl_mustpass = QLabel(main.texts["strings"].get("tests.mustpass_hint", ""))
    _apply_label_role(main.lbl_mustpass, "hint")
    main.btn_open_reports = QPushButton("Arbeitsberichte öffnen")
    lt.addWidget(
        QLabel(
            "Selftest: 1 Erfolg + 1 Quarantäne, danach wird 'Letzte Nacht' aktualisiert."
        )
    )
    lt.addWidget(main.btn_selftest)
    lt.addWidget(main.btn_mustpass)
    lt.addWidget(main.lbl_mustpass)
    lt.addWidget(main.btn_open_reports)
    lt.addStretch(1)
    main.left.addTab(
        tab_tests, main.texts["strings"].get("sidebar.tests", "Werkstatt-Prüfung")
    )

    # Entwicklerdoku tab
    tab_dev = QWidget()
    ld = QVBoxLayout(tab_dev)
    ld.addWidget(QLabel("Entwicklerdoku (im Tool)"))
    main.dev_search = QLineEdit()
    main.dev_search.setPlaceholderText("Suchen …")
    main.dev_view = QTextEdit()
    main.dev_view.setReadOnly(True)
    dev_path = config_dir() / "DEVELOPER_MANUAL.md"
    main.dev_view.setPlainText(
        dev_path.read_text(encoding="utf-8")
        if dev_path.exists()
        else "DEVELOPER_MANUAL.md fehlt."
    )
    ld.addWidget(main.dev_search)
    ld.addWidget(main.dev_view)

    # Hilfe-Tab (Hilfe-Center)
    tab_help = QWidget()
    lh = QVBoxLayout(tab_help)
    lh.addWidget(QLabel(main.texts["strings"].get("help.titel", "Hilfe-Center")))
    main.help_search = QLineEdit()
    main.help_search.setPlaceholderText(
        main.texts["strings"].get("help.suchen", "Suchen …")
    )
    main.help_view = QTextEdit()
    main.help_view.setReadOnly(True)
    help_path = config_dir() / "HELP_CENTER.md"
    main.help_view.setPlainText(
        help_path.read_text(encoding="utf-8")
        if help_path.exists()
        else "HELP_CENTER.md fehlt."
    )
    main.btn_help_open = QPushButton(
        main.texts["strings"].get("help.open_file", "Hilfe-Datei öffnen")
    )
    lh.addWidget(main.help_search)
    lh.addWidget(main.help_view, 1)
    lh.addWidget(main.btn_help_open)

    main.left.addTab(tab_help, main.texts["strings"].get("sidebar.hilfe", "Hilfe"))
    main.left.addTab(
        tab_dev,
        main.texts["strings"].get("sidebar.entwicklerdoku", "Entwicklerdoku"),
    )

    # --- MIDDLE DASHBOARD ---
    main.mid = QWidget()
    md = QVBoxLayout(main.mid)
    header = QLabel("Schaltzentrale: Auswahl, letzte Nacht, nächste Schritte.")
    header.setStyleSheet("font-size:16px;font-weight:600;")
    md.addWidget(header)

    # Preflight Banner (Laien-Schutz)
    main.preflight_banner = QGroupBox("Werkstatt-Check")
    pb = QVBoxLayout(main.preflight_banner)
    main.lbl_preflight = QLabel("")
    main.lbl_preflight.setWordWrap(True)
    rowp = QHBoxLayout()
    main.btn_preflight_setup = QPushButton(
        main.texts["strings"].get("preflight.setup", "Jetzt einrichten (FFmpeg)")
    )
    main.btn_preflight_details = QPushButton(
        main.texts["strings"].get("preflight.details", "Details")
    )
    rowp.addWidget(main.btn_preflight_setup)
    rowp.addWidget(main.btn_preflight_details)
    pb.addWidget(main.lbl_preflight)
    pb.addLayout(rowp)
    md.addWidget(main.preflight_banner)

    main.grp_sel = QGroupBox("Deine Auswahl (0)")
    sll = QVBoxLayout(main.grp_sel)

    sel_filters = QHBoxLayout()
    main.selection_search_box = QLineEdit()
    main.selection_search_box.setPlaceholderText("Suchen in Auswahl …")
    main.selection_type_combo = QComboBox()
    main.selection_type_combo.addItems(["Typ: alle", "Typ: audio", "Typ: bilder"])
    sel_filters.addWidget(main.selection_search_box, 2)
    sel_filters.addWidget(main.selection_type_combo)
    sll.addLayout(sel_filters)

    sll.addWidget(
        QLabel(
            "Hier liegt deine Auswahl. Du kannst Namen ändern oder aus der Auswahl werfen."
        )
    )
    main.sel_list = QListWidget()
    main.sel_list.setIconSize(QSize(48, 48))
    sll.addWidget(main.sel_list)

    row = QHBoxLayout()
    main.btn_queue = QPushButton(
        main.texts["strings"].get("buttons.in_warteschlange", "In Warteschlange")
    )
    main.btn_prev = QPushButton(
        main.texts["strings"].get("buttons.vorschau_10s", "Vorschau (zehn Sekunden)")
    )
    main.btn_clear = QPushButton("Auswahl leeren")
    row.addWidget(main.btn_queue)
    row.addWidget(main.btn_prev)
    row.addWidget(main.btn_clear)
    sll.addLayout(row)
    md.addWidget(main.grp_sel)

    # Werkbank: Standbild+Audio (Lauftext/Logo)
    main.grp_workbench = QGroupBox(
        main.texts["strings"].get("workbench.titel", "Werkbank – Standbild + Audio")
    )
    wb = QVBoxLayout(main.grp_workbench)
    wb.addWidget(QLabel(main.texts["strings"].get("workbench.hinweis", "")))

    wrow1 = QHBoxLayout()
    main.wb_preset = QComboBox()
    main.wb_preset.addItems(["youtube_hd_ton_safe", "shorts_9_16_ton_safe"])
    wrow1.addWidget(QLabel(main.texts["strings"].get("workbench.preset", "Vorlage")))
    wrow1.addWidget(main.wb_preset, 1)
    wb.addLayout(wrow1)

    # Bild-Zuweisung (Batch Pairing)
    wpair = QHBoxLayout()
    main.wb_pairing = QComboBox()
    main.wb_pairing.addItems(["one", "seq", "manual"])
    wpair.addWidget(
        QLabel(main.texts["strings"].get("workbench.pairing", "Bild-Zuweisung"))
    )
    wpair.addWidget(main.wb_pairing, 1)
    main.btn_wb_assign_open = QPushButton(
        main.texts["strings"].get("workbench.assign_open", "Zuweisung öffnen")
    )
    wpair.addWidget(main.btn_wb_assign_open)
    wb.addLayout(wpair)

    pair_hint = QLabel(main.texts["strings"].get("workbench.pairing_hint", ""))
    _apply_label_role(pair_hint, "hint")
    pair_hint.setWordWrap(True)
    wb.addWidget(pair_hint)

    main._wb_manual_map = []  # list of (audio_path, image_path)
    main.wb_text_on = QCheckBox(
        main.texts["strings"].get("workbench.text_on", "Lauftext aktiv")
    )
    main.wb_text = QLineEdit()
    main.wb_text.setPlaceholderText(
        main.texts["strings"].get("workbench.text", "Lauftext")
    )
    wrow2 = QHBoxLayout()
    main.wb_text_pos = QComboBox()
    main.wb_text_pos.addItems(["bottom", "top"])
    main.wb_text_speed = QComboBox()
    main.wb_text_speed.addItems(["slow", "medium", "fast", "auto"])
    main.wb_text_bg = QCheckBox(
        main.texts["strings"].get("workbench.text_bg", "Balken hinter Text")
    )
    wrow2.addWidget(QLabel(main.texts["strings"].get("workbench.text_pos", "Position")))
    wrow2.addWidget(main.wb_text_pos)
    wrow2.addWidget(QLabel(main.texts["strings"].get("workbench.text_speed", "Tempo")))
    wrow2.addWidget(main.wb_text_speed)
    wrow2.addWidget(main.wb_text_bg)
    wb.addWidget(main.wb_text_on)
    wb.addWidget(main.wb_text)
    wb.addLayout(wrow2)

    main.wb_logo_on = QCheckBox(
        main.texts["strings"].get("workbench.logo_on", "Logo aktiv")
    )
    wrow3 = QHBoxLayout()
    main.wb_logo_path = QLineEdit()
    main.wb_logo_path.setPlaceholderText(
        main.texts["strings"].get("workbench.logo", "Logo")
    )
    main.wb_logo_pick = QPushButton("…")
    main.wb_logo_pos = QComboBox()
    main.wb_logo_pos.addItems(["bottom-right", "bottom-left", "top-right", "top-left"])
    main.wb_logo_scale = QSpinBox()
    main.wb_logo_scale.setRange(5, 50)
    main.wb_logo_scale.setValue(14)
    wrow3.addWidget(main.wb_logo_path, 2)
    wrow3.addWidget(main.wb_logo_pick)
    wrow3.addWidget(QLabel(main.texts["strings"].get("workbench.logo_pos", "Position")))
    wrow3.addWidget(main.wb_logo_pos)
    wrow3.addWidget(
        QLabel(main.texts["strings"].get("workbench.logo_size", "Größe (%)"))
    )
    wrow3.addWidget(main.wb_logo_scale)
    wb.addWidget(main.wb_logo_on)
    wb.addLayout(wrow3)

    main.wb_gray = QCheckBox(
        main.texts["strings"].get("workbench.grayscale", "Schwarz/Weiß (optional)")
    )
    main.wb_gray.setChecked(
        bool(main.settings.get("video", {}).get("grayscale_default", False))
    )
    wb.addWidget(main.wb_gray)

    wrow4 = QHBoxLayout()
    main.btn_wb_export = QPushButton(
        main.texts["strings"].get("workbench.export_now", "Ausgabe bauen")
    )
    main.btn_wb_open_exports = QPushButton(
        main.texts["strings"].get("workbench.open_exports", "Ausgaben öffnen")
    )
    wrow4.addWidget(main.btn_wb_export)
    wrow4.addWidget(main.btn_wb_open_exports)
    wb.addLayout(wrow4)

    md.addWidget(main.grp_workbench)

    main.grp_last = QGroupBox(
        main.texts["strings"].get("reports.karte_titel", "Letzte Nacht")
    )
    lnl = QVBoxLayout(main.grp_last)
    main.lbl_last_summary = QLabel("Noch kein Lauf gefunden.")
    lnl.addWidget(main.lbl_last_summary)

    # Quarantine search
    qrow = QHBoxLayout()
    main.q_search_box = QLineEdit()
    main.q_search_box.setPlaceholderText("Suchen in Quarantäne …")
    qrow.addWidget(main.q_search_box, 1)
    lnl.addLayout(qrow)

    lnl.addWidget(QLabel("Quarantäne (kurz):"))
    main.list_q = QListWidget()
    lnl.addWidget(main.list_q)

    qbtns = QHBoxLayout()
    main.btn_open_qjobs = QPushButton("Tagesliste öffnen")
    main.btn_rerun_all = QPushButton("Alle neu machen (Ton Safe)")
    qbtns.addWidget(main.btn_open_qjobs)
    qbtns.addWidget(main.btn_rerun_all)
    lnl.addLayout(qbtns)

    # Done search
    drow = QHBoxLayout()
    main.done_search_box = QLineEdit()
    main.done_search_box.setPlaceholderText("Suchen in Ausgaben …")
    drow.addWidget(main.done_search_box, 1)
    lnl.addLayout(drow)

    lnl.addWidget(
        QLabel(
            main.texts["strings"].get(
                "reports.block_fertig_kurz", "Frisch aus der Werkbank"
            )
            + " (letzte 3):"
        )
    )
    main.list_done = QListWidget()
    lnl.addWidget(main.list_done)
    md.addWidget(main.grp_last)

    md.addStretch(1)

    # --- RIGHT PANEL ---
    main.right = QWidget()
    rd = QVBoxLayout(main.right)
    rd.addWidget(QLabel("Einstellungen (Basic)"))
    main.btn_setup = QPushButton("Systemeinrichtung (FFmpeg) – tagsüber")
    main.btn_exports = QPushButton("Ausgaben-Ordner öffnen")
    main.btn_open_last_report = QPushButton("Letzten Arbeitsbericht öffnen")
    main.btn_refresh_last = QPushButton("Letzte Nacht aktualisieren")
    rd.addWidget(main.btn_setup)
    rd.addWidget(main.btn_exports)
    rd.addWidget(main.btn_open_last_report)
    rd.addWidget(main.btn_refresh_last)
    rd.addStretch(1)

    splitter.addWidget(main.left)
    splitter.addWidget(main.mid)
    splitter.addWidget(main.right)
    splitter.setStretchFactor(1, 3)

    rootw = QWidget()
    rl = QVBoxLayout(rootw)
    rl.setContentsMargins(10, 10, 10, 10)
    rl.setSpacing(10)
    rl.addWidget(splitter)
    main.setCentralWidget(rootw)
