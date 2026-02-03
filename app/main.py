#!/usr/bin/env python3
import sys

from PySide6.QtWidgets import QApplication

from ui_main_window import Main


def main():
    app = QApplication(sys.argv)
    win = Main()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
