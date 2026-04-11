"""UI-independent helpers used by the PyQt6 pages."""

from __future__ import annotations

import html as _html
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urlparse

from models.report_generator import ReportSection
from utils.i18n import tr
from utils.sanitizer import sanitize_input

from ui.theme import get_html_document_css, get_palette
from ui.resources import (
    get_analyzer,
    get_api_client,
    get_cache,
    get_dataset_checker,
    get_ml,
    get_parser,
    get_report_generator,
    get_whois,
)


def T(key: str, lang: str = "pt") -> str:
    return tr(key, lang)


_SEV_LABELS = {
    "critical": "CRITICAL",
    "warning": "WARNING",
    "info": "INFO",
    "safe": "SAFE",
}

_SEV_COLORS = {
    "critical": "#F44336",
    "warning": "#FF9800",
    "info": "#2196F3",
    "safe": "#4CAF50",
}


@dataclass
class AnalysisExecutionResult:
    report: object | None = None
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    from_cache: bool = False


@dataclass
class ApiQueryBundle:
    url: str = ""
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)
    vt: object | None = None
    us: object | None = None
    sb: object | None = None


def sev_color(severity: str) -> str:
    return _SEV_COLORS.get(severity, "#555")


def sev_label(severity: str) -> str:
    return _SEV_LABELS.get(severity, "")


def html_document(content: str, compact: bool = False) -> str:
    body_class = "compact" if compact else ""
    return (
        "<html><head><style>"
        f"{get_html_document_css()}"
        "</style></head>"
        f"<body class=\"{body_class}\">{content}</body></html>"
    )


def empty_state_fragment(message: str, hint: str = "") -> str:
    hint_html = f'<p class="small">{_html.escape(hint)}</p>' if hint else ""
    return (
        '<div class="empty">'
        '<div class="kicker">Painel</div>'
        f"<p><b>{_html.escape(message)}</b></p>"
        f"{hint_html}"
        "</div>"
    )


def empty_state_html(message: str, hint: str = "", compact: bool = False) -> str:
    return html_document(empty_state_fragment(message, hint), compact=compact)


def _tone_palette(tone: str) -> tuple[str, str]:
    palette = get_palette()
    mapping = {
        "success": (palette["success"], palette["success_bg"]),
        "warning": (palette["warning"], palette["warning_bg"]),
        "danger": (palette["danger"], palette["danger_bg"]),
        "critical": (palette["danger"], palette["danger_bg"]),
        "info": (palette["info"], palette["info_bg"]),
        "neutral": (palette["text_muted"], palette["neutral_bg"]),
    }
    return mapping.get(tone, mapping["neutral"])


def badge_fragment(text: str, tone: str = "neutral") -> str:
    color, background = _tone_palette(tone)
    return (
        f'<span class="badge" style="background:{background};border-color:{color};color:{color};">'
        f"{_html.escape(text)}</span>"
    )


def status_banner_fragment(
    title: str,
    message: str = "",
    tone: str = "info",
    items: list[str] | None = None,
    icon: str = "",
) -> str:
    color, background = _tone_palette(tone)
    item_html = ""
    if items:
        item_html = "<ul>" + "".join(f"<li>{_html.escape(item)}</li>" for item in items) + "</ul>"
    icon_html = f"{_html.escape(icon)} " if icon else ""
    return (
        f'<div class="panel" style="background:{background};border-color:{color};">'
        '<div class="kicker">Status</div>'
        f'<h3 style="color:{color};margin-bottom:6px;">{icon_html}{_html.escape(title)}</h3>'
        f"<p>{_html.escape(message)}</p>"
        f"{item_html}"
        "</div>"
    )


def page_intro_fragment(
    title: str,
    description: str,
    bullets: list[str] | None = None,
    kicker: str = "Visao geral",
    tone: str = "info",
) -> str:
    color, background = _tone_palette(tone)
    bullets_html = ""
    if bullets:
        bullets_html = "<ul>" + "".join(f"<li>{_html.escape(item)}</li>" for item in bullets) + "</ul>"
    return (
        f'<div class="panel" style="background:{background};border-color:{color};">'
        f'<div class="kicker">{_html.escape(kicker)}</div>'
        f'<h3 style="color:{color};">{_html.escape(title)}</h3>'
        f'<p>{_html.escape(description)}</p>'
        f"{bullets_html}"
        "</div>"
    )


