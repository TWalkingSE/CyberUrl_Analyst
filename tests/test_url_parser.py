"""Testes unitários para o módulo URLParser."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from models.url_parser import URLParser


class TestURLParser(unittest.TestCase):
    """Testes para URLParser."""

    def setUp(self):
        self.parser = URLParser()

    def test_parse_full_url(self):
        comp = self.parser.parse("https://www.example.com/path?q=test#section")
        self.assertEqual(comp.scheme, "https")
        self.assertEqual(comp.subdomain, "www")
        self.assertEqual(comp.domain, "example")
        self.assertEqual(comp.tld, "com")
        self.assertEqual(comp.path, "/path")
        self.assertEqual(comp.query, "q=test")
        self.assertEqual(comp.fragment, "section")
        self.assertFalse(comp.is_ip)

    def test_parse_ip_url(self):
        comp = self.parser.parse("http://192.168.1.1/login")
        self.assertTrue(comp.is_ip)
        self.assertEqual(comp.ip_address, "192.168.1.1")
        self.assertEqual(comp.scheme, "http")
        self.assertEqual(comp.path, "/login")

    def test_parse_no_scheme(self):
        comp = self.parser.parse("example.com/page")
        self.assertEqual(comp.scheme, "https")
        self.assertEqual(comp.domain, "example")

    def test_parse_with_port(self):
        comp = self.parser.parse("http://example.com:8080/path")
        self.assertEqual(comp.port, "8080")

    def test_parse_empty(self):
        comp = self.parser.parse("")
        self.assertEqual(comp.raw_url, "")
        self.assertEqual(comp.scheme, "")

    def test_parse_com_br_tld(self):
        comp = self.parser.parse("https://www.bb.com.br/portal")
        self.assertEqual(comp.domain, "bb")
        self.assertEqual(comp.tld, "com.br")
        self.assertEqual(comp.subdomain, "www")

    def test_visual_breakdown_returns_parts(self):
        parts = self.parser.get_visual_breakdown("https://www.google.com/search?q=test")
        self.assertTrue(len(parts) > 0)
        types = [p.part_type for p in parts]
        self.assertIn("scheme", types)
        self.assertIn("domain", types)

    def test_visual_breakdown_ip(self):
        parts = self.parser.get_visual_breakdown("http://192.168.1.1/login")
        types = [p.part_type for p in parts]
        self.assertIn("domain", types)

    def test_visual_breakdown_empty(self):
        parts = self.parser.get_visual_breakdown("")
        self.assertEqual(parts, [])


if __name__ == "__main__":
    unittest.main()
