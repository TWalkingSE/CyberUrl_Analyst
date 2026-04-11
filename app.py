"""CyberURL Analyst v3.0 — desktop application powered by PyQt6."""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from config.settings import APP_NAME, APP_VERSION
from ui.main_window import APP_ICON_PATH, MainWindow
from ui.state import AppState
from ui.theme import apply_theme


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

load_dotenv(PROJECT_DIR / ".env")


def create_application(argv=None, theme: str = "dark") -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    apply_theme(app, theme)
    return app


def authenticate(state: AppState) -> bool:
    password = os.getenv("CYBERURL_PASSWORD", "")
    if not password:
        state.set_authenticated(True)
        return True

    typed_password, accepted = QInputDialog.getText(
        None,
        APP_NAME,
        "Senha de acesso",
        QLineEdit.EchoMode.Password,
    )
    if not accepted:
        return False
    if secrets.compare_digest(typed_password, password):
        state.set_authenticated(True)
        return True

    QMessageBox.critical(None, APP_NAME, "Senha incorreta.")
    return False


def build_main_window(state: AppState | None = None) -> tuple[AppState, MainWindow]:
    runtime_state = state or AppState()
    apply_theme(QApplication.instance(), runtime_state.theme)
    return runtime_state, MainWindow(runtime_state)


def main(argv=None) -> int:
    state = AppState()
    app = create_application(argv, theme=state.theme)
    if not authenticate(state):
        return 1
    window = MainWindow(state)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
