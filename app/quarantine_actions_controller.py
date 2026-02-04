from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QMessageBox

from app_services import activity, run_quarantine_worker
from logging_utils import log_message
from paths import data_dir


class QuarantineActionsController:
    def __init__(
        self,
        parent,
        table_controller,
        settings: dict,
        open_dir_with_feedback,
        open_qjobs_today,
        refresh_last_night,
        load_quarantine_table,
    ) -> None:
        self.parent = parent
        self.table_controller = table_controller
        self.settings = settings
        self.open_dir_with_feedback = open_dir_with_feedback
        self.open_qjobs_today = open_qjobs_today
        self.refresh_last_night = refresh_last_night
        self.load_quarantine_table = load_quarantine_table

    def _selected_job_id(self) -> str | None:
        return self.table_controller.selected_job_id()

    def _update_status(self, job_id: str, new_status: str) -> bool:
        return self.table_controller.update_job_status(job_id, new_status)

    def open_folder(self) -> None:
        qdir = (
            data_dir()
            / self.settings.get("paths", {}).get("quarantine_dir", "quarantine")
            / datetime.now().strftime("%Y-%m-%d")
        )
        self.open_dir_with_feedback(qdir, "Quarantäne-Ordner")

    def require_job_id(self, action_label: str) -> str | None:
        if not isinstance(action_label, str):
            action_label = str(action_label)
        job_id = self._selected_job_id()
        if job_id:
            return job_id
        msg = (
            f"{action_label}: Kein Eintrag gewählt. Nächster Schritt: Zeile anklicken."
        )
        QMessageBox.information(self.parent, action_label, msg)
        if hasattr(self.parent, "statusBar"):
            self.parent.statusBar().showMessage(msg)
        log_message(
            "Quarantäne-Aktion ohne Auswahl.",
            level="WARN",
            context="ui.quarantine",
            user_message=msg,
        )
        return None

    def rerun_selected(self) -> None:
        job_id = self.require_job_id("Quarantäne neu starten")
        if not job_id:
            return
        run_quarantine_worker(job_id)
        if hasattr(self.parent, "statusBar"):
            self.parent.statusBar().showMessage("Quarantäne-Auftrag gestartet.")
        activity("Quarantäne-Worker gestartet (Einzelauftrag).")
        self.refresh_last_night()

    def replace_selected(self) -> None:
        job_id = self.require_job_id("Quelle ersetzen")
        if not job_id:
            return
        self.replace_source_simple(job_id)

    def postpone_selected(self) -> None:
        job_id = self.require_job_id("Quarantäne zurückstellen")
        if not job_id:
            return
        if self._update_status(job_id, "zurueckgestellt"):
            self.load_quarantine_table()

    def done_selected(self) -> None:
        job_id = self.require_job_id("Quarantäne erledigt")
        if not job_id:
            return
        if self._update_status(job_id, "erledigt"):
            self.load_quarantine_table()

    def replace_source_simple(self, job_id: str) -> None:
        if not job_id:
            return
        QMessageBox.information(
            self.parent,
            "Quelle ersetzen",
            "Für jetzt: Öffne die Tagesliste (JSON) und ändere staging_audio/staging_image.\n"
            "Danach 'Neu (Ton Safe)'.",
        )
        self.open_qjobs_today()
