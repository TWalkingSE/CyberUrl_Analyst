"""Main application window for the PyQt6 desktop UI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_NAME, APP_VERSION
from utils.i18n import AVAILABLE_LANGUAGES
from ui.helpers import T
from ui.theme import THEME_LABELS, apply_theme
from ui.pages import (
    APIsPage,
    AnalysisPage,
    AnatomyPage,
    DashboardPage,
    DatasetsPage,
    GlossaryPage,
    QuizPage,
    ReportPage,
    ScenariosPage,
    SettingsPage,
)


PROJECT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
APP_ICON_FALLBACK_PATH = PROJECT_DIR / "phishing_tecnologico.png"
APP_ICON_PATH = (
    ICONS_DIR / "phishing_tecnologico.png"
    if (ICONS_DIR / "phishing_tecnologico.png").exists()
    else APP_ICON_FALLBACK_PATH
)


class MainWindow(QMainWindow):
    """Main window with sidebar navigation and stacked pages."""

    PAGE_DEFINITIONS = [
        ("🏠", "nav.dashboard", DashboardPage),
        ("🔍", "nav.anatomy", AnatomyPage),
        ("🛡️", "nav.analysis", AnalysisPage),
        ("📊", "nav.report", ReportPage),
        ("❓", "nav.quiz", QuizPage),
        ("🎭", "nav.scenarios", ScenariosPage),
        ("🔌", "nav.apis", APIsPage),
        ("📦", "nav.datasets", DatasetsPage),
        ("📖", "nav.glossary", GlossaryPage),
        ("⚙️", "nav.settings", SettingsPage),
    ]

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.pages = []

        apply_theme(QApplication.instance(), self.state.theme)

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1280, 820)
        self.resize(1440, 920)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        central_widget = QWidget(self)
        central_widget.setObjectName("windowRoot")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QWidget(self)
        sidebar.setObjectName("sidebarPanel")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        brand_card = QFrame(sidebar)
        brand_card.setObjectName("sidebarBrandCard")
        brand_layout = QVBoxLayout(brand_card)
        brand_layout.setContentsMargins(16, 16, 16, 16)
        brand_layout.setSpacing(8)

        title_label = QLabel(APP_NAME, brand_card)
        title_label.setObjectName("appTitle")
        brand_layout.addWidget(title_label)

        subtitle_label = QLabel("Analise educacional de URLs para usuarios nao tecnicos.", brand_card)
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setWordWrap(True)
        brand_layout.addWidget(subtitle_label)
        sidebar_layout.addWidget(brand_card)

        self.sidebar_list = QListWidget(sidebar)
        self.sidebar_list.setObjectName("sidebarList")
        self.sidebar_list.currentRowChanged.connect(self._switch_page)
        sidebar_layout.addWidget(self.sidebar_list, 1)

        language_row = QHBoxLayout()
        language_label = QLabel("Idioma", sidebar)
        language_label.setObjectName("fieldLabel")
        language_row.addWidget(language_label)
        self.language_combo = QComboBox(sidebar)
        for code, label in AVAILABLE_LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.currentIndexChanged.connect(self._change_language)
        language_row.addWidget(self.language_combo, 1)
        sidebar_layout.addLayout(language_row)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Tema", sidebar)
        theme_label.setObjectName("fieldLabel")
        theme_row.addWidget(theme_label)
        self.theme_toggle_button = QToolButton(sidebar)
        self.theme_toggle_button.setObjectName("sidebarThemeToggle")
        self.theme_toggle_button.clicked.connect(self._toggle_theme)
        theme_row.addWidget(self.theme_toggle_button, 1)
        sidebar_layout.addLayout(theme_row)

        self.version_label = QLabel(f"v{APP_VERSION}", sidebar)
        self.version_label.setObjectName("sidebarVersion")
        sidebar_layout.addWidget(self.version_label, alignment=Qt.AlignmentFlag.AlignRight)
        root_layout.addWidget(sidebar)

        content_shell = QWidget(self)
        content_shell.setObjectName("contentShell")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget(content_shell)
        self.stack.setObjectName("pageStack")
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content_shell, 1)

        self.statusBar().showMessage("Interface desktop pronta.")

        self.state.changed.connect(self._handle_state_change)
        self._populate_language_combo()
        self._refresh_theme_toggle()
        self._rebuild_pages(keep_index=False)

    def _populate_language_combo(self):
        self.language_combo.blockSignals(True)
        index = max(0, self.language_combo.findData(self.state.lang))
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)

    def _refresh_theme_toggle(self):
        current_label = THEME_LABELS.get(self.state.theme, self.state.theme)
        next_theme = "light" if self.state.theme == "dark" else "dark"
        next_label = THEME_LABELS.get(next_theme, next_theme)
        self.theme_toggle_button.setText(current_label)
        self.theme_toggle_button.setToolTip(f"Alternar para {next_label}")

    def _toggle_theme(self):
        self.state.set_theme("light" if self.state.theme == "dark" else "dark")

    def _clear_stack(self):
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

    def _rebuild_pages(self, keep_index: bool = True):
        current_row = self.sidebar_list.currentRow() if keep_index else 0
        self.sidebar_list.blockSignals(True)
        self.sidebar_list.clear()
        self._clear_stack()
        self.pages = []

        for icon, key, page_class in self.PAGE_DEFINITIONS:
            label = f"{icon} {T(key, self.state.lang)}"
            self.sidebar_list.addItem(label)
            page = page_class(self.state, self)
            self.pages.append(page)
            self.stack.addWidget(page)

        self.sidebar_list.blockSignals(False)
        if self.pages:
            current_row = min(max(current_row, 0), len(self.pages) - 1)
            self.sidebar_list.setCurrentRow(current_row)
            self.stack.setCurrentIndex(current_row)
        self.statusBar().showMessage("Interface atualizada.")

    def _switch_page(self, row: int):
        if 0 <= row < len(self.pages):
            self.stack.setCurrentIndex(row)
            self.statusBar().showMessage(self.sidebar_list.item(row).text())

    def _change_language(self, index: int):
        lang = self.language_combo.itemData(index)
        if lang:
            self.state.set_language(lang)

    def _handle_state_change(self, event: str):
        if event == "language":
            self._populate_language_combo()
            self._rebuild_pages()
        elif event == "theme":
            apply_theme(QApplication.instance(), self.state.theme)
            self._refresh_theme_toggle()
            self._rebuild_pages()
            self.statusBar().showMessage(
                f"Tema aplicado: {THEME_LABELS.get(self.state.theme, self.state.theme)}"
            )
        elif event == "analysis":
            self.statusBar().showMessage("Nova analise concluida.")