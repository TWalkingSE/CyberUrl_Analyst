"""Testes unitários para o módulo URLDefanger."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from models.defanger import URLDefanger


class TestURLDefanger(unittest.TestCase):
    """Testes para URLDefanger."""

    def setUp(self):
        self.defanger = URLDefanger()

    # === defang ===

    def test_defang_https(self):
        result = self.defanger.defang("https://example.com/path")
        self.assertEqual(result, "hxxps[://]example[.]com/path")

    def test_defang_http(self):
        result = self.defanger.defang("http://example.com")
        self.assertEqual(result, "hxxp[://]example[.]com")

    def test_defang_preserves_path_dots(self):
        result = self.defanger.defang("https://example.com/file.php?id=1")
        self.assertIn("[.]com", result)
        self.assertIn("/file.php", result)

    def test_defang_ip_address(self):
        result = self.defanger.defang("http://192.168.1.1/login")
        self.assertEqual(result, "hxxp[://]192[.]168[.]1[.]1/login")

    def test_defang_subdomain(self):
        result = self.defanger.defang("https://www.sub.example.com/page")
        self.assertIn("hxxps[://]", result)
        self.assertIn("[.]", result)

    def test_defang_empty(self):
        self.assertEqual(self.defanger.defang(""), "")

    def test_defang_none_like_empty(self):
        self.assertEqual(self.defanger.defang(""), "")

    # === refang ===

    def test_refang_basic(self):
        defanged = "hxxps[://]example[.]com/path"
        result = self.defanger.refang(defanged)
        self.assertEqual(result, "https://example.com/path")

    def test_refang_http(self):
        defanged = "hxxp[://]example[.]com"
        result = self.defanger.refang(defanged)
        self.assertEqual(result, "http://example.com")

    def test_refang_empty(self):
        self.assertEqual(self.defanger.refang(""), "")

    # === roundtrip ===

    def test_roundtrip(self):
        original = "https://www.example.com/page"
        defanged = self.defanger.defang(original)
        refanged = self.defanger.refang(defanged)
        self.assertEqual(refanged, original)

    # === is_defanged ===

    def test_is_defanged_true(self):
        self.assertTrue(self.defanger.is_defanged("hxxps[://]example[.]com"))

    def test_is_defanged_false(self):
        self.assertFalse(self.defanger.is_defanged("https://example.com"))

    def test_is_defanged_partial(self):
        self.assertTrue(self.defanger.is_defanged("example[.]com"))


if __name__ == "__main__":
    unittest.main()
