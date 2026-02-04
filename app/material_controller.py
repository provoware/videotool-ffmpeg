from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QImageReader
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QInputDialog,
    QWidget,
)

from app_services import (
    activity,
    get_thumb_pixmap,
    is_audio_path,
    is_image_path,
    rename_file_safe,
)
from logging_utils import log_exception, log_message


class MaterialController:
    def __init__(
        self,
        parent,
        material_list,
        preview_img,
        preview_info,
        sort_combo,
        sel_list,
        sel_group,
        status_bar,
    ) -> None:
        self.parent = parent
        self.material_list = material_list
        self.preview_img = preview_img
        self.preview_info = preview_info
        self.sort_combo = sort_combo
        self.sel_list = sel_list
        self.sel_group = sel_group
        self.status_bar = status_bar
        self.material_search = ""
        self.material_type_filter = "alle"
        self.selection_search = ""
        self.selection_type_filter = "alle"
        self._validate_components()

    def _validate_components(self) -> None:
        missing = [
            name
            for name, val in (
                ("material_list", self.material_list),
                ("preview_img", self.preview_img),
                ("preview_info", self.preview_info),
                ("sort_combo", self.sort_combo),
                ("sel_list", self.sel_list),
                ("sel_group", self.sel_group),
            )
            if val is None
        ]
        if missing:
            raise ValueError(
                "Material-Controller: Pflicht-Komponenten fehlen "
                f"({', '.join(missing)})."
            )

    def _status(self, message: str) -> None:
        if not isinstance(message, str):
            log_message(
                "Statusmeldung: unerwarteter Typ.",
                level="WARN",
                context="ui.material",
                extra={"type": type(message).__name__},
            )
            message = str(message)
        if self.status_bar is not None:
            self.status_bar.showMessage(message)
        else:
            log_message(
                message,
                context="ui.material",
            )

    def on_material_search(self, text: str) -> None:
        if not isinstance(text, str):
            log_message(
                "Material-Suche: unerwarteter Typ, wird umgewandelt.",
                level="WARN",
                context="ui.material",
                extra={"type": type(text).__name__},
            )
            text = str(text)
        self.material_search = text.strip().lower()
        self.apply_material_filter()

    def on_material_type(self, idx: int) -> None:
        if not isinstance(idx, int):
            log_message(
                "Material-Typfilter: unerwarteter Index.",
                level="WARN",
                context="ui.material",
                extra={"type": type(idx).__name__},
            )
        options = ["alle", "audio", "bilder"]
        self.material_type_filter = options[idx] if 0 <= idx < len(options) else "alle"
        self.apply_material_filter()

    def on_selection_search(self, text: str) -> None:
        if not isinstance(text, str):
            log_message(
                "Auswahl-Suche: unerwarteter Typ, wird umgewandelt.",
                level="WARN",
                context="ui.material",
                extra={"type": type(text).__name__},
            )
            text = str(text)
        self.selection_search = text.strip().lower()
        self.refresh_selection()

    def on_selection_type(self, idx: int) -> None:
        if not isinstance(idx, int):
            log_message(
                "Auswahl-Typfilter: unerwarteter Index.",
                level="WARN",
                context="ui.material",
                extra={"type": type(idx).__name__},
            )
        options = ["alle", "audio", "bilder"]
        self.selection_type_filter = options[idx] if 0 <= idx < len(options) else "alle"
        self.refresh_selection()

    def apply_material_filter(self) -> None:
        for i in range(self.material_list.count()):
            it = self.material_list.item(i)
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
                if self.material_type_filter != "alle":
                    show = False
            it.setHidden(not show)

    def pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Dateien holen",
            str(Path.home() / "Downloads"),
            "Audio/Bilder (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if not files:
            self._status("Keine Dateien gewählt. Nächster Schritt: Auswahl treffen.")
            return
        self.add_paths_to_material([Path(f) for f in files])

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self.parent, "Ordner holen", str(Path.home() / "Downloads")
        )
        if not folder:
            self._status("Kein Ordner gewählt. Nächster Schritt: Auswahl treffen.")
            return
        p = Path(folder)
        paths = [x for x in p.iterdir() if x.is_file()]
        self.add_paths_to_material(paths)

    def add_paths_to_material(self, paths) -> None:
        if not paths:
            self._status(
                "Keine neuen Dateien erhalten. Nächster Schritt: Auswahl prüfen."
            )
            return
        added = 0
        for p in paths:
            try:
                path = Path(p)
            except Exception:
                log_message(
                    "Material-Import: ungültiger Pfad.",
                    level="WARN",
                    context="ui.material",
                    extra={"path": str(p)},
                )
                continue
            if path.is_dir():
                for child in path.iterdir():
                    if child.is_file():
                        added += self._add_single_path(child)
            else:
                added += self._add_single_path(path)
        self.apply_sort()
        self.apply_material_filter()
        if added:
            self._status(f"{added} Datei(en) geholt. Jetzt: Checkboxen anklicken.")
            activity(f"Import: {added} Datei(en) hinzugefügt.")
        self.refresh_selection()

    def _add_single_path(self, path: Path) -> int:
        if not is_audio_path(path) and not is_image_path(path):
            return 0
        for i in range(self.material_list.count()):
            it = self.material_list.item(i)
            if it.data(Qt.UserRole) == str(path):
                return 0

        it = QListWidgetItem(path.name)
        it.setToolTip(str(path))
        it.setData(Qt.UserRole, str(path))
        it.setCheckState(Qt.Unchecked)

        if is_image_path(path):
            pm = get_thumb_pixmap(path, 96)
            if pm:
                it.setIcon(QIcon(pm))
        self.material_list.addItem(it)
        return 1

    def apply_sort(self) -> None:
        items = []
        for i in range(self.material_list.count()):
            it = self.material_list.item(i)
            path = it.data(Qt.UserRole)
            items.append((it.checkState(), it.text(), path, it.icon(), it.isHidden()))
        self.material_list.blockSignals(True)
        self.material_list.clear()
        mode = self.sort_combo.currentIndex()

        def key_fn(entry):
            chk, name, path, _icon, _hidden = entry
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
            self.material_list.addItem(it)
        self.material_list.blockSignals(False)

    def update_preview_from_current(self, current, prev) -> None:
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

    def refresh_selection(self) -> None:
        checked = []
        self.sel_list.clear()

        for i in range(self.material_list.count()):
            it = self.material_list.item(i)
            if it.checkState() == Qt.Checked:
                path = it.data(Qt.UserRole) or ""
                name = (it.text() or "").lower()
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

        self.sel_group.setTitle(f"Deine Auswahl ({len(checked)})")
        for it, path in checked:
            self._add_selection_row(it, path)

        self._status("Auswahl aktualisiert. Nächster Schritt: Vorschau klicken.")

    def _add_selection_row(self, material_item: QListWidgetItem, path_str: str) -> None:
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
            self.refresh_selection()
            activity(f"Auswahl entfernt: {material_item.text()}")

        def do_rename():
            if not path_str:
                QMessageBox.information(
                    self.parent, "Umbenennen", "Diese Auswahl hat keinen echten Pfad."
                )
                return
            p = Path(path_str)
            if not p.exists():
                QMessageBox.information(
                    self.parent,
                    "Umbenennen",
                    "Datei nicht gefunden. Pfad ist veraltet.",
                )
                return
            new_name, ok = QInputDialog.getText(
                self.parent, "Umbenennen", "Neuer Name (ohne Endung):", text=p.stem
            )
            if not ok or not new_name.strip():
                return
            try:
                new_path = rename_file_safe(p, new_name)
            except Exception as exc:
                log_exception(
                    "ui.material.rename",
                    exc,
                    extra={"path": str(p), "new_name": new_name},
                )
                QMessageBox.critical(
                    self.parent, "Umbenennen", f"Konnte nicht umbenennen:\n{exc}"
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
            self.refresh_selection()
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

    def clear_selection(self) -> None:
        for i in range(self.material_list.count()):
            self.material_list.item(i).setCheckState(Qt.Unchecked)
        self.refresh_selection()