def report_summary_fragment(report, context_label: str = "Ultimo resultado") -> str:
    if report is None:
        return empty_state_fragment(
            "Nenhum resumo disponivel.",
            "Assim que uma URL for analisada, os principais indicadores aparecerao aqui.",
        )

    palette = get_palette()
    verdict_tone = {
        "safe": "success",
        "suspicious": "warning",
        "malicious": "danger",
    }.get(report.classification, "neutral")
    accent, background = _tone_palette(verdict_tone)
    stats = [
        ("Score", f"{report.score}/100"),
        ("Fatores", str(len(report.sections))),
        ("APIs", str(len(report.api_sections))),
        ("Acoes", str(max(1, len(report.recommendations)))),
    ]
    cells = []
    for label, value in stats:
        cells.append(
            "<td>"
            f'<span class="stat-label">{_html.escape(label)}</span>'
            f'<span class="stat-value">{_html.escape(value)}</span>'
            "</td>"
        )
    return (
        f'<div class="panel" style="background:{background};border-color:{accent};">'
        '<div class="kicker">Resumo rapido</div>'
        f'<h3 style="color:{accent};margin-bottom:8px;">{_html.escape(report.classification_emoji)} '
        f'{_html.escape(report.classification_label)} {badge_fragment(context_label, "info")}</h3>'
        f'<p class="small">{_html.escape(report.url_defanged)}</p>'
        '<table class="stat-grid" style="margin-top:10px;"><tr>'
        f"{''.join(cells)}"
        "</tr></table>"
        f'<p class="small" style="margin-top:10px;color:{palette["text_muted"]};">'
        'Use o score como apoio visual. A decisao final continua dependendo do contexto.</p>'
        "</div>"
    )


def build_browser_bar_html(url: str) -> str:
    palette = get_palette()
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
    except Exception:
        return html_document(f"<pre>{_html.escape(url)}</pre>", compact=True)

    is_https = parsed.scheme.lower() == "https"
    lock_icon = "&#128274;" if is_https else "&#128275;"
    lock_color = palette["success"] if is_https else palette["danger"]
    lock_background = palette["success_bg"] if is_https else palette["danger_bg"]
    scheme_display = f"{parsed.scheme}://" if parsed.scheme else ""

    host = parsed.hostname or ""
    parts = host.split(".")
    if len(parts) >= 2:
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
    after_domain = _html.escape(f"{port_str}{path_str}{query_str}{frag_str}")
    sub_html = (
        f'<span style="color:{palette["text_dim"]}">{_html.escape(subdomain)}.</span>'
        if subdomain
        else ""
    )
    return html_document(
        (
            f'<div style="background:{palette["surface_deep"]};border:1px solid {palette["border"]};'
            'border-radius:20px;padding:10px 14px;font-family:Consolas,monospace;font-size:13px;">'
            f'<span style="background:{lock_background};color:{lock_color};padding:3px 8px;'
            'border-radius:999px;font-weight:700;margin-right:8px;display:inline-block;">'
            f"{lock_icon}</span>"
            f'<span style="color:{palette["text_dim"]}">{_html.escape(scheme_display)}</span>'
            f"{sub_html}"
            f'<span style="color:{palette["text_strong"]};font-weight:700">{_html.escape(registered)}</span>'
            f'<span style="color:{palette["text_muted"]}">{after_domain}</span>'
            "</div>"
        ),
        compact=True,
    )


