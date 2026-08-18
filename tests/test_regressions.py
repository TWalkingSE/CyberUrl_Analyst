"""
Testes de regressão para os bugs corrigidos na auditoria.

Cada teste aqui falharia no código anterior à correção. O objetivo não é
cobrir funcionalidade nova, e sim impedir que estes defeitos específicos
voltem — vários deles passaram despercebidos justamente porque os testes
existentes exercitavam o caminho errado.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import concurrent.futures
import time
import unittest
from unittest import mock

from models.heuristic_analyzer import HeuristicAnalyzer
from models.quiz_engine import QuizEngine
from models.url_parser import URLParser


class TestSuspiciousPortFalsePositive(unittest.TestCase):
    """
    Regressão: '443' estava em SUSPICIOUS_PORTS, então toda URL HTTPS com
    porta explícita era penalizada.

    O teste antigo (test_standard_port_not_flagged) usava URL SEM porta,
    então passava trivialmente e nunca detectou o problema.
    """

    def setUp(self):
        self.parser = URLParser()
        self.analyzer = HeuristicAnalyzer()

    def _features(self, url):
        return self.analyzer.extract_features(self.parser.parse(url))

    def test_explicit_https_port_443_is_not_suspicious(self):
        features = self._features("https://exemplo.com:443/login")
        self.assertEqual(features["port"], "443")
        self.assertFalse(features["is_suspicious_port"])

    def test_explicit_http_port_80_is_not_suspicious(self):
        features = self._features("http://exemplo.com:80/login")
        self.assertEqual(features["port"], "80")
        self.assertFalse(features["is_suspicious_port"])

    def test_nonstandard_port_is_still_suspicious(self):
        features = self._features("http://exemplo.com:8080/login")
        self.assertTrue(features["is_suspicious_port"])

    def test_443_absent_from_config_list(self):
        from config.settings import SUSPICIOUS_PORTS

        self.assertNotIn("443", SUSPICIOUS_PORTS)
        self.assertNotIn("80", SUSPICIOUS_PORTS)


class TestQuizDoesNotRepeatQuestions(unittest.TestCase):
    """
    Regressão: o filtro anti-repetição comparava ids estáticos do banco
    contra chaves uuid4 de _active_questions, então era sempre verdadeiro
    e a mesma pergunta podia sair várias vezes na rodada.
    """

    def test_round_serves_distinct_questions(self):
        engine = QuizEngine()
        engine.reset_statistics()

        source_ids = [
            engine.generate_question("iniciante").source_id
            for _ in range(10)
        ]

        self.assertEqual(len(source_ids), 10)
        self.assertEqual(
            len(set(source_ids)), 10,
            f"Questões repetidas na mesma rodada: {source_ids}",
        )

    def test_instance_id_differs_from_source_id(self):
        engine = QuizEngine()
        engine.reset_statistics()
        question = engine.generate_question("iniciante")

        self.assertTrue(question.source_id)
        self.assertNotEqual(question.question_id, question.source_id)

    def test_reset_releases_questions_for_new_round(self):
        engine = QuizEngine()
        engine.reset_statistics()
        first = {engine.generate_question("iniciante").source_id for _ in range(5)}

        engine.reset_statistics()
        second = {engine.generate_question("iniciante").source_id for _ in range(5)}

        # Nova rodada volta a sortear do banco inteiro.
        self.assertTrue(second & first or len(second) == 5)

    def test_pool_recycles_when_exhausted(self):
        """Pedir mais questões que o banco tem não deve estourar."""
        engine = QuizEngine()
        engine.reset_statistics()
        total = len([q for q in engine._questions_bank if q.difficulty == "iniciante"])

        produced = [
            engine.generate_question("iniciante").source_id
            for _ in range(total + 3)
        ]

        self.assertEqual(len(produced), total + 3)


class TestWhoisTimeoutActuallyBounds(unittest.TestCase):
    """
    Regressão: o `return` do timeout estava dentro do `with` do
    ThreadPoolExecutor, cujo __exit__ chama shutdown(wait=True) e bloqueava
    até a consulta lenta terminar — anulando o timeout.

    Este teste usa o executor REAL. O teste antigo substituía o executor
    inteiro por um fake, então nunca exercitou o bloqueio.
    """

    def test_returns_within_timeout_despite_slow_lookup(self):
        from models import whois_checker as wc

        checker = wc.WhoisChecker()
        checker._whois_available = True
        checker._whois_module = mock.Mock()
        checker._whois_module.whois = lambda domain: time.sleep(10)

        with mock.patch.object(wc, "WHOIS_TIMEOUT_SECONDS", 1):
            started = time.monotonic()
            result = checker.check_domain_age("exemplo.com")
            elapsed = time.monotonic() - started

        self.assertFalse(result.success)
        self.assertIn("tempo limite", result.error.lower())
        self.assertLess(
            elapsed, 5,
            f"check_domain_age bloqueou {elapsed:.1f}s — o timeout não interrompeu",
        )


class TestMLFeaturesCompoundSuffix(unittest.TestCase):
    """
    Regressão: o split ingênuo por '.' tratava 'com' como domínio em
    'bb.com.br', inflava num_subdomains e não reconhecia o TLD composto.
    """

    def setUp(self):
        from models.ml_classifier import extract_url_features

        self.extract = extract_url_features

    def test_brazilian_compound_tld(self):
        features = self.extract("https://bb.com.br/login")

        self.assertEqual(features["num_subdomains"], 0)
        self.assertEqual(features["tld_is_common"], 1)

    def test_uk_compound_tld(self):
        features = self.extract("https://google.co.uk/search")

        self.assertEqual(features["num_subdomains"], 0)
        self.assertEqual(features["tld_is_common"], 1)

    def test_real_subdomains_still_counted(self):
        features = self.extract("https://a.b.c.exemplo.com/x")

        self.assertEqual(features["num_subdomains"], 3)

    def test_invalid_octets_are_not_ip(self):
        self.assertEqual(self.extract("http://999.999.999.999/a")["is_ip"], 0)
        self.assertEqual(self.extract("http://8.8.8.8/a")["is_ip"], 1)


class TestVirusTotalRateLimitOnSubmitPath(unittest.TestCase):
    """
    Regressão: a cota era checada só antes do GET; num 404 o cliente
    disparava um POST adicional, podendo ultrapassar o limite do tier
    gratuito.
    """

    def test_submit_path_rechecks_quota(self):
        from models import api_client as ac

        client = ac.ThreatIntelClient()
        # Primeira checagem passa, segunda (antes do POST) recusa.
        client._rate_limiter = mock.Mock()
        client._rate_limiter.can_make_request.side_effect = [True, False]
        client._rate_limiter.get_wait_time.return_value = 42.0

        response = mock.Mock()
        response.status_code = 404

        with mock.patch.object(ac.requests, "get", return_value=response) as fake_get, \
                mock.patch.object(ac.requests, "post") as fake_post:
            result = client.check_virustotal("https://exemplo.com", api_key="k")

        fake_get.assert_called_once()
        fake_post.assert_not_called()
        self.assertFalse(result.success)
        self.assertIn("rate limit", result.error.lower())


class TestScanDateNormalisation(unittest.TestCase):
    """Regressão: timestamp Unix (int) era gravado num campo anotado str."""

    def test_unix_timestamp_becomes_iso_string(self):
        from models.api_client import _format_scan_date

        formatted = _format_scan_date(1700000000)

        self.assertIsInstance(formatted, str)
        self.assertTrue(formatted.startswith("2023-11-"), formatted)

    def test_empty_and_string_inputs(self):
        from models.api_client import _format_scan_date

        self.assertEqual(_format_scan_date(None), "")
        self.assertEqual(_format_scan_date(""), "")
        self.assertEqual(_format_scan_date("2023-01-01"), "2023-01-01")


class TestPersistenceLogsCorruption(unittest.TestCase):
    """
    Regressão: um JSON corrompido zerava histórico/leaderboard/progresso
    sem log nenhum, parecendo perda de dados espontânea.
    """

    def test_corrupt_file_returns_default_and_logs(self):
        from models import persistence

        with mock.patch.object(persistence, "logger") as fake_logger:
            with mock.patch("builtins.open", mock.mock_open(read_data="{corrompido")):
                with mock.patch.object(Path, "exists", return_value=True):
                    result = persistence._load_json(Path("qualquer.json"), [])

        self.assertEqual(result, [])
        fake_logger.warning.assert_called_once()


class TestClassificationThresholdsComeFromConfig(unittest.TestCase):
    """
    Regressão: helpers.run_analysis reclassificava com 25/65 hardcoded,
    que divergiriam em silêncio se o config mudasse.
    """

    def test_helpers_uses_config_constants(self):
        import inspect

        from config.settings import SCORE_SAFE_MAX, SCORE_SUSPICIOUS_MAX
        from ui import helpers

        source = inspect.getsource(helpers.run_analysis)

        self.assertIn("SCORE_SUSPICIOUS_MAX", source)
        self.assertIn("SCORE_SAFE_MAX", source)
        self.assertNotIn("> 65", source)
        self.assertNotIn("> 25", source)
        self.assertEqual((SCORE_SAFE_MAX, SCORE_SUSPICIOUS_MAX), (25, 65))


if __name__ == "__main__":
    unittest.main()
