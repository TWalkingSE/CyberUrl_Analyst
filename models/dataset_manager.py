"""
DatasetManager — Gerenciador centralizado de datasets.
Coordena download, carregamento e consulta de múltiplas fontes de dados.
Suporta carregamento chunked para datasets grandes.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import (
    DATASETS_DOWNLOAD_DIR,
    DATASET_REGISTRY,
    PHISHTANK_SAMPLE,
    URLHAUS_SAMPLE,
    MAJESTIC_MILLION_SAMPLE,
)
from utils.logger import setup_logger

logger = setup_logger("dataset_manager")

# Limite máximo de entradas em memória por categoria
_MAX_ENTRIES = 2_000_000


@dataclass
class DatasetStats:
    """Estatísticas de um dataset carregado."""
    dataset_id: str
    name: str
    category: str
    loaded: bool = False
    urls_count: int = 0
    domains_count: int = 0
    source: str = ""  # "sample" ou "downloaded"


class DatasetManager:
    """
    Gerenciador centralizado de datasets.
    Carrega e consulta URLs/domínios de múltiplas fontes.

    Prioridade de carregamento:
    1. Dataset baixado completo (datasets/downloads/)
    2. Amostra local (datasets/*_sample.csv)
    """

    def __init__(self):
        self._malicious_urls: set[str] = set()
        self._malicious_domains: set[str] = set()
        self._legitimate_domains: set[str] = set()
        self._dga_domains: set[str] = set()
        self._stats: dict[str, DatasetStats] = {}
        self._loaded = False

        # Garante diretório de downloads
        Path(DATASETS_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def load_all(self):
        """Carrega todos os datasets disponíveis (amostras + downloads)."""
        self._load_malicious_feeds()
        self._load_legitimate_feeds()
        self._load_dga_feeds()
        self._loaded = True

        total_mal = len(self._malicious_urls)
        total_leg = len(self._legitimate_domains)
        total_dga = len(self._dga_domains)
        logger.info(
            "DatasetManager carregado — Maliciosas: %d URLs, Legítimas: %d domínios, "
            "DGA: %d domínios",
            total_mal, total_leg, total_dga,
        )

    def is_malicious(self, url: str, domain: str = "") -> tuple[bool, str]:
        """
        Verifica se URL ou domínio está em datasets maliciosos.
        Retorna (encontrado, nome_do_dataset).
        """
        url_lower = url.lower().strip().rstrip("/")
        if url_lower in self._malicious_urls:
            return True, "URLs maliciosas"

        if domain:
            domain_lower = domain.lower()
            if domain_lower in self._malicious_domains:
                return True, "Domínios maliciosos"

        return False, ""

    def is_legitimate(self, domain: str) -> tuple[bool, str]:
        """
        Verifica se domínio está em datasets legítimos.
        Retorna (encontrado, nome_do_dataset).
        """
        if not domain:
            return False, ""
        domain_lower = domain.lower()
        if domain_lower in self._legitimate_domains:
            return True, "Domínios legítimos (Tranco/Majestic/Umbrella)"
        return False, ""

    def is_dga(self, domain: str) -> tuple[bool, str]:
        """
        Verifica se domínio está em datasets de DGA.
        Retorna (encontrado, nome_do_dataset).
        """
        if not domain:
            return False, ""
        domain_lower = domain.lower()
        if domain_lower in self._dga_domains:
            return True, "DGA conhecido"
        return False, ""

    def get_stats(self) -> dict[str, DatasetStats]:
        """Retorna estatísticas de todos os datasets."""
        return self._stats

    def get_summary(self) -> dict:
        """Retorna resumo consolidado."""
        return {
            "malicious_urls": len(self._malicious_urls),
            "malicious_domains": len(self._malicious_domains),
            "legitimate_domains": len(self._legitimate_domains),
            "dga_domains": len(self._dga_domains),
            "datasets_loaded": sum(1 for s in self._stats.values() if s.loaded),
            "datasets_total": len(self._stats),
        }

    def get_malicious_sample(self, n: int = 50) -> list[str]:
        """Retorna amostra de URLs maliciosas (para quiz)."""
        import random
        items = list(self._malicious_urls)
        return random.sample(items, min(n, len(items)))

    def get_legitimate_sample(self, n: int = 50) -> list[str]:
        """Retorna amostra de domínios legítimos (para quiz)."""
        import random
        items = list(self._legitimate_domains)
        return random.sample(items, min(n, len(items)))

    # === Loaders privados ===

    def _load_malicious_feeds(self):
        """Carrega todos os feeds de URLs maliciosas disponíveis."""
        # PhishTank
        self._try_load(
            "phishtank",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "phishtank_online.csv",
            sample_file=PHISHTANK_SAMPLE,
            loader=self._load_csv_urls,
            target="malicious",
        )

        # URLhaus (CSV)
        self._try_load(
            "urlhaus_full",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "urlhaus_recent.csv",
            sample_file=URLHAUS_SAMPLE,
            loader=self._load_csv_urls,
            target="malicious",
        )

        # URLhaus (texto)
        self._try_load(
            "urlhaus_txt",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "urlhaus_urls.txt",
            sample_file=None,
            loader=self._load_txt_urls,
            target="malicious",
        )

        # OpenPhish
        self._try_load(
            "openphish",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "openphish_feed.txt",
            sample_file=None,
            loader=self._load_txt_urls,
            target="malicious",
        )

    def _load_legitimate_feeds(self):
        """Carrega todos os feeds de domínios legítimos."""
        # Tranco
        self._try_load(
            "tranco",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "tranco_top1m.csv",
            sample_file=None,
            loader=self._load_csv_domains_no_header,
            target="legitimate",
        )

        # Majestic Million
        self._try_load(
            "majestic",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "majestic_million.csv",
            sample_file=MAJESTIC_MILLION_SAMPLE,
            loader=self._load_csv_domains,
            target="legitimate",
        )

        # Umbrella
        self._try_load(
            "umbrella",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "umbrella_top1m.csv",
            sample_file=None,
            loader=self._load_csv_domains_no_header,
            target="legitimate",
        )

    def _load_dga_feeds(self):
        """Carrega feeds de domínios DGA."""
        # 360 Netlab
        self._try_load(
            "dga_netlab360",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "netlab360_dga.txt",
            sample_file=None,
            loader=self._load_txt_domains,
            target="dga",
        )

        # DGA Kaggle (manual)
        self._try_load(
            "dga_kaggle",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "dga_kaggle.csv",
            sample_file=None,
            loader=self._load_csv_domains,
            target="dga",
        )

    def _try_load(self, dataset_id: str, downloaded_file: Optional[Path],
                  sample_file: Optional[Path], loader, target: str):
        """Tenta carregar dataset: prioriza download, fallback para amostra."""
        info = DATASET_REGISTRY.get(dataset_id, {})
        name = info.get("name", dataset_id)
        category = info.get("category", "unknown")

        stat = DatasetStats(
            dataset_id=dataset_id,
            name=name,
            category=category,
        )

        # Tenta arquivo baixado
        if downloaded_file and downloaded_file.exists():
            try:
                count = loader(downloaded_file, target)
                stat.loaded = True
                stat.source = "downloaded"
                if target == "malicious":
                    stat.urls_count = count
                else:
                    stat.domains_count = count
                logger.info("%s carregado (download): %d itens", name, count)
            except Exception as e:
                logger.error("Erro ao carregar %s (download): %s", name, e)

        # Fallback: amostra local
        elif sample_file and sample_file.exists():
            try:
                count = loader(sample_file, target)
                stat.loaded = True
                stat.source = "sample"
                if target == "malicious":
                    stat.urls_count = count
                else:
                    stat.domains_count = count
                logger.info("%s carregado (amostra): %d itens", name, count)
            except Exception as e:
                logger.error("Erro ao carregar %s (amostra): %s", name, e)

        self._stats[dataset_id] = stat

    def _load_csv_urls(self, path: Path, target: str) -> int:
        """Carrega URLs de um CSV (coluna 'url' ou posicional)."""
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                # Detecta se tem header com 'url'
                first_line = f.readline()
                f.seek(0)
                has_header = "url" in first_line.lower().split(",")[0:5]

                if has_header:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get("url", "").strip(' "').lower().rstrip("/")
                        if url and url.startswith("http"):
                            if len(self._malicious_urls) < _MAX_ENTRIES:
                                self._malicious_urls.add(url)
                            domain = self._extract_domain(url)
                            if domain:
                                self._malicious_domains.add(domain)
                            count += 1
                else:
                    # CSV sem header ou com header desconhecido (ex.: URLhaus)
                    reader = csv.reader(f, quotechar='"')
                    for row in reader:
                        if not row or row[0].startswith("#"):
                            continue
                        # Procura primeiro campo que parece URL
                        for field in row:
                            field = field.strip().lower().rstrip("/")
                            if field.startswith("http"):
                                if len(self._malicious_urls) < _MAX_ENTRIES:
                                    self._malicious_urls.add(field)
                                domain = self._extract_domain(field)
                                if domain:
                                    self._malicious_domains.add(domain)
                                count += 1
                                break
        except Exception as e:
            logger.error("Erro ao ler CSV %s: %s", path, e)
        return count

    def _load_txt_urls(self, path: Path, target: str) -> int:
        """Carrega URLs de arquivo texto (uma por linha)."""
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    url = line.strip().lower().rstrip("/")
                    if url and not url.startswith("#") and url.startswith("http"):
                        if len(self._malicious_urls) < _MAX_ENTRIES:
                            self._malicious_urls.add(url)
                        domain = self._extract_domain(url)
                        if domain:
                            self._malicious_domains.add(domain)
                        count += 1
        except Exception as e:
            logger.error("Erro ao ler TXT %s: %s", path, e)
        return count

    def _load_csv_domains(self, path: Path, target: str) -> int:
        """Carrega domínios de CSV (coluna 'Domain' ou 'domain')."""
        count = 0
        target_set = self._legitimate_domains if target == "legitimate" else self._dga_domains
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    domain = (
                        row.get("Domain", "") or
                        row.get("domain", "") or
                        row.get("hostname", "")
                    ).strip().lower()
                    if domain:
                        if len(target_set) < _MAX_ENTRIES:
                            target_set.add(domain)
                        count += 1
        except Exception as e:
            logger.error("Erro ao ler CSV domínios %s: %s", path, e)
        return count

    def _load_csv_domains_no_header(self, path: Path, target: str) -> int:
        """Carrega domínios de CSV sem cabeçalho (formato: rank,domain)."""
        count = 0
        target_set = self._legitimate_domains if target == "legitimate" else self._dga_domains
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(",")
                    if len(parts) >= 2:
                        domain = parts[1].strip().lower()
                    else:
                        domain = parts[0].strip().lower()
                    if domain and not domain[0].isdigit():
                        target_set.add(domain)
                        count += 1
                    elif len(parts) >= 2:
                        target_set.add(parts[1].strip().lower())
                        count += 1
        except Exception as e:
            logger.error("Erro ao ler CSV sem header %s: %s", path, e)
        return count

    def _load_txt_domains(self, path: Path, target: str) -> int:
        """Carrega domínios de arquivo texto (um por linha, ignora # e tabs)."""
        count = 0
        target_set = self._legitimate_domains if target == "legitimate" else self._dga_domains
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Alguns feeds DGA usam formato: familia\tdominio
                    parts = line.split("\t")
                    domain = parts[-1].strip().lower() if parts else ""
                    # Remove porta se presente
                    domain = domain.split(":")[0]
                    if domain and "." in domain:
                        target_set.add(domain)
                        count += 1
        except Exception as e:
            logger.error("Erro ao ler TXT domínios %s: %s", path, e)
        return count

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extrai domínio de uma URL de forma simples."""
        try:
            url = url.split("://", 1)[-1]
            domain = url.split("/", 1)[0]
            domain = domain.split(":")[0]
            return domain.lower()
        except Exception:
            return ""
