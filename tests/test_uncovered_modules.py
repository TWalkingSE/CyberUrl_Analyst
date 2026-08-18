"""
Cobertura para os módulos que não tinham nenhum teste.

Antes desta suíte, `utils/dataset_downloader.py`, `utils/logger.py`,
`ui/state.py`, `ui/theme.py`, `ui/widgets.py` e `ui/workers.py` não eram
exercitados por teste nenhum — quebrá-los não acusava falha em lugar algum.

São testes de contrato e de comportamento observável, sem rede: o
downloader é exercitado com `requests` mockado.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
import unittest
from unittest import mock

from PyQt6.QtWidgets import QApplication

# Uma única QApplication para todos os testes de widget.
_app = QApplication.instance() or QApplication([])


# =====================================================================
# utils/logger.py
# =====================================================================
class TestLogger(unittest.TestCase):
    def test_setup_logger_is_idempotent(self):
        from utils.logger import setup_logger

        first = setup_logger("teste_idempotente")
        handlers_after_first = len(first.handlers)
        second = setup_logger("teste_idempotente")

        self.assertIs(first, second)
        self.assertEqual(len(second.handlers), handlers_after_first)

    def test_log_analysis_records_hash_never_raw_url(self):
        """A promessa de privacidade do README: log guarda hash, não a URL."""
        from utils.logger import log_analysis
        from utils.sanitizer import hash_url

        url = "https://banco-falso.tk/login?cpf=12345678900"
        logger = mock.Mock(spec=logging.Logger)

        log_analysis(logger, url, "malicious", 88)

        logger.info.assert_called_once()
        args = logger.info.call_args.args
        rendered = args[0] % args[1:]

        self.assertIn(hash_url(url), rendered)
        self.assertNotIn("banco-falso.tk", rendered)
        self.assertNotIn("12345678900", rendered)

    def test_log_api_call_reports_both_outcomes(self):
        from utils.logger import log_api_call

        logger = mock.Mock(spec=logging.Logger)
        log_api_call(logger, "VirusTotal", True, "3/70")
        log_api_call(logger, "VirusTotal", False, "HTTP 429")

        rendered = [
            call.args[0] % call.args[1:] for call in logger.info.call_args_list
        ]
        self.assertIn("sucesso", rendered[0])
        self.assertIn("falha", rendered[1])

    def test_log_security_event_uses_warning(self):
        from utils.logger import log_security_event

        logger = mock.Mock(spec=logging.Logger)
        log_security_event(logger, "INPUT", "dados sensíveis detectados")

        logger.warning.assert_called_once()


# =====================================================================
# ui/theme.py
# =====================================================================
class TestTheme(unittest.TestCase):
    REQUIRED_KEYS = [
        "success", "success_bg", "warning", "warning_bg",
        "danger", "danger_bg", "info", "info_bg",
        "text_muted", "neutral_bg",
    ]

    def test_both_palettes_define_every_key_used_by_helpers(self):
        from ui.theme import get_palette

        for theme in ("dark", "light"):
            palette = get_palette(theme)
            for key in self.REQUIRED_KEYS:
                self.assertIn(key, palette, f"'{key}' ausente no tema {theme}")

    def test_palettes_differ_between_themes(self):
        from ui.theme import get_palette

        self.assertNotEqual(get_palette("dark"), get_palette("light"))

    def test_apply_theme_sets_active_theme(self):
        from ui.theme import apply_theme, get_active_theme

        apply_theme(_app, "light")
        self.assertEqual(get_active_theme(), "light")
        apply_theme(_app, "dark")
        self.assertEqual(get_active_theme(), "dark")

    def test_stylesheet_generation_is_non_empty(self):
        from ui.theme import get_app_stylesheet, get_html_document_css

        for theme in ("dark", "light"):
            self.assertGreater(len(get_app_stylesheet(theme)), 100)
            self.assertGreater(len(get_html_document_css(theme)), 50)


# =====================================================================
# ui/state.py
# =====================================================================
class TestAppState(unittest.TestCase):
    def _state(self):
        from ui.state import AppState

        return AppState()

    def test_theme_change_emits_signal_once(self):
        state = self._state()
        received = []
        state.changed.connect(received.append)

        state.theme = "dark"
        with mock.patch("ui.state.save_ui_preferences"):
            state.set_theme("light")
            state.set_theme("light")  # idempotente: não deve reemitir

        self.assertEqual(received.count("theme"), 1)
        self.assertEqual(state.theme, "light")

    def test_consent_and_auth_flags_emit(self):
        state = self._state()
        received = []
        state.changed.connect(received.append)

        state.set_consent_given(True)
        state.set_authenticated(True)

        self.assertTrue(state.consent_given)
        self.assertTrue(state.authenticated)
        self.assertIn("consent", received)

    def test_set_language_ignores_empty_and_same(self):
        state = self._state()
        received = []
        state.changed.connect(received.append)
        original = state.lang

        state.set_language("")
        state.set_language(original)

        self.assertEqual(received.count("language"), 0)


# =====================================================================
# ui/widgets.py
# =====================================================================
class TestWidgets(unittest.TestCase):
    def test_metric_card_updates_value(self):
        from ui.widgets import MetricCard

        card = MetricCard("Análises", "0")
        card.set_value("42")

        self.assertIn("42", card.value_label.text())

    def test_collapsible_section_toggles(self):
        from ui.widgets import CollapsibleSection

        section = CollapsibleSection("Detalhes")
        self.assertFalse(section._expanded)

        section._handle_toggle(True)
        self.assertTrue(section._expanded)

        section._handle_toggle(False)
        self.assertFalse(section._expanded)

    def test_collapsible_section_starts_expanded_when_asked(self):
        from ui.widgets import CollapsibleSection

        self.assertTrue(CollapsibleSection("Detalhes", expanded=True)._expanded)

    def test_section_header_sets_title(self):
        from ui.widgets import SectionHeader

        header = SectionHeader("Antes")
        header.set_title("Depois")

        self.assertEqual(header.title_label.text(), "Depois")

    def test_browsers_instantiate_without_error(self):
        from ui.widgets import BrowserBarWidget, ReportViewer, ThemedTextBrowser

        for factory in (BrowserBarWidget, ReportViewer, ThemedTextBrowser):
            widget = factory()
            widget.setHtml("<p>ok</p>")
            self.assertIn("ok", widget.toPlainText())


# =====================================================================
# ui/workers.py
# =====================================================================
class TestFunctionWorker(unittest.TestCase):
    def _run(self, worker):
        """Executa o worker e devolve (resultados, erros)."""
        results, errors = [], []
        worker.result_ready.connect(results.append)
        worker.error.connect(errors.append)
        worker.start()
        worker.wait(10_000)
        _app.processEvents()
        return results, errors

    def test_emits_result_on_success(self):
        from ui.workers import FunctionWorker

        results, errors = self._run(FunctionWorker(lambda a, b: a + b, 2, 3))

        self.assertEqual(results, [5])
        self.assertEqual(errors, [])

    def test_emits_error_instead_of_raising(self):
        from ui.workers import FunctionWorker

        def explode():
            raise ValueError("falhou de proposito")

        results, errors = self._run(FunctionWorker(explode))

        self.assertEqual(results, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("ValueError", errors[0])
        self.assertIn("falhou de proposito", errors[0])

    def test_progress_callback_is_injected_when_requested(self):
        from ui.workers import FunctionWorker

        def with_progress(progress_callback=None):
            progress_callback(50, "metade")
            return "pronto"

        worker = FunctionWorker(with_progress, use_progress=True)
        updates = []
        worker.progress.connect(lambda pct, msg: updates.append((pct, msg)))
        results, errors = self._run(worker)

        self.assertEqual(results, ["pronto"])
        self.assertEqual(errors, [])
        self.assertIn((50, "metade"), updates)

    def test_progress_tolerates_bare_percent(self):
        """_emit_progress precisa aceitar callback só com o percentual."""
        from ui.workers import FunctionWorker

        def with_progress(progress_callback=None):
            progress_callback(10)
            return "ok"

        worker = FunctionWorker(with_progress, use_progress=True)
        updates = []
        worker.progress.connect(lambda pct, msg: updates.append((pct, msg)))
        self._run(worker)

        self.assertIn((10, ""), updates)


# =====================================================================
# utils/dataset_downloader.py
# =====================================================================
class TestDatasetDownloader(unittest.TestCase):
    def test_unknown_dataset_is_rejected(self):
        from utils.dataset_downloader import DatasetDownloader

        result = DatasetDownloader().download("nao_existe")

        self.assertFalse(result.success)
        self.assertTrue(result.error)

    def test_manual_dataset_is_not_downloaded(self):
        """Datasets marcados como manual não devem tentar baixar nada."""
        from utils.dataset_downloader import DatasetDownloader

        with mock.patch("utils.dataset_downloader.requests.get") as fake_get:
            result = DatasetDownloader().download("phiusiil")

        fake_get.assert_not_called()
        self.assertFalse(result.success)

    def test_dataset_requiring_key_fails_without_key(self):
        from utils.dataset_downloader import DatasetDownloader

        with mock.patch("utils.dataset_downloader.requests.get") as fake_get:
            result = DatasetDownloader().download("phishtank", api_key="")

        fake_get.assert_not_called()
        self.assertFalse(result.success)

    def test_get_local_status_covers_registry(self):
        from config.settings import DATASET_REGISTRY
        from utils.dataset_downloader import DatasetDownloader

        status = DatasetDownloader().get_local_status()

        self.assertEqual(set(status.keys()), set(DATASET_REGISTRY.keys()))
        for entry in status.values():
            self.assertIn("exists", entry)

    def test_get_file_path_returns_none_for_unknown(self):
        from utils.dataset_downloader import DatasetDownloader

        self.assertIsNone(DatasetDownloader().get_file_path("nao_existe"))


if __name__ == "__main__":
    unittest.main()
