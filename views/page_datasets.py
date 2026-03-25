"""
Página Datasets — Gerenciamento e download de datasets.
"""

import streamlit as st

from config.settings import AUTO_DOWNLOADABLE
from views.helpers import T
from views.resources import get_downloader


def page_datasets():
    st.title(f"📦 {T('nav.datasets')}")
    dl = get_downloader()
    status = dl.get_local_status()
    total = len(status)
    avail = sum(1 for s in status.values() if s["exists"])
    st.markdown(f"**{avail}/{total}** datasets disponíveis")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(f"⬇️ {T('datasets.download_all')}", key="dl_all"):
            prog = st.progress(0)
            for i, did in enumerate(AUTO_DOWNLOADABLE):
                st.text(f"Baixando {did}...")
                try:
                    r = dl.download(did)
                    if r.success:
                        st.success(f"✅ {did}")
                    else:
                        st.warning(f"⚠️ {did}: {r.error[:60]}")
                except Exception as e:
                    st.error(f"❌ {did}: {e}")
                prog.progress((i + 1) / len(AUTO_DOWNLOADABLE))
            st.cache_data.clear()
            st.rerun()
    with c2:
        if st.button(f"🔄 {T('datasets.refresh')}", key="dl_ref"):
            st.cache_data.clear()
            st.rerun()

    cats = {
        "malicious": "🔴 Maliciosas",
        "legitimate": "🟢 Legítimas",
        "dga": "🟣 DGA",
        "ml_features": "🔵 ML",
        "multimodal": "🟠 Multi",
    }
    for cid, ct in cats.items():
        cds = {k: v for k, v in status.items() if v["category"] == cid}
        if not cds:
            continue
        st.subheader(ct)
        for did, ds in cds.items():
            ic = (
                "✅" if ds["exists"]
                else ("📥" if ds["manual"] else "⬇️")
            )
            det = (
                ds["size_human"] if ds["exists"]
                else ("Manual" if ds["manual"] else "Disponível")
            )
            with st.expander(f"{ic} {ds['name']} — {det}"):
                st.markdown(ds["description"])
                st.caption(f"📜 {ds['license']}")
                if ds["exists"]:
                    st.success(f"Atualizado: {ds['modified']}")
                if ds["website"]:
                    st.markdown(f"🌐 [{ds['website']}]({ds['website']})")
                if not ds["manual"] and not ds.get("requires_key"):
                    if st.button(
                        f"⬇️ {'Atualizar' if ds['exists'] else 'Baixar'}",
                        key=f"dl_{did}",
                    ):
                        with st.spinner("Baixando..."):
                            r = dl.download(did)
                        if r.success:
                            st.success(f"✅ {r.lines_count} linhas")
                        else:
                            st.error(r.error)
                        st.rerun()
