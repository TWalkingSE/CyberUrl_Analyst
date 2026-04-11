"""
AnalysisCache — Cache local para evitar re-análise de URLs idênticas.
Usa hash SHA-256 como chave para proteger dados pessoais.
"""

from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

from config.settings import ANALYSIS_CACHE_MAX_SIZE
from utils.sanitizer import hash_url


@dataclass
class CachedAnalysis:
    """Entrada no cache de análise."""
    url_hash: str
    report: object  # FullReport
    timestamp: float = 0.0


class AnalysisCache:
    """
    Cache LRU para resultados de análise.
    Evita recalcular análises para URLs já processadas na mesma sessão.
    Chave: SHA-256 hash da URL (nunca armazena URL em texto).
    """

    def __init__(self, max_size: int = ANALYSIS_CACHE_MAX_SIZE):
        self._cache: OrderedDict[str, CachedAnalysis] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, url: str) -> Optional[object]:
        """
        Busca resultado em cache. Retorna FullReport ou None.
        Move a entrada para o final (LRU).
        """
        url_hash = hash_url(url)
        if url_hash in self._cache:
            self._cache.move_to_end(url_hash)
            self._hits += 1
            return self._cache[url_hash].report
        self._misses += 1
        return None

    def put(self, url: str, report: object):
        """
        Armazena resultado no cache.
        Remove a entrada mais antiga se o cache estiver cheio.
        """
        import time
        url_hash = hash_url(url)

        if url_hash in self._cache:
            self._cache.move_to_end(url_hash)
            self._cache[url_hash].report = report
            return

        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[url_hash] = CachedAnalysis(
            url_hash=url_hash,
            report=report,
            timestamp=time.time(),
        )

    def invalidate(self, url: str):
        """Remove uma entrada específica do cache."""
        url_hash = hash_url(url)
        self._cache.pop(url_hash, None)

    def clear(self):
        """Limpa todo o cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> dict:
        """Retorna estatísticas do cache."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
        }
