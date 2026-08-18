"""Desktop integration tests for the PyQt6 application."""

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from PyQt6.QtWidgets import QApplication, QWidget

from app import build_main_window, create_application


class TestAppIntegration(unittest.TestCase):
    """Smoke tests for the PyQt6 main window."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    def _get_window(self):
        state, window = build_main_window()
        self.addCleanup(window.close)
        self.addCleanup(window.deleteLater)
        self.app.processEvents()
        return state, window

    def test_app_loads_without_error(self):
        state, window = self._get_window()
        self.assertIsNotNone(state)
        self.assertEqual(window.windowTitle(), "CyberURL Analyst v3.0.0")

    def test_dashboard_is_default_page(self):
        _, window = self._get_window()
        dashboard = window.stack.widget(0)
        self.assertEqual(window.stack.currentIndex(), 0)
        self.assertEqual(dashboard.__class__.__name__, "DashboardPage")
        self.assertEqual(len(getattr(dashboard, "metric_cards", [])), 4)

    def test_sidebar_lists_all_pages(self):
        _, window = self._get_window()
        labels = [window.sidebar_list.item(index).text() for index in range(window.sidebar_list.count())]
        self.assertEqual(len(labels), 10)
        self.assertTrue(any("Gloss" in label for label in labels))

    def test_sidebar_has_language_selector(self):
        _, window = self._get_window()
        self.assertGreaterEqual(window.language_combo.count(), 3)

    def test_page_stack_matches_navigation(self):
        _, window = self._get_window()
        self.assertEqual(window.sidebar_list.count(), window.stack.count())


class TestUiImports(unittest.TestCase):
    """Checks that the desktop UI modules import cleanly."""

    def test_import_ui_pages(self):
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

        for page in [
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
        ]:
            self.assertTrue(issubclass(page, QWidget))

    def test_import_ui_helpers(self):
        from ui.helpers import T, sev_color, sev_label

        self.assertTrue(callable(T))
        self.assertEqual(sev_color("critical"), "#F44336")
        self.assertEqual(sev_color("safe"), "#4CAF50")
        self.assertEqual(sev_color("unknown"), "#555")
        self.assertEqual(sev_label("critical"), "CRITICAL")
        self.assertEqual(sev_label("safe"), "SAFE")

    def test_import_ui_resources(self):
        from ui.resources import API_AVAILABLE, ML_AVAILABLE, get_analyzer, get_defanger, get_parser

        self.assertTrue(callable(get_parser))
        self.assertTrue(callable(get_analyzer))
        self.assertTrue(callable(get_defanger))
        self.assertIsInstance(ML_AVAILABLE, bool)
        self.assertIsInstance(API_AVAILABLE, bool)

    def test_glossary_data_loaded(self):
        from ui.glossary_data import GLOSSARY, GLOSSARY_CATEGORIES

        self.assertGreater(len(GLOSSARY), 0)
        self.assertGreater(len(GLOSSARY_CATEGORIES), 0)


class TestRateLimiter(unittest.TestCase):
    """Testa o rate limiter usado nas APIs."""

    def test_rate_limiter_allows_requests(self):
        from utils.rate_limiter import RateLimiter, RateLimitConfig
        rl = RateLimiter()
        rl.register_service("test", RateLimitConfig(
            requests_per_minute=2, requests_per_day=10,
        ))
        self.assertTrue(rl.can_make_request("test"))
        rl.record_request("test")
        rl.record_request("test")
        self.assertFalse(rl.can_make_request("test"))

    def test_rate_limiter_unknown_service(self):
        from utils.rate_limiter import RateLimiter
        rl = RateLimiter()
        self.assertTrue(rl.can_make_request("unknown"))


if __name__ == "__main__":
    unittest.main()
