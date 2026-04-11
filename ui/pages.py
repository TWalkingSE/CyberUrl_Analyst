"""PyQt6 page widgets for the desktop interface."""

from __future__ import annotations

import time
from functools import partial

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config import settings
from config.settings import APP_NAME, AUTO_DOWNLOADABLE, QUIZ_QUESTIONS_PER_ROUND
from models.persistence import (
    BADGE_DEFINITIONS,
    load_feedback,
    load_leaderboard,
    save_feedback,
    save_leaderboard_entry,
    unlock_badge,
    update_quiz_progress,
    update_scenario_progress,
)
from models.quiz_engine import QuizEngine
from models.scenarios import SCENARIOS, SCENARIO_CATEGORIES
from utils.sanitizer import sanitize_input

from ui.glossary_data import GLOSSARY, GLOSSARY_CATEGORIES
from ui.helpers import (
    T,
    build_domain_diff,
    build_visual_breakdown_html,
    badge_fragment,
    empty_state_html,
    page_intro_fragment,
    query_external_apis,
    render_report_fragment,
    report_summary_fragment,
    run_analysis,
    status_banner_fragment,
)
from ui.resources import (
    ML_AVAILABLE,
    MODEL_PATH,
    get_downloader,
    get_ml,
    get_parser,
    get_report_generator,
    reload_dataset_checker,
    reload_ml,
)
from ui.widgets import (
    BrowserBarWidget,
    CollapsibleSection,
    MetricCard,
    ReportViewer,
    SectionHeader,
    ThemedTextBrowser as QTextBrowser,
)
from ui.workers import FunctionWorker
from ui.theme import THEME_LABELS


PAGE_MARGINS = (18, 18, 18, 18)
PAGE_SPACING = 14


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        child_layout = item.layout()
        widget = item.widget()
        if child_layout is not None:
            _clear_layout(child_layout)
        if widget is not None:
            widget.deleteLater()


def _readonly_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


def _apply_page_layout(layout):
    layout.setContentsMargins(*PAGE_MARGINS)
    layout.setSpacing(PAGE_SPACING)


