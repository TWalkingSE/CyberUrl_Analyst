"""
CyberURL Analyst v2.0 — Aplicação Streamlit.
Ferramenta educacional de análise de URLs e domínios maliciosos.

Ponto de entrada único. Lógica de páginas em views/.

Uso:
    streamlit run app.py
"""

import sys
import os
import secrets
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

import streamlit as st
from PIL import Image

from config.settings import APP_NAME, APP_VERSION
from models.persistence import load_stats
from utils.i18n import tr, set_language, AVAILABLE_LANGUAGES

from views import (
    page_dashboard, page_anatomy, page_analysis, page_report,
    page_quiz, page_scenarios, page_apis, page_datasets, page_settings,
    page_glossary,
)


# =====================================================================
# Page Config
# =====================================================================
st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon=Image.open(PROJECT_DIR / "phishing_tecnologico.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS — classes de severidade + acessibilidade (#9)
st.markdown("""<style>
.finding-critical{border-left:4px solid #F44336;background:#1a1a2e;border-radius:6px;padding:12px;margin-bottom:8px}
.finding-warning{border-left:4px solid #FFC107;background:#1a1a2e;border-radius:6px;padding:12px;margin-bottom:8px}
.finding-safe{border-left:4px solid #4CAF50;background:#1a1a2e;border-radius:6px;padding:12px;margin-bottom:8px}
.finding-info{border-left:4px solid #2196F3;background:#1a1a2e;border-radius:6px;padding:12px;margin-bottom:8px}
[role="status"]{outline:none}
[role="region"]{outline:none}
</style>""", unsafe_allow_html=True)


# =====================================================================
# Session State
# =====================================================================
def _init_state():
    persisted = load_stats()
    defaults = {
        "analysis_count": persisted.get("analysis_count", 0),
        "safe_count": persisted.get("safe_count", 0),
        "suspicious_count": persisted.get("suspicious_count", 0),
        "malicious_count": persisted.get("malicious_count", 0),
        "analysis_history": [],
        "last_report": None,
        "quiz_engine": None, "quiz_question": None, "quiz_q_num": 0,
        "quiz_answered": False, "quiz_running": False,
        "scenario_index": 0, "scenario_score": 0, "scenario_total": 0,
        "scenario_running": False, "scenario_answered": False,
        "scenario_presentation": False,
        "consent_given": False, "authenticated": False,
        "lang": "pt",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


# =====================================================================
# i18n helper
# =====================================================================
def T(key):
    return tr(key, st.session_state.get("lang", "pt"))


# =====================================================================
# Authentication (#5 — timing-safe comparison via secrets.compare_digest)
# =====================================================================
def _check_auth():
    pwd_env = os.getenv("CYBERURL_PASSWORD", "")
    if not pwd_env:
        return True
    if st.session_state.get("authenticated"):
        return True
    st.title("🔒 CyberURL Analyst")
    pwd = st.text_input("Senha de acesso", type="password", key="auth_pwd")
    if st.button("Entrar", key="btn_auth"):
        if secrets.compare_digest(pwd.encode(), pwd_env.encode()):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    return False

if not _check_auth():
    st.stop()


# =====================================================================
# Sidebar
# =====================================================================
with st.sidebar:
    st.image(str(PROJECT_DIR / "phishing_tecnologico.png"), width=80)
    st.markdown("## CyberURL Analyst")
    st.divider()

    _PAGE_OPTIONS = [
        ("🏠", "nav.dashboard", page_dashboard),
        ("🔍", "nav.anatomy",   page_anatomy),
        ("🛡️", "nav.analysis",  page_analysis),
        ("📊", "nav.report",    page_report),
        ("❓", "nav.quiz",      page_quiz),
        ("🎭", "nav.scenarios", page_scenarios),
        ("🔌", "nav.apis",      page_apis),
        ("📦", "nav.datasets",  page_datasets),
        ("📖", "nav.glossary",  page_glossary),
        ("⚙️", "nav.settings",  page_settings),
    ]
    _page_labels = [f"{icon} {T(key)}" for icon, key, _ in _PAGE_OPTIONS]
    page = st.radio(
        "Nav", _page_labels, label_visibility="collapsed",
    )

    st.divider()
    lang_keys = list(AVAILABLE_LANGUAGES.keys())
    cur_idx = (
        lang_keys.index(st.session_state.lang)
        if st.session_state.lang in lang_keys else 0
    )
    sel_lang = st.selectbox(
        "🌐", lang_keys, index=cur_idx,
        format_func=lambda x: AVAILABLE_LANGUAGES[x], key="lang_sel",
    )
    if sel_lang != st.session_state.lang:
        st.session_state.lang = sel_lang
        set_language(sel_lang)
        st.rerun()

    st.caption(f"v{APP_VERSION}")


# =====================================================================
# Router
# =====================================================================
_page_index = _page_labels.index(page) if page in _page_labels else 0
_PAGE_OPTIONS[_page_index][2]()
