"""
DatasetChecker — Verificação de URLs contra datasets públicos de ameaças.
Carrega e consulta múltiplas fontes: amostras locais + datasets baixados.
Delegado pelo DatasetManager para cobertura ampla.
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import (
    PHISHTANK_SAMPLE,
    URLHAUS_SAMPLE,
    MAJESTIC_MILLION_SAMPLE,
    HEURISTIC_WEIGHTS,
)
from utils.logger import setup_logger

logger = setup_logger("dataset_checker")


@dataclass
class DatasetMatch:
    """Resultado de uma correspondência com dataset."""
    dataset_name: str          # "PhishTank", "URLhaus", "Majestic Million"
    matched: bool              # Se houve correspondência
    match_type: str            # "exact", "domain", "none"
    detail: str                # Detalhes da correspondência
    weight: int = 0            # Peso no score de ameaça
    is_legitimate: bool = False  # True para match em Majestic Million


@dataclass
class DatasetCheckResult:
    """Resultado consolidado de todas as verificações de dataset."""
    matches: list[DatasetMatch] = field(default_factory=list)
    is_in_phishing_db: bool = False
    is_in_malware_db: bool = False
    is_in_legitimate_db: bool = False
    is_in_dga_db: bool = False
    total_weight: int = 0


class DatasetChecker:
    """
    Verifica URLs contra datasets locais.
    Carrega os dados em memória na inicialização para buscas rápidas.
    """

    def __init__(self):
        self._phishtank_urls: set[str] = set()
        self._phishtank_domains: set[str] = set()
        self._urlhaus_urls: set[str] = set()
        self._urlhaus_domains: set[str] = set()
        self._majestic_domains: set[str] = set()
        self._loaded = False
        self._manager = None  # DatasetManager (lazy-loaded)

    def load_datasets(self):
        """Carrega todos os datasets disponíveis para memória."""
        # Carrega amostras locais (sempre presentes)
        self._load_phishtank()
        self._load_urlhaus()
        self._load_majestic_million()

        # Carrega DatasetManager (amostras + downloads)
        try:
            from models.dataset_manager import DatasetManager
            self._manager = DatasetManager()
            self._manager.load_all()
        except Exception as e:
            logger.warning("DatasetManager não carregado: %s", e)
            self._manager = None

        self._loaded = True
        logger.info(
            "Datasets carregados — PhishTank: %d URLs, URLhaus: %d URLs, "
            "Majestic: %d domínios",
            len(self._phishtank_urls),
            len(self._urlhaus_urls),
            len(self._majestic_domains),
        )

    def check(self, url: str, domain: str, registered_domain: str) -> DatasetCheckResult:
        """
        Verifica a URL e domínio contra todos os datasets carregados.
        Retorna resultado consolidado com todas as correspondências.
        """
        if not self._loaded:
            self.load_datasets()

        result = DatasetCheckResult()
        url_lower = url.lower().strip().rstrip("/")
        domain_lower = domain.lower() if domain else ""
        reg_domain_lower = registered_domain.lower() if registered_domain else ""

        # === PhishTank ===
        phish_match = self._check_phishtank(url_lower, domain_lower, reg_domain_lower)
        result.matches.append(phish_match)
        if phish_match.matched:
            result.is_in_phishing_db = True
            result.total_weight += phish_match.weight

        # === URLhaus ===
        urlhaus_match = self._check_urlhaus(url_lower, domain_lower, reg_domain_lower)
        result.matches.append(urlhaus_match)
        if urlhaus_match.matched:
            result.is_in_malware_db = True
            result.total_weight += urlhaus_match.weight

        # === Majestic Million ===
        majestic_match = self._check_majestic(domain_lower, reg_domain_lower)
        result.matches.append(majestic_match)
        if majestic_match.matched:
            result.is_in_legitimate_db = True

        # === DatasetManager (fontes adicionais: OpenPhish, Tranco, Umbrella, DGA) ===
        if self._manager:
            # Maliciosas adicionais
            found_mal, src_mal = self._manager.is_malicious(url_lower, domain_lower)
            if found_mal and not result.is_in_phishing_db and not result.is_in_malware_db:
                result.matches.append(DatasetMatch(
                    dataset_name=f"Feeds ({src_mal})",
                    matched=True,
                    match_type="domain" if not url_lower else "exact",
                    detail=f"URL/domínio encontrado em feeds adicionais ({src_mal}).",
                    weight=HEURISTIC_WEIGHTS["dataset_phishtank_match"],
                ))
                result.is_in_phishing_db = True
                result.total_weight += HEURISTIC_WEIGHTS["dataset_phishtank_match"]

            # Legítimas adicionais (Tranco, Umbrella)
            if not result.is_in_legitimate_db:
                found_leg, src_leg = self._manager.is_legitimate(
                    reg_domain_lower or domain_lower
                )
                if found_leg:
                    result.matches.append(DatasetMatch(
                        dataset_name=src_leg,
                        matched=True,
                        match_type="domain",
                        detail=(
                            f"Domínio presente em datasets de domínios legítimos "
                            f"({src_leg}). Endereço bem estabelecido."
                        ),
                        is_legitimate=True,
                    ))
                    result.is_in_legitimate_db = True

            # DGA
            found_dga, src_dga = self._manager.is_dga(domain_lower)
            if found_dga:
                result.matches.append(DatasetMatch(
                    dataset_name=f"DGA ({src_dga})",
                    matched=True,
                    match_type="domain",
                    detail=(
                        f"Domínio encontrado em feed de DGA ({src_dga}). "
                        "Este domínio foi gerado por malware/botnet."
                    ),
                    weight=HEURISTIC_WEIGHTS.get("dga_domain", 18),
                ))
                result.is_in_dga_db = True
                result.total_weight += HEURISTIC_WEIGHTS.get("dga_domain", 18)

        return result

    def _check_phishtank(self, url: str, domain: str, reg_domain: str) -> DatasetMatch:
        """Verifica correspondência no PhishTank."""
        if url in self._phishtank_urls:
            return DatasetMatch(
                dataset_name="PhishTank",
                matched=True,
                match_type="exact",
                detail="URL encontrada no banco de phishing PhishTank (correspondência exata).",
                weight=HEURISTIC_WEIGHTS["dataset_phishtank_match"],
            )
        if domain in self._phishtank_domains or reg_domain in self._phishtank_domains:
            return DatasetMatch(
                dataset_name="PhishTank",
                matched=True,
                match_type="domain",
                detail="Domínio encontrado no banco de phishing PhishTank.",
                weight=HEURISTIC_WEIGHTS["dataset_phishtank_match"],
            )
        return DatasetMatch(
            dataset_name="PhishTank",
            matched=False,
            match_type="none",
            detail="URL/domínio NÃO encontrado no PhishTank.",
        )

    def _check_urlhaus(self, url: str, domain: str, reg_domain: str) -> DatasetMatch:
        """Verifica correspondência no URLhaus."""
        if url in self._urlhaus_urls:
            return DatasetMatch(
                dataset_name="URLhaus",
                matched=True,
                match_type="exact",
                detail="URL encontrada no banco de malware URLhaus (correspondência exata).",
                weight=HEURISTIC_WEIGHTS["dataset_urlhaus_match"],
            )
        if domain in self._urlhaus_domains or reg_domain in self._urlhaus_domains:
            return DatasetMatch(
                dataset_name="URLhaus",
                matched=True,
                match_type="domain",
                detail="Domínio encontrado no banco de malware URLhaus.",
                weight=HEURISTIC_WEIGHTS["dataset_urlhaus_match"],
            )
        return DatasetMatch(
            dataset_name="URLhaus",
            matched=False,
            match_type="none",
            detail="URL/domínio NÃO encontrado no URLhaus.",
        )

    def _check_majestic(self, domain: str, reg_domain: str) -> DatasetMatch:
        """Verifica se o domínio está no Majestic Million (legítimo)."""
        if domain in self._majestic_domains or reg_domain in self._majestic_domains:
            return DatasetMatch(
                dataset_name="Majestic Million",
                matched=True,
                match_type="domain",
                detail=(
                    "Domínio presente no Majestic Million (top 1M domínios). "
                    "É um endereço bem estabelecido e de alta reputação."
                ),
                is_legitimate=True,
            )
        return DatasetMatch(
            dataset_name="Majestic Million",
            matched=False,
            match_type="none",
            detail="Domínio NÃO encontrado no Majestic Million.",
        )

    def _load_phishtank(self):
        """Carrega dataset PhishTank."""
        path = Path(PHISHTANK_SAMPLE)
        if not path.exists():
            logger.warning("Dataset PhishTank não encontrado: %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("url", "").strip().lower().rstrip("/")
                    if url:
                        self._phishtank_urls.add(url)
                        domain = self._extract_domain(url)
                        if domain:
                            self._phishtank_domains.add(domain)
            logger.info("PhishTank carregado: %d URLs", len(self._phishtank_urls))
        except Exception as e:
            logger.error("Erro ao carregar PhishTank: %s", e)

    def _load_urlhaus(self):
        """Carrega dataset URLhaus."""
        path = Path(URLHAUS_SAMPLE)
        if not path.exists():
            logger.warning("Dataset URLhaus não encontrado: %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("url", "").strip().lower().rstrip("/")
                    if url:
                        self._urlhaus_urls.add(url)
                        domain = self._extract_domain(url)
                        if domain:
                            self._urlhaus_domains.add(domain)
            logger.info("URLhaus carregado: %d URLs", len(self._urlhaus_urls))
        except Exception as e:
            logger.error("Erro ao carregar URLhaus: %s", e)

    def _load_majestic_million(self):
        """Carrega dataset Majestic Million."""
        path = Path(MAJESTIC_MILLION_SAMPLE)
        if not path.exists():
            logger.warning("Dataset Majestic Million não encontrado: %s", path)
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    domain = row.get("Domain", row.get("domain", "")).strip().lower()
                    if domain:
                        self._majestic_domains.add(domain)
            logger.info("Majestic Million carregado: %d domínios", len(self._majestic_domains))
        except Exception as e:
            logger.error("Erro ao carregar Majestic Million: %s", e)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extrai domínio de uma URL de forma simples."""
        try:
            url = url.split("://", 1)[-1]
            domain = url.split("/", 1)[0]
            domain = domain.split(":")[0]  # Remove porta
            return domain.lower()
        except Exception:
            return ""

    def get_stats(self) -> dict:
        """Retorna estatísticas dos datasets carregados."""
        stats = {
            "phishtank_urls": len(self._phishtank_urls),
            "phishtank_domains": len(self._phishtank_domains),
            "urlhaus_urls": len(self._urlhaus_urls),
            "urlhaus_domains": len(self._urlhaus_domains),
            "majestic_domains": len(self._majestic_domains),
            "loaded": self._loaded,
        }
        if self._manager:
            stats["manager"] = self._manager.get_summary()
        return stats

    def get_manager(self):
        """Retorna referência ao DatasetManager (ou None)."""
        return self._manager
