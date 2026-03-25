"""Testes unitários para o módulo HeuristicAnalyzer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from models.url_parser import URLParser
from models.heuristic_analyzer import HeuristicAnalyzer


class TestHeuristicAnalyzer(unittest.TestCase):
    """Testes para HeuristicAnalyzer."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _analyze(self, url: str):
        components = self.parser.parse(url)
        return self.analyzer.analyze(components)

    # === Classificação ===

    def test_safe_url(self):
        result = self._analyze("https://www.google.com/search?q=python")
        self.assertEqual(result.classification, "safe")
        self.assertLessEqual(result.score, 25)

    def test_malicious_ip_url(self):
        result = self._analyze("http://192.168.45.23/paypal/login.php")
        # IP(30) + HTTP(15) + keywords(10) + php(5) = 60 → suspicious
        # Typosquatting not triggered because 'paypal' is in path, not domain
        self.assertIn(result.classification, ("suspicious", "malicious"))
        self.assertGreater(result.score, 50)

    def test_suspicious_url(self):
        result = self._analyze("https://secure-login.bancodobrasil-verify.com.br/auth")
        self.assertIn(result.classification, ("suspicious", "malicious"))
        self.assertGreater(result.score, 25)

    # === Features ===

    def test_detects_ip(self):
        components = self.parser.parse("http://192.168.1.1/login")
        features = self.analyzer.extract_features(components)
        self.assertTrue(features["is_ip"])

    def test_detects_http(self):
        components = self.parser.parse("http://example.com")
        features = self.analyzer.extract_features(components)
        self.assertTrue(features["is_http"])
        self.assertFalse(features["is_https"])

    def test_detects_trigger_words(self):
        components = self.parser.parse("https://secure-login.example.com/verify")
        features = self.analyzer.extract_features(components)
        self.assertTrue(len(features["trigger_words_found"]) > 0)

    def test_detects_shortener(self):
        components = self.parser.parse("https://bit.ly/abc123")
        features = self.analyzer.extract_features(components)
        self.assertTrue(features["is_shortener"])

    def test_detects_risky_tld(self):
        components = self.parser.parse("https://example.tk/page")
        features = self.analyzer.extract_features(components)
        self.assertTrue(features["tld_is_risky"])

    def test_detects_hyphens(self):
        components = self.parser.parse("https://my-fake-bank-login.com")
        features = self.analyzer.extract_features(components)
        self.assertGreaterEqual(features["hyphen_count"], 3)

    # === Typosquatting ===

    def test_detects_typosquatting_paypa1(self):
        components = self.parser.parse("https://paypa1.com/login")
        features = self.analyzer.extract_features(components)
        self.assertTrue(len(features["typosquatting_matches"]) > 0)

    def test_detects_typosquatting_arnazon(self):
        components = self.parser.parse("https://arnazon.com/cart")
        features = self.analyzer.extract_features(components)
        self.assertTrue(len(features["typosquatting_matches"]) > 0)

    # === Findings ===

    def test_findings_contain_explanations(self):
        result = self._analyze("http://192.168.1.1/paypal/login.php")
        for finding in result.findings:
            self.assertTrue(finding.title)
            self.assertTrue(finding.explanation)
            self.assertIn(finding.severity, ("critical", "warning", "info", "safe"))

    # === Score limites ===

    def test_score_never_exceeds_100(self):
        result = self._analyze("http://192.168.1.1/paypal-secure-login-verify.php?token=abc&redirect=evil.com")
        self.assertLessEqual(result.score, 100)

    def test_score_never_below_0(self):
        result = self._analyze("https://google.com")
        self.assertGreaterEqual(result.score, 0)


if __name__ == "__main__":
    unittest.main()
