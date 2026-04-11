"""
Testes adicionais para melhorias v2.1.
Cobre: persistência, sanitizer, relatório, cenários, i18n, APIs,
datasets, resiliência de ML e timeout de WHOIS.
"""

import concurrent.futures
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


class TestAtomicWrite(unittest.TestCase):
    def test_save_and_load_history(self):
        from models import persistence

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            history_file = temp_path / "analysis_history.json"
            with mock.patch.object(persistence, "DATA_DIR", temp_path), mock.patch.object(
                persistence,
                "HISTORY_FILE",
                history_file,
            ):
                data = [{"url": "hxxps://test[.]com", "score": 50, "timestamp": 0}]
                persistence._atomic_write(history_file, data)
                loaded = persistence.load_history()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["url"], "hxxps://test[.]com")

    def test_atomic_write_creates_valid_json(self):
        from models.persistence import _atomic_write

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            path = temp_path / "test.json"
            _atomic_write(path, {"key": "value"})
            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["key"], "value")


class TestSanitizerImproved(unittest.TestCase):
    def test_token_pattern_requires_16_chars(self):
        from utils.sanitizer import sanitize_input

        result = sanitize_input("https://example.com?token=short")
        self.assertIn("short", result.sanitized_input)

    def test_long_token_is_redacted(self):
        from utils.sanitizer import sanitize_input

        long_token = "A" * 20
        result = sanitize_input(f"https://example.com?token={long_token}")
        self.assertNotIn(long_token, result.sanitized_input)

    def test_key_not_matched_without_keyword(self):
        from utils.sanitizer import sanitize_input

        result = sanitize_input("https://example.com?data=abcdef1234567890extra")
        self.assertNotIn("[REDACTED]", result.sanitized_input)


class TestReportGenerator(unittest.TestCase):
    def test_generate_report(self):
        from models.heuristic_analyzer import AnalysisResult
        from models.report_generator import ReportGenerator

        gen = ReportGenerator()
        analysis = AnalysisResult(
            score=75,
            classification="suspicious",
            classification_label="Suspeito",
            classification_emoji="🟡",
        )
        report = gen.generate("https://evil.com/login", analysis)
        self.assertNotEqual(report.url_defanged, "https://evil.com/login")
        self.assertEqual(report.score, 75)
        self.assertEqual(report.classification, "suspicious")

    def test_html_report_escapes_xss(self):
        from models.report_generator import FullReport, ReportGenerator

        gen = ReportGenerator()
        report = FullReport(
            url_defanged='<script>alert("xss")</script>',
            score=0,
            classification="malicious",
            classification_label="Malicioso",
            classification_emoji="🔴",
        )
        html = gen.format_html_report(report)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_text_report_format(self):
        from models.report_generator import FullReport, ReportGenerator

        gen = ReportGenerator()
        report = FullReport(
            url_defanged="hxxps[://]test[.]com",
            score=50,
            classification="suspicious",
            classification_label="Suspeito",
            classification_emoji="🟡",
            recommendations=["Não clique."],
        )
        text = gen.format_text_report(report)
        self.assertIn("hxxps[://]test[.]com", text)
        self.assertIn("Não clique.", text)


class TestScenariosJSON(unittest.TestCase):
    def test_scenarios_loaded_from_json(self):
        from models.scenarios import SCENARIOS, SCENARIO_CATEGORIES

        self.assertGreater(len(SCENARIOS), 0)
        self.assertGreater(len(SCENARIO_CATEGORIES), 0)

    def test_scenario_structure(self):
        from models.scenarios import SCENARIOS

        scenario = SCENARIOS[0]
        self.assertIn("id", scenario)
        self.assertIn("category", scenario)
        self.assertIn("alerts", scenario)
        self.assertIsInstance(scenario["alerts"], list)
        if scenario["alerts"]:
            self.assertIsInstance(scenario["alerts"][0], tuple)

    def test_json_file_is_valid(self):
        path = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("categories", data)
        self.assertIn("scenarios", data)
        self.assertEqual(len(data["scenarios"]), 20)


