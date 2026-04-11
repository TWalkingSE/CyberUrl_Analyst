"""Application stylesheet and palette utilities for the PyQt6 desktop interface."""

from __future__ import annotations

DARK_PALETTE = {
    "window": "#0B1118",
    "window_alt": "#111A24",
    "content": "#0E151D",
    "sidebar_top": "#162334",
    "sidebar_bottom": "#0F1A28",
    "surface": "#111A24",
    "surface_alt": "#162231",
    "surface_deep": "#0B131B",
    "panel": "#14202C",
    "panel_alt": "#182635",
    "border": "#294158",
    "border_soft": "#223549",
    "text": "#E7EEF5",
    "text_strong": "#F6FAFD",
    "text_muted": "#A7B7C8",
    "text_dim": "#8093A6",
    "accent": "#2A9D8F",
    "accent_hover": "#36B4A5",
    "accent_pressed": "#24786D",
    "accent_secondary": "#1F6F8B",
    "accent_soft": "#8AD4C9",
    "accent_warm": "#E7C879",
    "success": "#5BC48C",
    "success_bg": "#11261C",
    "warning": "#F2B84B",
    "warning_bg": "#2D2411",
    "danger": "#EF6B73",
    "danger_bg": "#2E151A",
    "info": "#75B7FF",
    "info_bg": "#122133",
    "neutral_bg": "#162231",
}

LIGHT_PALETTE = {
    "window": "#F4EFE6",
    "window_alt": "#E7DDCF",
    "content": "#EFE6D8",
    "sidebar_top": "#D9C9AF",
    "sidebar_bottom": "#C8B28F",
    "surface": "#FFF9F1",
    "surface_alt": "#F4EBDD",
    "surface_deep": "#E9DCC7",
    "panel": "#FFF6EA",
    "panel_alt": "#F8EDDE",
    "border": "#C9B599",
    "border_soft": "#DCCCB7",
    "text": "#2E251D",
    "text_strong": "#18120D",
    "text_muted": "#665847",
    "text_dim": "#8B7965",
    "accent": "#157265",
    "accent_hover": "#1A8676",
    "accent_pressed": "#10574D",
    "accent_secondary": "#A5632D",
    "accent_soft": "#2C7E72",
    "accent_warm": "#9B6828",
    "success": "#2F8C57",
    "success_bg": "#E3F3E7",
    "warning": "#B97A16",
    "warning_bg": "#FFF2D8",
    "danger": "#C95761",
    "danger_bg": "#FDE5E8",
    "info": "#2E78C8",
    "info_bg": "#E5F0FD",
    "neutral_bg": "#F4EBDD",
}

THEMES = {
    "dark": DARK_PALETTE,
    "light": LIGHT_PALETTE,
}

THEME_LABELS = {
    "dark": "Escuro",
    "light": "Claro",
}

_ACTIVE_THEME = "dark"


def get_active_theme() -> str:
    return _ACTIVE_THEME


def get_palette(theme: str | None = None) -> dict[str, str]:
    selected = theme if theme in THEMES else _ACTIVE_THEME
    return THEMES.get(selected, DARK_PALETTE)