def _section_label(text: str, parent=None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("sectionTitle")
    return label


def _centered_cell_widget(child: QWidget, parent=None) -> QWidget:
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(child)
    return container


class BasePage(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._workers: list[FunctionWorker] = []

    def _track_worker(self, worker: FunctionWorker) -> FunctionWorker:
        self._workers.append(worker)

        def _cleanup():
            if worker in self._workers:
                self._workers.remove(worker)

        worker.finished.connect(_cleanup)
        return worker


class DashboardPage(BasePage):
    HISTORY_PAGE_SIZE = 10

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self._history_page = 0

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"🏠 {T('nav.dashboard', self.state.lang)}")
        layout.addWidget(self.header)

        self.onboarding_frame = QFrame(self)
        self.onboarding_frame.setObjectName("panelCard")
        onboarding_layout = QVBoxLayout(self.onboarding_frame)
        onboarding_layout.setContentsMargins(14, 14, 14, 14)
        onboarding_layout.setSpacing(8)
        self.onboarding_label = QLabel(self.onboarding_frame)
        self.onboarding_label.setWordWrap(True)
        self.dismiss_onboarding_button = QPushButton("Nao mostrar novamente", self.onboarding_frame)
        self.dismiss_onboarding_button.clicked.connect(self._dismiss_onboarding)
        onboarding_layout.addWidget(self.onboarding_label)
        onboarding_layout.addWidget(self.dismiss_onboarding_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.onboarding_frame)

        metrics_layout = QHBoxLayout()
        self.metric_cards = [
            MetricCard("Analises", "0", self),
            MetricCard("Seguras", "0", self),
            MetricCard("Suspeitas", "0", self),
            MetricCard("Maliciosas", "0", self),
        ]
        for card in self.metric_cards:
            metrics_layout.addWidget(card)
        layout.addLayout(metrics_layout)

        self.progress_browser = QTextBrowser(self)
        self.progress_browser.setObjectName("panelCard")
        self.progress_browser.setMaximumHeight(180)
        layout.addWidget(self.progress_browser)

        self.badges_browser = QTextBrowser(self)
        self.badges_browser.setObjectName("panelCard")
        self.badges_browser.setMaximumHeight(180)
        layout.addWidget(self.badges_browser)

        history_header = QLabel("Historico persistido")
        history_header.setObjectName("sectionTitle")
        layout.addWidget(history_header)

        controls = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar URL...")
        self.search_input.textChanged.connect(self._refresh_history_table)
        self.class_filter = QComboBox(self)
        self.class_filter.addItems(["Todas", "Segura", "Suspeita", "Maliciosa"])
        self.class_filter.currentIndexChanged.connect(self._reset_and_refresh_history)
        controls.addWidget(self.search_input, 3)
        controls.addWidget(self.class_filter, 1)
        layout.addLayout(controls)

        self.history_table = QTableWidget(0, 4, self)
        self.history_table.setHorizontalHeaderLabels(["URL", "Classificacao", "Score", "Data"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        pagination = QHBoxLayout()
        self.prev_history_button = QPushButton("Anterior", self)
        self.prev_history_button.clicked.connect(partial(self._change_history_page, -1))
        self.history_page_label = QLabel(self)
        self.next_history_button = QPushButton("Proxima", self)
        self.next_history_button.clicked.connect(partial(self._change_history_page, 1))
        pagination.addWidget(self.prev_history_button)
        pagination.addWidget(self.history_page_label, alignment=Qt.AlignmentFlag.AlignCenter)
        pagination.addWidget(self.next_history_button)
        layout.addLayout(pagination)

        self.quick_guide_browser = QTextBrowser(self)
        self.quick_guide_browser.setObjectName("panelCard")
        self.quick_guide_browser.setMaximumHeight(180)
        layout.addWidget(self.quick_guide_browser)

        self.state.changed.connect(self._handle_state_change)
        self._refresh_all()

    def _dismiss_onboarding(self):
        self.state.onboarding_dismissed = True
        self._refresh_all()

    def _handle_state_change(self, event: str):
        if event in {"analysis", "language"}:
            self._refresh_all()

    def _reset_and_refresh_history(self):
        self._history_page = 0
        self._refresh_history_table()

    def _change_history_page(self, delta: int):
        self._history_page = max(0, self._history_page + delta)
        self._refresh_history_table()

    def _refresh_all(self):
        self.header.set_title(f"🏠 {T('nav.dashboard', self.state.lang)}")
        self.onboarding_label.setText(
            "Bem-vindo ao CyberURL Analyst. Fluxo recomendado: Anatomia, Analise, Quiz, "
            "Cenarios e Glossario."
        )
        self.onboarding_frame.setVisible(not self.state.onboarding_dismissed)

        stats = self.state.get_stats()
        values = [
            str(stats["analysis_count"]),
            str(stats["safe_count"]),
            str(stats["suspicious_count"]),
            str(stats["malicious_count"]),
        ]
        titles = ["Analises", "Seguras", "Suspeitas", "Maliciosas"]
        for card, title, value in zip(self.metric_cards, titles, values):
            card.set_title(title)
            card.set_value(value)

        progress = self.state.get_progress()
        threats = progress.get("threats_identified", {})
        progress_html = [
            "<h3>Progresso de aprendizado</h3>",
            f"<p>Quizs concluidos: <b>{progress.get('quiz_rounds', 0)}</b> | Melhor quiz: <b>{int(progress.get('quiz_best_accuracy', 0) * 100)}%</b></p>",
            f"<p>Cenarios concluidos: <b>{progress.get('scenarios_completed', 0)}</b> | Melhor cenario: <b>{int(progress.get('scenarios_best_accuracy', 0) * 100)}%</b></p>",
        ]
        if any(threats.values()):
            progress_html.append("<ul>")
            for key, value in sorted(threats.items(), key=lambda item: item[1], reverse=True)[:6]:
                progress_html.append(f"<li>{key}: <b>{value}</b></li>")
            progress_html.append("</ul>")
        else:
            progress_html.append("<p style='color:#999'>Ainda sem progresso registrado.</p>")
        self.progress_browser.setHtml("".join(progress_html))

        earned_badges = self.state.get_badges()
        locked_badges = [badge for badge in BADGE_DEFINITIONS if badge["id"] not in earned_badges]
        badge_html = ["<h3>Conquistas</h3>"]
        if earned_badges:
            badge_html.append("<ul>")
            for badge_id in earned_badges:
                badge = next((item for item in BADGE_DEFINITIONS if item["id"] == badge_id), None)
                if badge:
                    badge_html.append(
                        f"<li>{badge['icon']} <b>{badge['name']}</b> - {badge['desc']}</li>"
                    )
            badge_html.append("</ul>")
        else:
            badge_html.append("<p style='color:#999'>Nenhuma conquista liberada ainda.</p>")
        if locked_badges:
            badge_html.append(f"<p style='color:#888'>Restantes: {len(locked_badges)}</p>")
        self.badges_browser.setHtml("".join(badge_html))

        self.quick_guide_browser.setHtml(
            "<h3>Guia rapido</h3>"
            "<ul>"
            "<li><b>Anatomia</b> - decompoe a URL em partes.</li>"
            "<li><b>Analise</b> - executa heuristicas, datasets e ML.</li>"
            "<li><b>Relatorio</b> - exporta o ultimo resultado.</li>"
            "<li><b>Quiz</b> - pratica com perguntas didaticas.</li>"
            "<li><b>Cenarios</b> - simula golpes reais.</li>"
            "</ul>"
        )
        self._refresh_history_table()

    def _refresh_history_table(self):
        history = self.state.get_persistent_history()
        search = self.search_input.text().strip().lower()
        class_filter = self.class_filter.currentText()
        if search:
            history = [item for item in history if search in item.get("url", "").lower()]
        mapping = {"Segura": "safe", "Suspeita": "suspicious", "Maliciosa": "malicious"}
        if class_filter != "Todas":
            history = [item for item in history if item.get("classification") == mapping.get(class_filter)]

        total_pages = max(1, (len(history) + self.HISTORY_PAGE_SIZE - 1) // self.HISTORY_PAGE_SIZE)
        self._history_page = min(self._history_page, total_pages - 1)
        start = self._history_page * self.HISTORY_PAGE_SIZE
        page_items = history[start:start + self.HISTORY_PAGE_SIZE]

        self.history_table.setRowCount(len(page_items))
        for row, item in enumerate(page_items):
            timestamp = time.strftime("%d/%m %H:%M", time.localtime(item.get("timestamp", 0)))
            classification = item.get("classification", "")
            classification_label = {
                "safe": "Segura",
                "suspicious": "Suspeita",
                "malicious": "Maliciosa",
            }.get(classification, classification)
            self.history_table.setItem(row, 0, _readonly_item(item.get("url", "")))
            self.history_table.setItem(row, 1, _readonly_item(f"{item.get('emoji', '')} {classification_label}"))
            self.history_table.setItem(row, 2, _readonly_item(str(item.get("score", "-"))))
            self.history_table.setItem(row, 3, _readonly_item(timestamp))

        self.history_page_label.setText(
            f"Pagina {self._history_page + 1} de {total_pages} ({len(history)} registros)"
        )
        self.prev_history_button.setEnabled(self._history_page > 0)
        self.next_history_button.setEnabled(self._history_page < total_pages - 1)


class AnatomyPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"🔍 {T('nav.anatomy', self.state.lang)}")
        layout.addWidget(self.header)

        input_row = QHBoxLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("https://www.exemplo.com/pagina?q=teste")
        self.analyze_button = QPushButton("Analisar anatomia", self)
        self.analyze_button.clicked.connect(self._analyze)
        input_row.addWidget(self.url_input)
        input_row.addWidget(self.analyze_button)
        layout.addLayout(input_row)

        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.browser_bar = BrowserBarWidget(self)
        layout.addWidget(self.browser_bar)

        self.breakdown_browser = QTextBrowser(self)
        self.breakdown_browser.setObjectName("panelCard")
        self.breakdown_browser.setMaximumHeight(120)
        layout.addWidget(self.breakdown_browser)

        self.components_browser = QTextBrowser(self)
        self.components_browser.setObjectName("panelCard")
        self.components_browser.setMaximumHeight(220)
        layout.addWidget(self.components_browser)

        compare_group = QGroupBox("Comparacao visual")
        compare_layout = QVBoxLayout(compare_group)
        compare_inputs = QHBoxLayout()
        self.legit_input = QLineEdit(compare_group)
        self.legit_input.setPlaceholderText("https://www.paypal.com/login")
        self.suspect_input = QLineEdit(compare_group)
        self.suspect_input.setPlaceholderText("https://www.paypa1.com/login")
        self.legit_input.textChanged.connect(self._refresh_compare)
        self.suspect_input.textChanged.connect(self._refresh_compare)
        compare_inputs.addWidget(self.legit_input)
        compare_inputs.addWidget(self.suspect_input)
        compare_layout.addLayout(compare_inputs)

        compare_bars = QHBoxLayout()
        self.legit_bar = BrowserBarWidget(compare_group)
        self.suspect_bar = BrowserBarWidget(compare_group)
        compare_bars.addWidget(self.legit_bar)
        compare_bars.addWidget(self.suspect_bar)
        compare_layout.addLayout(compare_bars)

        self.diff_browser = QTextBrowser(compare_group)
        self.diff_browser.setObjectName("panelCard")
        self.diff_browser.setMaximumHeight(180)
        compare_layout.addWidget(self.diff_browser)

        layout.addWidget(compare_group)

        self.browser_bar.setHtml("<p style='color:#888'>Cole uma URL e clique em analisar.</p>")
        self.breakdown_browser.setHtml("<p style='color:#888'>A decomposicao visual aparecera aqui.</p>")
        self.components_browser.setHtml("<p style='color:#888'>Os componentes estruturados da URL aparecerao aqui.</p>")
        self.diff_browser.setHtml("<p style='color:#888'>A comparacao de dominios aparecera aqui.</p>")

    def _analyze(self):
        raw_url = self.url_input.text().strip()
        sanitized = sanitize_input(raw_url)
        messages = []
        if sanitized.warnings:
            messages.extend(sanitized.warnings)
        if sanitized.removed_items:
            messages.append("Itens sensiveis removidos: " + ", ".join(sanitized.removed_items))
        if not sanitized.is_valid_url:
            self.status_label.setText("\n".join(messages or ["URL invalida."]))
            return

        unlock_badge("anatomy_first")
        parser = get_parser()
        components = parser.parse(sanitized.sanitized_input)
        parts = parser.get_visual_breakdown(sanitized.sanitized_input)

        self.status_label.setText("\n".join(messages) or "Estrutura da URL analisada com sucesso.")
        self.browser_bar.set_url(sanitized.sanitized_input)
        self.breakdown_browser.setHtml(build_visual_breakdown_html(parts))

        details = ["<h3>Componentes</h3><ul>"]
        if components.scheme:
            details.append(f"<li><b>Protocolo:</b> {components.scheme}</li>")
        if components.subdomain:
            details.append(f"<li><b>Subdominio:</b> {components.subdomain}</li>")
        if components.is_ip:
            details.append(f"<li><b>IP:</b> {components.ip_address}</li>")
        elif components.domain:
            details.append(f"<li><b>Dominio:</b> {components.domain}</li>")
        if components.tld:
            details.append(f"<li><b>TLD:</b> .{components.tld}</li>")
        if components.port:
            details.append(f"<li><b>Porta:</b> {components.port}</li>")
        if components.path and components.path != "/":
            details.append(f"<li><b>Path:</b> {components.path}</li>")
        if components.query:
            details.append(f"<li><b>Query:</b> ?{components.query}</li>")
        if components.fragment:
            details.append(f"<li><b>Fragmento:</b> #{components.fragment}</li>")
        if components.registered_domain:
            details.append(f"<li><b>Dominio registrado:</b> {components.registered_domain}</li>")
        details.append("</ul>")
        self.components_browser.setHtml("".join(details))

    def _refresh_compare(self):
        legit = self.legit_input.text().strip()
        suspect = self.suspect_input.text().strip()
        if not legit or not suspect:
            self.diff_browser.setHtml("<p style='color:#888'>Informe uma URL legitima e outra suspeita.</p>")
            return

        self.legit_bar.set_url(legit)
        self.suspect_bar.set_url(suspect)
        left_html, right_html, similarity, message = build_domain_diff(legit, suspect)
        self.diff_browser.setHtml(
            f"<h3>Diff de dominio</h3>"
            f"<p><b>Legitima:</b> <code>{left_html}</code></p>"
            f"<p><b>Suspeita:</b> <code>{right_html}</code></p>"
            f"<p><b>Similaridade:</b> {similarity}% - {message}</p>"
        )


class AnalysisPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"🛡️ {T('nav.analysis', self.state.lang)}")
        layout.addWidget(self.header)

        self.intro_browser = QTextBrowser(self)
        self.intro_browser.setMaximumHeight(150)
        layout.addWidget(self.intro_browser)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        self.single_tab = QWidget(self)
        self.batch_tab = QWidget(self)
        self.tabs.addTab(self.single_tab, T("analysis.tab_single", self.state.lang))
        self.tabs.addTab(self.batch_tab, T("analysis.tab_batch", self.state.lang))

        self._build_single_tab()
        self._build_batch_tab()
        self.state.changed.connect(self._handle_state_change)
        self._refresh_from_state()

    def _build_single_tab(self):
        layout = QVBoxLayout(self.single_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.single_intro_browser = QTextBrowser(self.single_tab)
        self.single_intro_browser.setMaximumHeight(130)
        layout.addWidget(self.single_intro_browser)

        input_row = QHBoxLayout()
        self.single_url_input = QLineEdit(self.single_tab)
        self.single_url_input.setPlaceholderText(T("analysis.placeholder", self.state.lang))
        self.single_analyze_button = QPushButton(T("analysis.btn_analyze", self.state.lang), self.single_tab)
        self.single_analyze_button.clicked.connect(self._analyze_single)
        input_row.addWidget(self.single_url_input)
        input_row.addWidget(self.single_analyze_button)
        layout.addLayout(input_row)

        self.single_status = QTextBrowser(self.single_tab)
        self.single_status.setMaximumHeight(170)
        layout.addWidget(self.single_status)

        self.single_summary = QTextBrowser(self.single_tab)
        self.single_summary.setMaximumHeight(210)
        layout.addWidget(self.single_summary)

        self.single_report = ReportViewer(self.single_tab)
        self.single_report.setMinimumHeight(360)
        layout.addWidget(self.single_report)

        feedback_row = QHBoxLayout()
        self.feedback_yes_button = QPushButton("👍 Analise util", self.single_tab)
        self.feedback_no_button = QPushButton("👎 Precisa melhorar", self.single_tab)
        self.feedback_yes_button.clicked.connect(partial(self._send_feedback, True))
        self.feedback_no_button.clicked.connect(partial(self._send_feedback, False))
        feedback_row.addWidget(self.feedback_yes_button)
        feedback_row.addWidget(self.feedback_no_button)
        layout.addLayout(feedback_row)

        session_label = _section_label("Historico da sessao", self.single_tab)
        layout.addWidget(session_label)
        self.session_history_list = QListWidget(self.single_tab)
        self.session_history_list.setMinimumHeight(170)
        layout.addWidget(self.session_history_list)

    def _build_batch_tab(self):
        layout = QVBoxLayout(self.batch_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.batch_intro_browser = QTextBrowser(self.batch_tab)
        self.batch_intro_browser.setMaximumHeight(140)
        layout.addWidget(self.batch_intro_browser)

        self.batch_input = QPlainTextEdit(self.batch_tab)
        self.batch_input.setPlaceholderText("Uma URL por linha")
        self.batch_input.setMaximumHeight(140)
        layout.addWidget(self.batch_input)

        self.batch_analyze_button = QPushButton(T("analysis.btn_batch", self.state.lang), self.batch_tab)
        self.batch_analyze_button.clicked.connect(self._analyze_batch)
        layout.addWidget(self.batch_analyze_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.batch_status = QTextBrowser(self.batch_tab)
        self.batch_status.setMaximumHeight(170)
        layout.addWidget(self.batch_status)

        self.batch_results = QTextBrowser(self.batch_tab)
        self.batch_results.setMinimumHeight(360)
        layout.addWidget(self.batch_results)

    def _compose_status_fragment(self, execution) -> str:
        details = []
        if execution.warnings:
            details.extend(execution.warnings)
        if execution.removed_items:
            details.append("Itens sensiveis removidos: " + ", ".join(execution.removed_items))
        if execution.from_cache and execution.report is not None:
            details.append("Resultado carregado do cache local.")

        if execution.error:
            return status_banner_fragment(
                "Nao foi possivel concluir a analise",
                execution.error,
                tone="danger",
                items=details,
                icon="⛔",
            )

        if execution.report is not None:
            tone = {
                "safe": "success",
                "suspicious": "warning",
                "malicious": "danger",
            }.get(execution.report.classification, "info")
            title = "Resultado recuperado do cache" if execution.from_cache else "Analise concluida"
            message = (
                "O painel abaixo resume os principais sinais encontrados nesta URL."
                if not execution.from_cache
                else "Este resultado veio do cache local para acelerar a consulta."
            )
            return status_banner_fragment(title, message, tone=tone, items=details, icon="✅")

        return status_banner_fragment(
            "Nenhuma analise executada",
            "Informe uma URL para iniciar a verificacao.",
            tone="info",
            icon="ℹ️",
        )

    def _refresh_intro_panels(self):
        self.intro_browser.setHtml(
            page_intro_fragment(
                "Analisar com contexto",
                "Compare o resultado, o score e os sinais detalhados antes de tomar uma decisao.",
                bullets=[
                    "Use a aba individual para investigar uma URL em profundidade.",
                    "Use a aba em lote para triagem rapida de varias entradas.",
                    "Considere o relatorio como apoio didatico, nao como veredito absoluto.",
                ],
                kicker="Analise guiada",
                tone="info",
            )
        )
        self.single_intro_browser.setHtml(
            page_intro_fragment(
                "Inspecao individual",
                "Ideal para entender porque uma URL parece segura, suspeita ou maliciosa.",
                bullets=[
                    "Cole a URL completa.",
                    "Leia o resumo e depois desca para os fatores analisados.",
                ],
                kicker="Fluxo recomendado",
                tone="success",
            )
        )
        self.batch_intro_browser.setHtml(
            page_intro_fragment(
                "Triagem em lote",
                "Boa para limpar listas grandes e identificar rapidamente os casos que merecem revisao manual.",
                bullets=[
                    "Use uma URL por linha.",
                    "O resultado prioriza velocidade e consolidacao visual.",
                ],
                kicker="Triagem",
                tone="warning",
            )
        )

    def _analyze_single(self):
        execution = run_analysis(self.single_url_input.text().strip(), state=self.state)
        self.single_status.setHtml(self._compose_status_fragment(execution))
        if execution.report is not None:
            source_label = "Cache local" if execution.from_cache else "Processado agora"
            self.single_summary.setHtml(report_summary_fragment(execution.report, source_label))
            self.single_report.set_report(execution.report)
        else:
            self.single_summary.setHtml(
                empty_state_html(
                    "Sem resumo para exibir.",
                    "Quando a analise terminar, score, fatores e consultas externas aparecerao aqui.",
                )
            )
            self.single_report.setHtml(
                empty_state_html(
                    "Nenhum relatorio disponivel.",
                    "Revise a URL informada e tente novamente.",
                )
            )
        self._refresh_session_history()

    def _analyze_batch(self):
        urls = [line.strip() for line in self.batch_input.toPlainText().splitlines() if line.strip()]
        if not urls:
            self.batch_status.setHtml(
                status_banner_fragment(
                    "Nada para analisar",
                    "Informe pelo menos uma URL para iniciar a triagem em lote.",
                    tone="warning",
                    icon="⚠️",
                )
            )
            return

        html_chunks = []
        errors = []
        for index, url in enumerate(urls, start=1):
            execution = run_analysis(url, state=self.state)
            if execution.report is not None:
                html_chunks.append(
                    f"<div class='panel' style='margin-bottom:12px'>"
                    f"<div class='kicker'>Analise {index}/{len(urls)}</div>"
                    f"{render_report_fragment(execution.report)}"
                    "</div>"
                )
            else:
                errors.append(f"{url}: {execution.error or 'falha ao analisar'}")

        if errors:
            self.batch_status.setHtml(
                status_banner_fragment(
                    "Triagem concluida com ressalvas",
                    f"{len(urls) - len(errors)} de {len(urls)} URLs geraram relatorio.",
                    tone="warning",
                    items=errors[:8],
                    icon="⚠️",
                )
            )
        else:
            self.batch_status.setHtml(
                status_banner_fragment(
                    "Triagem concluida",
                    f"{len(urls)} URLs analisadas com sucesso.",
                    tone="success",
                    icon="✅",
                )
            )
        self.batch_results.setHtml(
            "<hr>".join(html_chunks)
            or empty_state_html(
                "Nenhum resultado disponivel.",
                "As URLs sem analise concluida ficarao listadas no banner acima.",
            )
        )
        self._refresh_session_history()

    def _send_feedback(self, useful: bool):
        report = self.state.last_report
        if report is None:
            QMessageBox.information(self, APP_NAME, "Nenhum relatorio para avaliar.")
            return
        save_feedback(report.url_defanged, report.classification, useful)
        QMessageBox.information(self, APP_NAME, "Feedback registrado.")

    def _handle_state_change(self, event: str):
        if event in {"analysis", "report"}:
            self._refresh_from_state()

    def _refresh_from_state(self):
        self._refresh_intro_panels()
        if self.state.last_report is not None:
            self.single_status.setHtml(
                status_banner_fragment(
                    "Ultimo resultado carregado",
                    "O relatorio abaixo corresponde a analise mais recente da sessao.",
                    tone="info",
                    icon="📌",
                )
            )
            self.single_summary.setHtml(report_summary_fragment(self.state.last_report, "Ultima analise"))
            self.single_report.set_report(self.state.last_report)
        else:
            self.single_status.setHtml(
                status_banner_fragment(
                    "Pronto para analisar",
                    "Cole uma URL e use o painel para investigar sinais de risco.",
                    tone="info",
                    icon="🧭",
                )
            )
            self.single_summary.setHtml(
                empty_state_html(
                    "O resumo rapido aparecera aqui.",
                    "Depois da analise voce vera score, quantidade de fatores e consultas externas.",
                )
            )
            self.single_report.setHtml(
                empty_state_html(
                    "Nenhum relatorio disponivel.",
                    "Use a aba individual para gerar um relatorio detalhado desta URL.",
                )
            )

        self.batch_status.setHtml(
            status_banner_fragment(
                "Fila em lote pronta",
                "Cole uma lista de URLs para gerar relatorios consolidados nesta aba.",
                tone="info",
                icon="📚",
            )
        )
        self.batch_results.setHtml(
            empty_state_html(
                "Nenhum lote analisado ainda.",
                "Os relatorios em lote serao empilhados aqui em blocos visuais.",
            )
        )
        self._refresh_session_history()

    def _refresh_session_history(self):
        self.session_history_list.clear()
        for item in self.state.session_history[:20]:
            self.session_history_list.addItem(f"{item['emoji']} {item['url']}")


class ReportPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"📊 {T('nav.report', self.state.lang)}")
        layout.addWidget(self.header)

        self.report_intro = QTextBrowser(self)
        self.report_intro.setMaximumHeight(150)
        layout.addWidget(self.report_intro)

        actions = QHBoxLayout()
        self.export_text_button = QPushButton("Baixar TXT", self)
        self.export_text_button.clicked.connect(self._export_text)
        self.export_html_button = QPushButton("Baixar HTML", self)
        self.export_html_button.clicked.connect(self._export_html)
        self.feedback_yes_button = QPushButton("👍 Analise util", self)
        self.feedback_no_button = QPushButton("👎 Precisa melhorar", self)
        self.feedback_yes_button.clicked.connect(partial(self._send_feedback, True))
        self.feedback_no_button.clicked.connect(partial(self._send_feedback, False))
        for button in [
            self.export_text_button,
            self.export_html_button,
            self.feedback_yes_button,
            self.feedback_no_button,
        ]:
            actions.addWidget(button)
        layout.addLayout(actions)

        self.report_summary = QTextBrowser(self)
        self.report_summary.setMaximumHeight(210)
        layout.addWidget(self.report_summary)

        self.report_viewer = ReportViewer(self)
        layout.addWidget(self.report_viewer)

        self.state.changed.connect(self._handle_state_change)
        self._refresh_view()

    def _handle_state_change(self, event: str):
        if event in {"analysis", "report", "language"}:
            self._refresh_view()

    def _refresh_view(self):
        report = self.state.last_report
        enabled = report is not None
        for button in [
            self.export_text_button,
            self.export_html_button,
            self.feedback_yes_button,
            self.feedback_no_button,
        ]:
            button.setEnabled(enabled)
        if report is None:
            self.report_intro.setHtml(
                page_intro_fragment(
                    "Relatorios exportaveis",
                    T("report.placeholder", self.state.lang),
                    bullets=[
                        "Exporte em TXT para compartilhar rapidamente.",
                        "Exporte em HTML quando quiser um relatorio mais apresentavel.",
                        "Registre feedback para melhorar a ferramenta.",
                    ],
                    kicker="Centro de relatorios",
                    tone="info",
                )
            )
            self.report_summary.setHtml(
                empty_state_html(
                    "Nenhum resumo disponivel.",
                    "Assim que uma URL for analisada, o painel acima mostrara score e volume de sinais.",
                )
            )
            self.report_viewer.setHtml(
                empty_state_html(
                    "Nenhum relatorio disponivel.",
                    "Analise uma URL na pagina anterior para habilitar exportacao e feedback.",
                )
            )
        else:
            self.report_intro.setHtml(
                status_banner_fragment(
                    "Relatorio pronto para exportacao",
                    "Revise o resumo, exporte nos formatos desejados e registre se a analise foi util.",
                    tone="success",
                    items=[
                        f"Classificacao: {report.classification_label}",
                        f"Score atual: {report.score}/100",
                    ],
                    icon="📄",
                )
            )
            self.report_summary.setHtml(report_summary_fragment(report, "Pronto para exportar"))
            self.report_viewer.set_report(report)

    def _export_text(self):
        report = self.state.last_report
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar relatorio TXT", "relatorio.txt", "Text (*.txt)")
        if not file_path:
            return
        content = get_report_generator().format_text_report(report)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _export_html(self):
        report = self.state.last_report
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar relatorio HTML", "relatorio.html", "HTML (*.html)")
        if not file_path:
            return
        content = get_report_generator().format_html_report(report)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _send_feedback(self, useful: bool):
        report = self.state.last_report
        if report is None:
            return
        save_feedback(report.url_defanged, report.classification, useful)
        QMessageBox.information(self, APP_NAME, "Feedback registrado.")


class QuizPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.engine = QuizEngine()
        try:
            self.engine.load_from_dataset_manager()
        except Exception:
            pass
        self.question_number = 0
        self.current_question = None
        self.completed_difficulty = "iniciante"
        self._results_recorded = False
        self._saved_to_leaderboard = False
        self._checklist_boxes: list[QCheckBox] = []

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"❓ {T('nav.quiz', self.state.lang)}")
        layout.addWidget(self.header)

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("Dificuldade:"))
        self.difficulty_combo = QComboBox(self)
        self.difficulty_combo.addItems(["Auto", "Iniciante", "Intermediario", "Avancado"])
        control_row.addWidget(self.difficulty_combo)
        control_row.addStretch(1)
        layout.addLayout(control_row)

        metrics_layout = QHBoxLayout()
        self.quiz_metric_cards = [
            MetricCard("Acertos", "0", self),
            MetricCard("Sequencia", "0", self),
            MetricCard("Precisao", "0%", self),
        ]
        for card in self.quiz_metric_cards:
            metrics_layout.addWidget(card)
        layout.addLayout(metrics_layout)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self._build_quiz_intro_page()
        self._build_quiz_question_page()
        self._build_quiz_results_page()

        self._refresh_leaderboard()
        self._refresh_metrics()
        self.stack.setCurrentWidget(self.intro_page)

    def _build_quiz_intro_page(self):
        self.intro_page = QWidget(self)
        layout = QVBoxLayout(self.intro_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        intro_browser = QTextBrowser(self.intro_page)
        intro_browser.setMaximumHeight(130)
        intro_browser.setHtml(
            page_intro_fragment(
                "Treinamento gamificado",
                "Responda dez perguntas para praticar reconhecimento de URLs maliciosas sem perder o contexto da URL analisada.",
                bullets=[
                    "O modo Auto ajusta a dificuldade ao seu ritmo.",
                    "Acompanhe progresso, precisao e sequencia em tempo real.",
                ],
                kicker="Aprendizado ativo",
                tone="info",
            )
        )
        layout.addWidget(intro_browser)

        button_row = QHBoxLayout()
        self.quiz_start_button = QPushButton(T("quiz.btn_start", self.state.lang), self.intro_page)
        self.quiz_start_button.clicked.connect(self._start_round)
        self.quiz_reset_button = QPushButton("Resetar", self.intro_page)
        self.quiz_reset_button.clicked.connect(self._reset_round)
        button_row.addWidget(self.quiz_start_button)
        button_row.addWidget(self.quiz_reset_button)
        layout.addLayout(button_row)

        leaderboard_label = _section_label("Leaderboard", self.intro_page)
        layout.addWidget(leaderboard_label)
        self.leaderboard_table = QTableWidget(0, 5, self.intro_page)
        self.leaderboard_table.setHorizontalHeaderLabels(["Nome", "Precisao", "Acertos", "Dificuldade", "Data"])
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.leaderboard_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.leaderboard_table.verticalHeader().setVisible(False)
        layout.addWidget(self.leaderboard_table)
        self.stack.addWidget(self.intro_page)

    def _build_quiz_question_page(self):
        self.question_page = QWidget(self)
        layout = QVBoxLayout(self.question_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.question_status = QLabel(self.question_page)
        self.question_status.setWordWrap(True)
        layout.addWidget(self.question_status)

        self.question_browser_bar = BrowserBarWidget(self.question_page)
        layout.addWidget(self.question_browser_bar)

        self.question_context = QLabel(self.question_page)
        self.question_context.setWordWrap(True)
        layout.addWidget(self.question_context)

        self.question_text = QLabel(self.question_page)
        self.question_text.setWordWrap(True)
        layout.addWidget(self.question_text)

        self.options_widget = QWidget(self.question_page)
        self.options_layout = QVBoxLayout(self.options_widget)
        layout.addWidget(self.options_widget)

        self.question_feedback = QTextBrowser(self.question_page)
        self.question_feedback.setObjectName("panelCard")
        self.question_feedback.setVisible(False)
        layout.addWidget(self.question_feedback)

        self.next_question_button = QPushButton(T("quiz.btn_next", self.state.lang), self.question_page)
        self.next_question_button.clicked.connect(self._next_question)
        self.next_question_button.setVisible(False)
        layout.addWidget(self.next_question_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(self.question_page)

    def _build_quiz_results_page(self):
        self.results_page = QWidget(self)
        layout = QVBoxLayout(self.results_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.results_browser = QTextBrowser(self.results_page)
        layout.addWidget(self.results_browser)

        form = QFormLayout()
        self.leaderboard_name_input = QLineEdit(self.results_page)
        self.leaderboard_name_input.setText("Jogador")
        form.addRow("Nome para o leaderboard:", self.leaderboard_name_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.save_leaderboard_button = QPushButton("Salvar no leaderboard", self.results_page)
        self.save_leaderboard_button.clicked.connect(self._save_leaderboard)
        self.export_quiz_button = QPushButton("Exportar resultado CSV", self.results_page)
        self.export_quiz_button.clicked.connect(self._export_quiz_result)
        self.restart_quiz_button = QPushButton("Nova rodada", self.results_page)
        self.restart_quiz_button.clicked.connect(self._reset_round)
        button_row.addWidget(self.save_leaderboard_button)
        button_row.addWidget(self.export_quiz_button)
        button_row.addWidget(self.restart_quiz_button)
        layout.addLayout(button_row)
        self.stack.addWidget(self.results_page)

    def _refresh_leaderboard(self):
        rows = sorted(load_leaderboard(), key=lambda item: item.get("accuracy", 0), reverse=True)[:10]
        self.leaderboard_table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            date_text = time.strftime("%d/%m", time.localtime(entry.get("timestamp", 0)))
            self.leaderboard_table.setItem(row, 0, _readonly_item(entry.get("name", "Anon")))
            self.leaderboard_table.setItem(row, 1, _readonly_item(f"{int(entry.get('accuracy', 0) * 100)}%"))
            self.leaderboard_table.setItem(row, 2, _readonly_item(f"{entry.get('correct', 0)}/{entry.get('total', 0)}"))
            self.leaderboard_table.setItem(row, 3, _readonly_item(entry.get("difficulty", "")))
            self.leaderboard_table.setItem(row, 4, _readonly_item(date_text))

    def _difficulty_code(self) -> str:
        text = self.difficulty_combo.currentText()
        mapping = {
            "Iniciante": "iniciante",
            "Intermediario": "intermediario",
            "Avancado": "avancado",
        }
        if text == "Auto":
            return self.engine.get_suggested_difficulty()
        return mapping.get(text, "iniciante")

    def _difficulty_label(self, code: str) -> str:
        mapping = {
            "iniciante": "Iniciante",
            "intermediario": "Intermediario",
            "avancado": "Avancado",
        }
        return mapping.get(code, code)

    def _refresh_metrics(self):
        stats = self.engine.get_statistics()
        self.quiz_metric_cards[0].set_value(str(stats.correct_answers))
        self.quiz_metric_cards[1].set_value(str(stats.current_streak))
        self.quiz_metric_cards[2].set_value(f"{int(stats.accuracy * 100)}%")
        progress_value = 0 if self.question_number == 0 else int(
            min(self.question_number, QUIZ_QUESTIONS_PER_ROUND) / QUIZ_QUESTIONS_PER_ROUND * 100
        )
        self.progress_bar.setValue(progress_value)

    def _start_round(self):
        self.engine.reset_statistics()
        self.question_number = 1
        self.completed_difficulty = self._difficulty_code()
        self.current_question = self.engine.generate_question(self.completed_difficulty)
        self._results_recorded = False
        self._saved_to_leaderboard = False
        self._render_question()
        self.stack.setCurrentWidget(self.question_page)

    def _reset_round(self):
        self.engine.reset_statistics()
        self.question_number = 0
        self.current_question = None
        self._results_recorded = False
        self._saved_to_leaderboard = False
        self._refresh_metrics()
        self._refresh_leaderboard()
        self.stack.setCurrentWidget(self.intro_page)

    def _render_question(self):
        if self.question_number > QUIZ_QUESTIONS_PER_ROUND:
            self._finish_round()
            return

        self._refresh_metrics()
        question = self.current_question
        self.question_status.setText(
            f"Questao {self.question_number}/{QUIZ_QUESTIONS_PER_ROUND} - {self._difficulty_label(question.difficulty)}"
        )
        self.question_browser_bar.set_url(question.url_display or question.url_defanged)
        self.question_context.setText(question.scenario_context)
        self.question_context.setVisible(bool(question.scenario_context))
        self.question_text.setText(question.question_text)

        _clear_layout(self.options_layout)
        self._checklist_boxes = []
        if question.question_type == "binary":
            row = QHBoxLayout()
            safe_button = QPushButton("🟢 SEGURA", self.options_widget)
            malicious_button = QPushButton("🔴 MALICIOSA", self.options_widget)
            safe_button.clicked.connect(partial(self._submit_answer, True))
            malicious_button.clicked.connect(partial(self._submit_answer, False))
            row.addWidget(safe_button)
            row.addWidget(malicious_button)
            self.options_layout.addLayout(row)
        elif question.question_type == "multiple_choice":
            for index, option in enumerate(question.options):
                button = QPushButton(option, self.options_widget)
                button.clicked.connect(partial(self._submit_answer, chr(65 + index)))
                self.options_layout.addWidget(button)
        elif question.question_type == "checklist":
            for option in question.options:
                checkbox = QCheckBox(option, self.options_widget)
                self._checklist_boxes.append(checkbox)
                self.options_layout.addWidget(checkbox)
            confirm_button = QPushButton("Confirmar", self.options_widget)
            confirm_button.clicked.connect(self._submit_checklist)
            self.options_layout.addWidget(confirm_button)

        self.question_feedback.setVisible(False)
        self.next_question_button.setVisible(False)

    def _submit_checklist(self):
        selected = [checkbox.text() for checkbox in self._checklist_boxes if checkbox.isChecked()]
        self._submit_answer(selected)

    def _submit_answer(self, answer):
        feedback = self.engine.check_answer(self.current_question.question_id, answer)
        self._refresh_metrics()
        tone = "#4CAF50" if feedback.is_correct else "#F44336"
        findings = "".join(f"<li>{item}</li>" for item in feedback.detailed_findings)
        partial_line = (
            f"<p>Pontuacao parcial: {int(feedback.partial_score * 100)}%</p>"
            if feedback.partial_score and feedback.partial_score < 1.0
            else ""
        )
        self.question_feedback.setHtml(
            status_banner_fragment(
                "Resposta correta" if feedback.is_correct else "Resposta incorreta",
                feedback.explanation,
                tone="success" if feedback.is_correct else "danger",
                items=feedback.detailed_findings,
                icon="✅" if feedback.is_correct else "⛔",
            )
            + (f"<p>{partial_line}</p>" if partial_line else "")
            + f"<p class='small'>{feedback.tip}</p>"
        )
        self.question_feedback.setVisible(True)
        self.next_question_button.setVisible(True)

    def _next_question(self):
        self.question_number += 1
        self.current_question = self.engine.generate_question(self.completed_difficulty)
        self._render_question()

    def _finish_round(self):
        stats = self.engine.get_statistics()
        if not self._results_recorded:
            update_quiz_progress(stats.accuracy)
            unlock_badge("quiz_complete")
            if stats.accuracy >= 1.0:
                unlock_badge("quiz_perfect")
            if self.completed_difficulty == "avancado":
                unlock_badge("quiz_advanced")
            self._results_recorded = True

        if stats.accuracy >= 0.9:
            message = "Excelente desempenho."
        elif stats.accuracy >= 0.7:
            message = "Bom trabalho."
        elif stats.accuracy >= 0.5:
            message = "Resultado razoavel."
        else:
            message = "Vale praticar mais um pouco."

        self.results_browser.setHtml(
            status_banner_fragment(
                T('quiz.final', self.state.lang),
                message,
                tone="success" if stats.accuracy >= 0.7 else "warning",
                items=[
                    f"Acertos: {stats.correct_answers}/{stats.total_questions}",
                    f"Precisao: {int(stats.accuracy * 100)}%",
                    f"Melhor sequencia: {stats.best_streak}",
                    f"Dificuldade: {self._difficulty_label(self.completed_difficulty)}",
                ],
                icon="🏁",
            )
        )
        self.stack.setCurrentWidget(self.results_page)
        self._refresh_metrics()

    def _save_leaderboard(self):
        if self._saved_to_leaderboard:
            QMessageBox.information(self, APP_NAME, "Resultado ja salvo.")
            return
        stats = self.engine.get_statistics()
        save_leaderboard_entry(
            self.leaderboard_name_input.text().strip() or "Jogador",
            stats.correct_answers,
            stats.total_questions,
            stats.accuracy,
            self.completed_difficulty,
            stats.best_streak,
        )
        self._saved_to_leaderboard = True
        self._refresh_leaderboard()
        QMessageBox.information(self, APP_NAME, "Resultado salvo no leaderboard.")

    def _export_quiz_result(self):
        stats = self.engine.get_statistics()
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar resultado do quiz", "quiz_resultado.csv", "CSV (*.csv)")
        if not file_path:
            return
        lines = ["Acertos,Total,Precisao,Sequencia,Dificuldade"]
        lines.append(
            f"{stats.correct_answers},{stats.total_questions},{int(stats.accuracy * 100)}%,{stats.best_streak},{self.completed_difficulty}"
        )
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


class ScenariosPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.scenario_index = 0
        self.scenario_score = 0
        self.scenario_total = 0
        self.presentation_mode = False
        self._results_recorded = False

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"🎭 {T('nav.scenarios', self.state.lang)}")
        layout.addWidget(self.header)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Categoria:"))
        self.category_combo = QComboBox(self)
        self.category_combo.addItems(SCENARIO_CATEGORIES)
        controls.addWidget(self.category_combo)
        self.presentation_checkbox = QCheckBox("Modo apresentacao", self)
        controls.addWidget(self.presentation_checkbox)
        controls.addStretch(1)
        self.score_card = MetricCard("Score", "0/0", self)
        controls.addWidget(self.score_card)
        layout.addLayout(controls)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self._build_scenario_intro_page()
        self._build_scenario_page()
        self._build_scenario_results_page()
        self.stack.setCurrentWidget(self.scenario_intro_page)

    def _build_scenario_intro_page(self):
        self.scenario_intro_page = QWidget(self)
        layout = QVBoxLayout(self.scenario_intro_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        intro = QTextBrowser(self.scenario_intro_page)
        intro.setMaximumHeight(150)
        intro.setHtml(
            page_intro_fragment(
                "Treinamento por cenarios",
                "Analise mensagens, e-mails e abordagens suspeitas e decida se clicaria ou nao antes de ver a explicacao.",
                bullets=[
                    "Use Modo apresentacao para telas maiores ou aula expositiva.",
                    "Os alertas explicam exatamente o que entregou o golpe.",
                ],
                kicker="Simulacoes",
                tone="warning",
            )
        )
        layout.addWidget(intro)
        self.start_scenario_button = QPushButton("Iniciar simulacao", self.scenario_intro_page)
        self.start_scenario_button.clicked.connect(self._start_scenarios)
        layout.addWidget(self.start_scenario_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(self.scenario_intro_page)

    def _build_scenario_page(self):
        self.scenario_page = QWidget(self)
        layout = QVBoxLayout(self.scenario_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.scenario_header_label = QLabel(self.scenario_page)
        self.scenario_header_label.setWordWrap(True)
        layout.addWidget(self.scenario_header_label)
        self.scenario_message = QTextBrowser(self.scenario_page)
        layout.addWidget(self.scenario_message)
        self.scenario_question_label = QLabel(T("scenarios.question", self.state.lang), self.scenario_page)
        layout.addWidget(self.scenario_question_label)
        button_row = QHBoxLayout()
        self.scenario_yes_button = QPushButton(T("scenarios.yes", self.state.lang), self.scenario_page)
        self.scenario_no_button = QPushButton(T("scenarios.no", self.state.lang), self.scenario_page)
        self.scenario_yes_button.clicked.connect(partial(self._submit_scenario, True))
        self.scenario_no_button.clicked.connect(partial(self._submit_scenario, False))
        button_row.addWidget(self.scenario_yes_button)
        button_row.addWidget(self.scenario_no_button)
        layout.addLayout(button_row)
        self.scenario_feedback = QTextBrowser(self.scenario_page)
        self.scenario_feedback.setObjectName("panelCard")
        self.scenario_feedback.setVisible(False)
        layout.addWidget(self.scenario_feedback)
        self.next_scenario_button = QPushButton("Proximo", self.scenario_page)
        self.next_scenario_button.clicked.connect(self._next_scenario)
        self.next_scenario_button.setVisible(False)
        layout.addWidget(self.next_scenario_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.stack.addWidget(self.scenario_page)

    def _build_scenario_results_page(self):
        self.scenario_results_page = QWidget(self)
        layout = QVBoxLayout(self.scenario_results_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self.scenario_results_browser = QTextBrowser(self.scenario_results_page)
        layout.addWidget(self.scenario_results_browser)
        button_row = QHBoxLayout()
        self.export_scenario_button = QPushButton("Exportar resultado", self.scenario_results_page)
        self.export_scenario_button.clicked.connect(self._export_scenario_result)
        self.restart_scenario_button = QPushButton("Nova simulacao", self.scenario_results_page)
        self.restart_scenario_button.clicked.connect(self._reset_scenarios)
        button_row.addWidget(self.export_scenario_button)
        button_row.addWidget(self.restart_scenario_button)
        layout.addLayout(button_row)
        self.stack.addWidget(self.scenario_results_page)

    def _filtered_scenarios(self) -> list[dict]:
        category = self.category_combo.currentText()
        if category == "Todos":
            return SCENARIOS
        return [scenario for scenario in SCENARIOS if scenario["category"] == category]

    def _start_scenarios(self):
        scenarios = self._filtered_scenarios()
        if not scenarios:
            QMessageBox.information(self, APP_NAME, "Nao ha cenarios para a categoria selecionada.")
            return
        self.scenario_index = 0
        self.scenario_score = 0
        self.scenario_total = 0
        self.presentation_mode = self.presentation_checkbox.isChecked()
        self._results_recorded = False
        self._render_scenario()
        self.stack.setCurrentWidget(self.scenario_page)

    def _render_scenario(self):
        scenarios = self._filtered_scenarios()
        if self.scenario_index >= len(scenarios):
            self._finish_scenarios()
            return
        scenario = scenarios[self.scenario_index]
        self.score_card.set_value(f"{self.scenario_score}/{self.scenario_total}")
        self.scenario_header_label.setText(
            f"{scenario['category_icon']} {scenario['category']} - {scenario['channel_icon']} {scenario['channel']} "
            f"({self.scenario_index + 1}/{len(scenarios)})"
        )
        font_size = "18px" if self.presentation_mode else "14px"
        sender_html = f"<p><b>De:</b> {scenario['sender']}</p>" if scenario.get("sender") else ""
        subject_html = f"<p><b>Assunto:</b> {scenario['subject']}</p>" if scenario.get("subject") else ""
        self.scenario_message.setHtml(
            f"<div class='panel'>"
            f"<div class='kicker'>Mensagem em analise</div>"
            f"{sender_html}{subject_html}<hr><pre style='white-space:pre-wrap;font-size:{font_size};'>{scenario['body']}</pre>"
            "</div>"
        )
        self.scenario_feedback.setVisible(False)
        self.next_scenario_button.setVisible(False)
        self.scenario_yes_button.setEnabled(True)
        self.scenario_no_button.setEnabled(True)

    def _submit_scenario(self, click: bool):
        scenarios = self._filtered_scenarios()
        scenario = scenarios[self.scenario_index]
        self.scenario_total += 1
        correct = (not click) if scenario["is_phishing"] else click
        if correct:
            self.scenario_score += 1
        alerts_html = "".join(f"<li><b>{name}</b> - {detail}</li>" for name, detail in scenario["alerts"])
        self.scenario_feedback.setHtml(
            status_banner_fragment(
                "Decisao correta" if correct else "Decisao incorreta",
                scenario['lesson'],
                tone="success" if correct else "danger",
                items=[f"{name} - {detail}" for name, detail in scenario['alerts']],
                icon="✅" if correct else "⛔",
            )
        )
        self.scenario_feedback.setVisible(True)
        self.next_scenario_button.setVisible(True)
        self.score_card.set_value(f"{self.scenario_score}/{self.scenario_total}")
        self.scenario_yes_button.setEnabled(False)
        self.scenario_no_button.setEnabled(False)

    def _next_scenario(self):
        self.scenario_index += 1
        self._render_scenario()

    def _finish_scenarios(self):
        if not self._results_recorded:
            update_scenario_progress(self.scenario_score, self.scenario_total)
            unlock_badge("scenario_complete")
            if self.scenario_total and (self.scenario_score / self.scenario_total) >= 0.8:
                unlock_badge("scenario_ace")
            self._results_recorded = True
        accuracy = int((self.scenario_score / max(1, self.scenario_total)) * 100)
        if accuracy >= 80:
            message = "Excelente leitura dos sinais de alerta."
        elif accuracy >= 60:
            message = "Bom trabalho. Continue praticando."
        else:
            message = "Vale revisar os alertas mostrados em cada cenario."
        self.scenario_results_browser.setHtml(
            status_banner_fragment(
                "Simulacao concluida",
                message,
                tone="success" if accuracy >= 80 else ("warning" if accuracy >= 60 else "danger"),
                items=[
                    f"Decisoes corretas: {self.scenario_score}/{self.scenario_total}",
                    f"Precisao: {accuracy}%",
                ],
                icon="🎯",
            )
        )
        self.stack.setCurrentWidget(self.scenario_results_page)

    def _export_scenario_result(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar resultado da simulacao", "cenarios_resultado.csv", "CSV (*.csv)")
        if not file_path:
            return
        accuracy = int((self.scenario_score / max(1, self.scenario_total)) * 100)
        lines = ["Score,Total,Precisao", f"{self.scenario_score},{self.scenario_total},{accuracy}%"]
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _reset_scenarios(self):
        self.scenario_index = 0
        self.scenario_score = 0
        self.scenario_total = 0
        self.score_card.set_value("0/0")
        self.stack.setCurrentWidget(self.scenario_intro_page)


class APIsPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.current_worker = None

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"🔌 {T('nav.apis', self.state.lang)}")
        layout.addWidget(self.header)

        self.api_intro_browser = QTextBrowser(self)
        self.api_intro_browser.setMaximumHeight(150)
        layout.addWidget(self.api_intro_browser)

        self.quota_browser = QTextBrowser(self)
        self.quota_browser.setMaximumHeight(160)
        layout.addWidget(self.quota_browser)

        form = QFormLayout()
        self.vt_key_input = QLineEdit(self)
        self.vt_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.us_key_input = QLineEdit(self)
        self.us_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.sb_key_input = QLineEdit(self)
        self.sb_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("VirusTotal", self.vt_key_input)
        form.addRow("URLScan.io", self.us_key_input)
        form.addRow("Safe Browsing", self.sb_key_input)
        layout.addLayout(form)

        consent_row = QHBoxLayout()
        self.consent_button = QPushButton("Concordo com o envio de dados", self)
        self.consent_button.clicked.connect(self._grant_consent)
        self.consent_state_label = QLabel(self)
        consent_row.addWidget(self.consent_button)
        consent_row.addWidget(self.consent_state_label)
        consent_row.addStretch(1)
        layout.addLayout(consent_row)

        query_row = QHBoxLayout()
        self.api_url_input = QLineEdit(self)
        self.api_url_input.setPlaceholderText("https://exemplo.com")
        self.api_query_button = QPushButton("Consultar APIs", self)
        self.api_query_button.clicked.connect(self._run_query)
        query_row.addWidget(self.api_url_input)
        query_row.addWidget(self.api_query_button)
        layout.addLayout(query_row)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.results_browser = QTextBrowser(self)
        self.results_browser.setOpenExternalLinks(True)
        layout.addWidget(self.results_browser)

        self.state.changed.connect(self._handle_state_change)
        self._refresh_intro_panel()
        self._refresh_consent_state()
        self._refresh_quota()

    def _refresh_intro_panel(self):
        self.api_intro_browser.setHtml(
            page_intro_fragment(
                "Consulta a servicos externos",
                "Use esta area apenas quando fizer sentido compartilhar a URL com servicos de reputacao e sandbox.",
                bullets=[
                    "O envio so e liberado apos consentimento explicito.",
                    "As cotas abaixo ajudam a evitar bloqueios ou desperdicio de requests.",
                ],
                kicker="Integracoes",
                tone="warning",
            )
        )

    def _handle_state_change(self, event: str):
        if event == "consent":
            self._refresh_consent_state()

    def _grant_consent(self):
        self.state.set_consent_given(True)

    def _refresh_consent_state(self):
        if self.state.consent_given:
            self.consent_state_label.setText("Consentimento registrado")
            self.consent_button.setEnabled(False)
            self.api_query_button.setEnabled(True)
        else:
            self.consent_state_label.setText("Sem consentimento")
            self.consent_button.setEnabled(True)
            self.api_query_button.setEnabled(False)

    def _refresh_quota(self):
        from ui.resources import get_api_client

        client = get_api_client()
        if client is None:
            self.quota_browser.setHtml(
                status_banner_fragment(
                    "Modulo indisponivel",
                    "As integracoes externas nao puderam ser carregadas nesta execucao.",
                    tone="warning",
                    icon="⚠️",
                )
            )
            return
        quotas = client.get_remaining_quota()
        lines = ["<div class='panel'><div class='kicker'>Cotas restantes</div><table>"]
        for key, label in [
            ("virustotal", "VirusTotal"),
            ("urlscan", "URLScan.io"),
            ("safebrowsing", "Safe Browsing"),
        ]:
            remaining = quotas.get(key, {"minute": 0, "daily": 0})
            lines.append(
                f"<tr><th>{label}</th><td>{badge_fragment(f'{remaining['minute']} req/min', 'info')} "
                f"{badge_fragment(f'{remaining['daily']} req/dia', 'warning')}</td></tr>"
            )
        lines.append("</table></div>")
        self.quota_browser.setHtml("".join(lines))

    def _run_query(self):
        if not self.state.consent_given:
            QMessageBox.warning(self, APP_NAME, "Voce precisa consentir com o envio antes de consultar APIs externas.")
            return
        api_keys = {
            "virustotal": self.vt_key_input.text().strip(),
            "urlscan": self.us_key_input.text().strip(),
            "safebrowsing": self.sb_key_input.text().strip(),
        }
        worker = self._track_worker(
            FunctionWorker(
                query_external_apis,
                self.api_url_input.text().strip(),
                api_keys,
                use_progress=True,
            )
        )
        worker.progress.connect(self._update_progress)
        worker.error.connect(self._handle_query_error)
        worker.result_ready.connect(self._display_query_results)
        self.api_query_button.setEnabled(False)
        self.status_label.setText("Consultando servicos externos...")
        worker.start()

    def _update_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        if message:
            self.status_label.setText(message)

    def _handle_query_error(self, message: str):
        self.api_query_button.setEnabled(True)
        self.status_label.setText(message)

    def _format_service_result(self, name: str, result) -> str:
        if result is None:
            return f"<p><b>{name}:</b> chave nao configurada.</p>"
        if getattr(result, "success", False):
            if name == "VirusTotal":
                return (
                    f"<p><b>{name}</b>: {result.detection_ratio or 'submetido'}"
                    f" | Deteccoes: {getattr(result, 'detections', 0)}</p>"
                )
            if name == "URLScan.io":
                result_url = getattr(result, "result_url", "")
                link = f" - <a href='{result_url}'>{result_url}</a>" if result_url else ""
                return f"<p><b>{name}</b>: scan submetido{link}</p>"
            if name == "Safe Browsing":
                if getattr(result, "is_unsafe", False):
                    threats = ", ".join(getattr(result, "threat_types", []) or ["ameaca"])
                    return f"<p><b>{name}</b>: INSEGURO - {threats}</p>"
                return f"<p><b>{name}</b>: sem ameacas conhecidas.</p>"
        return f"<p><b>{name}</b>: {getattr(result, 'error', 'erro desconhecido')}</p>"

    def _display_query_results(self, bundle):
        self.api_query_button.setEnabled(self.state.consent_given)
        self.progress_bar.setValue(100)
        if bundle.error:
            self.results_browser.setHtml(
                status_banner_fragment(
                    "Falha na consulta",
                    bundle.error,
                    tone="danger",
                    icon="⛔",
                )
            )
            self.status_label.setText(bundle.error)
            return

        extras = []
        if bundle.warnings:
            extras.extend(f"<li>{warning}</li>" for warning in bundle.warnings)
        if bundle.removed_items:
            extras.append("<li>Itens sensiveis removidos: " + ", ".join(bundle.removed_items) + "</li>")
        html = ["<div class='panel'><div class='kicker'>Resultados externos</div>"]
        html.append(f"<h3>Resultados para {bundle.url}</h3>")
        if extras:
            html.append("<ul>" + "".join(extras) + "</ul>")
        html.append(self._format_service_result("VirusTotal", bundle.vt))
        html.append(self._format_service_result("URLScan.io", bundle.us))
        html.append(self._format_service_result("Safe Browsing", bundle.sb))
        html.append("</div>")
        self.results_browser.setHtml("".join(html))
        self.status_label.setText("Consultas concluidas.")
        self._refresh_quota()


class DatasetsPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"📦 {T('nav.datasets', self.state.lang)}")
        layout.addWidget(self.header)

        top_row = QHBoxLayout()
        self.summary_label = QLabel(self)
        top_row.addWidget(self.summary_label)
        top_row.addStretch(1)
        self.download_all_button = QPushButton(T("datasets.download_all", self.state.lang), self)
        self.download_all_button.clicked.connect(self._download_all)
        self.refresh_button = QPushButton(T("datasets.refresh", self.state.lang), self)
        self.refresh_button.clicked.connect(self.refresh_status)
        top_row.addWidget(self.download_all_button)
        top_row.addWidget(self.refresh_button)
        layout.addLayout(top_row)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        self.status_label = QLabel(self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(["Categoria", "Dataset", "Status", "Tamanho", "Atualizado", "Acao"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.horizontalHeader().setMinimumSectionSize(96)
        self.table.setColumnWidth(5, 138)
        layout.addWidget(self.table)

        self.refresh_status()

    def refresh_status(self):
        status = get_downloader().get_local_status()
        available = sum(1 for item in status.values() if item["exists"])
        self.summary_label.setText(f"{available}/{len(status)} datasets disponiveis")
        rows = list(sorted(status.items(), key=lambda item: (item[1]["category"], item[1]["name"])))
        self.table.setRowCount(len(rows))
        for row, (dataset_id, info) in enumerate(rows):
            item = _readonly_item(info["name"])
            item.setToolTip(f"{info['description']}\n{info['website']}")
            self.table.setItem(row, 0, _readonly_item(info["category"]))
            self.table.setItem(row, 1, item)
            status_text = "Disponivel" if info["exists"] else ("Manual" if info["manual"] else "Ausente")
            self.table.setItem(row, 2, _readonly_item(status_text))
            self.table.setItem(row, 3, _readonly_item(info["size_human"]))
            self.table.setItem(row, 4, _readonly_item(info["modified"] or "-"))
            if not info["manual"] and not info.get("requires_key"):
                button = QPushButton("Atualizar" if info["exists"] else "Baixar", self.table)
                button.setObjectName("tableActionButton")
                button.clicked.connect(partial(self._download_one, dataset_id))
                self.table.setCellWidget(row, 5, _centered_cell_widget(button, self.table))
            else:
                label = QLabel("N/A", self.table)
                self.table.setCellWidget(row, 5, _centered_cell_widget(label, self.table))

    def _download_all_impl(self, progress_callback=None):
        results = {}
        total = len(AUTO_DOWNLOADABLE)
        downloader = get_downloader()
        for index, dataset_id in enumerate(AUTO_DOWNLOADABLE, start=1):
            if progress_callback:
                progress_callback(int((index - 1) / max(1, total) * 100), f"Baixando {dataset_id}...")

            def _dataset_progress(percent, *_):
                if progress_callback:
                    overall = ((index - 1) + (percent / 100.0)) / max(1, total)
                    progress_callback(int(overall * 100), f"Baixando {dataset_id}...")

            results[dataset_id] = downloader.download(dataset_id, progress_callback=_dataset_progress)
        return results

    def _download_all(self):
        worker = self._track_worker(FunctionWorker(self._download_all_impl, use_progress=True))
        worker.progress.connect(self._handle_progress)
        worker.result_ready.connect(self._handle_all_downloads)
        worker.error.connect(self._handle_download_error)
        self.download_all_button.setEnabled(False)
        self.status_label.setText("Baixando datasets...")
        worker.start()

    def _download_one(self, dataset_id: str):
        worker = self._track_worker(FunctionWorker(get_downloader().download, dataset_id, use_progress=True))
        worker.progress.connect(self._handle_progress)
        worker.result_ready.connect(self._handle_single_download)
        worker.error.connect(self._handle_download_error)
        self.status_label.setText(f"Baixando {dataset_id}...")
        worker.start()

    def _handle_progress(self, percent: int, message: str):
        self.progress_bar.setValue(percent)
        if message:
            self.status_label.setText(message)

    def _handle_all_downloads(self, results):
        self.download_all_button.setEnabled(True)
        self.progress_bar.setValue(100)
        reload_dataset_checker()
        success = sum(1 for result in results.values() if result.success)
        self.status_label.setText(f"Downloads concluidos: {success}/{len(results)} com sucesso.")
        self.refresh_status()

    def _handle_single_download(self, result):
        self.progress_bar.setValue(100)
        reload_dataset_checker()
        if result.success:
            self.status_label.setText(f"Download concluido: {result.lines_count} linhas.")
        else:
            self.status_label.setText(result.error)
        self.refresh_status()

    def _handle_download_error(self, message: str):
        self.download_all_button.setEnabled(True)
        self.status_label.setText(message)


class GlossaryPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        unlock_badge("glossary_explorer")
        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"📖 {T('nav.glossary', self.state.lang)}")
        layout.addWidget(self.header)

        controls = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Buscar termo...")
        self.search_input.textChanged.connect(self._refresh_results)
        self.category_combo = QComboBox(self)
        self.category_combo.addItems(["Todas"] + GLOSSARY_CATEGORIES)
        self.category_combo.currentIndexChanged.connect(self._refresh_results)
        controls.addWidget(self.search_input, 3)
        controls.addWidget(self.category_combo, 1)
        layout.addLayout(controls)

        self.count_label = QLabel(self)
        layout.addWidget(self.count_label)

        self.results_browser = QTextBrowser(self)
        self.results_browser.setObjectName("panelCard")
        layout.addWidget(self.results_browser)

        self._refresh_results()

    def _refresh_results(self):
        search = self.search_input.text().strip().lower()
        category = self.category_combo.currentText()
        filtered = GLOSSARY
        if search:
            filtered = [
                item
                for item in filtered
                if search in item["term"].lower()
                or search in item["definition"].lower()
                or search in item.get("example", "").lower()
            ]
        if category != "Todas":
            filtered = [item for item in filtered if item["category"] == category]
        self.count_label.setText(f"{len(filtered)} termos encontrados")
        if not filtered:
            self.results_browser.setHtml("<p>Nenhum termo encontrado.</p>")
            return

        html = []
        for current_category in sorted({item["category"] for item in filtered}):
            html.append(f"<h2>{current_category}</h2>")
            for item in [entry for entry in filtered if entry["category"] == current_category]:
                html.append(
                    f"<div style='background:#1A1A2E;border:1px solid #2D2D45;border-radius:8px;padding:12px;margin-bottom:10px'>"
                    f"<h3>{item['term']}</h3>"
                    f"<p>{item['definition']}</p>"
                    f"<p><b>Exemplo:</b> {item.get('example', '-')}</p>"
                    f"<p><b>Modulo relacionado:</b> {item.get('related_module', '-')}</p>"
                    "</div>"
                )
        self.results_browser.setHtml("".join(html))


class SettingsPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self.current_worker = None

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"⚙️ {T('nav.settings', self.state.lang)}")
        layout.addWidget(self.header)

        appearance_group = QGroupBox("Aparencia")
        appearance_layout = QVBoxLayout(appearance_group)
        self.theme_preview_browser = QTextBrowser(appearance_group)
        self.theme_preview_browser.setMaximumHeight(140)
        appearance_layout.addWidget(self.theme_preview_browser)
        theme_row = QHBoxLayout()
        theme_label = QLabel("Tema visual", appearance_group)
        theme_label.setObjectName("fieldLabel")
        theme_row.addWidget(theme_label)
        self.theme_combo = QComboBox(appearance_group)
        for code, label in THEME_LABELS.items():
            self.theme_combo.addItem(label, code)
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addLayout(theme_row)
        layout.addWidget(appearance_group)

        self.trigger_section = CollapsibleSection("Trigger words", self, expanded=False)
        self.trigger_edit = QPlainTextEdit(self.trigger_section)
        self.trigger_edit.setPlainText("\n".join(settings.TRIGGER_WORDS))
        self.trigger_section.content_layout.addWidget(self.trigger_edit)
        layout.addWidget(self.trigger_section)

        self.tld_section = CollapsibleSection("TLDs de risco", self, expanded=False)
        self.tld_edit = QPlainTextEdit(self.tld_section)
        self.tld_edit.setPlainText("\n".join(settings.HIGH_RISK_TLDS))
        self.tld_section.content_layout.addWidget(self.tld_edit)
        layout.addWidget(self.tld_section)

        self.shortener_section = CollapsibleSection("Encurtadores", self, expanded=False)
        self.shortener_edit = QPlainTextEdit(self.shortener_section)
        self.shortener_edit.setPlainText("\n".join(settings.URL_SHORTENERS))
        self.shortener_section.content_layout.addWidget(self.shortener_edit)
        layout.addWidget(self.shortener_section)

        save_row = QHBoxLayout()
        self.apply_button = QPushButton(T("settings.apply", self.state.lang), self)
        self.apply_button.clicked.connect(self._apply_runtime_settings)
        save_row.addWidget(self.apply_button)
        save_row.addStretch(1)
        layout.addLayout(save_row)

        self.settings_status = QTextBrowser(self)
        self.settings_status.setMaximumHeight(150)
        layout.addWidget(self.settings_status)

        ml_group = QGroupBox("Classificador ML")
        ml_layout = QVBoxLayout(ml_group)
        self.ml_status_browser = QTextBrowser(ml_group)
        self.ml_status_browser.setObjectName("panelCard")
        self.ml_status_browser.setMaximumHeight(150)
        ml_layout.addWidget(self.ml_status_browser)
        self.feature_browser = QTextBrowser(ml_group)
        self.feature_browser.setObjectName("panelCard")
        self.feature_browser.setMaximumHeight(180)
        ml_layout.addWidget(self.feature_browser)
        self.train_ml_button = QPushButton("Treinar modelo", ml_group)
        self.train_ml_button.clicked.connect(self._train_model)
        ml_layout.addWidget(self.train_ml_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(ml_group)

        feedback_group = QGroupBox("Feedback recebido")
        feedback_layout = QVBoxLayout(feedback_group)
        self.feedback_label = QLabel(feedback_group)
        self.feedback_label.setWordWrap(True)
        feedback_layout.addWidget(self.feedback_label)
        layout.addWidget(feedback_group)

        self._populate_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self._apply_selected_theme)
        self._refresh_theme_preview()
        self._refresh_ml_status()
        self._refresh_feedback_stats()
        self.settings_status.setHtml(
            status_banner_fragment(
                "Configuracoes prontas",
                "Ajuste o tema, revise listas heuristicas e acompanhe o estado do modelo local.",
                tone="info",
                icon="⚙️",
            )
        )

    def _populate_theme_combo(self):
        self.theme_combo.blockSignals(True)
        index = max(0, self.theme_combo.findData(self.state.theme))
        self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(False)

    def _refresh_theme_preview(self):
        theme = self.theme_combo.currentData() or self.state.theme
        if theme == "light":
            self.theme_preview_browser.setHtml(
                page_intro_fragment(
                    "Modo claro",
                    "Superficies quentes e leitura mais leve para ambientes claros ou uso prolongado durante o dia.",
                    bullets=[
                        "Melhora leitura em telas com muita luz ambiente.",
                        "Mantem contraste sem depender de branco puro.",
                    ],
                    kicker="Tema ativo",
                    tone="warning",
                )
            )
        else:
            self.theme_preview_browser.setHtml(
                page_intro_fragment(
                    "Modo escuro",
                    "Contraste controlado e foco nos paineis de analise para reduzir fadiga visual em ambientes fechados.",
                    bullets=[
                        "Bom para leitura concentrada e investigacao detalhada.",
                        "Valoriza alertas, badges e blocos de risco.",
                    ],
                    kicker="Tema ativo",
                    tone="info",
                )
            )

    def _apply_selected_theme(self, index: int):
        theme = self.theme_combo.itemData(index)
        if theme:
            self._refresh_theme_preview()
            self.state.set_theme(theme)

    def _apply_runtime_settings(self):
        settings.TRIGGER_WORDS.clear()
        settings.TRIGGER_WORDS.extend(
            [line.strip() for line in self.trigger_edit.toPlainText().splitlines() if line.strip()]
        )
        settings.HIGH_RISK_TLDS.clear()
        settings.HIGH_RISK_TLDS.extend(
            [line.strip() for line in self.tld_edit.toPlainText().splitlines() if line.strip()]
        )
        settings.URL_SHORTENERS.clear()
        settings.URL_SHORTENERS.extend(
            [line.strip() for line in self.shortener_edit.toPlainText().splitlines() if line.strip()]
        )
        self.settings_status.setHtml(
            status_banner_fragment(
                "Heuristicas aplicadas em memoria",
                "As listas abaixo foram atualizadas para esta execucao do aplicativo.",
                tone="success",
                items=[
                    f"Trigger words: {len(settings.TRIGGER_WORDS)}",
                    f"TLDs de risco: {len(settings.HIGH_RISK_TLDS)}",
                    f"Encurtadores: {len(settings.URL_SHORTENERS)}",
                ],
                icon="✅",
            )
        )

    def _refresh_ml_status(self):
        if not ML_AVAILABLE:
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    "Classificador indisponivel",
                    "scikit-learn nao esta instalado. O classificador ML nao pode ser usado nesta maquina.",
                    tone="warning",
                    icon="⚠️",
                )
            )
            self.feature_browser.setHtml("")
            self.train_ml_button.setEnabled(False)
            return

        self.train_ml_button.setEnabled(True)
        classifier = get_ml()
        if classifier and classifier.is_available:
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    "Modelo pronto",
                    f"Acuracia estimada: {classifier._accuracy * 100:.1f}%.",
                    tone="success",
                    icon="🧠",
                )
            )
            if hasattr(classifier, "get_feature_importance"):
                importance = classifier.get_feature_importance()
                if importance:
                    lines = ["<h3>Features mais relevantes</h3><ul>"]
                    for name, score in importance[:10]:
                        lines.append(f"<li>{name}: {score:.3f}</li>")
                    lines.append("</ul>")
                    self.feature_browser.setHtml("".join(lines))
                else:
                    self.feature_browser.setHtml("<p>Sem feature importance disponivel.</p>")
            else:
                self.feature_browser.setHtml("<p>Feature importance nao disponivel.</p>")
        elif MODEL_PATH and MODEL_PATH.exists():
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    "Modelo inconsistente",
                    "Um modelo foi encontrado no disco, mas nao foi carregado corretamente. Re-treine para corrigir.",
                    tone="warning",
                    icon="⚠️",
                )
            )
            self.feature_browser.setHtml("")
        else:
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    "Modelo nao treinado",
                    "Use o botao abaixo para iniciar o treino local e habilitar o apoio do classificador ML.",
                    tone="info",
                    icon="📦",
                )
            )
            self.feature_browser.setHtml("")

    def _refresh_feedback_stats(self):
        feedback = load_feedback()
        if feedback:
            useful = sum(1 for item in feedback if item.get("useful"))
            self.feedback_label.setText(
                f"Total: {len(feedback)} | 👍 {useful} | 👎 {len(feedback) - useful}"
            )
        else:
            self.feedback_label.setText("Nenhum feedback registrado ainda.")

    def _train_model_impl(self):
        from models.ml_classifier import MLClassifier

        classifier = MLClassifier()
        return classifier.train()

    def _train_model(self):
        worker = self._track_worker(FunctionWorker(self._train_model_impl))
        worker.result_ready.connect(self._handle_train_result)
        worker.error.connect(self._handle_train_error)
        self.train_ml_button.setEnabled(False)
        self.settings_status.setHtml(
            status_banner_fragment(
                "Treino em andamento",
                "Treinando modelo ML. Isso pode levar alguns minutos.",
                tone="info",
                icon="⏳",
            )
        )
        worker.start()

    def _handle_train_result(self, result):
        self.train_ml_button.setEnabled(True)
        if result.success:
            reload_ml()
            self.settings_status.setHtml(
                status_banner_fragment(
                    "Treino concluido",
                    "O modelo foi atualizado e ja pode ser usado nas proximas analises.",
                    tone="success",
                    items=[
                        f"Acuracia: {result.accuracy * 100:.2f}%",
                        f"F1: {result.f1 * 100:.2f}%",
                    ],
                    icon="✅",
                )
            )
        else:
            self.settings_status.setHtml(
                status_banner_fragment(
                    "Falha no treino",
                    result.error,
                    tone="danger",
                    icon="⛔",
                )
            )
        self._refresh_ml_status()

    def _handle_train_error(self, message: str):
        self.train_ml_button.setEnabled(True)
        self.settings_status.setHtml(
            status_banner_fragment(
                "Erro durante o treino",
                message,
                tone="danger",
                icon="⛔",
            )
        )