class TestI18nImproved(unittest.TestCase):
    def test_translations_loaded_from_json(self):
        from utils.i18n import set_language, tr

        set_language("pt")
        self.assertEqual(tr("app.title"), "CyberURL Analyst")

    def test_english_translation(self):
        from utils.i18n import set_language, tr

        set_language("en")
        self.assertEqual(tr("nav.analysis"), "Analysis Engine")
        set_language("pt")

    def test_spanish_translation(self):
        from utils.i18n import set_language, tr

        set_language("es")
        self.assertEqual(tr("nav.analysis"), "Motor de Análisis")
        set_language("pt")

    def test_fallback_to_key(self):
        from utils.i18n import tr

        self.assertEqual(tr("nonexistent.key"), "nonexistent.key")

    def test_thread_safety(self):
        from utils.i18n import get_language, set_language

        results = []

        def _set_and_get(lang):
            set_language(lang)
            results.append(get_language())

        threads = [
            threading.Thread(target=_set_and_get, args=(lang,))
            for lang in ["pt", "en", "es"] * 5
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertTrue(all(result in ("pt", "en", "es") for result in results))


class TestAPIClientValidation(unittest.TestCase):
    def test_virustotal_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient

        client = ThreatIntelClient()
        result = client.check_virustotal("not-a-url", api_key="fake")
        self.assertFalse(result.success)
        self.assertTrue(
            "inválida" in result.error.lower() or "invalid" in result.error.lower()
        )

    def test_urlscan_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient

        client = ThreatIntelClient()
        result = client.check_urlscan("not-a-url", api_key="fake")
        self.assertFalse(result.success)

    def test_safebrowsing_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient

        client = ThreatIntelClient()
        result = client.check_safebrowsing("not-a-url", api_key="fake")
        self.assertFalse(result.success)


class TestDatasetMemoryLimit(unittest.TestCase):
    def test_max_entries_constant_exists(self):
        from config.settings import DATASET_MAX_ENTRIES
        from models.dataset_manager import _MAX_ENTRIES

        self.assertEqual(_MAX_ENTRIES, DATASET_MAX_ENTRIES)
        self.assertEqual(_MAX_ENTRIES, 2_000_000)


class TestDatasetManagerIntegration(unittest.TestCase):
    def test_manager_matches_sample_datasets(self):
        import models.dataset_manager as dataset_manager

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            dataset_manager,
            "DATASETS_DOWNLOAD_DIR",
            Path(temp_dir),
        ):
            manager = dataset_manager.DatasetManager()
            manager.load_all()

        self.assertEqual(
            manager.match_dataset(
                "phishtank",
                url="http://paypa1.com/login",
                domain="paypa1.com",
                registered_domain="paypa1.com",
            ),
            "exact",
        )
        self.assertEqual(
            manager.match_dataset(
                "urlhaus_full",
                url="http://malware-distribution.tk/payload.exe",
                domain="malware-distribution.tk",
                registered_domain="malware-distribution.tk",
            ),
            "exact",
        )
        self.assertEqual(
            manager.match_dataset(
                "majestic",
                domain="google.com",
                registered_domain="google.com",
            ),
            "domain",
        )

    def test_checker_uses_manager_for_core_matches(self):
        import models.dataset_manager as dataset_manager
        from models.dataset_checker import DatasetChecker

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            dataset_manager,
            "DATASETS_DOWNLOAD_DIR",
            Path(temp_dir),
        ):
            checker = DatasetChecker()
            result = checker.check(
                "http://paypa1.com/login",
                "paypa1.com",
                "paypa1.com",
            )

        self.assertTrue(result.is_in_phishing_db)
        self.assertTrue(any(match.dataset_name == "PhishTank" and match.matched for match in result.matches))


class TestMLClassifierResilience(unittest.TestCase):
    def test_predict_maps_probabilities_by_class_order(self):
        from models.ml_classifier import MLClassifier

        class FakeModel:
            classes_ = [1, 0]

            def predict_proba(self, rows):
                del rows
                return [[0.85, 0.15]]

        classifier = MLClassifier()
        classifier._model = FakeModel()
        classifier._is_trained = True
        classifier._accuracy = 0.91

        result = classifier.predict("https://example.com/login")

        self.assertTrue(result.available)
        self.assertEqual(result.prediction, "malicious")
        self.assertAlmostEqual(result.probability_malicious, 0.85)
        self.assertAlmostEqual(result.probability_safe, 0.15)
        self.assertAlmostEqual(result.model_accuracy, 0.91)

    def test_load_saved_feature_order_falls_back_to_file(self):
        from models.ml_classifier import MLClassifier

        with tempfile.TemporaryDirectory() as temp_dir:
            feature_path = Path(temp_dir) / "feature_names.txt"
            feature_path.write_text("feature_a\nfeature_b\n", encoding="utf-8")
            with mock.patch("models.ml_classifier.FEATURE_NAMES_PATH", feature_path):
                classifier = MLClassifier()
                feature_order = classifier._load_saved_feature_order(None)

        self.assertEqual(feature_order, ["feature_a", "feature_b"])


class TestWhoisCheckerTimeout(unittest.TestCase):
    def test_timeout_returns_structured_result(self):
        from models.whois_checker import WhoisChecker

        class FakeFuture:
            def result(self, timeout=None):
                del timeout
                raise concurrent.futures.TimeoutError()

        class FakeExecutor:
            def __init__(self, *args, **kwargs):
                del args, kwargs

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                del exc_type, exc, tb
                return False

            def submit(self, func, domain):
                del func, domain
                return FakeFuture()

        checker = WhoisChecker()
        checker._whois_available = True
        checker._whois_module = mock.Mock()

        with mock.patch("models.whois_checker.concurrent.futures.ThreadPoolExecutor", FakeExecutor):
            result = checker.check_domain_age("example.com")

        self.assertFalse(result.success)
        self.assertEqual(result.domain, "example.com")
        self.assertIn("tempo limite", result.error.lower())


if __name__ == "__main__":
    unittest.main()