def build_visual_breakdown_html(parts: list) -> str:
    palette = get_palette()
    if not parts:
        return empty_state_html(
            "Nenhuma URL analisada.",
            "Cole um endereco para ver a decomposicao visual da URL.",
            compact=True,
        )
    html_parts = []
    for part in parts:
        html_parts.append(
            f'<span title="{_html.escape(part.tooltip)}" '
            f'style="display:inline-block;margin:0 8px 8px 0;padding:8px 12px;'
            f'border-radius:999px;background:{palette["surface_deep"]};'
            f'border:1px solid {part.color};color:{part.color};font-weight:700;font-size:14px;">'
            f"{_html.escape(part.text)}</span>"
        )
    return html_document(
        '<div class="panel">'
        '<div class="kicker">Mapa visual da URL</div>'
        '<p class="small">Cada parte da URL aparece separada para facilitar a leitura.</p>'
        f"<div>{''.join(html_parts)}</div>"
        "</div>",
        compact=True,
    )


def build_domain_diff(url_left: str, url_right: str) -> tuple[str, str, int, str]:
    palette = get_palette()
    try:
        host_left = urlparse(url_left if "://" in url_left else f"https://{url_left}").hostname or ""
        host_right = urlparse(url_right if "://" in url_right else f"https://{url_right}").hostname or ""
    except Exception:
        host_left = url_left
        host_right = url_right

    matcher = SequenceMatcher(None, host_left, host_right)
    left_html = ""
    right_html = ""
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        seg_left = _html.escape(host_left[i1:i2])
        seg_right = _html.escape(host_right[j1:j2])
        if tag == "equal":
            left_html += f'<span style="color:{palette["success"]}">{seg_left}</span>'
            right_html += f'<span style="color:{palette["success"]}">{seg_right}</span>'
        elif tag == "replace":
            left_html += (
                f'<span style="background:{palette["success"]};color:{palette["surface_deep"]};padding:0 3px;'
                f'border-radius:2px">{seg_left}</span>'
            )
            right_html += (
                f'<span style="background:{palette["danger"]};color:{palette["text_strong"]};padding:0 3px;'
                f'border-radius:2px">{seg_right}</span>'
            )
        elif tag == "delete":
            left_html += (
                f'<span style="background:{palette["warning"]};color:{palette["surface_deep"]};padding:0 3px;'
                f'border-radius:2px">{seg_left}</span>'
            )
        elif tag == "insert":
            right_html += (
                f'<span style="background:{palette["danger"]};color:{palette["text_strong"]};padding:0 3px;'
                f'border-radius:2px">{seg_right}</span>'
            )

    similarity = int(matcher.ratio() * 100)
    if similarity > 80:
        message = "Muito parecidos. Facil confundir."
    elif similarity > 50:
        message = "Algumas diferencas visiveis."
    else:
        message = "Bastante diferentes."
    return left_html, right_html, similarity, message


def _section_html(section: ReportSection) -> str:
    palette = get_palette()
    color = sev_color(section.severity)
    extras = []
    if section.analogy:
        extras.append(
            f'<div style="color:{palette["text_muted"]};font-size:12px;margin-top:8px">&#128173; '
            f'{_html.escape(section.analogy)}</div>'
        )
    if section.tip:
        extras.append(
            f'<div style="color:{palette["accent_soft"]};font-size:12px;margin-top:8px">&#128737; '
            f'{_html.escape(section.tip)}</div>'
        )
    return (
        f'<div class="panel-soft" style="border-left:4px solid {color};margin-bottom:10px;">'
        f'<div style="color:{color};font-weight:700">{_html.escape(section.icon)} '
        f'{_html.escape(section.title)} '
        f'<span style="font-size:11px;border:1px solid {color};padding:1px 6px;'
        f'border-radius:3px">{sev_label(section.severity)}</span></div>'
        f'<div style="color:{palette["text"]};margin-top:6px">{_html.escape(section.content)}</div>'
        f"{''.join(extras)}"
        "</div>"
    )