def build_html_document_css(palette: dict[str, str]) -> str:
    return f"""
body {{
    background: {palette['surface']};
    color: {palette['text']};
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
    padding: 14px;
}}

body.compact {{
    padding: 0;
}}

h1, h2, h3, h4 {{
    color: {palette['text_strong']};
    margin: 0 0 10px 0;
    font-weight: 700;
}}

p {{
    margin: 0 0 10px 0;
}}

ul, ol {{
    margin: 10px 0 0 18px;
    padding: 0;
}}

li {{
    margin: 4px 0;
}}

table {{
    border-collapse: collapse;
    width: 100%;
}}

th, td {{
    padding: 8px 10px;
    border-bottom: 1px solid {palette['border_soft']};
    text-align: left;
    vertical-align: top;
}}

th {{
    color: {palette['accent_soft']};
    font-weight: 700;
}}

h2 + table,
h3 + table {{
    margin-top: 8px;
}}

a {{
    color: {palette['info']};
    text-decoration: none;
}}

code {{
    background: {palette['surface_deep']};
    color: {palette['accent_warm']};
    border: 1px solid {palette['border']};
    border-radius: 6px;
    padding: 2px 6px;
    font-family: Consolas, monospace;
}}

pre {{
    background: {palette['surface_deep']};
    color: {palette['accent_warm']};
    border: 1px solid {palette['border']};
    border-radius: 10px;
    padding: 12px;
    white-space: pre-wrap;
}}

hr {{
    border: 0;
    border-top: 1px solid {palette['border']};
    margin: 18px 0;
}}

.kicker {{
    color: {palette['accent_soft']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    margin: 0 0 8px 0;
    text-transform: uppercase;
}}

.muted {{
    color: {palette['text_muted']};
}}

.small {{
    color: {palette['text_dim']};
    font-size: 12px;
}}

.panel {{
    background: {palette['panel']};
    border: 1px solid {palette['border']};
    border-radius: 14px;
    padding: 14px 16px;
}}

.panel-soft {{
    background: {palette['panel_alt']};
    border: 1px solid {palette['border_soft']};
    border-radius: 14px;
    padding: 14px 16px;
}}

.empty {{
    background: {palette['surface_alt']};
    border: 1px dashed {palette['border']};
    border-radius: 14px;
    padding: 18px;
}}

.badge {{
    background: {palette['surface_deep']};
    border: 1px solid {palette['border']};
    border-radius: 999px;
    color: {palette['text_muted']};
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 9px;
}}

.stat-grid td {{
    background: {palette['surface_deep']};
    border: 1px solid {palette['border']};
    border-radius: 12px;
    padding: 12px;
}}

.stat-value {{
    color: {palette['text_strong']};
    display: block;
    font-size: 22px;
    font-weight: 800;
    margin-top: 4px;
}}

.stat-label {{
    color: {palette['text_dim']};
    display: block;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.7px;
    text-transform: uppercase;
}}
"""


