"""
Página Simulador de Cenários — Cenários realistas de phishing.
"""

import html as _html

import streamlit as st

from models.scenarios import SCENARIOS, SCENARIO_CATEGORIES
from models.persistence import update_scenario_progress, unlock_badge
from views.helpers import T


def page_scenarios():
    st.title(f"🎭 {T('nav.scenarios')}")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c2:
        category = st.selectbox("Categoria", SCENARIO_CATEGORIES, key="sc_cat")
    with c3:
        pres_mode = st.checkbox("📽️ Apresentação", key="sc_pres")
    with c1:
        st.metric(
            "🎯 Score",
            f"{st.session_state.scenario_score}/"
            f"{st.session_state.scenario_total}",
        )

    filtered = (
        SCENARIOS
        if category == "Todos"
        else [s for s in SCENARIOS if s["category"] == category]
    )

    if not st.session_state.scenario_running:
        if st.button(
            "▶️ Iniciar Simulação", type="primary", key="btn_sc_start",
        ):
            st.session_state.scenario_running = True
            st.session_state.scenario_index = 0
            st.session_state.scenario_score = 0
            st.session_state.scenario_total = 0
            st.session_state.scenario_answered = False
            st.session_state.scenario_presentation = pres_mode
            st.rerun()
        return

    idx = st.session_state.scenario_index
    is_pres = st.session_state.scenario_presentation

    if idx >= len(filtered):
        _render_scenario_results()
        return

    s = filtered[idx]
    ch = s["channel"].lower()
    bc = (
        "#25D366" if "whatsapp" in ch
        else "#0088cc" if "telegram" in ch
        else "#0084FF" if "messenger" in ch
        else "#FFC107" if "telefone" in ch
        else "#FF9800" if "papel" in ch or "físico" in ch
        else "#9C27B0" if "push" in ch or "app" in ch
        else "#333355"
    )

    fs = "1.1em" if is_pres else "0.9em"

    st.markdown(
        f"**{s['category_icon']} {s['category']}** — "
        f"{s['channel_icon']} {s['channel']}"
        + (f"  *(cenário {idx + 1}/{len(filtered)})*" if is_pres else "")
    )

    e = _html.escape
    st.markdown(
        f'<div style="background:#1e1e2e;border:1px solid {bc};'
        f'border-radius:10px;padding:16px;margin:8px 0">'
        + (
            f'<p style="color:#AAA;font-size:{fs}">De: {e(s["sender"])}</p>'
            if s["sender"] else ""
        )
        + (
            f'<p style="color:#FFF;font-weight:bold;font-size:{fs}">'
            f'Assunto: {e(s["subject"])}</p>'
            if s["subject"] else ""
        )
        + f'<hr style="border-color:#333355">'
        f'<pre style="color:#CCC;white-space:pre-wrap;'
        f'font-family:Courier New;font-size:{fs}">{e(s["body"])}</pre></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.scenario_answered:
        st.subheader(f"🤔 {T('scenarios.question')}")
        ca, cb = st.columns(2)
        with ca:
            if st.button(
                f"👆 {T('scenarios.yes')}", key="sy",
                width="stretch",
            ):
                _submit_scenario(True, s)
                st.rerun()
        with cb:
            if st.button(
                f"🚫 {T('scenarios.no')}", key="sn",
                width="stretch",
            ):
                _submit_scenario(False, s)
                st.rerun()
    else:
        fb = st.session_state.get("_sfb", {})
        if fb.get("correct"):
            st.success("✅ Decisão correta!")
        else:
            if s["is_phishing"]:
                st.error("❌ PHISHING!")
            else:
                st.error("❌ Era legítimo.")
        label = "🔍 Sinais:" if s["is_phishing"] else "✅ Legitimidade:"
        st.subheader(label)
        for i, (n, d) in enumerate(s["alerts"], 1):
            st.markdown(f"**{i}. {n}** — {d}")
        st.warning(s["lesson"])
        if st.button("Próximo →", key="btn_nsc"):
            st.session_state.scenario_index += 1
            st.session_state.scenario_answered = False
            if "_sfb" in st.session_state:
                del st.session_state._sfb
            st.rerun()


def _submit_scenario(click, s):
    st.session_state.scenario_total += 1
    ok = (not click) if s["is_phishing"] else click
    if ok:
        st.session_state.scenario_score += 1
    st.session_state.scenario_answered = True
    st.session_state._sfb = {"correct": ok}


def _render_scenario_results():
    st.subheader("🏆 SIMULAÇÃO CONCLUÍDA")
    total = st.session_state.scenario_total
    score = st.session_state.scenario_score
    acc = int((score / max(1, total)) * 100)
    st.metric("Decisões corretas", f"{score}/{total}")
    st.metric("Precisão", f"{acc}%")

    # Salvar progresso de aprendizado e badges
    update_scenario_progress(score, total)
    unlock_badge("scenario_complete")
    if acc >= 80:
        unlock_badge("scenario_ace")
    if acc >= 80:
        st.success("🌟 Excelente!")
    elif acc >= 60:
        st.info("👍 Bom trabalho!")
    else:
        st.warning("📚 Pratique mais!")

    csv_data = f"Score,Total,Precisão\n{score},{total},{acc}%\n"
    st.download_button(
        "📥 Exportar Resultado",
        csv_data, "cenarios_resultado.csv", "text/csv",
    )
    st.session_state.scenario_running = False
