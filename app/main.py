#!/usr/bin/env python3
from __future__ import annotations

import sys
from typing import Iterable

from PySide6.QtWidgets import QApplication

from logging_utils import log_exception, log_message
from ui_main_window import Main


class UiApplication:
    def __init__(self, argv: Iterable[str] | None = None) -> None:
        self.argv = self._validate_argv(argv)

    def _validate_argv(self, argv: Iterable[str] | None) -> list[str]:
        if argv is None:
            argv = sys.argv
        if not isinstance(argv, (list, tuple)):
            log_message(
                "Unerwarteter argv-Typ. Standard wird genutzt.",
                level="WARN",
                context="ui",
                extra={"argv_type": type(argv).__name__},
            )
            argv = list(sys.argv)
        cleaned: list[str] = []
        for item in argv:
            if isinstance(item, str):
                cleaned.append(item)
            else:
                cleaned.append(str(item))
        if not cleaned:
            cleaned = ["modultool"]
        return cleaned

    def build_app(self) -> QApplication:
        app = QApplication(self.argv)
        if app is None:
            raise RuntimeError("Qt Application konnte nicht erstellt werden.")
        log_message(
            "Qt-Anwendung erstellt.",
            context="ui",
            extra={"argv": self.argv},
        )
        return app


class MainWindowLauncher:
    def __init__(self, app: QApplication) -> None:
        self.app = self._validate_app(app)

    def _validate_app(self, app: QApplication) -> QApplication:
        if not isinstance(app, QApplication):
            raise TypeError("Ungültige QApplication-Instanz.")
        return app

    def build_window(self) -> Main:
        window = Main()
        if not isinstance(window, Main):
            raise RuntimeError("Main-Window konnte nicht erstellt werden.")
        log_message("Hauptfenster erstellt.", context="ui")
        return window

    def show_window(self, window: Main) -> None:
        if not isinstance(window, Main):
            raise TypeError("Ungültige Main-Window-Instanz.")
        window.show()
        log_message(
            "Hauptfenster angezeigt.",
            context="ui",
            user_message="Oberfläche bereit.",
        )


class UiRunner:
    def __init__(self, argv: Iterable[str] | None = None) -> None:
        self.app_factory = UiApplication(argv)

    def run(self) -> int:
        try:
            app = self.app_factory.build_app()
            launcher = MainWindowLauncher(app)
            window = launcher.build_window()
            launcher.show_window(window)
            exit_code = app.exec()
            if not isinstance(exit_code, int):
                log_message(
                    "Unerwarteter Exit-Code, wird normalisiert.",
                    level="WARN",
                    context="ui",
                    extra={"exit_code": exit_code},
                )
                exit_code = int(exit_code)
            log_message(
                "Qt-Anwendung beendet.",
                context="ui",
                extra={"exit_code": exit_code},
            )
            return exit_code
        except Exception as exc:
            log_exception(
                "ui",
                exc,
                user_message="Start fehlgeschlagen. Bitte Logs prüfen (Protokoll).",
            )
            return 1


def main() -> int:
    runner = UiRunner()
    result = runner.run()
    if not isinstance(result, int):
        log_message(
            "main() gab einen unerwarteten Exit-Code zurück.",
            level="WARN",
            context="ui",
            extra={"exit_code": result},
        )
        result = int(result)
    return result


if __name__ == "__main__":
    sys.exit(main())