def build_app_stylesheet(palette: dict[str, str]) -> str:
    return f"""
QMainWindow, QWidget {{
    background-color: {palette['window']};
    color: {palette['text']};
    font-family: 'Segoe UI Variable Text', 'Segoe UI';
    font-size: 13px;
}}

QWidget#windowRoot {{
    background-color: {palette['window']};
}}

QWidget#sidebarPanel {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['sidebar_top']},
        stop: 1 {palette['sidebar_bottom']}
    );
    border-right: 1px solid {palette['border_soft']};
}}

QFrame#sidebarBrandCard {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['surface_alt']},
        stop: 1 {palette['panel']}
    );
    border: 1px solid {palette['border']};
    border-radius: 20px;
}}

QWidget#contentShell {{
    background-color: {palette['content']};
}}

QLabel#appTitle {{
    color: {palette['text_strong']};
    font-size: 22px;
    font-weight: 800;
}}

QLabel#appSubtitle {{
    color: {palette['text_muted']};
    font-size: 12px;
}}

QLabel#sidebarVersion {{
    color: {palette['accent_warm']};
    font-size: 11px;
    font-weight: 700;
}}

QLabel#fieldLabel {{
    color: {palette['text_dim']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}

QLabel#pageTitle {{
    color: {palette['text_strong']};
    font-size: 26px;
    font-weight: 800;
}}

QLabel#sectionTitle {{
    color: {palette['text_strong']};
    font-size: 18px;
    font-weight: 700;
}}

QLabel#pageSubtitle {{
    color: {palette['text_muted']};
    font-size: 13px;
}}

QFrame#metricCard {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['surface']},
        stop: 1 {palette['panel_alt']}
    );
    border: 1px solid {palette['border']};
    border-radius: 16px;
}}

QLabel#metricValue {{
    color: {palette['text_strong']};
    font-size: 28px;
    font-weight: 800;
}}

QLabel#metricTitle {{
    color: {palette['text_muted']};
    font-size: 11px;
    font-weight: 700;
}}

QFrame#panelCard, QTextBrowser, QPlainTextEdit, QLineEdit, QComboBox, QListWidget,
QTableWidget, QTreeWidget, QTabWidget::pane, QScrollArea, QGroupBox {{
    background-color: {palette['surface']};
    border: 1px solid {palette['border_soft']};
    border-radius: 14px;
}}

QTextBrowser#browserChrome {{
    background-color: {palette['surface_deep']};
    border: 1px solid {palette['border']};
    border-radius: 18px;
}}

QTextBrowser, QPlainTextEdit, QLineEdit, QComboBox, QListWidget, QTableWidget, QTreeWidget {{
    selection-background-color: {palette['accent_secondary']};
    selection-color: {palette['text_strong']};
}}

QTextBrowser, QPlainTextEdit {{
    padding: 4px;
}}

QLineEdit, QComboBox, QPlainTextEdit {{
    background-color: {palette['surface_deep']};
    padding: 10px 12px;
}}

QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus,
QTableWidget:focus, QTreeWidget:focus, QTextBrowser:focus {{
    border: 1px solid {palette['accent']};
}}

QPushButton {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['accent']},
        stop: 1 {palette['accent_secondary']}
    );
    color: {palette['text_strong']};
    border: 1px solid {palette['border']};
    border-radius: 10px;
    padding: 10px 16px;
    font-weight: 700;
}}

QPushButton:hover {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['accent_hover']},
        stop: 1 {palette['accent']}
    );
}}

QPushButton:pressed {{
    background-color: {palette['accent_pressed']};
}}

QPushButton:disabled {{
    background-color: {palette['surface_alt']};
    color: {palette['text_dim']};
    border-color: {palette['border_soft']};
}}

QPushButton#tableActionButton {{
    border-radius: 9px;
    min-width: 104px;
    padding: 6px 12px;
}}

QToolButton {{
    background-color: {palette['surface_alt']};
    border: 1px solid {palette['border_soft']};
    border-radius: 10px;
    color: {palette['text_strong']};
    font-weight: 700;
    padding: 8px 10px;
}}

QToolButton:hover {{
    border-color: {palette['border']};
}}

QToolButton#sidebarThemeToggle {{
    background-color: {palette['surface_deep']};
    border: 1px solid {palette['border']};
    border-radius: 10px;
    color: {palette['text_strong']};
    padding: 8px 12px;
}}

QToolButton#sidebarThemeToggle:hover {{
    border-color: {palette['accent']};
}}

QComboBox QAbstractItemView, QListWidget::item, QTableView {{
    background-color: {palette['surface']};
    color: {palette['text']};
}}

QHeaderView::section {{
    background-color: {palette['surface_deep']};
    color: {palette['accent_soft']};
    border: none;
    border-right: 1px solid {palette['border_soft']};
    padding: 8px;
    font-weight: 700;
}}

QTableWidget {{
    alternate-background-color: {palette['surface_deep']};
    gridline-color: {palette['border_soft']};
}}

QProgressBar {{
    background-color: {palette['surface_deep']};
    border: 1px solid {palette['border_soft']};
    border-radius: 9px;
    color: {palette['text_strong']};
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {palette['accent']};
    border-radius: 8px;
}}

QListWidget#sidebarList {{
    background: transparent;
    border: none;
    padding: 4px;
}}

QListWidget#sidebarList::item {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 12px;
    margin: 4px 0;
    padding: 12px 14px;
}}

QListWidget#sidebarList::item:hover {{
    background-color: {palette['surface_alt']};
    border-color: {palette['border_soft']};
}}

QListWidget#sidebarList::item:selected {{
    background-color: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 {palette['surface_alt']},
        stop: 1 {palette['panel_alt']}
    );
    border-color: {palette['accent']};
    color: {palette['text_strong']};
}}

QGroupBox {{
    margin-top: 14px;
    padding-top: 18px;
}}

QGroupBox::title {{
    color: {palette['accent_warm']};
    left: 12px;
    padding: 0 6px;
    subcontrol-origin: margin;
    subcontrol-position: top left;
}}

QTabBar::tab {{
    background-color: {palette['surface_alt']};
    border: 1px solid {palette['border_soft']};
    border-bottom: none;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    color: {palette['text_muted']};
    margin-right: 4px;
    padding: 10px 14px;
}}

QTabBar::tab:selected {{
    background-color: {palette['surface']};
    color: {palette['text_strong']};
    border-color: {palette['border']};
}}

QTabBar::tab:hover {{
    color: {palette['text_strong']};
}}

QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    background-color: {palette['surface_deep']};
    border: 1px solid {palette['border']};
    border-radius: 4px;
    height: 16px;
    width: 16px;
}}

QCheckBox::indicator:checked {{
    background-color: {palette['accent']};
}}

QScrollBar:vertical {{
    background: transparent;
    margin: 4px 0 4px 0;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {palette['border']};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {palette['accent_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    border: none;
}}

QStatusBar {{
    background-color: {palette['window_alt']};
    color: {palette['text_dim']};
    border-top: 1px solid {palette['border_soft']};
}}
"""


def get_html_document_css(theme: str | None = None) -> str:
    return build_html_document_css(get_palette(theme))


def get_app_stylesheet(theme: str | None = None) -> str:
    return build_app_stylesheet(get_palette(theme))


def apply_theme(app, theme: str = "dark"):
    global _ACTIVE_THEME
    selected = theme if theme in THEMES else "dark"
    _ACTIVE_THEME = selected
    if app is not None:
        app.setStyleSheet(get_app_stylesheet(selected))
