"""
Helpers compartilhados — Funções de UI usadas por múltiplas páginas.

Melhorias:
  #9  Acessibilidade — labels textuais redundantes junto com cores
  #M3 Simulador de barra de navegador
"""

import html as _html
import time
from urllib.parse import urlparse

import streamlit as st

from models.report_generator import ReportSection
from models.persistence import (
    add_history_entry, save_stats, save_feedback, unlock_badge,
)
from utils.sanitizer import sanitize_input
from utils.i18n import tr

from views.resources import (
    get_parser, get_analyzer, get_dataset_checker, get_whois,
    get_report_gen, get_cache, get_ml, get_defanger,
)


# ── i18n shortcut ──────────────────────────────────────────────────
def T(key):
    """Traduz chave usando o idioma ativo na sessão."""
    return tr(key, st.session_state.get("lang", "pt"))


# ── Severity helpers (#9 — acessibilidade) ─────────────────────────
_SEV_MAP = {
    "critical": {"color": "#F44336", "label": "CRITICAL", "aria": "Criticidade alta"},
    "warning":  {"color": "#FFC107", "label": "WARNING",  "aria": "Atenção"},
    "info":     {"color": "#2196F3", "label": "INFO",     "aria": "Informativo"},
    "safe":     {"color": "#4CAF50", "label": "SAFE",     "aria": "Seguro"},
}


def sev_color(s):
    return _SEV_MAP.get(s, {}).get("color", "#555")


def sev_label(s):
    """Retorna label textual para o nível de severidade (#9 a11y)."""
    return _SEV_MAP.get(s, {}).get("label", "")


def render_finding(sec):
    """Renderiza um finding com label de severidade textual (#9 a11y)."""
    c = sev_color(sec.severity)
    label = sev_label(sec.severity)
    e = _html.escape
    html = (
        f'<div class="finding-{sec.severity}" role="region" '
        f'aria-label="{_SEV_MAP.get(sec.severity, {}).get("aria", "")}">' 
        f'<strong style="color:{c}">{e(sec.icon)} {e(sec.title)}</strong>'
        f' <span style="font-size:0.75em;color:{c};border:1px solid {c};'
        f'border-radius:3px;padding:1px 5px;margin-left:6px">{label}</span><br>'
        f'<span style="color:#CCC">{e(sec.content)}</span>'
    )
    if sec.analogy:
        html += f'<br><em style="color:#AAA;font-size:0.85em">💭 {e(sec.analogy)}</em>'
    if sec.tip:
        html += f'<br><span style="color:#4CAF50;font-size:0.85em">🛡️ {e(sec.tip)}</span>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def display_report(report):
    """Renderiza relatório completo com labels textuais (#9 a11y)."""
    cm = {"safe": "#4CAF50", "suspicious": "#FFC107", "malicious": "#F44336"}
    cl = {"safe": "SEGURO", "suspicious": "SUSPEITO", "malicious": "MALICIOSO"}
    c = cm.get(report.classification, "#CCC")
    text_label = cl.get(report.classification, "")
    st.markdown(
        f'<div style="background:#1e1e2e;border:2px solid {c};border-radius:10px;'
        f'padding:20px;text-align:center;margin-bottom:16px" role="status">'
        f'<h2 style="color:{c};margin:0">{report.classification_emoji} '
        f'{report.classification_label.upper()} — Score: {report.score}/100</h2>'
        f'<p style="color:{c};margin:4px 0 0 0;font-size:0.85em">'
        f'Classificação: {text_label}</p></div>',
        unsafe_allow_html=True,
    )
    st.progress(min(report.score, 100) / 100)
    st.code(report.url_defanged, language=None)
    if report.sections:
        st.subheader("📊 " + T("report.factors"))
        for sec in report.sections:
            render_finding(sec)
    if report.api_sections:
        st.subheader("🔍 Análise Externa")
        for sec in report.api_sections:
            render_finding(sec)
    if report.recommendations:
        st.subheader("🛡️ " + T("report.recommendations"))
        for r in report.recommendations:
            st.markdown(f"- {r}")
    st.caption(T("common.disclaimer"))


# ── Persistência de stats ──────────────────────────────────────────
def persist_stats():
    save_stats({
        "analysis_count": st.session_state.analysis_count,
        "safe_count": st.session_state.safe_count,
        "suspicious_count": st.session_state.suspicious_count,
        "malicious_count": st.session_state.malicious_count,
    })


