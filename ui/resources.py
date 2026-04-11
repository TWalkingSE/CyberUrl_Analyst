"""Lazy shared services for the PyQt6 interface."""

from __future__ import annotations

from functools import lru_cache

from models.analysis_cache import AnalysisCache
from models.dataset_checker import DatasetChecker
from models.defanger import URLDefanger
from models.heuristic_analyzer import HeuristicAnalyzer
from models.report_generator import ReportGenerator
from models.url_parser import URLParser
from models.whois_checker import WhoisChecker
from utils.dataset_downloader import DatasetDownloader
from utils.logger import setup_logger

logger = setup_logger("ui_resources")

try:
    from models.ml_classifier import MLClassifier, MODEL_PATH

    ML_AVAILABLE = True
except Exception:
    ML_AVAILABLE = False
    MODEL_PATH = None
    MLClassifier = None

try:
    from models.api_client import ThreatIntelClient

    API_AVAILABLE = True
except Exception:
    API_AVAILABLE = False
    ThreatIntelClient = None


@lru_cache(maxsize=1)
def get_parser() -> URLParser:
    return URLParser()


@lru_cache(maxsize=1)
def get_analyzer() -> HeuristicAnalyzer:
    return HeuristicAnalyzer()


@lru_cache(maxsize=1)
def get_dataset_checker() -> DatasetChecker:
    checker = DatasetChecker()
    try:
        checker.load_datasets()
        logger.info("Datasets carregados com sucesso.")
    except Exception as exc:
        logger.error("Falha ao carregar datasets: %s", exc)
    return checker


@lru_cache(maxsize=1)
def get_defanger() -> URLDefanger:
    return URLDefanger()


@lru_cache(maxsize=1)
def get_report_generator() -> ReportGenerator:
    return ReportGenerator()


@lru_cache(maxsize=1)
def get_whois() -> WhoisChecker:
    return WhoisChecker()


@lru_cache(maxsize=1)
def get_cache() -> AnalysisCache:
    return AnalysisCache()


@lru_cache(maxsize=1)
def get_ml():
    if not ML_AVAILABLE or MLClassifier is None:
        return None
    classifier = MLClassifier()
    try:
        classifier.load_model()
    except Exception as exc:
        logger.warning("Modelo ML nao carregado: %s", exc)
    return classifier


@lru_cache(maxsize=1)
def get_downloader() -> DatasetDownloader:
    return DatasetDownloader()


@lru_cache(maxsize=1)
def get_api_client():
    if not API_AVAILABLE or ThreatIntelClient is None:
        return None
    return ThreatIntelClient()


def reload_dataset_checker() -> DatasetChecker:
    get_dataset_checker.cache_clear()
    return get_dataset_checker()


def reload_ml():
    get_ml.cache_clear()
    return get_ml()