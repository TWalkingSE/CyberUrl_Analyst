"""Testes unitários para as features v1.1 do HeuristicAnalyzer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from models.url_parser import URLParser
from models.heuristic_analyzer import HeuristicAnalyzer
from models.analysis_cache import AnalysisCache


class TestBrandInPath(unittest.TestCase):
    """Testes para detecção de marca no path."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_paypal_in_path_of_ip(self):
        f = self._features("http://192.168.1.1/paypal/login")
        self.assertEqual(f["brand_in_path"], "paypal")

    def test_netflix_in_path_of_unknown_domain(self):
        f = self._features("http://evil.com/netflix/login")
        self.assertEqual(f["brand_in_path"], "netflix")

    def test_no_brand_if_domain_matches(self):
        f = self._features("https://paypal.com/paypal/account")
        self.assertEqual(f["brand_in_path"], "")

    def test_no_brand_in_clean_path(self):
        f = self._features("https://example.com/about")
        self.assertEqual(f["brand_in_path"], "")

    def test_brand_in_path_generates_finding(self):
        result = self.analyzer.analyze(self.parser.parse("http://192.168.1.1/paypal/login"))
        factors = [f.factor for f in result.findings]
        self.assertIn("brand_in_path", factors)


class TestBrandAsSubdomain(unittest.TestCase):
    """Testes para detecção de marca como subdomínio."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_paypal_subdomain_evil_domain(self):
        f = self._features("https://paypal.evil-site.com/login")
        self.assertEqual(f["brand_as_subdomain"], "paypal")

    def test_google_subdomain(self):
        f = self._features("https://google.phishing-site.xyz/auth")
        self.assertEqual(f["brand_as_subdomain"], "google")

    def test_no_alert_if_legitimate_domain(self):
        f = self._features("https://mail.google.com/inbox")
        self.assertEqual(f["brand_as_subdomain"], "")

    def test_generates_finding(self):
        result = self.analyzer.analyze(self.parser.parse("https://netflix.attacker.xyz/login"))
        factors = [f.factor for f in result.findings]
        self.assertIn("brand_as_subdomain", factors)


class TestURLEncodingAbuse(unittest.TestCase):
    """Testes para detecção de URL encoding abusivo."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_normal_url_low_encoding(self):
        f = self._features("https://example.com/path")
        self.assertLessEqual(f["percent_encoding_count"], 5)

    def test_high_encoding(self):
        url = "https://evil.com/%70%61%79%70%61%6C/%6C%6F%67%69%6E"
        f = self._features(url)
        self.assertGreater(f["percent_encoding_count"], 5)

    def test_decoded_url_available(self):
        url = "https://evil.com/%70ath"
        f = self._features(url)
        self.assertIn("decoded_url", f)


class TestBase64Detection(unittest.TestCase):
    """Testes para detecção de Base64 em query strings."""

    def setUp(self):
        self.analyzer = HeuristicAnalyzer()

    def test_detect_base64_in_query(self):
        import base64
        payload = base64.b64encode(b"https://evil.com/steal-data").decode()
        found = self.analyzer._detect_base64(f"data={payload}")
        self.assertTrue(len(found) > 0)

    def test_no_false_positive_short_strings(self):
        found = self.analyzer._detect_base64("q=python&page=1")
        self.assertEqual(len(found), 0)