def render_report_fragment(report) -> str:
    if report is None:
        return empty_state_fragment(
            "Nenhum relatorio disponivel.",
            "Execute uma analise para preencher este painel.",
        )

    palette = get_palette()
    verdict_colors = {
        "safe": (palette["success"], palette["success_bg"]),
        "suspicious": (palette["warning"], palette["warning_bg"]),
        "malicious": (palette["danger"], palette["danger_bg"]),
    }
    color, background = verdict_colors.get(report.classification, (palette["text_muted"], palette["surface_alt"]))
    section_html = "".join(_section_html(section) for section in report.sections)
    api_html = "".join(_section_html(section) for section in report.api_sections)
    recommendations = "".join(
        f"<li>{_html.escape(recommendation)}</li>" for recommendation in report.recommendations
    )
    return (
        f'<div class="panel" style="background:{background};border:1px solid {color};margin-bottom:12px;">'
        '<div class="kicker">Veredito final</div>'
        f'<h2 style="margin:0;color:{color};">{_html.escape(report.classification_emoji)} '
        f'{_html.escape(report.classification_label.upper())}</h2>'
        f'<p><span class="badge" style="border-color:{color};color:{palette["text_strong"]};">'
        f'Score {report.score}/100</span></p>'
        f'<div style="margin-top:10px;padding:12px 14px;background:{palette["surface_deep"]};'
        f'border:1px solid {palette["border"]};border-radius:12px;font-family:Consolas,monospace;'>
        f'{_html.escape(report.url_defanged)}</div>'
        '</div>'
        '<div class="panel" style="margin-bottom:12px;">'
        '<div class="kicker">Fatores analisados</div>'
        f"{section_html or '<div class=\"empty\"><p><b>Nenhum fator detalhado.</b></p></div>'}"
        '</div>'
        '<div class="panel" style="margin-bottom:12px;">'
        '<div class="kicker">Analise externa</div>'
        f"{api_html or '<div class=\"empty\"><p><b>Nenhuma consulta externa executada.</b></p></div>'}"
        '</div>'
        '<div class="panel" style="margin-bottom:12px;">'
        '<div class="kicker">Recomendacoes</div>'
        f"<ul>{recommendations or '<li>Nenhuma recomendacao adicional.</li>'}</ul>"
        '</div>'
        f'<p class="small">{_html.escape(report.disclaimer)}</p>'
    )


def render_report_html(report) -> str:
    return html_document(render_report_fragment(report))


def _apply_whois_and_ml(report, url: str, registered_domain: str):
    whois_checker = get_whois()
    whois_result = None
    if whois_checker.is_available and registered_domain:
        try:
            whois_result = whois_checker.check_domain_age(registered_domain)
        except Exception:
            whois_result = None

    if whois_result and whois_result.success and whois_result.age_days >= 0:
        if whois_result.is_young:
            report.sections.append(
                ReportSection(
                    title=f"Dominio jovem ({whois_result.age_days}d)",
                    icon="🔴",
                    severity="critical",
                    content=f"Registrado ha {whois_result.age_days} dias.",
                    tip="Desconfie de dominios com menos de 30 dias.",
                )
            )
        else:
            years = whois_result.age_days // 365
            report.sections.append(
                ReportSection(
                    title=f"Dominio estabelecido ({years}a)",
                    icon="✅",
                    severity="safe",
                    content=f"Registrado ha aproximadamente {years} anos.",
                )
            )
    elif whois_result and whois_result.error:
        report.sections.append(
            ReportSection(
                title="WHOIS indisponivel",
                icon="ℹ️",
                severity="info",
                content=whois_result.error,
                tip="A analise continuou normalmente sem usar a idade do dominio.",
            )
        )

    classifier = get_ml()
    if classifier and classifier.is_available:
        prediction = classifier.predict(url)
        if prediction.available:
            if prediction.probability_malicious > 0.7:
                severity, icon = "critical", "🔴"
            elif prediction.probability_malicious > 0.4:
                severity, icon = "warning", "⚠️"
            else:
                severity, icon = "safe", "✅"
            report.sections.append(
                ReportSection(
                    title=(
                        f"ML: {prediction.prediction.upper()} "
                        f"({prediction.probability_malicious * 100:.0f}%)"
                    ),
                    icon=icon,
                    severity=severity,
                    content=(
                        f"Probabilidade maliciosa: "
                        f"{prediction.probability_malicious * 100:.1f}%"
                    ),
                    tip="Heuristica + ML concordando aumenta a confianca.",
                )
            )


