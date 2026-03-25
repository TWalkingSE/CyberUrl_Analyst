"""
Página APIs Externas — Consulta VirusTotal, URLScan, Safe Browsing.

Melhorias:
  #4  Rate limiting integrado com utils/rate_limiter.py
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from config.settings import (
    VIRUSTOTAL_RATE_LIMIT, VIRUSTOTAL_DAILY_LIMIT,
    URLSCAN_PRIVATE_DAILY_LIMIT, SAFEBROWSING_DAILY_LIMIT,
)
from utils.sanitizer import sanitize_input
from utils.rate_limiter import RateLimiter, RateLimitConfig
from views.helpers import T
from views.resources import API_AVAILABLE, ThreatIntelClient


@st.cache_resource
def _get_rate_limiter():
    """Rate limiter compartilhado (#4)."""
    rl = RateLimiter()
    rl.register_service("virustotal", RateLimitConfig(
        requests_per_minute=VIRUSTOTAL_RATE_LIMIT,
        requests_per_day=VIRUSTOTAL_DAILY_LIMIT,
    ))
    rl.register_service("urlscan", RateLimitConfig(
        requests_per_minute=10,
        requests_per_day=URLSCAN_PRIVATE_DAILY_LIMIT,
    ))
    rl.register_service("safebrowsing", RateLimitConfig(
        requests_per_minute=60,
        requests_per_day=SAFEBROWSING_DAILY_LIMIT,
    ))
    return rl


def page_apis():
    st.title(f"🔌 {T('nav.apis')}")
    st.markdown("⚠️ Envia URL para servidores externos.")

    if not API_AVAILABLE:
        st.error("Módulo de API indisponível.")
        return

    # Verificação de conectividade
    try:
        import requests as _req
        _req.head("https://www.google.com", timeout=5)
    except Exception:
        st.warning(
            "⚠️ **Modo Offline** — Sem conexão com a internet. "
            "As APIs externas não estão disponíveis no momento."
        )
        return

    rl = _get_rate_limiter()

    # Mostrar cotas restantes (#4)
    with st.expander("📊 Cotas de API", expanded=False):
        for svc, label in [
            ("virustotal", "VirusTotal"),
            ("urlscan", "URLScan.io"),
            ("safebrowsing", "Safe Browsing"),
        ]:
            rem = rl.get_remaining(svc)
            st.caption(
                f"**{label}** — {rem['minute']} req/min restantes | "
                f"{rem['daily']} req/dia restantes"
            )

    with st.expander("🔑 Chaves de API", expanded=False):
        vt = st.text_input(
            "VirusTotal",
            value=os.getenv("VIRUSTOTAL_API_KEY", ""),
            type="password", key="vt",
        )
        us = st.text_input(
            "URLScan.io",
            value=os.getenv("URLSCAN_API_KEY", ""),
            type="password", key="us",
        )
        sb = st.text_input(
            "Safe Browsing",
            value=os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", ""),
            type="password", key="sb",
        )

    # Consentimento antes de habilitar consultas
    if not st.session_state.consent_given:
        st.warning(
            "⚠️ Esta funcionalidade envia URLs para servidores externos "
            "(VirusTotal, URLScan.io, Google Safe Browsing)."
        )
        if st.button("✅ Concordo com o envio de dados", key="btn_consent"):
            st.session_state.consent_given = True
            st.rerun()
        return

    url_in = st.text_input(
        "URL", placeholder="https://exemplo.com", key="api_url",
    )

    if st.button("🔍 Consultar APIs", key="btn_api") and url_in:
        san = sanitize_input(url_in.strip())
        if san.warnings:
            st.warning("\n".join(san.warnings))
        if not san.is_valid_url:
            st.error("URL inválida.")
            return
        url = san.sanitized_input

        client = ThreatIntelClient()
        results = {}

        # Rate-limited API calls (#4)
        def _check_vt():
            if not vt:
                return ("vt", None)
            if not rl.can_make_request("virustotal"):
                return ("vt", _rate_limit_error("VirusTotal"))
            rl.record_request("virustotal")
            return ("vt", client.check_virustotal(url, vt))

        def _check_us():
            if not us:
                return ("us", None)
            if not rl.can_make_request("urlscan"):
                return ("us", _rate_limit_error("URLScan.io"))
            rl.record_request("urlscan")
            return ("us", client.check_urlscan(url, us))

        def _check_sb():
            if not sb:
                return ("sb", None)
            if not rl.can_make_request("safebrowsing"):
                return ("sb", _rate_limit_error("Safe Browsing"))
            rl.record_request("safebrowsing")
            return ("sb", client.check_safebrowsing(url, sb))

        with st.spinner("Consultando APIs em paralelo..."):
            with ThreadPoolExecutor(max_workers=3) as ex:
                futures = [
                    ex.submit(f) for f in [_check_vt, _check_us, _check_sb]
                ]
                for fut in as_completed(futures):
                    try:
                        k, r = fut.result()
                        results[k] = r
                    except Exception as e:
                        st.error(f"❌ Erro na consulta: {e}")

        _display_vt_result(results.get("vt"))
        _display_us_result(results.get("us"))
        _display_sb_result(results.get("sb"))


def _rate_limit_error(service):
    """Cria objeto simulado de erro de rate limit."""
    class _Err:
        success = False
        error = f"Rate limit atingido para {service}. Aguarde."
    return _Err()


def _display_vt_result(r):
    if r is None:
        st.info("VirusTotal: chave não configurada.")
    elif r.success:
        if r.detections > 5:
            st.error(
                f"🔴 **VirusTotal — {r.detection_ratio}** — "
                f"{r.detections} detecções (ALTO RISCO)"
            )
        elif r.detections > 0:
            st.warning(f"⚠️ **VirusTotal — {r.detection_ratio}** (ATENÇÃO)")
        else:
            st.success(
                f"✅ **VirusTotal — {r.detection_ratio}** — "
                f"Nenhuma detecção (LIMPO)"
            )
    else:
        st.error(f"❌ VT: {r.error}")


def _display_us_result(r):
    if r is None:
        st.info("URLScan.io: chave não configurada.")
    elif r.success:
        st.info(
            f"🔍 **URLScan.io** — Scan submetido. {r.result_url or ''}"
        )
    else:
        st.error(f"❌ US: {r.error}")


def _display_sb_result(r):
    if r is None:
        st.info("Safe Browsing: chave não configurada.")
    elif r.success:
        if r.is_unsafe:
            st.error(
                f"🔴 **Safe Browsing — INSEGURO** — "
                f"{', '.join(r.threat_types or ['ameaça'])} (PERIGO)"
            )
        else:
            st.success("✅ **Safe Browsing — Seguro** (LIMPO)")
    else:
        st.error(f"❌ SB: {r.error}")
