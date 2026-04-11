"""Application state shared across PyQt6 pages."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from models.persistence import (
    add_history_entry,
    load_badges,
    load_history,
    load_progress,
    load_stats,
    load_ui_preferences,
    save_stats,
    save_ui_preferences,
    unlock_badge,
)
from utils.i18n import get_language, set_language


class AppState(QObject):
    """Central runtime state used by the desktop interface."""

    changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        persisted = load_stats()
        ui_preferences = load_ui_preferences()
        self.analysis_count = persisted.get("analysis_count", 0)
        self.safe_count = persisted.get("safe_count", 0)
        self.suspicious_count = persisted.get("suspicious_count", 0)
        self.malicious_count = persisted.get("malicious_count", 0)
        self.session_history: list[dict] = []
        self.last_report = None
        self.consent_given = False
        self.authenticated = False
        self.onboarding_dismissed = False
        self.lang = get_language() or "pt"
        self.theme = ui_preferences.get("theme", "dark")
        set_language(self.lang)

    def set_language(self, lang: str):
        if not lang or lang == self.lang:
            return
        self.lang = lang
        set_language(lang)
        self.changed.emit("language")

    def set_theme(self, theme: str):
        if theme not in {"dark", "light"} or theme == self.theme:
            return
        self.theme = theme
        save_ui_preferences({"theme": theme})
        self.changed.emit("theme")

    def set_authenticated(self, authenticated: bool):
        if self.authenticated == authenticated:
            return
        self.authenticated = authenticated
        self.changed.emit("auth")

    def set_consent_given(self, consent_given: bool):
        if self.consent_given == consent_given:
            return
        self.consent_given = consent_given
        self.changed.emit("consent")

    def set_last_report(self, report):
        self.last_report = report
        self.changed.emit("report")

    def record_analysis(self, raw_url: str, report):
        self.last_report = report
        self.analysis_count += 1
        if report.classification == "safe":
            self.safe_count += 1
        elif report.classification == "suspicious":
            self.suspicious_count += 1
        elif report.classification == "malicious":
            self.malicious_count += 1

        save_stats(
            {
                "analysis_count": self.analysis_count,
                "safe_count": self.safe_count,
                "suspicious_count": self.suspicious_count,
                "malicious_count": self.malicious_count,
            }
        )

        count = self.analysis_count
        if count == 1:
            unlock_badge("first_analysis")
        if count >= 10:
            unlock_badge("ten_analyses")
        if count >= 50:
            unlock_badge("fifty_analyses")

        entry = add_history_entry(
            report.url_defanged,
            report.classification,
            report.classification_emoji,
            report.score,
        )
        self.session_history.insert(
            0,
            {
                "url": report.url_defanged[:80],
                "classification": report.classification,
                "emoji": report.classification_emoji,
                "report": report,
                "raw_url": raw_url,
            },
        )
        self.changed.emit("analysis")
        return entry

    def get_persistent_history(self) -> list[dict]:
        return load_history()

    def get_progress(self) -> dict:
        return load_progress()

    def get_badges(self) -> list[str]:
        return load_badges()

    def get_stats(self) -> dict:
        return {
            "analysis_count": self.analysis_count,
            "safe_count": self.safe_count,
            "suspicious_count": self.suspicious_count,
            "malicious_count": self.malicious_count,
        }