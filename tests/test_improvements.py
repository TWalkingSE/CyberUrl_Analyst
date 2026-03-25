"""
Testes adicionais para melhorias v2.1.
Cobre: persistence (atomic writes), sanitizer, report_generator, scenarios, i18n.
"""

import json
import threading
from pathlib import Path


# ── Persistence (atomic write) ──

class TestAtomicWrite:
    def test_save_and_load_history(self):
        from models.persistence import _atomic_write, load_history, HISTORY_FILE
        # Backup
        backup = None
        if HISTORY_FILE.exists():
            backup = HISTORY_FILE.read_text(encoding="utf-8")
        try:
            data = [{"url": "hxxps://test[.]com", "score": 50, "timestamp": 0}]
            _atomic_write(HISTORY_FILE, data)
            loaded = load_history()
            assert len(loaded) >= 1
            assert loaded[-1]["url"] == "hxxps://test[.]com"
        finally:
            if backup is not None:
                HISTORY_FILE.write_text(backup, encoding="utf-8")

    def test_atomic_write_creates_valid_json(self, tmp_path):
        from models.persistence import _atomic_write
        path = tmp_path / "test.json"
        _atomic_write(path, {"key": "value"})
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["key"] == "value"


# ── Sanitizer ──

class TestSanitizerImproved:
    def test_token_pattern_requires_16_chars(self):
        from utils.sanitizer import sanitize_input
        # Short tokens should NOT be redacted
        result = sanitize_input("https://example.com?token=short")
        assert "short" in result.sanitized_input

    def test_long_token_is_redacted(self):
        from utils.sanitizer import sanitize_input
        long_token = "A" * 20
        result = sanitize_input(f"https://example.com?token={long_token}")
        assert long_token not in result.sanitized_input

    def test_key_not_matched_without_keyword(self):
        from utils.sanitizer import sanitize_input
        result = sanitize_input("https://example.com?data=abcdef1234567890extra")
        assert "[REDACTED]" not in result.sanitized_input


# ── Report Generator ──

class TestReportGenerator:
    def test_generate_report(self):
        from models.report_generator import ReportGenerator
        from models.heuristic_analyzer import AnalysisResult
        gen = ReportGenerator()
        analysis = AnalysisResult(
            score=75,
            classification="suspicious",
            classification_label="Suspeito",
            classification_emoji="🟡",
        )
        report = gen.generate("https://evil.com/login", analysis)
        assert report.url_defanged != "https://evil.com/login"
        assert report.score == 75
        assert report.classification == "suspicious"

    def test_html_report_escapes_xss(self):
        from models.report_generator import ReportGenerator, FullReport
        gen = ReportGenerator()
        report = FullReport(
            url_defanged='<script>alert("xss")</script>',
            score=0,
            classification="malicious",
            classification_label="Malicioso",
            classification_emoji="🔴",
        )
        html = gen.format_html_report(report)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_text_report_format(self):
        from models.report_generator import ReportGenerator, FullReport
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
        assert "hxxps[://]test[.]com" in text
        assert "Não clique." in text


# ── Scenarios (JSON loader) ──

class TestScenariosJSON:
    def test_scenarios_loaded_from_json(self):
        from models.scenarios import SCENARIOS, SCENARIO_CATEGORIES
        assert len(SCENARIOS) > 0
        assert len(SCENARIO_CATEGORIES) > 0

    def test_scenario_structure(self):
        from models.scenarios import SCENARIOS
        scenario = SCENARIOS[0]
        assert "id" in scenario
        assert "category" in scenario
        assert "alerts" in scenario
        assert isinstance(scenario["alerts"], list)
        # alerts should be tuples after loading
        if scenario["alerts"]:
            assert isinstance(scenario["alerts"][0], tuple)

    def test_json_file_is_valid(self):
        path = Path(__file__).resolve().parent.parent / "data" / "scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "categories" in data
        assert "scenarios" in data
        assert len(data["scenarios"]) == 20


# ── i18n (JSON + thread-safe) ──

class TestI18nImproved:
    def test_translations_loaded_from_json(self):
        from utils.i18n import tr, set_language
        set_language("pt")
        assert tr("app.title") == "CyberURL Analyst"

    def test_english_translation(self):
        from utils.i18n import tr, set_language
        set_language("en")
        assert tr("nav.analysis") == "Analysis Engine"
        set_language("pt")  # reset

    def test_spanish_translation(self):
        from utils.i18n import tr, set_language
        set_language("es")
        assert tr("nav.analysis") == "Motor de Análisis"
        set_language("pt")

    def test_fallback_to_key(self):
        from utils.i18n import tr
        assert tr("nonexistent.key") == "nonexistent.key"

    def test_thread_safety(self):
        from utils.i18n import set_language, get_language
        results = []

        def _set_and_get(lang):
            set_language(lang)
            results.append(get_language())

        threads = [threading.Thread(target=_set_and_get, args=(l,))
                    for l in ["pt", "en", "es"] * 5]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All results should be valid languages
        assert all(r in ("pt", "en", "es") for r in results)


# ── API Client (URL validation) ──

class TestAPIClientValidation:
    def test_virustotal_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient
        client = ThreatIntelClient()
        result = client.check_virustotal("not-a-url", api_key="fake")
        assert not result.success
        assert "inválida" in result.error.lower() or "invalid" in result.error.lower()

    def test_urlscan_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient
        client = ThreatIntelClient()
        result = client.check_urlscan("not-a-url", api_key="fake")
        assert not result.success

    def test_safebrowsing_rejects_invalid_url(self):
        from models.api_client import ThreatIntelClient
        client = ThreatIntelClient()
        result = client.check_safebrowsing("not-a-url", api_key="fake")
        assert not result.success


# ── Dataset manager (memory limits) ──

class TestDatasetMemoryLimit:
    def test_max_entries_constant_exists(self):
        from models.dataset_manager import _MAX_ENTRIES
        assert _MAX_ENTRIES == 2_000_000
