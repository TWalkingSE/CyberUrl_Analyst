"""
Testes de integração da aplicação Streamlit usando AppTest.
Verifica que as páginas renderizam sem erros e que a navegação funciona.

Requer streamlit >= 1.28.0 (streamlit.testing.v1).
"""

import unittest
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

try:
    from streamlit.testing.v1 import AppTest
    _ST_TESTING_AVAILABLE = True
except ImportError:
    _ST_TESTING_AVAILABLE = False


@unittest.skipUnless(_ST_TESTING_AVAILABLE, "streamlit.testing não disponível")
class TestAppIntegration(unittest.TestCase):
    """Testes de integração usando streamlit.testing.v1.AppTest."""

    def _get_app(self):
        """Cria instância AppTest a partir de app.py."""
        at = AppTest.from_file(str(PROJECT_DIR / "app.py"), default_timeout=30)
        at.session_state["authenticated"] = True
        at.run()
        return at

    def test_app_loads_without_error(self):
        """Verifica que o app carrega sem exceções."""
        at = self._get_app()
        self.assertFalse(at.exception, f"App lançou exceção: {at.exception}")

    def test_dashboard_renders(self):
        """Verifica que o dashboard renderiza métricas."""
        at = self._get_app()
        # Dashboard é a página padrão
        metrics = [m.label for m in at.metric]
        self.assertTrue(
            any("Análises" in m for m in metrics),
            f"Métrica 'Análises' não encontrada. Métricas: {metrics}",
        )

    def test_sidebar_has_navigation(self):
        """Verifica que a sidebar tem o radio de navegação."""
        at = self._get_app()
        radios = at.sidebar.radio
        self.assertTrue(len(radios) > 0, "Nenhum radio de navegação na sidebar")

    def test_sidebar_has_language_selector(self):
        """Verifica que a sidebar tem o seletor de idioma."""
        at = self._get_app()
        selectboxes = at.sidebar.selectbox
        self.assertTrue(
            len(selectboxes) > 0,
            "Nenhum selectbox na sidebar",
        )


@unittest.skipUnless(_ST_TESTING_AVAILABLE, "streamlit.testing não disponível")
class TestViewsImport(unittest.TestCase):
    """Testa que todos os módulos de views importam corretamente."""

    def test_import_views_package(self):
        from views import (
            page_dashboard, page_anatomy, page_analysis, page_report,
            page_quiz, page_scenarios, page_apis, page_datasets,
            page_settings,
        )
        self.assertTrue(callable(page_dashboard))
        self.assertTrue(callable(page_anatomy))
        self.assertTrue(callable(page_analysis))
        self.assertTrue(callable(page_report))
        self.assertTrue(callable(page_quiz))
        self.assertTrue(callable(page_scenarios))
        self.assertTrue(callable(page_apis))
        self.assertTrue(callable(page_datasets))
        self.assertTrue(callable(page_settings))

    def test_import_helpers(self):
        from views.helpers import T, sev_color, sev_label, render_finding
        self.assertTrue(callable(T))
        self.assertTrue(callable(sev_color))
        self.assertTrue(callable(sev_label))

    def test_import_resources(self):
        from views.resources import (
            get_parser, get_analyzer, get_defanger,
            ML_AVAILABLE, API_AVAILABLE,
        )
        self.assertTrue(callable(get_parser))
        self.assertIsInstance(ML_AVAILABLE, bool)
        self.assertIsInstance(API_AVAILABLE, bool)

    def test_sev_color_returns_valid_colors(self):
        from views.helpers import sev_color, sev_label
        self.assertEqual(sev_color("critical"), "#F44336")
        self.assertEqual(sev_color("safe"), "#4CAF50")
        self.assertEqual(sev_color("unknown"), "#555")
        self.assertEqual(sev_label("critical"), "CRITICAL")
        self.assertEqual(sev_label("safe"), "SAFE")


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
