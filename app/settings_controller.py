from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from io_utils import atomic_write_json
from logging_utils import log_message
from paths import config_dir, data_dir
from app_services import activity


class SettingsController:
    def __init__(
        self,
        parent,
        settings: dict,
        texts: dict,
        widgets: dict,
    ) -> None:
        self.parent = parent
        self.settings = settings
        self.texts = texts
        self.widgets = widgets

    def pick_folder_into(self, line_edit, title: str) -> None:
        if line_edit is None or not hasattr(line_edit, "setText"):
            log_message(
                "Einstellungen: Ziel-Feld fehlt für Ordnerauswahl.",
                level="WARN",
                context="ui.settings",
            )
            return
        if not isinstance(title, str):
            title = str(title)
        folder = QFileDialog.getExistingDirectory(
            self.parent, title, str(Path.home() / "Downloads")
        )
        if folder:
            line_edit.setText(folder)

    def apply_defaults(self) -> None:
        self.widgets["set_watch_folder"].setText(str(Path.home() / "Downloads"))
        self.widgets["set_exports_dir"].setText("exports")
        self.widgets["set_library_audio_dir"].setText("library/audio")
        self.widgets["set_library_images_dir"].setText("library/images")
        self.widgets["set_quarantine_dir"].setText("quarantine")
        self.widgets["set_quarantine_jobs_dir"].setText("quarantine_jobs")
        self.widgets["set_reports_dir"].setText("reports")
        self.widgets["set_staging_dir"].setText("staging")
        self.widgets["set_trash_dir"].setText("trash")

        self.widgets["set_fade_in"].setValue(0.5)
        self.widgets["set_fade_out"].setValue(1.0)
        self.widgets["set_min_br"].setValue(192)
        self.widgets["set_target_br"].setValue(320)
        self.widgets["set_sr"].setValue(48000)

        self.widgets["set_tmpl_single"].setText(
            "{audio}_{vorlage}_{datum}_{uhrzeit}{sw}"
        )
        self.widgets["set_tmpl_batch"].setText("{audio}_{vorlage}_{datum}_{nummer}{sw}")
        self.widgets["set_append_label"].setChecked(False)
        ix = self.widgets["set_append_mode"].findText("only_quarantine")
        if ix >= 0:
            self.widgets["set_append_mode"].setCurrentIndex(ix)
        self.widgets["set_append_short"].setChecked(True)
        self.update_name_preview()

    def save_settings(self) -> None:
        if not self._validate_templates():
            return
        self.settings.setdefault("paths", {})
        self.settings["paths"]["watch_folder"] = (
            self.widgets["set_watch_folder"].text().strip()
        )
        for key in [
            "exports_dir",
            "library_audio_dir",
            "library_images_dir",
            "quarantine_dir",
            "quarantine_jobs_dir",
            "reports_dir",
            "staging_dir",
            "trash_dir",
        ]:
            le = self.widgets[f"set_{key}"]
            value = le.text().strip()
            self.settings["paths"][key] = value or self.settings["paths"].get(key, "")

        self.settings.setdefault("audio", {})
        self.settings["audio"]["fade_in_sec"] = float(
            self.widgets["set_fade_in"].value()
        )
        self.settings["audio"]["fade_out_sec"] = float(
            self.widgets["set_fade_out"].value()
        )
        self.settings["audio"]["min_bitrate_kbps"] = int(
            self.widgets["set_min_br"].value()
        )
        self.settings["audio"]["target_bitrate_kbps"] = int(
            self.widgets["set_target_br"].value()
        )
        self.settings["audio"]["target_samplerate_hz"] = int(
            self.widgets["set_sr"].value()
        )

        self.settings.setdefault("naming", {})
        self.settings["naming"]["template_single"] = (
            self.widgets["set_tmpl_single"].text().strip()
        )
        self.settings["naming"]["template_batch"] = (
            self.widgets["set_tmpl_batch"].text().strip()
        )
        self.settings["naming"]["append_label_to_output"] = bool(
            self.widgets["set_append_label"].isChecked()
        )
        self.settings["naming"]["append_label_mode"] = (
            self.widgets["set_append_mode"].currentText().strip()
        )
        self.settings["naming"]["append_label_shortform"] = bool(
            self.widgets["set_append_short"].isChecked()
        )

        settings_path = config_dir() / "settings.json"
        ok = atomic_write_json(
            settings_path,
            self.settings,
            context="ui.settings_save",
        )
        if ok:
            QMessageBox.information(
                self.parent,
                self.texts["strings"].get("settings.ok", "OK"),
                "Gespeichert. Werkstatt läuft weiter.",
            )
            activity("Einstellungen gespeichert.")
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage("Einstellungen gespeichert.")
        else:
            QMessageBox.critical(
                self.parent,
                "Einstellungen",
                "Speichern fehlgeschlagen. Bitte erneut versuchen.",
            )

    def test_paths(self) -> None:
        base_dir = data_dir()
        rels = {
            "exports": self.widgets["set_exports_dir"].text().strip(),
            "library_audio": self.widgets["set_library_audio_dir"].text().strip(),
            "library_images": self.widgets["set_library_images_dir"].text().strip(),
            "quarantine": self.widgets["set_quarantine_dir"].text().strip(),
            "quarantine_jobs": self.widgets["set_quarantine_jobs_dir"].text().strip(),
            "reports": self.widgets["set_reports_dir"].text().strip(),
            "staging": self.widgets["set_staging_dir"].text().strip(),
            "trash": self.widgets["set_trash_dir"].text().strip(),
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
            except Exception as exc:
                errors.append(f"{key}: {exc}")

        watch = Path(self.widgets["set_watch_folder"].text().strip()).expanduser()
        if not watch.exists():
            errors.append(f"watch_folder fehlt: {watch}")
        else:
            try:
                testfile = watch / ".modultool_watch_write_test.tmp"
                testfile.write_text("ok", encoding="utf-8")
                testfile.unlink(missing_ok=True)
            except Exception as exc:
                errors.append(f"watch_folder nicht schreibbar: {exc}")
                log_message(
                    "Einstellungen: Watchfolder nicht schreibbar.",
                    level="WARN",
                    context="ui.settings",
                    user_message=(
                        "Watchfolder (Eingangsordner) braucht Schreibrechte. "
                        "Nächster Schritt: Ordnerrechte prüfen oder neuen Ordner wählen."
                    ),
                    extra={"path": str(watch), "error": str(exc)},
                )

        if errors:
            QMessageBox.critical(
                self.parent,
                self.texts["strings"].get("settings.fehler", "Fehler"),
                "Pfade nicht ok:\n- " + "\n- ".join(errors),
            )
        else:
            QMessageBox.information(
                self.parent,
                self.texts["strings"].get("settings.ok", "OK"),
                "Alle Pfade sind schreibbar. Nachtbetrieb ist safe.",
            )
        activity("Pfade getestet.")

    def _validate_templates(self) -> bool:
        keys = {
            "audio": "track_demo",
            "vorlage": "youtube_hd_ton_safe",
            "datum": "2026-02-14",
            "uhrzeit": "120000",
            "nummer": "001",
            "sw": "",
        }
        templates = {
            "Einzelvorlage": self.widgets["set_tmpl_single"].text(),
            "Sammelvorlage": self.widgets["set_tmpl_batch"].text(),
        }
        for label, template in templates.items():
            try:
                template.format(**keys)
            except Exception as exc:
                log_message(
                    "Einstellungen: Vorlage ungültig.",
                    level="WARN",
                    context="ui.settings",
                    user_message=(
                        "Vorlage ungültig (Formatierung = Felder mit {name}). "
                        "Nächster Schritt: Felder prüfen und Beispiel übernehmen."
                    ),
                    extra={"template": label, "error": str(exc)},
                )
                QMessageBox.critical(
                    self.parent,
                    "Einstellungen",
                    (
                        f"{label} ungültig. "
                        "Bitte Felder wie {audio} oder {datum} prüfen."
                    ),
                )
                if hasattr(self.parent, "statusBar"):
                    self.parent.statusBar().showMessage(
                        "Vorlage ungültig. Nächster Schritt: Felder prüfen."
                    )
                return False
        return True

    def update_name_preview(self) -> None:
        import datetime as _dt

        audio = "track_demo"
        vorlage = "youtube_hd_ton_safe"
        datum = _dt.datetime.now().strftime("%Y-%m-%d")
        uhrzeit = _dt.datetime.now().strftime("%H%M%S")
        nummer = "003"
        sw = ""
        try:
            example = (
                self.widgets["set_tmpl_batch"]
                .text()
                .format(
                    audio=audio,
                    vorlage=vorlage,
                    datum=datum,
                    uhrzeit=uhrzeit,
                    nummer=nummer,
                    sw=sw,
                )
            )
        except Exception:
            example = "(Vorlage hat Fehler)"
            if hasattr(self.parent, "statusBar"):
                self.parent.statusBar().showMessage(
                    "Vorlage hat Fehler. Nächster Schritt: Felder prüfen."
                )
        self.widgets["lbl_preview_name"].setText(example + ".mp4")
