"""Reusable widgets used by the PyQt6 pages."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ui.helpers import build_browser_bar_html, html_document, render_report_html


class ThemedTextBrowser(QTextBrowser):
    """Text browser that wraps fragments with the application HTML theme."""

    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self._compact = compact
        self.setObjectName("panelCard")
        self.setOpenExternalLinks(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.document().setDocumentMargin(0)

    def setHtml(self, text: str):
        markup = text or ""
        if "<html" not in markup.lower():
            markup = html_document(markup, compact=self._compact)
        super().setHtml(markup)


class MetricCard(QFrame):
    """Simple dashboard metric card."""

    def __init__(self, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("metricTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_title(self, title: str):
        self.title_label.setText(title)


class BrowserBarWidget(ThemedTextBrowser):
    """Visual browser bar simulator."""

    def __init__(self, parent=None):
        super().__init__(parent, compact=True)
        self.setObjectName("browserChrome")
        self.setMaximumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def set_url(self, url: str):
        self.setHtml(build_browser_bar_html(url))


class ReportViewer(ThemedTextBrowser):
    """HTML report preview widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def set_report(self, report):
        self.setHtml(render_report_html(report))


class CollapsibleSection(QWidget):
    """Simple collapsible panel used in datasets and settings pages."""

    def __init__(self, title: str, parent=None, expanded: bool = False):
        super().__init__(parent)
        self._expanded = expanded
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)

        self._toggle = QToolButton(self)
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(expanded)
        self._toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._toggle.clicked.connect(self._handle_toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._toggle)
        layout.addWidget(self._content)

        self._content.setVisible(expanded)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def set_title(self, title: str):
        self._toggle.setText(title)

    def _handle_toggle(self, checked: bool):
        self._expanded = checked
        self._toggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )
        self._content.setVisible(checked)


class SectionHeader(QWidget):
    """Small title row with optional right-side widget area."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

    def set_title(self, title: str):
        self.title_label.setText(title)