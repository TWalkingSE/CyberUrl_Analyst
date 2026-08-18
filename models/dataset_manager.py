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
    DATASET_MAX_ENTRIES,
)
from utils.logger import setup_logger
from utils.url_utils import extract_domain

logger = setup_logger("dataset_manager")


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
        self._dataset_urls: dict[str, set[str]] = {}
        self._dataset_domains: dict[str, set[str]] = {}
        self._stats: dict[str, DatasetStats] = {}
        self._loaded = False

        Path(DATASETS_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

    def load_all(self):
        """Carrega todos os datasets disponíveis (amostras + downloads)."""
        self._reset_state()
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
            total_mal,
            total_leg,
            total_dga,
        )

    def is_malicious(self, url: str, domain: str = "") -> tuple[bool, str]:
        """
        Verifica se URL ou domínio está em datasets maliciosos.
        Retorna (encontrado, nome_do_dataset).
        """
        for dataset_id in ("phishtank", "urlhaus_full", "urlhaus_txt", "openphish"):
            match_type = self.match_dataset(dataset_id, url=url, domain=domain)
            if match_type != "none":
                return True, self._dataset_name(dataset_id)
        return False, ""

    def is_legitimate(self, domain: str) -> tuple[bool, str]:
        """
        Verifica se domínio está em datasets legítimos.
        Retorna (encontrado, nome_do_dataset).
        """
        if not domain:
            return False, ""

        for dataset_id in ("tranco", "majestic", "umbrella"):
            match_type = self.match_dataset(
                dataset_id,
                domain=domain,
                registered_domain=domain,
            )
            if match_type != "none":
                return True, self._dataset_name(dataset_id)
        return False, ""

    def is_dga(self, domain: str) -> tuple[bool, str]:
        """
        Verifica se domínio está em datasets de DGA.
        Retorna (encontrado, nome_do_dataset).
        """
        if not domain:
            return False, ""

        for dataset_id, stat in self._stats.items():
            if stat.category != "dga":
                continue
            match_type = self.match_dataset(
                dataset_id,
                domain=domain,
                registered_domain=domain,
            )
            if match_type != "none":
                return True, stat.name
        return False, ""

    def match_dataset(self, dataset_id: str, url: str = "", domain: str = "",
                      registered_domain: str = "") -> str:
        """Retorna o tipo de correspondência em um dataset específico."""
        dataset_urls = self._dataset_urls.get(dataset_id, set())
        dataset_domains = self._dataset_domains.get(dataset_id, set())

        url_lower = url.lower().strip().rstrip("/") if url else ""
        if url_lower and url_lower in dataset_urls:
            return "exact"

        for candidate in (domain, registered_domain):
            candidate_lower = candidate.lower().strip() if candidate else ""
            if candidate_lower and candidate_lower in dataset_domains:
                return "domain"

        return "none"

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

    def get_dataset_item_count(self, dataset_ids: str | tuple[str, ...],
                               item_type: str = "url") -> int:
        """Retorna a contagem única de URLs ou domínios em um ou mais datasets."""
        if isinstance(dataset_ids, str):
            dataset_ids = (dataset_ids,)

        source = self._dataset_urls if item_type == "url" else self._dataset_domains
        combined_items: set[str] = set()
        for dataset_id in dataset_ids:
            combined_items.update(source.get(dataset_id, set()))
        return len(combined_items)

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

    def _reset_state(self):
        """Limpa o estado interno para permitir recarga idempotente."""
        self._malicious_urls.clear()
        self._malicious_domains.clear()
        self._legitimate_domains.clear()
        self._dga_domains.clear()
        self._dataset_urls.clear()
        self._dataset_domains.clear()
        self._stats = {}
        self._loaded = False

    def _dataset_name(self, dataset_id: str) -> str:
        """Resolve o nome amigável de um dataset."""
        stat = self._stats.get(dataset_id)
        if stat:
            return stat.name
        return DATASET_REGISTRY.get(dataset_id, {}).get("name", dataset_id)

    def _load_malicious_feeds(self):
        """Carrega todos os feeds de URLs maliciosas disponíveis."""
        self._try_load(
            "phishtank",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "phishtank_online.csv",
            sample_file=PHISHTANK_SAMPLE,
            loader=self._load_csv_urls,
            target="malicious",
        )
        self._try_load(
            "urlhaus_full",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "urlhaus_recent.csv",
            sample_file=URLHAUS_SAMPLE,
            loader=self._load_csv_urls,
            target="malicious",
        )
        self._try_load(
            "urlhaus_txt",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "urlhaus_urls.txt",
            sample_file=None,
            loader=self._load_txt_urls,
            target="malicious",
        )
        self._try_load(
            "openphish",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "openphish_feed.txt",
            sample_file=None,
            loader=self._load_txt_urls,
            target="malicious",
        )

    def _load_legitimate_feeds(self):
        """Carrega todos os feeds de domínios legítimos."""
        self._try_load(
            "tranco",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "tranco_top1m.csv",
            sample_file=None,
            loader=self._load_csv_domains_no_header,
            target="legitimate",
        )
        self._try_load(
            "majestic",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "majestic_million.csv",
            sample_file=MAJESTIC_MILLION_SAMPLE,
            loader=self._load_csv_domains,
            target="legitimate",
        )
        self._try_load(
            "umbrella",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "umbrella_top1m.csv",
            sample_file=None,
            loader=self._load_csv_domains_no_header,
            target="legitimate",
        )

    def _load_dga_feeds(self):
        """Carrega feeds de domínios DGA."""
        self._try_load(
            "dga_netlab360",
            downloaded_file=DATASETS_DOWNLOAD_DIR / "netlab360_dga.txt",
            sample_file=None,
            loader=self._load_txt_domains,
            target="dga",
        )
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
        self._ensure_dataset_storage(dataset_id)

        stat = DatasetStats(
            dataset_id=dataset_id,
            name=name,
            category=category,
        )

        if downloaded_file and downloaded_file.exists():
            try:
                count = loader(downloaded_file, target, dataset_id)
                stat.loaded = True
                stat.source = "downloaded"
                if target == "malicious":
                    stat.urls_count = count
                else:
                    stat.domains_count = count
                logger.info("%s carregado (download): %d itens", name, count)
            except Exception as e:
                logger.error("Erro ao carregar %s (download): %s", name, e)
        elif sample_file and sample_file.exists():
            try:
                count = loader(sample_file, target, dataset_id)
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

    def _load_csv_urls(self, path: Path, target: str, dataset_id: str) -> int:
        """Carrega URLs de um CSV (coluna 'url' ou posicional)."""
        del target
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                f.seek(0)
                has_header = "url" in first_line.lower().split(",")[0:5]

                if has_header:
                    reader = csv.DictReader(f)
                    for row in reader:
                        url = row.get("url", "").strip(' "').lower().rstrip("/")
                        if url and url.startswith("http"):
                            if self._add_url_entry(dataset_id, url):
                                count += 1
                else:
                    reader = csv.reader(f, quotechar='"')
                    for row in reader:
                        if not row or row[0].startswith("#"):
                            continue
                        for field in row:
                            field = field.strip().lower().rstrip("/")
                            if field.startswith("http"):
                                if self._add_url_entry(dataset_id, field):
                                    count += 1
                                break
        except Exception as e:
            logger.error("Erro ao ler CSV %s: %s", path, e)
        return count

    def _load_txt_urls(self, path: Path, target: str, dataset_id: str) -> int:
        """Carrega URLs de arquivo texto (uma por linha)."""
        del target
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    url = line.strip().lower().rstrip("/")
                    if url and not url.startswith("#") and url.startswith("http"):
                        if self._add_url_entry(dataset_id, url):
                            count += 1
        except Exception as e:
            logger.error("Erro ao ler TXT %s: %s", path, e)
        return count

    def _load_csv_domains(self, path: Path, target: str, dataset_id: str) -> int:
        """Carrega domínios de CSV (coluna 'Domain' ou 'domain')."""
        count = 0
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
                        if self._add_domain_entry(dataset_id, domain, target):
                            count += 1
        except Exception as e:
            logger.error("Erro ao ler CSV domínios %s: %s", path, e)
        return count

    def _load_csv_domains_no_header(self, path: Path, target: str, dataset_id: str) -> int:
        """Carrega domínios de CSV sem cabeçalho (formato: rank,domain)."""
        count = 0
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
                        if self._add_domain_entry(dataset_id, domain, target):
                            count += 1
                    elif len(parts) >= 2:
                        if self._add_domain_entry(dataset_id, parts[1].strip().lower(), target):
                            count += 1
        except Exception as e:
            logger.error("Erro ao ler CSV sem header %s: %s", path, e)
        return count

    def _load_txt_domains(self, path: Path, target: str, dataset_id: str) -> int:
        """Carrega domínios de arquivo texto (um por linha, ignora # e tabs)."""
        count = 0
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    domain = parts[-1].strip().lower() if parts else ""
                    domain = domain.split(":")[0]
                    if domain and "." in domain:
                        if self._add_domain_entry(dataset_id, domain, target):
                            count += 1
        except Exception as e:
            logger.error("Erro ao ler TXT %s: %s", path, e)
        return count

    def _ensure_dataset_storage(self, dataset_id: str):
        """Inicializa os sets por dataset usados nas consultas específicas."""
        self._dataset_urls.setdefault(dataset_id, set())
        self._dataset_domains.setdefault(dataset_id, set())

    def _add_url_entry(self, dataset_id: str, url: str) -> bool:
        """
        Adiciona uma URL maliciosa ao agregado e ao dataset específico.

        Retorna True se a URL foi de fato armazenada. Acima de
        DATASET_MAX_ENTRIES nada é guardado — e o chamador precisa saber,
        senão a contagem informada passa a mentir sobre o que é consultável.
        """
        stored = False
        if len(self._malicious_urls) < DATASET_MAX_ENTRIES:
            self._malicious_urls.add(url)
            self._dataset_urls[dataset_id].add(url)
            stored = True

        domain = self._extract_domain(url)
        if domain:
            self._add_domain_entry(dataset_id, domain, "malicious")
        return stored

    def _add_domain_entry(self, dataset_id: str, domain: str, target: str) -> bool:
        """
        Adiciona um domínio ao agregado e ao dataset específico correspondente.

        Retorna True se o domínio foi de fato armazenado (ver `_add_url_entry`).
        """
        if not domain:
            return False

        if target == "legitimate":
            target_set = self._legitimate_domains
        elif target == "dga":
            target_set = self._dga_domains
        else:
            target_set = self._malicious_domains

        if len(target_set) < DATASET_MAX_ENTRIES:
            target_set.add(domain)
            self._dataset_domains[dataset_id].add(domain)
            return True
        return False

    _extract_domain = staticmethod(extract_domain)
