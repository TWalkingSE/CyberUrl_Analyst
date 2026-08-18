"""
ThreatIntelClient — Integração com APIs externas de inteligência de ameaças.
Toda comunicação externa passa por aqui.
Implementa rate limiting, fallback e consentimento.

APIs suportadas:
- VirusTotal API v3
- URLScan.io API
- Google Safe Browsing API v4
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
import validators
from dotenv import load_dotenv

from utils.logger import setup_logger, log_api_call
from utils.rate_limiter import RateLimiter, RateLimitConfig
from config.settings import (
    VIRUSTOTAL_RATE_LIMIT,
    VIRUSTOTAL_DAILY_LIMIT,
    URLSCAN_PRIVATE_DAILY_LIMIT,
    SAFEBROWSING_DAILY_LIMIT,
)

load_dotenv()
logger = setup_logger("api_client")


def _format_scan_date(raw) -> str:
    """
    Normaliza a data de scan do VirusTotal para ISO-8601.

    A API devolve um timestamp Unix (int), mas o campo é `str` — guardar o
    int cru fazia a formatação a jusante exibir "1712345678" como data.
    """
    if not raw:
        return ""
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            return ""
    return str(raw)


# === Dataclasses de resultado ===

@dataclass
class VTResult:
    """Resultado da verificação VirusTotal."""
    success: bool = False
    error: str = ""
    detections: int = 0
    total_engines: int = 0
    detection_ratio: str = ""
    categories: list[str] = field(default_factory=list)
    community_score: int = 0
    permalink: str = ""
    scan_date: str = ""


@dataclass
class USResult:
    """Resultado da verificação URLScan.io."""
    success: bool = False
    error: str = ""
    screenshot_url: str = ""
    effective_url: str = ""
    ip_addresses: list[str] = field(default_factory=list)
    certificates: list[dict] = field(default_factory=list)
    redirects: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    verdicts_malicious: bool = False
    score: int = 0
    result_url: str = ""


@dataclass
class SBResult:
    """Resultado da verificação Google Safe Browsing."""
    success: bool = False
    error: str = ""
    is_unsafe: bool = False
    threat_types: list[str] = field(default_factory=list)
    platform_types: list[str] = field(default_factory=list)


class ThreatIntelClient:
    """
    Integração com APIs externas. Toda comunicação externa passa por aqui.
    Implementa rate limiting, fallback e consentimento.

    IMPORTANTE:
    - Chaves de API são lidas de variáveis de ambiente (.env).
    - Rate limiting local para não exceder tiers gratuitos.
    - Fallback gracioso se API indisponível.
    - Consentimento do usuário é gerenciado pela View, não pelo Model.
    """

    REQUEST_TIMEOUT = 30  # segundos

    def __init__(self):
        self._rate_limiter = RateLimiter()
        self._setup_rate_limits()

    def _setup_rate_limits(self):
        """Configura rate limits para cada serviço."""
        self._rate_limiter.register_service("virustotal", RateLimitConfig(
            requests_per_minute=VIRUSTOTAL_RATE_LIMIT,
            requests_per_day=VIRUSTOTAL_DAILY_LIMIT,
        ))
        self._rate_limiter.register_service("urlscan", RateLimitConfig(
            requests_per_minute=10,
            requests_per_day=URLSCAN_PRIVATE_DAILY_LIMIT,
        ))
        self._rate_limiter.register_service("safebrowsing", RateLimitConfig(
            requests_per_minute=60,
            requests_per_day=SAFEBROWSING_DAILY_LIMIT,
        ))

    # === VirusTotal ===

    def check_virustotal(self, url: str, api_key: Optional[str] = None) -> VTResult:
        """
        Submete URL para verificação no VirusTotal API v3.
        Tier gratuito: 4 req/min, 500/dia.
        """
        key = api_key or os.getenv("VIRUSTOTAL_API_KEY", "")
        if not key:
            return VTResult(error="Chave de API do VirusTotal não configurada.")

        if not validators.url(url):
            return VTResult(error="URL inválida.")

        if not self._rate_limiter.can_make_request("virustotal"):
            remaining = self._rate_limiter.get_remaining("virustotal")
            wait = self._rate_limiter.get_wait_time("virustotal")
            return VTResult(
                error=f"Rate limit atingido. Restantes — minuto: {remaining['minute']}, "
                      f"dia: {remaining['daily']}. Aguarde {wait:.0f}s."
            )

        try:
            # Passo 1: Submeter URL para scan
            import base64
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")

            headers = {"x-apikey": key}
            response = requests.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
            )
            self._rate_limiter.record_request("virustotal")

            if response.status_code == 404:
                # URL não encontrada, submeter para scan.
                # Recheca a cota: este é um SEGUNDO request e o limite só foi
                # verificado antes do primeiro — sem isto, o par GET+POST
                # pode ultrapassar o teto do tier gratuito.
                if not self._rate_limiter.can_make_request("virustotal"):
                    wait = self._rate_limiter.get_wait_time("virustotal")
                    return VTResult(
                        error=(
                            "Rate limit atingido antes de submeter a URL para "
                            f"análise. Aguarde {wait:.0f}s e tente de novo."
                        )
                    )
                submit_resp = requests.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers=headers,
                    data={"url": url},
                    timeout=self.REQUEST_TIMEOUT,
                )
                self._rate_limiter.record_request("virustotal")

                if submit_resp.status_code != 200:
                    log_api_call(logger, "VirusTotal", False, f"HTTP {submit_resp.status_code}")
                    return VTResult(error=f"Erro ao submeter URL: HTTP {submit_resp.status_code}")

                return VTResult(
                    success=True,
                    error="URL submetida para análise. Resultados podem levar alguns minutos.",
                )

            if response.status_code != 200:
                log_api_call(logger, "VirusTotal", False, f"HTTP {response.status_code}")
                return VTResult(error=f"Erro na API: HTTP {response.status_code}")

            data = response.json().get("data", {}).get("attributes", {})
            stats = data.get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            total = sum(stats.values()) if stats else 0

            detections = malicious + suspicious

            # Extrair categorias
            categories = []
            for engine, cat in data.get("categories", {}).items():
                if cat not in categories:
                    categories.append(cat)

            result = VTResult(
                success=True,
                detections=detections,
                total_engines=total,
                detection_ratio=f"{detections} / {total}",
                categories=categories[:10],
                community_score=data.get("reputation", 0),
                scan_date=_format_scan_date(data.get("last_analysis_date")),
            )

            log_api_call(logger, "VirusTotal", True, f"{detections}/{total} detecções")
            return result

        except requests.Timeout:
            log_api_call(logger, "VirusTotal", False, "Timeout")
            return VTResult(error="Timeout na conexão com VirusTotal.")
        except requests.ConnectionError:
            log_api_call(logger, "VirusTotal", False, "Sem conexão")
            return VTResult(error="Sem conexão com VirusTotal. Verifique sua internet.")
        except Exception as e:
            log_api_call(logger, "VirusTotal", False, str(e))
            return VTResult(error=f"Erro inesperado: {e}")

    # === URLScan.io ===

    def check_urlscan(self, url: str, api_key: Optional[str] = None,
                      private: bool = True) -> USResult:
        """
        Submete URL para scan no URLScan.io.
        Usa scan privado por padrão (IMPORTANTE: para proteger dados do usuário).
        """
        key = api_key or os.getenv("URLSCAN_API_KEY", "")
        if not key:
            return USResult(error="Chave de API do URLScan.io não configurada.")

        if not validators.url(url):
            return USResult(error="URL inválida.")

        if not self._rate_limiter.can_make_request("urlscan"):
            return USResult(error="Rate limit atingido para URLScan.io.")

        try:
            headers = {
                "API-Key": key,
                "Content-Type": "application/json",
            }
            payload = {
                "url": url,
                "visibility": "private" if private else "public",
            }

            response = requests.post(
                "https://urlscan.io/api/v1/scan/",
                headers=headers,
                json=payload,
                timeout=self.REQUEST_TIMEOUT,
            )
            self._rate_limiter.record_request("urlscan")

            if response.status_code != 200:
                log_api_call(logger, "URLScan.io", False, f"HTTP {response.status_code}")
                return USResult(error=f"Erro na API: HTTP {response.status_code}")

            data = response.json()
            result_url = data.get("result", "")

            # Os resultados levam alguns segundos para processar
            result = USResult(
                success=True,
                result_url=result_url,
            )

            log_api_call(logger, "URLScan.io", True, f"Scan submetido: {result_url}")
            return result

        except requests.Timeout:
            log_api_call(logger, "URLScan.io", False, "Timeout")
            return USResult(error="Timeout na conexão com URLScan.io.")
        except requests.ConnectionError:
            log_api_call(logger, "URLScan.io", False, "Sem conexão")
            return USResult(error="Sem conexão com URLScan.io.")
        except Exception as e:
            log_api_call(logger, "URLScan.io", False, str(e))
            return USResult(error=f"Erro inesperado: {e}")

    # === Google Safe Browsing ===

    def check_safebrowsing(self, url: str, api_key: Optional[str] = None) -> SBResult:
        """
        Verifica URL contra o Google Safe Browsing API v4.
        Verificação binária: seguro ou inseguro.
        """
        key = api_key or os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")
        if not key:
            return SBResult(error="Chave de API do Google Safe Browsing não configurada.")

        if not validators.url(url):
            return SBResult(error="URL inválida.")

        if not self._rate_limiter.can_make_request("safebrowsing"):
            return SBResult(error="Rate limit atingido para Google Safe Browsing.")

        try:
            payload = {
                "client": {
                    "clientId": "cyberurl-analyst",
                    "clientVersion": "1.0.0",
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                        "POTENTIALLY_HARMFUL_APPLICATION",
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url}],
                },
            }

            response = requests.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={key}",
                json=payload,
                timeout=self.REQUEST_TIMEOUT,
            )
            self._rate_limiter.record_request("safebrowsing")

            if response.status_code != 200:
                log_api_call(logger, "Safe Browsing", False, f"HTTP {response.status_code}")
                return SBResult(error=f"Erro na API: HTTP {response.status_code}")

            data = response.json()
            matches = data.get("matches", [])

            threat_types = list({m.get("threatType", "") for m in matches})
            platform_types = list({m.get("platformType", "") for m in matches})

            result = SBResult(
                success=True,
                is_unsafe=bool(matches),
                threat_types=threat_types,
                platform_types=platform_types,
            )

            status = "INSEGURO" if matches else "seguro"
            log_api_call(logger, "Safe Browsing", True, status)
            return result

        except requests.Timeout:
            log_api_call(logger, "Safe Browsing", False, "Timeout")
            return SBResult(error="Timeout na conexão com Google Safe Browsing.")
        except requests.ConnectionError:
            log_api_call(logger, "Safe Browsing", False, "Sem conexão")
            return SBResult(error="Sem conexão com Google Safe Browsing.")
        except Exception as e:
            log_api_call(logger, "Safe Browsing", False, str(e))
            return SBResult(error=f"Erro inesperado: {e}")

    # === Utilitários ===

    def get_remaining_quota(self) -> dict:
        """Retorna cotas restantes para todos os serviços."""
        return {
            "virustotal": self._rate_limiter.get_remaining("virustotal"),
            "urlscan": self._rate_limiter.get_remaining("urlscan"),
            "safebrowsing": self._rate_limiter.get_remaining("safebrowsing"),
        }

    def is_api_configured(self, service: str) -> bool:
        """Verifica se a chave de API está configurada para o serviço."""
        env_map = {
            "virustotal": "VIRUSTOTAL_API_KEY",
            "urlscan": "URLSCAN_API_KEY",
            "safebrowsing": "GOOGLE_SAFE_BROWSING_API_KEY",
        }
        env_var = env_map.get(service, "")
        return bool(os.getenv(env_var, ""))
