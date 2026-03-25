"""
Página Relatório Didático — Visualização e exportação de relatórios.
"""

import streamlit as st

from views.helpers import T, display_report
from views.resources import get_report_gen


def page_report():
    st.title(f"📊 {T('nav.report')}")
    report = st.session_state.last_report
    if report is None:
        st.info(T("report.placeholder"))
        return

    rg = get_report_gen()
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📋 Baixar TXT",
            rg.format_text_report(report),
            "relatorio.txt",
            "text/plain",
        )
    with c2:
        try:
            st.download_button(
                "📄 Baixar HTML",
                rg.format_html_report(report),
                "relatorio.html",
                "text/html",
            )
        except Exception:
            pass
    display_report(report)
