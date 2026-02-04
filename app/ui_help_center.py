from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QListWidgetItem, QTextEdit

from logging_utils import log_exception


class HelpCenterController:
    def __init__(self, help_view: QTextEdit, help_topics, status_bar):
        self._help_view = help_view
        self._help_topics = help_topics
        self._status_bar = status_bar
        self._help_index: dict[str, int] = {}

    def load_help_center(self, help_path: Path) -> None:
        if not isinstance(help_path, Path):
            self._status_bar.showMessage(
                "Hilfe-Center Pfad ungültig. Nächster Schritt: Einstellungen prüfen."
            )
            return
        try:
            content = (
                help_path.read_text(encoding="utf-8")
                if help_path.exists()
                else "HELP_CENTER.md fehlt."
            )
        except Exception as exc:
            log_exception(
                "help_center.read",
                exc,
                extra={"path": str(help_path)},
            )
            content = "HELP_CENTER.md konnte nicht geladen werden."
        self._help_view.setPlainText(content)
        self._help_index = self._build_help_index(content)
        self._help_topics.clear()
        for title in self._help_index:
            self._help_topics.addItem(title)
        self._status_bar.showMessage("Hilfe-Center geladen.")

    def find(self, query: str, label: str, success_msg: str) -> None:
        if not query.strip():
            self._status_bar.showMessage(
                f"{label}: Bitte Suchbegriff eingeben (Query = Suchtext)."
            )
            return
        text = self._help_view.toPlainText()
        idx = text.lower().find(query.lower())
        if idx >= 0:
            cursor = self._help_view.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(query), cursor.KeepAnchor)
            self._help_view.setTextCursor(cursor)
            self._status_bar.showMessage(success_msg)
        else:
            self._status_bar.showMessage(
                f"{label}: Kein Treffer gefunden. Nächster Schritt: Begriff prüfen."
            )

    def jump_to_topic(self, item: QListWidgetItem) -> None:
        if not item:
            return
        title = item.text()
        pos = self._help_index.get(title)
        if pos is None:
            return
        cursor = self._help_view.textCursor()
        cursor.setPosition(pos)
        self._help_view.setTextCursor(cursor)
        self._status_bar.showMessage("Hilfe-Thema geöffnet.")

    def _build_help_index(self, content: str) -> dict[str, int]:
        index: dict[str, int] = {}
        if not isinstance(content, str):
            return index
        offset = 0
        for line in content.splitlines(keepends=True):
            stripped = line.strip()
            if stripped.startswith("## "):
                title = stripped.replace("## ", "", 1).strip()
                if title:
                    index[title] = offset
            offset += len(line)
        return index
