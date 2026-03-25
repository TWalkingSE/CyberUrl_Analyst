"""
Cached resources — Instâncias compartilhadas de modelos e serviços.
Todas as funções usam @st.cache_resource para evitar re-criação.

Melhorias:
  #2  Error handling com logging (não silencia exceções)
  #6  TTL de 1h no dataset checker para recarregar automaticamente
"""

import streamlit as st

from models.url_parser import URLParser
from models.heuristic_analyzer import HeuristicAnalyzer
from models.dataset_checker import DatasetChecker
from models.defanger import URLDefanger
from models.report_generator import ReportGenerator
from models.whois_checker import WhoisChecker
from models.analysis_cache import AnalysisCache
from utils.dataset_downloader import DatasetDownloader
from utils.logger import setup_logger

_logger = setup_logger("resources")

try:
    from models.ml_classifier import MLClassifier, MODEL_PATH
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    MODEL_PATH = None

try:
    from models.api_client import ThreatIntelClient
    API_AVAILABLE = True
except Exception:
    API_AVAILABLE = False
    ThreatIntelClient = None


@st.cache_resource
def get_parser():
    return URLParser()


@st.cache_resource
def get_analyzer():
    return HeuristicAnalyzer()


@st.cache_resource(ttl=3600)
def _load_dc():
    """Carrega DatasetChecker com TTL de 1 hora (#6)."""
    dc = DatasetChecker()
    try:
        dc.load_datasets()
        _logger.info("Datasets carregados com sucesso.")
    except Exception as e:
        _logger.error("Falha ao carregar datasets: %s", e)
        st.toast("⚠️ Alguns datasets não puderam ser carregados.", icon="⚠️")
    return dc


def get_dataset_checker():
    return _load_dc()


@st.cache_resource
def get_defanger():
    return URLDefanger()


@st.cache_resource
def get_report_gen():
    return ReportGenerator()


@st.cache_resource
def get_whois():
    return WhoisChecker()


@st.cache_resource
def get_cache():
    return AnalysisCache()


@st.cache_resource
def get_ml():
    if not ML_AVAILABLE:
        return None
    clf = MLClassifier()
    try:
        clf.load_model()
        _logger.info("Modelo ML carregado.")
    except Exception as e:
        _logger.warning("Modelo ML não carregado: %s", e)
    return clf


@st.cache_resource
def get_downloader():
    return DatasetDownloader()
