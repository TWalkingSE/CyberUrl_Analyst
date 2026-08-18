"""
Logging seguro para o CyberURL Analyst.
Nunca registra URLs completas que possam conter dados pessoais.
Usa hash SHA-256 no lugar de URLs originais quando necessário.
"""

import logging
import logging.handlers
from pathlib import Path

from config.settings import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT
from utils.sanitizer import hash_url


def setup_logger(name: str = "cyberurl") -> logging.Logger:
    """
    Configura e retorna o logger principal da aplicação.
    Rotação automática de arquivos de log.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Garante que o diretório de log existe
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    # Handler de arquivo com rotação
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)

    # Handler de console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formato
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_analysis(logger: logging.Logger, url: str, classification: str, score: int):
    """
    Registra uma análise de forma segura.
    A URL é armazenada como hash SHA-256 para proteger dados sensíveis.
    """
    url_hash = hash_url(url)
    logger.info(
        "Análise concluída — hash=%s classificação=%s score=%d",
        url_hash, classification, score,
    )


def log_api_call(logger: logging.Logger, service: str, success: bool, detail: str = ""):
    """Registra chamada a API externa."""
    status = "sucesso" if success else "falha"
    logger.info("API %s — %s %s", service, status, detail)


def log_security_event(logger: logging.Logger, event_type: str, detail: str):
    """Registra evento de segurança (tentativa de uso ofensivo, dados pessoais, etc.)."""
    logger.warning("SEGURANÇA [%s] — %s", event_type, detail)