# ── Motor de análise ──────────────────────────────────────────────
def run_analysis(url):
    """Executa pipeline completo de análise de uma URL."""
    san = sanitize_input(url)
    if not san.is_valid_url:
        st.warning("URL inválida.")
        return None
    url = san.sanitized_input
    if san.warnings:
        st.warning("\n".join(san.warnings))

    cache = get_cache()
    cached = cache.get(url)
    if cached is not None:
        return cached

    parser = get_parser()
    analyzer = get_analyzer()
    dc = get_dataset_checker()
    whois = get_whois()
    rg = get_report_gen()
    ml = get_ml()

    comp = parser.parse(url)
    analysis = analyzer.analyze(comp)
    ds = dc.check(url, comp.domain, comp.registered_domain)

    wr = None
    if whois.is_available and comp.registered_domain:
        try:
            wr = whois.check_domain_age(comp.registered_domain)
        except Exception:
            pass

    extra = ds.total_weight
    if wr and wr.is_young:
        extra += wr.weight
    analysis.score = min(100, analysis.score + extra)
    if analysis.score > 65:
        analysis.classification = "malicious"
        analysis.classification_label = "Malicioso"
        analysis.classification_emoji = "🔴"
    elif analysis.score > 25:
        analysis.classification = "suspicious"
        analysis.classification_label = "Suspeito"
        analysis.classification_emoji = "🟡"

    report = rg.generate(
        raw_url=url, analysis=analysis,
        dataset_result=ds, anatomy_parts=parser.get_visual_breakdown(url),
    )

    if wr and wr.success and wr.age_days >= 0:
        if wr.is_young:
            report.sections.append(ReportSection(
                title=f"Domínio jovem ({wr.age_days}d)", icon="🔴",
                severity="critical",
                content=f"Registrado há {wr.age_days} dias.",
                tip="Desconfie de domínios < 30 dias.",
            ))
        else:
            y = wr.age_days // 365
            report.sections.append(ReportSection(
                title=f"Domínio estabelecido ({y}a)", icon="✅",
                severity="safe",
                content=f"Registrado há ~{y} anos.",
            ))

    if ml and ml.is_available:
        pred = ml.predict(url)
        if pred.available:
            if pred.probability_malicious > 0.7:
                sv, ic = "critical", "🔴"
            elif pred.probability_malicious > 0.4:
                sv, ic = "warning", "⚠️"
            else:
                sv, ic = "safe", "✅"
            report.sections.append(ReportSection(
                title=f"ML: {pred.prediction.upper()} "
                      f"({pred.probability_malicious * 100:.0f}%)",
                icon=ic, severity=sv,
                content=f"Prob. maliciosa: "
                        f"{pred.probability_malicious * 100:.1f}%",
                tip="Heurística + ML concordando = maior confiança.",
            ))

    cache.put(url, report)
    st.session_state.last_report = report

    st.session_state.analysis_count += 1
    cls = report.classification
    if cls == "safe":
        st.session_state.safe_count += 1
    elif cls == "suspicious":
        st.session_state.suspicious_count += 1
    elif cls == "malicious":
        st.session_state.malicious_count += 1
    persist_stats()

    # Badges (#M8)
    count = st.session_state.analysis_count
    if count == 1:
        unlock_badge("first_analysis")
    if count >= 10:
        unlock_badge("ten_analyses")
    if count >= 50:
        unlock_badge("fifty_analyses")

    dfg = get_defanger().defang(url)
    add_history_entry(dfg, cls, report.classification_emoji, report.score)
    st.session_state.analysis_history.insert(0, {
        "url": dfg[:50], "classification": cls,
        "emoji": report.classification_emoji, "report": report,
    })
    return report


# ── Feedback pós-análise ──────────────────────────────────────────
def render_feedback(report):
    """#14 — Botões de feedback após análise."""
    st.divider()
    st.markdown("**Essa análise foi útil?**")
    c1, c2 = st.columns(2)
    fb_key = f"fb_{hash(report.url_defanged)}_{int(time.time())}"
    with c1:
        if st.button("👍 Sim", key=f"{fb_key}_y"):
            save_feedback(report.url_defanged, report.classification, True)
            st.success("Obrigado pelo feedback!")
    with c2:
        if st.button("👎 Não", key=f"{fb_key}_n"):
            save_feedback(report.url_defanged, report.classification, False)
            st.info("Obrigado! Vamos melhorar.")


# ── Simulador de barra de navegador (#M3) ────────────────────────
def render_browser_bar(url: str, key_suffix: str = ""):
    """
    Renderiza um simulador visual de barra de navegador.
    Mostra a URL como apareceria num browser real, com:
    - Cadeado verde (HTTPS) ou vermelho (HTTP)
    - Domínio registrado em destaque
    - Path/query em cinza
    """
    e = _html.escape
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except Exception:
        st.code(url, language=None)
        return

    is_https = parsed.scheme.lower() == "https"
    lock_icon = "🔒" if is_https else "🔓"
    lock_color = "#4CAF50" if is_https else "#F44336"
    scheme_display = f"{parsed.scheme}://" if parsed.scheme else ""

    # Extrair domínio registrado (últimos 2 segmentos)
    host = parsed.hostname or ""
    parts = host.split(".")
    if len(parts) >= 2:
        # Tratar .com.br, .co.uk, etc.
        if len(parts) >= 3 and parts[-2] in ("com", "co", "org", "net", "gov"):
            registered = ".".join(parts[-3:])
            subdomain = ".".join(parts[:-3])
        else:
            registered = ".".join(parts[-2:])
            subdomain = ".".join(parts[:-2])
    else:
        registered = host
        subdomain = ""

    port_str = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
    path_str = parsed.path if parsed.path and parsed.path != "/" else ""
    query_str = f"?{parsed.query}" if parsed.query else ""
    frag_str = f"#{parsed.fragment}" if parsed.fragment else ""
    after_domain = e(f"{port_str}{path_str}{query_str}{frag_str}")

    sub_html = f'<span style="color:#888">{e(subdomain)}.</span>' if subdomain else ""

    html = (
        f'<div style="background:#2a2a3e;border:1px solid #555;border-radius:24px;'
        f'padding:8px 16px;display:flex;align-items:center;gap:8px;'
        f'font-family:monospace;font-size:0.95em;margin:8px 0;max-width:100%;'
        f'overflow-x:auto" role="img" aria-label="Barra de endereço do navegador">'
        f'<span style="color:{lock_color};font-size:1.1em">{lock_icon}</span>'
        f'<span style="color:#777">{e(scheme_display)}</span>'
        f'{sub_html}'
        f'<span style="color:#FFF;font-weight:bold">{e(registered)}</span>'
        f'<span style="color:#888">{after_domain}</span>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
