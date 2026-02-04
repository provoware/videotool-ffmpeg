from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
)

from app_services import (
    fav_id_for_path,
    get_thumb_pixmap,
    is_image_path,
    load_favorites,
    norm_tags,
    open_path,
    save_favorites,
)
from logging_utils import log_message


class FavoritesController:
    def __init__(self, parent, fav_list, fav_tag_combo, texts) -> None:
        self.parent = parent
        self.fav_list = fav_list
        self.fav_tag_combo = fav_tag_combo
        self.texts = texts
        self._search = ""
        self._tag_filter = "alle"

    def on_search(self, text: str) -> None:
        if not isinstance(text, str):
            log_message(
                "Favoriten-Suche: unerwarteter Typ, wird umgewandelt.",
                level="WARN",
                context="ui.favorites",
                extra={"type": type(text).__name__},
            )
            text = str(text)
        self._search = text.strip().lower()
        self.refresh_favorites()

    def on_tag(self, idx: int) -> None:
        if not isinstance(idx, int):
            log_message(
                "Favoriten-Tag-Filter: unerwarteter Index.",
                level="WARN",
                context="ui.favorites",
                extra={"type": type(idx).__name__},
            )
        text = self.fav_tag_combo.currentText() if self.fav_tag_combo else ""
        self._tag_filter = "alle"
        if text.startswith("Tag: "):
            val = text[5:].strip()
            self._tag_filter = val if val and val != "alle" else "alle"
        self.refresh_favorites()

    def refresh_favorites(self) -> None:
        doc = load_favorites()
        items = doc.get("items", [])

        tags = set()
        for it in items:
            for tg in it.get("tags", []):
                tags.add(tg)

        current = (
            self.fav_tag_combo.currentText()
            if self.fav_tag_combo and self.fav_tag_combo.count()
            else "Tag: alle"
        )
        if self.fav_tag_combo:
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
            if self._search and self._search not in name.lower():
                continue
            if self._tag_filter != "alle" and self._tag_filter not in tgs:
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

    def _selected_fav_ids(self) -> list[str]:
        return [it.data(Qt.UserRole) for it in self.fav_list.selectedItems()]

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self.parent,
            "Favorit hinzufügen",
            str(Path.home() / "Downloads"),
            "Bilder/Logos (*.jpg *.jpeg *.png *.webp *.bmp)",
        )
        if not files:
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Keine Dateien gewählt. Nächster Schritt: Auswahl treffen."
                )
            return
        doc = load_favorites()
        items = doc.get("items", [])
        existing = {it.get("id") for it in items}
        added = 0
        skipped = 0
        for f in files:
            p = Path(f)
            if not p.exists() or not is_image_path(p):
                skipped += 1
                continue
            fid = fav_id_for_path(p)
            if fid in existing:
                skipped += 1
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
        QMessageBox.information(
            self.parent,
            "Favoriten",
            f"Hinzugefügt: {added}. Übersprungen: {skipped}.",
        )
        self.refresh_favorites()

    def remove_selected(self) -> None:
        ids = set(self._selected_fav_ids())
        if not ids:
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Keine Favoriten gewählt. Nächster Schritt: Eintrag markieren."
                )
            return
        doc = load_favorites()
        before = len(doc.get("items", []))
        doc["items"] = [it for it in doc.get("items", []) if it.get("id") not in ids]
        save_favorites(doc)
        removed = before - len(doc["items"])
        QMessageBox.information(self.parent, "Favoriten", f"Entfernt: {removed}")
        self.refresh_favorites()

    def toggle_star(self) -> None:
        ids = set(self._selected_fav_ids())
        if not ids:
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Keine Favoriten gewählt. Nächster Schritt: Eintrag markieren."
                )
            return
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") in ids:
                it["starred"] = not bool(it.get("starred", False))
        save_favorites(doc)
        self.refresh_favorites()

    def set_tags(self) -> None:
        ids = set(self._selected_fav_ids())
        if not ids:
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Keine Favoriten gewählt. Nächster Schritt: Eintrag markieren."
                )
            return
        text, ok = QInputDialog.getText(
            self.parent,
            "Tags setzen",
            "Tags (kommagetrennt):",
            text="logo, hell, transparent",
        )
        if not ok:
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Tag-Vergabe abgebrochen. Nächster Schritt: Eingabe bestätigen."
                )
            return
        tags = norm_tags(text)
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") in ids:
                it["tags"] = tags
        save_favorites(doc)
        self.refresh_favorites()

    def open_selected(self, item: QListWidgetItem) -> None:
        if item is None:
            return
        fid = item.data(Qt.UserRole)
        if not fid:
            return
        doc = load_favorites()
        for it in doc.get("items", []):
            if it.get("id") == fid:
                p = Path(it.get("path", ""))
                if p.exists():
                    open_path(p)
                    return
                QMessageBox.information(
                    self.parent,
                    "Favorit",
                    "Datei nicht gefunden. Pfad ist veraltet.",
                )
                return
