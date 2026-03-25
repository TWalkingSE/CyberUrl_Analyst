"""
Página Dashboard — Estatísticas, gráficos e histórico.

Melhorias:
  #10  Paginação no histórico (10 itens por página)
"""

import time

import plotly.graph_objects as go
import streamlit as st

from config.settings import APP_NAME
from models.persistence import load_history, load_progress, load_badges, BADGE_DEFINITIONS
from views.helpers import T


HISTORY_PAGE_SIZE = 10


def page_dashboard():
    st.title(f"🏠 {T('nav.dashboard')} — {APP_NAME}")

    # Onboarding (#M7) — mostrado apenas para novos usuários
    if not st.session_state.get("onboarding_dismissed"):
        with st.container():
            st.info(
                "👋 **Bem-vindo ao CyberURL Analyst!**\n\n"
                "Esta é uma ferramenta **educacional** para aprender a identificar "
                "URLs maliciosas e ataques de phishing.\n\n"
                "**Fluxo recomendado para iniciantes:**\n"
                "1. 🔍 **Anatomia** — Entenda como uma URL é formada\n"
                "2. 🛡️ **Análise** — Analise URLs reais com heurísticas e ML\n"
                "3. ❓ **Quiz** — Teste seus conhecimentos\n"
                "4. 🎭 **Cenários** — Pratique com simulações realistas\n"
                "5. 📖 **Glossário** — Consulte termos quando tiver dúvidas\n"
            )
            if st.button("✅ Entendi, não mostrar novamente", key="btn_onboard"):
                st.session_state.onboarding_dismissed = True
                st.rerun()
    else:
        st.markdown("Bem-vindo! Use a sidebar para navegar entre os módulos.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔍 Análises", st.session_state.analysis_count)
    c2.metric("🟢 Seguras (safe)", st.session_state.safe_count)
    c3.metric("🟡 Suspeitas (suspicious)", st.session_state.suspicious_count)
    c4.metric("🔴 Maliciosas (malicious)", st.session_state.malicious_count)

    # Gráfico de distribuição
    total = (
        st.session_state.safe_count
        + st.session_state.suspicious_count
        + st.session_state.malicious_count
    )
    if total > 0:
        st.subheader("📊 Distribuição de Classificações")
        fig = go.Figure(data=[go.Pie(
            labels=["Seguras", "Suspeitas", "Maliciosas"],
            values=[
                st.session_state.safe_count,
                st.session_state.suspicious_count,
                st.session_state.malicious_count,
            ],
            marker_colors=["#4CAF50", "#FFC107", "#F44336"],
            hole=0.4,
        )])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#CCCCCC",
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, width="stretch")

    # Progresso de Aprendizado (#M5)
    progress = load_progress()
    threats = progress.get("threats_identified", {})
    has_progress = (
        progress.get("quiz_rounds", 0) > 0
        or progress.get("scenarios_completed", 0) > 0
        or sum(threats.values()) > 0
    )
    if has_progress:
        st.subheader("📈 Seu Progresso de Aprendizado")
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric("🎯 Rodadas Quiz", progress.get("quiz_rounds", 0))
        pc2.metric(
            "🏆 Melhor Quiz",
            f"{int(progress.get('quiz_best_accuracy', 0) * 100)}%",
        )
        pc3.metric("🎭 Cenários", progress.get("scenarios_completed", 0))
        pc4.metric(
            "🏆 Melhor Cenário",
            f"{int(progress.get('scenarios_best_accuracy', 0) * 100)}%",
        )

        # Radar chart de ameaças identificadas
        threat_labels = {
            "typosquatting": "Typosquatting",
            "dga": "DGA",
            "tld_risco": "TLD Risco",
            "ip_em_url": "IP em URL",
            "http_inseguro": "HTTP",
            "url_encurtada": "Encurtada",
            "subdominio_enganoso": "Subdomínio",
            "palavras_gatilho": "Gatilhos",
            "dominio_falso": "Dom. Falso",
            "open_redirect": "Redirect",
            "homografo": "Homógrafo",
            "url_encoding": "Encoding",
        }
        labels = list(threat_labels.values())
        values = [threats.get(k, 0) for k in threat_labels]
        if max(values) > 0:
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                fillcolor="rgba(76, 175, 80, 0.2)",
                line_color="#4CAF50",
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, color="#555"),
                    bgcolor="rgba(0,0,0,0)",
                    angularaxis=dict(color="#AAA"),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#CCCCCC",
                height=320,
                margin=dict(t=30, b=30, l=60, r=60),
                showlegend=False,
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            st.caption(
                "Gráfico mostra quantas vezes você identificou cada tipo de ameaça "
                "nos quizzes e análises. Áreas maiores = mais experiência."
            )

    # Conquistas (#M8)
    earned_badges = load_badges()
    if earned_badges:
        st.subheader("🏅 Conquistas")
        badge_cols = st.columns(min(len(earned_badges), 5))
        for i, bid in enumerate(earned_badges):
            bdef = next((b for b in BADGE_DEFINITIONS if b["id"] == bid), None)
            if bdef:
                with badge_cols[i % min(len(earned_badges), 5)]:
                    st.markdown(
                        f'<div style="text-align:center;background:#1a1a2e;'
                        f'border:1px solid #333;border-radius:10px;padding:10px;'
                        f'margin:4px 0">'
                        f'<span style="font-size:2em">{bdef["icon"]}</span><br>'
                        f'<strong style="color:#FFF;font-size:0.8em">{bdef["name"]}</strong><br>'
                        f'<span style="color:#888;font-size:0.7em">{bdef["desc"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        # Show remaining locked badges
        locked = [b for b in BADGE_DEFINITIONS if b["id"] not in earned_badges]
        if locked:
            with st.expander(f"🔒 {len(locked)} conquistas restantes"):
                for b in locked:
                    st.caption(f"🔒 **{b['name']}** — {b['desc']}")

    # Histórico com paginação (#10) e busca/filtro
    hist = load_history()
    if hist:
        st.subheader("📜 Últimas Análises (persistidas)")

        # Filtros
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            search_term = st.text_input(
                "🔎 Buscar URL", placeholder="Filtrar por URL...",
                key="hist_search", label_visibility="collapsed",
            )
        with col_filter:
            class_filter = st.selectbox(
                "Classificação", ["Todas", "Segura", "Suspeita", "Maliciosa"],
                key="hist_class_filter", label_visibility="collapsed",
            )

        _CLASS_MAP = {"Segura": "safe", "Suspeita": "suspicious", "Maliciosa": "malicious"}
        filtered = hist
        if search_term:
            term_lower = search_term.lower()
            filtered = [h for h in filtered if term_lower in h.get("url", "").lower()]
        if class_filter != "Todas":
            cls_val = _CLASS_MAP.get(class_filter)
            filtered = [h for h in filtered if h.get("classification") == cls_val]

        total_pages = max(1, (len(filtered) + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE)

        if "hist_page" not in st.session_state:
            st.session_state.hist_page = 0

        page_num = min(st.session_state.hist_page, total_pages - 1)
        start = page_num * HISTORY_PAGE_SIZE
        end = start + HISTORY_PAGE_SIZE
        page_items = filtered[start:end]

        for h in page_items:
            ts = time.strftime(
                "%d/%m %H:%M", time.localtime(h.get("timestamp", 0))
            )
            st.markdown(
                f"{h.get('emoji', '')} `{h.get('url', '')}` "
                f"— Score: {h.get('score', '-')} — {ts}"
            )

        if total_pages > 1:
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("← Anterior", key="hist_prev",
                             disabled=(page_num == 0)):
                    st.session_state.hist_page = max(0, page_num - 1)
                    st.rerun()
            with col_info:
                st.caption(
                    f"Página {page_num + 1} de {total_pages} "
                    f"({len(filtered)} registros)"
                )
            with col_next:
                if st.button("Próxima →", key="hist_next",
                             disabled=(page_num >= total_pages - 1)):
                    st.session_state.hist_page = page_num + 1
                    st.rerun()

    st.divider()
    st.subheader("🚀 Guia Rápido")
    for title, desc in [
        ("🔍 Anatomia", "Decomponha URLs com código de cores"),
        ("🛡️ Análise", "25+ heurísticas + datasets + ML"),
        ("📊 Relatório", "Relatórios didáticos exportáveis"),
        ("❓ Quiz", "Teste seus conhecimentos"),
        ("🎭 Cenários", "Simule phishing realista"),
        ("🔌 APIs", "VirusTotal, URLScan, Safe Browsing"),
        ("📦 Datasets", "Gerencie datasets"),
        ("⚙️ Config", "Wordlists, ML, idioma"),
    ]:
        st.markdown(f"**{title}** — {desc}")