class TestDGADetection(unittest.TestCase):
    """Testes para detecção de DGA no domínio."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_random_domain_detected(self):
        f = self._features("http://xk4m9z2q1abc.com/page")
        self.assertTrue(f["is_dga_domain"])

    def test_legitimate_domain_not_flagged(self):
        f = self._features("https://google.com/search")
        self.assertFalse(f["is_dga_domain"])

    def test_short_domain_not_flagged(self):
        f = self._features("https://abc.com")
        self.assertFalse(f["is_dga_domain"])


class TestDoubleExtension(unittest.TestCase):
    """Testes para detecção de extensão dupla."""

    def setUp(self):
        self.analyzer = HeuristicAnalyzer()

    def test_pdf_exe(self):
        result = self.analyzer._detect_double_extension("/downloads/nota.pdf.exe")
        self.assertIsNotNone(result)
        self.assertEqual(result, (".pdf", ".exe"))

    def test_doc_js(self):
        result = self.analyzer._detect_double_extension("/file/invoice.doc.js")
        self.assertIsNotNone(result)

    def test_normal_extension(self):
        result = self.analyzer._detect_double_extension("/page/file.pdf")
        self.assertIsNone(result)

    def test_no_extension(self):
        result = self.analyzer._detect_double_extension("/about")
        self.assertIsNone(result)


class TestOpenRedirect(unittest.TestCase):
    """Testes para detecção de open redirect."""

    def setUp(self):
        self.analyzer = HeuristicAnalyzer()

    def test_redirect_param_with_url(self):
        params = {"redirect": ["https://evil.com/steal"]}
        result = self.analyzer._detect_open_redirect(params)
        self.assertEqual(result, "redirect")

    def test_next_param(self):
        params = {"next": ["https://phishing.com/login"]}
        result = self.analyzer._detect_open_redirect(params)
        self.assertEqual(result, "next")

    def test_no_redirect(self):
        params = {"q": ["python"], "page": ["1"]}
        result = self.analyzer._detect_open_redirect(params)
        self.assertEqual(result, "")

    def test_empty_params(self):
        result = self.analyzer._detect_open_redirect({})
        self.assertEqual(result, "")


class TestKeyboardTyposquatting(unittest.TestCase):
    """Testes para detecção de typosquatting por proximidade de teclado."""

    def setUp(self):
        self.analyzer = HeuristicAnalyzer()

    def test_goofle_detected(self):
        # 'f' is neighbor of 'g' on QWERTY — but 'goofle' changes 'g' to 'f' at pos 3
        # Actually: google → goofle: 'g'→'f' at index 3 ('g' neighbor includes 'f')
        matches = self.analyzer._detect_keyboard_typosquatting("googke")
        # 'l' neighbor includes 'k', so googke should match google
        has_google = any(b == "google" for b, _ in matches)
        self.assertTrue(has_google)

    def test_legitimate_domain_no_match(self):
        matches = self.analyzer._detect_keyboard_typosquatting("example")
        self.assertEqual(len(matches), 0)

    def test_exact_brand_no_match(self):
        matches = self.analyzer._detect_keyboard_typosquatting("google")
        self.assertEqual(len(matches), 0)


class TestDataURI(unittest.TestCase):
    """Testes para detecção de Data URI."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_data_uri_detected(self):
        f = self._features("data:text/html,<script>alert(1)</script>")
        self.assertTrue(f["is_data_uri"])

    def test_javascript_detected(self):
        f = self._features("javascript:alert(document.cookie)")
        self.assertTrue(f["is_data_uri"])

    def test_normal_url_not_flagged(self):
        f = self._features("https://example.com")
        self.assertFalse(f["is_data_uri"])


class TestSuspiciousPort(unittest.TestCase):
    """Testes para detecção de portas suspeitas."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_port_8080(self):
        f = self._features("http://example.com:8080/page")
        self.assertTrue(f["is_suspicious_port"])

    def test_standard_port_not_flagged(self):
        f = self._features("https://example.com/page")
        self.assertFalse(f["is_suspicious_port"])


class TestConfidenceScore(unittest.TestCase):
    """Testes para score de confiança nos findings."""

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def test_findings_have_confidence(self):
        result = self.analyzer.analyze(self.parser.parse("http://192.168.1.1/paypal/login"))
        for finding in result.findings:
            self.assertGreaterEqual(finding.confidence, 0.0)
            self.assertLessEqual(finding.confidence, 1.0)


class TestAnalysisCache(unittest.TestCase):
    """Testes para o cache de análise."""

    def test_cache_miss(self):
        cache = AnalysisCache()
        result = cache.get("https://example.com")
        self.assertIsNone(result)

    def test_cache_hit(self):
        cache = AnalysisCache()
        cache.put("https://example.com", {"score": 10})
        result = cache.get("https://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result["score"], 10)

    def test_cache_lru_eviction(self):
        cache = AnalysisCache(max_size=3)
        cache.put("url1", "report1")
        cache.put("url2", "report2")
        cache.put("url3", "report3")
        cache.put("url4", "report4")  # Should evict url1
        self.assertIsNone(cache.get("url1"))
        self.assertIsNotNone(cache.get("url4"))

    def test_cache_clear(self):
        cache = AnalysisCache()
        cache.put("url1", "report1")
        cache.clear()
        self.assertIsNone(cache.get("url1"))

    def test_cache_stats(self):
        cache = AnalysisCache()
        cache.put("url1", "report1")
        cache.get("url1")  # hit
        cache.get("url2")  # miss
        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)


class TestExpandedHomoglyphs(unittest.TestCase):
    """Testes para tabela expandida de homógrafos."""

    def setUp(self):
        self.analyzer = HeuristicAnalyzer()

    def test_cyrillic_a_detected(self):
        found = self.analyzer._detect_homoglyphs("аpple")  # Cyrillic 'а'
        self.assertTrue(len(found) > 0)

    def test_greek_omicron_detected(self):
        found = self.analyzer._detect_homoglyphs("gοοgle")  # Greek 'ο'
        self.assertTrue(len(found) > 0)

    def test_ascii_not_detected(self):
        found = self.analyzer._detect_homoglyphs("google")
        self.assertEqual(len(found), 0)


if __name__ == "__main__":
    unittest.main()
