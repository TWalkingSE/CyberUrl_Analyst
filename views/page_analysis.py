"""
Página Motor de Análise — Análise heurística de URLs.
"""

import streamlit as st

from views.helpers import T, run_analysis, display_report, render_feedback


def page_analysis():
    st.title(f"🛡️ {T('nav.analysis')}")
    st.markdown(T("analysis.subtitle"))

    tab1, tab2 = st.tabs([T("analysis.tab_single"), T("analysis.tab_batch")])
    with tab1:
        url_in = st.text_input(
            "URL", placeholder=T("analysis.placeholder"), key="an_single",
        )
        if (
            st.button(
                f"🛡️ {T('analysis.btn_analyze')}",
                key="btn_an", type="primary",
            )
            and url_in
        ):
            with st.spinner("Analisando..."):
                report = run_analysis(url_in.strip())
            if report:
                display_report(report)
                render_feedback(report)

    with tab2:
        batch = st.text_area(
            "Uma URL por linha", height=100, key="an_batch",
        )
        if (
            st.button(f"📋 {T('analysis.btn_batch')}", key="btn_batch")
            and batch
        ):
            urls = [line.strip() for line in batch.splitlines() if line.strip()]
            for i, u in enumerate(urls):
                st.markdown(f"---\n### Análise {i + 1}/{len(urls)}")
                with st.spinner(f"Analisando {u[:50]}..."):
                    r = run_analysis(u)
                if r:
                    display_report(r)

    if st.session_state.analysis_history:
        with st.expander("📜 Histórico da sessão", expanded=False):
            for item in st.session_state.analysis_history[:20]:
                st.text(f"{item['emoji']} {item['url']}")