def run_analysis(raw_url: str, state=None) -> AnalysisExecutionResult:
    sanitized = sanitize_input(raw_url)
    result = AnalysisExecutionResult(
        warnings=list(sanitized.warnings),
        removed_items=list(sanitized.removed_items),
    )
    if not sanitized.is_valid_url:
        result.error = "\n".join(sanitized.warnings) if sanitized.warnings else "URL invalida."
        return result

    url = sanitized.sanitized_input
    cache = get_cache()
    cached = cache.get(url)
    if cached is not None:
        result.report = cached
        result.from_cache = True
        if state is not None:
            state.set_last_report(cached)
        return result

    parser = get_parser()
    analyzer = get_analyzer()
    dataset_checker = get_dataset_checker()
    report_generator = get_report_generator()

    components = parser.parse(url)
    analysis = analyzer.analyze(components)
    dataset_result = dataset_checker.check(url, components.domain, components.registered_domain)

    extra_weight = dataset_result.total_weight
    whois_checker = get_whois()
    if whois_checker.is_available and components.registered_domain:
        try:
            whois_result = whois_checker.check_domain_age(components.registered_domain)
            if whois_result and whois_result.is_young:
                extra_weight += whois_result.weight
        except Exception:
            pass

    analysis.score = min(100, analysis.score + extra_weight)
    if analysis.score > 65:
        analysis.classification = "malicious"
        analysis.classification_label = "Malicioso"
        analysis.classification_emoji = "🔴"
    elif analysis.score > 25:
        analysis.classification = "suspicious"
        analysis.classification_label = "Suspeito"
        analysis.classification_emoji = "🟡"

    report = report_generator.generate(
        raw_url=url,
        analysis=analysis,
        dataset_result=dataset_result,
        anatomy_parts=parser.get_visual_breakdown(url),
    )
    _apply_whois_and_ml(report, url, components.registered_domain)
    cache.put(url, report)

    if state is not None:
        state.record_analysis(url, report)

    result.report = report
    return result


def query_external_apis(raw_url: str, api_keys: dict[str, str], progress_callback=None) -> ApiQueryBundle:
    sanitized = sanitize_input(raw_url)
    bundle = ApiQueryBundle(
        warnings=list(sanitized.warnings),
        removed_items=list(sanitized.removed_items),
    )
    if not sanitized.is_valid_url:
        bundle.error = "\n".join(sanitized.warnings) if sanitized.warnings else "URL invalida."
        return bundle

    client = get_api_client()
    if client is None:
        bundle.error = "Modulo de APIs externas indisponivel."
        return bundle

    url = sanitized.sanitized_input
    bundle.url = url

    tasks = []
    if progress_callback:
        progress_callback(5, "Preparando consultas externas...")

    def _vt():
        return "vt", client.check_virustotal(url, api_keys.get("virustotal", ""))

    def _us():
        return "us", client.check_urlscan(url, api_keys.get("urlscan", ""))

    def _sb():
        return "sb", client.check_safebrowsing(url, api_keys.get("safebrowsing", ""))

    if api_keys.get("virustotal"):
        tasks.append(_vt)
    if api_keys.get("urlscan"):
        tasks.append(_us)
    if api_keys.get("safebrowsing"):
        tasks.append(_sb)

    if not tasks:
        bundle.error = "Configure pelo menos uma chave de API para consultar servicos externos."
        return bundle

    with ThreadPoolExecutor(max_workers=min(3, len(tasks))) as executor:
        futures = [executor.submit(task) for task in tasks]
        completed = 0
        for future in as_completed(futures):
            service, service_result = future.result()
            setattr(bundle, service, service_result)
            completed += 1
            if progress_callback:
                percent = 5 + int((completed / max(1, len(tasks))) * 95)
                progress_callback(percent, f"Consulta concluida: {service.upper()}")

    return bundle