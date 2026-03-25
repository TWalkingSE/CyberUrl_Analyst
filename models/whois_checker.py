"""
WhoisChecker — Verificação de idade do domínio via WHOIS local.
Domínios registrados recentemente (< 30 dias) são altamente suspeitos.
"""

import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from config.settings import DOMAIN_YOUNG_DAYS, HEURISTIC_WEIGHTS
from utils.logger import setup_logger

logger = setup_logger("whois_checker")


@dataclass
class WhoisResult:
    """Resultado da consulta WHOIS."""
    success: bool = False
    error: str = ""
    domain: str = ""
    creation_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    registrar: str = ""
    age_days: int = -1
    is_young: bool = False
    weight: int = 0


class WhoisChecker:
    """
    Consulta WHOIS local para determinar idade do domínio.
    Usa python-whois para consulta direta (não passa por API externa).

    NOTA: WHOIS pode falhar para muitos domínios (rate limiting,
    privacidade WHOIS, etc.). O sistema funciona normalmente sem ele.
    """

    def __init__(self):
        self._whois_available = False
        try:
            import whois
            self._whois_module = whois
            self._whois_available = True
        except ImportError:
            logger.warning(
                "Módulo python-whois não disponível. "
                "Análise de idade do domínio desabilitada."
            )

    def check_domain_age(self, domain: str) -> WhoisResult:
        """
        Consulta WHOIS para verificar a idade do domínio.
        Retorna WhoisResult com idade e classificação.
        """
        if not self._whois_available:
            return WhoisResult(error="Módulo WHOIS não disponível.")

        if not domain:
            return WhoisResult(error="Domínio vazio.")

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._whois_module.whois, domain)
                w = future.result(timeout=10)

            if not w or not w.creation_date:
                return WhoisResult(
                    success=True,
                    domain=domain,
                    error="Data de criação não disponível no WHOIS.",
                )

            # creation_date pode ser lista ou datetime
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]

            if not isinstance(creation, datetime):
                return WhoisResult(
                    success=True,
                    domain=domain,
                    error="Formato de data não reconhecido.",
                )

            # Calcula idade
            now = datetime.now(timezone.utc)
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)

            age_delta = now - creation
            age_days = age_delta.days

            # Expiration date
            expiration = None
            if w.expiration_date:
                exp = w.expiration_date
                if isinstance(exp, list):
                    exp = exp[0]
                if isinstance(exp, datetime):
                    expiration = exp

            # Registrar
            registrar = ""
            if w.registrar:
                registrar = str(w.registrar)

            # Classificação
            is_young = age_days < DOMAIN_YOUNG_DAYS
            weight = HEURISTIC_WEIGHTS.get("domain_too_young", 15) if is_young else 0

            result = WhoisResult(
                success=True,
                domain=domain,
                creation_date=creation,
                expiration_date=expiration,
                registrar=registrar,
                age_days=age_days,
                is_young=is_young,
                weight=weight,
            )

            logger.info(
                "WHOIS %s — idade: %d dias, jovem: %s",
                domain, age_days, is_young,
            )
            return result

        except Exception as e:
            logger.debug("WHOIS falhou para %s: %s", domain, e)
            return WhoisResult(
                domain=domain,
                error=f"Consulta WHOIS falhou: {type(e).__name__}",
            )

    @property
    def is_available(self) -> bool:
        """Verifica se o módulo WHOIS está disponível."""
        return self._whois_available
