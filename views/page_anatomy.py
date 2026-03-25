"""
Página Anatomia da URL — Decomposição visual com código de cores.

Melhorias:
  #M3 Simulador de barra de navegador
  #M6 Comparação visual URL legítima vs phishing
"""

import html as _html
from urllib.parse import urlparse
from difflib import SequenceMatcher

import streamlit as st

from utils.sanitizer import sanitize_input
from models.persistence import unlock_badge
from views.helpers import T, render_browser_bar
from views.resources import get_parser


def page_anatomy():
    st.title(f"🔍 {T('nav.anatomy')}")
    st.markdown(T("analysis.subtitle").split("\n")[0])

    url_in = st.text_input(
        "URL",
        placeholder="https://www.exemplo.com/pagina?q=teste",
        key="anat_in",
    )
    if st.button("Analisar Anatomia", key="btn_anat") and url_in:
        unlock_badge("anatomy_first")
        san = sanitize_input(url_in.strip())
        if san.warnings:
            st.warning("\n".join(san.warnings))
        if not san.is_valid_url:
            st.error("URL inválida.")
            return
        parser = get_parser()
        parts = parser.get_visual_breakdown(san.sanitized_input)
        comp = parser.parse(san.sanitized_input)

        st.subheader("� Visão do Navegador")
        render_browser_bar(san.sanitized_input)

        st.subheader("�🎨 Decomposição Visual")
        html = "".join(
            f'<span style="color:{p.color};font-weight:bold;'
            f'font-size:1.2em" title="{_html.escape(p.tooltip)}">{_html.escape(p.text)}</span>'
            for p in parts
        )
        st.markdown(html, unsafe_allow_html=True)

        st.subheader("📐 Componentes")
        if comp.scheme:
            st.markdown(f"🟢 **Protocolo:** {comp.scheme}")
        if comp.subdomain:
            st.markdown(f"🔵 **Subdomínio:** {comp.subdomain}")
        if comp.is_ip:
            st.markdown(f"🟡 **IP:** {comp.ip_address} ⚠️")
        elif comp.domain:
            st.markdown(f"🟡 **Domínio:** {comp.domain}")
        if comp.tld:
            st.markdown(f"🟠 **TLD:** .{comp.tld}")
        if comp.port:
            st.markdown(f"🟣 **Porta:** {comp.port}")
        if comp.path and comp.path != "/":
            st.markdown(f"🔴 **Path:** {comp.path}")
        if comp.query:
            st.markdown(f"🔴 **Query:** ?{comp.query}")
        if comp.fragment:
            st.markdown(f"🔴 **Fragment:** #{comp.fragment}")
        if comp.registered_domain:
            st.markdown(f"📋 **Registrado:** {comp.registered_domain}")

    # ── Comparação Visual (#M6) ──────────────────────────────────────
    st.divider()
    st.subheader("⚖️ Comparação: URL Legítima vs Phishing")
    st.caption(
        "Cole duas URLs lado a lado para ver as diferenças visuais. "
        "Útil para treinar o olho a identificar domínios falsos."
    )
    cc1, cc2 = st.columns(2)
    with cc1:
        url_legit = st.text_input(
            "✅ URL Legítima",
            placeholder="https://www.paypal.com/login",
            key="cmp_legit",
        )
    with cc2:
        url_suspect = st.text_input(
            "❓ URL Suspeita",
            placeholder="https://www.paypa1.com/login",
            key="cmp_suspect",
        )
    if url_legit and url_suspect:
        st.markdown("**Visão no navegador:**")
        cl, cr = st.columns(2)
        with cl:
            st.markdown("✅ **Legítima**")
            render_browser_bar(url_legit)
        with cr:
            st.markdown("❓ **Suspeita**")
            render_browser_bar(url_suspect)

        # Diff visual entre os domínios
        try:
            host_l = urlparse(
                url_legit if "://" in url_legit else f"https://{url_legit}"
            ).hostname or ""
            host_s = urlparse(
                url_suspect if "://" in url_suspect else f"https://{url_suspect}"
            ).hostname or ""
        except Exception:
            host_l, host_s = url_legit, url_suspect

        if host_l and host_s:
            st.markdown("**Diff de domínio:**")
            matcher = SequenceMatcher(None, host_l, host_s)
            diff_html_l = ""
            diff_html_s = ""
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                seg_l = _html.escape(host_l[i1:i2])
                seg_s = _html.escape(host_s[j1:j2])
                if tag == "equal":
                    diff_html_l += f'<span style="color:#4CAF50">{seg_l}</span>'
                    diff_html_s += f'<span style="color:#4CAF50">{seg_s}</span>'
                elif tag == "replace":
                    diff_html_l += f'<span style="background:#4CAF50;color:#000;padding:0 2px;border-radius:2px">{seg_l}</span>'
                    diff_html_s += f'<span style="background:#F44336;color:#FFF;padding:0 2px;border-radius:2px">{seg_s}</span>'
                elif tag == "delete":
                    diff_html_l += f'<span style="background:#FFC107;color:#000;padding:0 2px;border-radius:2px">{seg_l}</span>'
                elif tag == "insert":
                    diff_html_s += f'<span style="background:#F44336;color:#FFF;padding:0 2px;border-radius:2px">{seg_s}</span>'

            dl, dr = st.columns(2)
            with dl:
                st.markdown(
                    f'<code style="font-size:1.2em">{diff_html_l}</code>',
                    unsafe_allow_html=True,
                )
            with dr:
                st.markdown(
                    f'<code style="font-size:1.2em">{diff_html_s}</code>',
                    unsafe_allow_html=True,
                )

            sim = SequenceMatcher(None, host_l, host_s).ratio()
            st.markdown(
                f"**Similaridade:** {sim * 100:.0f}% — "
                + (
                    "⚠️ Muito parecidos! Fácil confundir."
                    if sim > 0.8 else
                    "Diferenças visíveis." if sim > 0.5 else
                    "Bastante diferentes."
                )
            )
