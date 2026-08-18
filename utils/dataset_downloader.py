"""
Dataset Downloader — Baixa e gerencia datasets públicos de segurança.
Suporta CSV, TXT, ZIP. Implementa timeout, verificação e logging seguro.

IMPORTANTE:
- Nunca acessa URLs dos datasets — apenas baixa os arquivos de feed.
- Respeita licenças de uso (documentadas em settings.DATASET_REGISTRY).
- Datasets com API key só são baixados se a chave estiver configurada.
"""

import io
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

from config.settings import (
    DATASETS_DOWNLOAD_DIR,
    DATASET_REGISTRY,
    DATASET_DOWNLOAD_TIMEOUT,
)
from utils.logger import setup_logger

logger = setup_logger("dataset_downloader")

# Limite máximo de download (500 MB)
_MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024


@dataclass
class DownloadResult:
    """Resultado de uma operação de download."""
    dataset_id: str
    success: bool
    file_path: str = ""
    size_bytes: int = 0
    error: str = ""
    timestamp: str = ""
    lines_count: int = 0


class DatasetDownloader:
    """
    Gerencia download de datasets públicos de segurança.
    Apenas datasets sem autenticação são baixados automaticamente.
    Datasets que requerem API key precisam da chave configurada em .env.
    """

    def __init__(self):
        self._download_dir = Path(DATASETS_DOWNLOAD_DIR)
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._results: dict[str, DownloadResult] = {}

    def download(self, dataset_id: str, api_key: str = "",
                  progress_callback=None) -> DownloadResult:
        """
        Baixa um dataset específico pelo ID.
        Retorna DownloadResult com status da operação.
        """
        if dataset_id not in DATASET_REGISTRY:
            return DownloadResult(
                dataset_id=dataset_id,
                success=False,
                error=f"Dataset '{dataset_id}' não encontrado no registro.",
            )

        info = DATASET_REGISTRY[dataset_id]

        # Verifica se requer download manual
        if info.get("manual"):
            return DownloadResult(
                dataset_id=dataset_id,
                success=False,
                error=(
                    f"'{info['name']}' requer download manual.\n"
                    f"Acesse: {info['website']}\n"
                    f"Coloque o arquivo em: {self._download_dir / info['file']}"
                ),
            )

        # Monta URL
        url = info["url"]
        if info.get("requires_key"):
            key = api_key or os.getenv(info.get("key_env", ""), "")
            if not key:
                return DownloadResult(
                    dataset_id=dataset_id,
                    success=False,
                    error=(
                        f"'{info['name']}' requer API key.\n"
                        f"Configure a variável de ambiente '{info['key_env']}' "
                        f"no arquivo .env ou forneça a chave manualmente."
                    ),
                )
            url = url.format(api_key=key)

        if not url:
            return DownloadResult(
                dataset_id=dataset_id,
                success=False,
                error="URL de download não disponível para este dataset.",
            )

        # Download
        dest = self._download_dir / info["file"]
        fmt = info.get("format", "csv")

        try:
            logger.info("Baixando '%s' de %s...", info["name"], info["website"])

            response = requests.get(
                url,
                timeout=(15, DATASET_DOWNLOAD_TIMEOUT),
                stream=True,
                headers={"User-Agent": "CyberURL-Analyst/1.2 (Educational)"},
            )
            response.raise_for_status()

            # Download com progresso usando streaming
            total_size = int(response.headers.get('content-length', 0))
            if total_size > _MAX_DOWNLOAD_BYTES:
                return DownloadResult(
                    dataset_id=dataset_id,
                    success=False,
                    error=(
                        f"Arquivo muito grande ({total_size / 1024 / 1024:.1f} MB). "
                        f"Limite: {_MAX_DOWNLOAD_BYTES / 1024 / 1024:.0f} MB."
                    ),
                )
            content = self._stream_download(response, total_size, progress_callback)

            # Processa conforme formato
            if fmt == "csv_zip":
                result = self._save_zip_csv_from_bytes(content, dest)
            elif fmt == "txt":
                result = self._save_text_from_str(content.decode('utf-8', errors='ignore'), dest, info)
            elif fmt == "csv_no_header":
                result = self._save_raw_from_str(content.decode('utf-8', errors='ignore'), dest)
            else:
                result = self._save_csv_from_str(content.decode('utf-8', errors='ignore'), dest, info)

            result.dataset_id = dataset_id
            if result.success:
                self._results[dataset_id] = result
                logger.info(
                    "'%s' baixado com sucesso: %d bytes, %d linhas",
                    info["name"], result.size_bytes, result.lines_count,
                )

            return result

        except requests.Timeout:
            err = f"Timeout ao baixar '{info['name']}' ({DATASET_DOWNLOAD_TIMEOUT}s)."
            logger.error(err)
            return DownloadResult(dataset_id=dataset_id, success=False, error=err)
        except requests.ConnectionError:
            err = f"Sem conexão para baixar '{info['name']}'. Verifique sua internet."
            logger.error(err)
            return DownloadResult(dataset_id=dataset_id, success=False, error=err)
        except requests.HTTPError as e:
            err = f"Erro HTTP ao baixar '{info['name']}': {e.response.status_code}"
            logger.error(err)
            return DownloadResult(dataset_id=dataset_id, success=False, error=err)
        except Exception as e:
            err = f"Erro ao baixar '{info['name']}': {type(e).__name__}: {e}"
            logger.error(err)
            return DownloadResult(dataset_id=dataset_id, success=False, error=err)

    def download_all_auto(self) -> dict[str, DownloadResult]:
        """Baixa todos os datasets auto-baixáveis (sem autenticação)."""
        from config.settings import AUTO_DOWNLOADABLE
        results = {}
        for ds_id in AUTO_DOWNLOADABLE:
            results[ds_id] = self.download(ds_id)
        return results

    def get_local_status(self) -> dict[str, dict]:
        """Retorna status local de cada dataset (existe, tamanho, data)."""
        status = {}
        for ds_id, info in DATASET_REGISTRY.items():
            file_path = self._download_dir / info["file"]
            # Também verifica amostras locais
            if not file_path.exists():
                sample_map = {
                    "phishtank": Path(DATASETS_DOWNLOAD_DIR).parent / "phishtank_sample.csv",
                    "urlhaus_full": Path(DATASETS_DOWNLOAD_DIR).parent / "urlhaus_sample.csv",
                    "majestic": Path(DATASETS_DOWNLOAD_DIR).parent / "majestic_million_sample.csv",
                }
                alt = sample_map.get(ds_id)
                if alt and alt.exists():
                    file_path = alt

            exists = file_path.exists()
            size = file_path.stat().st_size if exists else 0
            modified = (
                datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                if exists else ""
            )

            status[ds_id] = {
                "name": info["name"],
                "category": info["category"],
                "exists": exists,
                "file": str(file_path),
                "size_bytes": size,
                "size_human": self._human_size(size),
                "modified": modified,
                "requires_key": info.get("requires_key", False),
                "manual": info.get("manual", False),
                "auto": not info.get("requires_key") and not info.get("manual") and bool(info.get("url")),
                "description": info.get("description", ""),
                "website": info.get("website", ""),
                "license": info.get("license", ""),
            }
        return status

    def get_file_path(self, dataset_id: str) -> Optional[Path]:
        """Retorna path do arquivo de um dataset (download ou amostra)."""
        if dataset_id not in DATASET_REGISTRY:
            return None
        info = DATASET_REGISTRY[dataset_id]
        path = self._download_dir / info["file"]
        if path.exists():
            return path
        return None

    # === Métodos privados ===

    @staticmethod
    def _stream_download(response, total_size: int, progress_callback=None) -> bytes:
        """Baixa conteúdo com streaming e callback de progresso."""
        chunks = []
        downloaded = 0
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                chunks.append(chunk)
                downloaded += len(chunk)
                if downloaded > _MAX_DOWNLOAD_BYTES:
                    raise ValueError(
                        f"Download excedeu limite de {_MAX_DOWNLOAD_BYTES / 1024 / 1024:.0f} MB."
                    )
                if progress_callback and total_size > 0:
                    pct = min(100, int(downloaded / total_size * 100))
                    progress_callback(pct, downloaded, total_size)
        return b"".join(chunks)

    def _save_csv_from_str(self, content: str, dest: Path, info: dict) -> DownloadResult:
        """Salva string como CSV, opcionalmente pulando linhas de cabeçalho."""
        skip = info.get("skip_header_lines", 0)
        if skip > 0:
            lines = content.split("\n")
            content = "\n".join(lines[skip:])
        dest.write_text(content, encoding="utf-8")
        return DownloadResult(
            dataset_id="", success=True, file_path=str(dest),
            size_bytes=dest.stat().st_size, lines_count=content.count("\n"),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _save_text_from_str(self, content: str, dest: Path, info: dict) -> DownloadResult:
        """Salva string como texto, removendo comentários."""
        lines = [l for l in content.strip().split("\n") if l and not l.startswith("#")]
        dest.write_text("\n".join(lines), encoding="utf-8")
        return DownloadResult(
            dataset_id="", success=True, file_path=str(dest),
            size_bytes=dest.stat().st_size, lines_count=len(lines),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _save_raw_from_str(self, content: str, dest: Path) -> DownloadResult:
        """Salva string sem processamento."""
        dest.write_text(content, encoding="utf-8")
        return DownloadResult(
            dataset_id="", success=True, file_path=str(dest),
            size_bytes=dest.stat().st_size, lines_count=content.count("\n"),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def _save_zip_csv_from_bytes(self, content: bytes, dest: Path) -> DownloadResult:
        """Extrai CSV de bytes ZIP e salva."""
        z = zipfile.ZipFile(io.BytesIO(content))
        csv_names = [n for n in z.namelist() if n.endswith(".csv")]
        if not csv_names:
            return DownloadResult(
                dataset_id="", success=False,
                error="Nenhum CSV encontrado dentro do ZIP.",
            )
        text = z.read(csv_names[0]).decode("utf-8", errors="ignore")
        dest.write_text(text, encoding="utf-8")
        return DownloadResult(
            dataset_id="", success=True, file_path=str(dest),
            size_bytes=dest.stat().st_size, lines_count=text.count("\n"),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Converte bytes para formato legível."""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB"]
        i = 0
        size = float(size_bytes)
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"
