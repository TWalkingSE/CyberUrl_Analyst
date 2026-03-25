"""
Página Configurações — Wordlists, ML, feedback.
"""

import streamlit as st

from config import settings
from models.persistence import load_feedback
from views.helpers import T
from views.resources import ML_AVAILABLE, MODEL_PATH, get_ml


def page_settings():
    st.title(f"⚙️ {T('nav.settings')}")

    with st.expander("🎯 Trigger Words", expanded=False):
        tw = st.text_area(
            "Uma por linha",
            "\n".join(settings.TRIGGER_WORDS),
            height=150, key="s_tw",
        )
    with st.expander("⚠️ TLDs de Risco", expanded=False):
        tl = st.text_area(
            "Sem ponto",
            "\n".join(settings.HIGH_RISK_TLDS),
            height=150, key="s_tl",
        )
    with st.expander("🔗 Encurtadores", expanded=False):
        sh = st.text_area(
            "Um por linha",
            "\n".join(settings.URL_SHORTENERS),
            height=150, key="s_sh",
        )

    if st.button(f"💾 {T('settings.apply')}", key="btn_sav"):
        settings.TRIGGER_WORDS.clear()
        settings.TRIGGER_WORDS.extend(
            [line.strip() for line in tw.splitlines() if line.strip()]
        )
        settings.HIGH_RISK_TLDS.clear()
        settings.HIGH_RISK_TLDS.extend(
            [line.strip() for line in tl.splitlines() if line.strip()]
        )
        settings.URL_SHORTENERS.clear()
        settings.URL_SHORTENERS.extend(
            [line.strip() for line in sh.splitlines() if line.strip()]
        )
        st.success(
            f"✅ {len(settings.TRIGGER_WORDS)} triggers, "
            f"{len(settings.HIGH_RISK_TLDS)} TLDs, "
            f"{len(settings.URL_SHORTENERS)} encurtadores"
        )

    st.divider()
    st.subheader("🤖 Classificador ML")
    if not ML_AVAILABLE:
        st.error("scikit-learn não instalado.")
    else:
        from models.ml_classifier import MLClassifier

        clf = get_ml()
        if clf and clf.is_available:
            st.success(
                f"✅ Modelo pronto (acurácia: {clf._accuracy * 100:.1f}%)"
            )
            imp = clf.get_feature_importance()
            if imp:
                for n, s in imp[:7]:
                    st.text(f"  {n:25s} {'█' * int(s * 50)} ({s:.3f})")
        elif MODEL_PATH and MODEL_PATH.exists():
            st.warning("Modelo corrompido. Re-treine.")
        else:
            st.info("Modelo não treinado.")

        if st.button("🧠 Treinar Modelo", key="btn_ml"):
            with st.spinner("Treinando... (30-60s)"):
                c = MLClassifier()
                r = c.train()
            if r.success:
                st.success(
                    f"✅ Acurácia: {r.accuracy * 100:.2f}% | "
                    f"F1: {r.f1 * 100:.2f}% | "
                    f"Treino: {r.samples_train:,} | "
                    f"Teste: {r.samples_test:,}"
                )
                st.cache_resource.clear()
            else:
                st.error(f"Falha: {r.error}")

    st.divider()
    st.subheader("📊 Feedback recebido")
    fb = load_feedback()
    if fb:
        useful = sum(1 for f in fb if f.get("useful"))
        st.markdown(
            f"Total: **{len(fb)}** | 👍 {useful} | 👎 {len(fb) - useful}"
        )
    else:
        st.info("Nenhum feedback ainda.")
