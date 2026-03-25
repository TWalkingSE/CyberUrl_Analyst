"""
ReportGenerator — Monta relatório estruturado e didático.
Combina resultados de análise heurística, datasets e APIs externas
em um relatório visual unificado para a View.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from config.settings import DISCLAIMER_TEXT
from models.defanger import URLDefanger
from models.heuristic_analyzer import AnalysisResult, Finding
from models.dataset_checker import DatasetCheckResult
from models.api_client import VTResult, USResult, SBResult


@dataclass
class ReportSection:
    """Uma seção do relatório."""
    title: str
    icon: str              # Emoji/ícone
    severity: str          # "safe", "warning", "critical", "info"
    content: str           # Conteúdo textual
    analogy: str = ""      # Analogia (opcional)
    tip: str = ""          # Dica de proteção (opcional)
    comparison: str = ""   # Comparação visual (opcional)


@dataclass
class FullReport:
    """Relatório completo de uma análise."""
    url_defanged: str
    score: int
    classification: str
    classification_label: str
    classification_emoji: str
    anatomy_parts: list = field(default_factory=list)
    sections: list[ReportSection] = field(default_factory=list)
    api_sections: list[ReportSection] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER_TEXT


class ReportGenerator:
    """
    Monta relatório estruturado combinando todos os resultados de análise.
    A View nunca recebe URLs no formato original — tudo passa pelo Defanger.
    """

    def __init__(self):
        self._defanger = URLDefanger()

    def generate(
        self,
        raw_url: str,
        analysis: AnalysisResult,
        dataset_result: Optional[DatasetCheckResult] = None,
        vt_result: Optional[VTResult] = None,
        us_result: Optional[USResult] = None,
        sb_result: Optional[SBResult] = None,
        anatomy_parts: Optional[list] = None,
    ) -> FullReport:
        """
        Gera relatório completo combinando todas as fontes de análise.
        """
        # Defang URL para exibição segura
        url_defanged = self._defanger.defang(raw_url)

        report = FullReport(
            url_defanged=url_defanged,
            score=analysis.score,
            classification=analysis.classification,
            classification_label=analysis.classification_label,
            classification_emoji=analysis.classification_emoji,
            anatomy_parts=anatomy_parts or [],
        )

        # Seções dos findings heurísticos
        for finding in analysis.findings:
            report.sections.append(self._finding_to_section(finding))

        # Seções dos datasets
        if dataset_result:
            report.sections.extend(self._dataset_sections(dataset_result))

        # Seções das APIs externas
        if vt_result and vt_result.success:
            report.api_sections.append(self._vt_section(vt_result))
        if sb_result and sb_result.success:
            report.api_sections.append(self._sb_section(sb_result))
        if us_result and us_result.success:
            report.api_sections.append(self._us_section(us_result))

        # Recomendações
        report.recommendations = self._generate_recommendations(analysis, dataset_result)

        return report

    def _finding_to_section(self, finding: Finding) -> ReportSection:
        """Converte um Finding em uma seção do relatório."""
        severity_map = {
            "critical": "🔴",
            "warning": "⚠️",
            "info": "ℹ️",
            "safe": "✅",
        }
        icon = severity_map.get(finding.severity, "ℹ️")

        return ReportSection(
            title=finding.title,
            icon=icon,
            severity=finding.severity,
            content=finding.explanation,
            analogy=finding.analogy,
            tip=finding.tip,
        )

    def _dataset_sections(self, result: DatasetCheckResult) -> list[ReportSection]:
        """Gera seções de relatório para correspondências de dataset."""
        sections = []
        for match in result.matches:
            if match.matched and not match.is_legitimate:
                sections.append(ReportSection(
                    title=f"Encontrado no {match.dataset_name}",
                    icon="🔴",
                    severity="critical",
                    content=match.detail,
                    tip=(
                        f"Esta URL foi reportada e verificada pela comunidade "
                        f"{match.dataset_name}."
                    ),
                ))
            elif match.matched and match.is_legitimate:
                sections.append(ReportSection(
                    title=f"Domínio no {match.dataset_name}",
                    icon="✅",
                    severity="safe",
                    content=match.detail,
                ))
            else:
                sections.append(ReportSection(
                    title=f"Não encontrado no {match.dataset_name}",
                    icon="❓",
                    severity="info",
                    content=match.detail,
                    tip=(
                        "Não estar em um dataset de ameaças NÃO garante segurança. "
                        "O site pode ser novo demais para ter sido catalogado."
                    ),
                ))
        return sections

    def _vt_section(self, result: VTResult) -> ReportSection:
        """Gera seção do VirusTotal."""
        if result.detections > 0:
            severity = "critical" if result.detections > 5 else "warning"
            icon = "🔴" if severity == "critical" else "⚠️"
            explanation = (
                f"{result.detections} dos {result.total_engines} antivírus consultados "
                f"marcaram esta URL como perigosa."
            )
            if result.detections > 5:
                explanation += (
                    f" {result.detections} detecções é um forte indicativo de ameaça."
                )
        else:
            severity = "safe"
            icon = "✅"
            explanation = (
                f"Nenhum dos {result.total_engines} antivírus detectou ameaça nesta URL."
            )

        return ReportSection(
            title=f"VirusTotal — {result.detection_ratio}",
            icon=icon,
            severity=severity,
            content=explanation,
            analogy=(
                "O VirusTotal consulta dezenas de antivírus ao mesmo tempo. "
                "É como pedir a opinião de 72 especialistas em segurança."
            ),
            tip=(
                "Nenhum antivírus é perfeito. É por isso que existem serviços "
                "que consultam VÁRIOS ao mesmo tempo."
            ),
        )

    def _sb_section(self, result: SBResult) -> ReportSection:
        """Gera seção do Google Safe Browsing."""
        if result.is_unsafe:
            threats = ", ".join(result.threat_types) if result.threat_types else "ameaça genérica"
            return ReportSection(
                title="Google Safe Browsing — INSEGURO",
                icon="🔴",
                severity="critical",
                content=(
                    f"O Google marcou este site como perigoso. "
                    f"Tipos de ameaça: {threats}."
                ),
                tip="Mesmo o Google já marcou este site como perigoso.",
            )
        return ReportSection(
            title="Google Safe Browsing — Seguro",
            icon="✅",
            severity="safe",
            content="O Google não identificou ameaças conhecidas nesta URL.",
            tip=(
                "O Safe Browsing é atualizado frequentemente, mas pode não "
                "detectar ameaças muito recentes."
            ),
        )

    def _us_section(self, result: USResult) -> ReportSection:
        """Gera seção do URLScan.io."""
        content = "Scan submetido ao URLScan.io."
        if result.result_url:
            content += f"\nResultado disponível em: {result.result_url}"

        return ReportSection(
            title="URLScan.io — Scan enviado",
            icon="🔍",
            severity="info",
            content=content,
            tip=(
                "O URLScan.io faz um scan em sandbox, mostrando screenshots "
                "e tecnologias sem que você precise acessar o site."
            ),
        )

    def _generate_recommendations(
        self,
        analysis: AnalysisResult,
        dataset_result: Optional[DatasetCheckResult],
    ) -> list[str]:
        """Gera lista de recomendações baseada na classificação."""
        recs = []

        if analysis.classification == "malicious":
            recs.extend([
                "🚫 DEFINITIVAMENTE NÃO CLIQUE nesta URL.",
                "Se já clicou, NÃO insira nenhuma informação pessoal.",
                "Feche a aba imediatamente.",
                "Limpe o cache do navegador.",
                "Se inseriu dados, troque suas senhas imediatamente e ative 2FA.",
            ])
        elif analysis.classification == "suspicious":
            recs.extend([
                "⚠️ NÃO clique nesta URL sem verificação adicional.",
                "Se recebeu por e-mail ou SMS, acesse o site oficial digitando "
                "o endereço diretamente no navegador.",
                "Considere consultar APIs externas (VirusTotal, Safe Browsing) "
                "para uma segunda opinião.",
            ])
        else:
            recs.append(
                "✅ URL aparentemente segura. Ainda assim, mantenha cautela "
                "ao inserir dados pessoais."
            )

        return recs

    def format_text_report(self, report: FullReport) -> str:
        """Formata o relatório como texto puro (para copiar/exportar)."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {report.classification_emoji} RESULTADO: "
                      f"{report.classification_label.upper()} "
                      f"(Score: {report.score}/100)")
        lines.append("=" * 60)
        lines.append("\n  URL analisada (defanged):")
        lines.append(f"  {report.url_defanged}\n")

        lines.append("  FATORES ANALISADOS:")
        lines.append("-" * 60)
        for section in report.sections:
            lines.append(f"\n  {section.icon} {section.title}")
            lines.append(f"     {section.content}")
            if section.analogy:
                lines.append(f"     💭 {section.analogy}")
            if section.tip:
                lines.append(f"     🛡️ {section.tip}")

        if report.api_sections:
            lines.append("\n" + "-" * 60)
            lines.append("  ANÁLISE EXTERNA:")
            for section in report.api_sections:
                lines.append(f"\n  {section.icon} {section.title}")
                lines.append(f"     {section.content}")

        if report.recommendations:
            lines.append("\n" + "-" * 60)
            lines.append("  RECOMENDAÇÕES:")
            for rec in report.recommendations:
                lines.append(f"  {rec}")

        lines.append("\n" + "-" * 60)
        lines.append(f"  {report.disclaimer}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def format_html_report(self, report: FullReport) -> str:
        """Formata o relatório como HTML completo usando Jinja2."""
        severity_colors = {
            "critical": "#F44336", "warning": "#FFC107",
            "info": "#2196F3", "safe": "#4CAF50",
        }
        verdict_colors = {
            "safe": ("#e8f5e9", "#4CAF50"),
            "suspicious": ("#fff8e1", "#FFC107"),
            "malicious": ("#ffebee", "#F44336"),
        }
        bg, fg = verdict_colors.get(report.classification, ("#f5f5f5", "#999"))

        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        template = env.get_template("report.html")
        return template.render(
            report=report,
            severity_colors=severity_colors,
            verdict_bg=bg,
            verdict_fg=fg,
        )
