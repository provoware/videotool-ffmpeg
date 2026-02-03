from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


class QuarantineTableController:
    allowed_statuses = {
        "bereit",
        "laeuft",
        "fest",
        "erledigt",
        "zurueckgestellt",
    }
    editable_columns = {0: "status", 2: "summary", 4: "recommended_action"}

    def __init__(
        self,
        table,
        status_bar,
        load_today,
        save_today,
        update_status,
    ):
        self.table = table
        self.status_bar = status_bar
        self.load_today = load_today
        self.save_today = save_today
        self.update_status = update_status
        self._loading = False

    def _get_doc(self) -> dict:
        try:
            return self.load_today()
        except Exception:
            return {"items": [], "list_status": "offen"}

    def load_table(self) -> None:
        doc = self._get_doc()
        doc = self.update_status(doc)
        self.save_today(doc)

        items = doc.get("items", [])
        self._loading = True
        self.table.blockSignals(True)
        self.table.setRowCount(len(items))
        for r, it in enumerate(items):
            status = it.get("status", "")
            out_file = it.get("output_file", "")
            reason = it.get("summary", "")
            tries = f"{it.get('tries', 0)}/{it.get('max_tries', 3)}"
            job_id = it.get("job_id", "")
            recommended = it.get("recommended_action", "")
            values = [status, out_file, reason, tries, recommended, job_id]
            for c, val in enumerate(values):
                item = QTableWidgetItem(val)
                flags = item.flags() & ~Qt.ItemIsEditable
                if c in self.editable_columns:
                    flags |= Qt.ItemIsEditable
                item.setFlags(flags)
                self.table.setItem(r, c, item)
        self.table.blockSignals(False)
        self._loading = False

    def selected_job_id(self) -> str | None:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        row = sel[0].row()
        item = self.table.item(row, 5)
        return item.text() if item else None

    def update_job_status(self, job_id: str, new_status: str) -> bool:
        if new_status not in self.allowed_statuses:
            self.status_bar.showMessage(
                "Status ungültig. Erlaubt: bereit, laeuft, fest, erledigt, zurueckgestellt."
            )
            return False
        doc = self._get_doc()
        changed = False
        for it in doc.get("items", []):
            if it.get("job_id") == job_id:
                it["status"] = new_status
                changed = True
        if changed:
            doc = self.update_status(doc)
            self.save_today(doc)
            self.status_bar.showMessage("Quarantäne-Status aktualisiert.")
        return changed

    def on_item_changed(self, item) -> None:
        if self._loading or item is None:
            return
        field = self.editable_columns.get(item.column())
        if not field:
            return
        job_id = self._job_id_for_row(item.row())
        if not job_id:
            return
        doc = self._get_doc()
        target = None
        for it in doc.get("items", []):
            if it.get("job_id") == job_id:
                target = it
                break
        if target is None:
            return
        new_value = item.text().strip()
        if field == "status" and new_value not in self.allowed_statuses:
            self._restore_item(item, target.get(field, ""))
            self.status_bar.showMessage(
                "Status ungültig. Änderungen wurden zurückgesetzt."
            )
            return
        target[field] = new_value
        doc = self.update_status(doc)
        self.save_today(doc)
        self.status_bar.showMessage("Quarantäne-Eintrag aktualisiert.")

    def _restore_item(self, item, value: str) -> None:
        self._loading = True
        self.table.blockSignals(True)
        item.setText(value)
        self.table.blockSignals(False)
        self._loading = False

    def _job_id_for_row(self, row: int) -> str | None:
        job_item = self.table.item(row, 5)
        return job_item.text() if job_item else None
