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
    verdict_label,
    verdict_tone,
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

    def _send_feedback(self, useful: bool):
        """
        Registra feedback sobre o último relatório.

        Compartilhado por AnalysisPage e ReportPage, que tinham cópias quase
        iguais — a do ReportPage não avisava nada quando não havia relatório,
        deixando o clique sem resposta visível.
        """
        report = self.state.last_report
        if report is None:
            QMessageBox.information(
                self, APP_NAME,
                T("Nenhum relatório para avaliar.", self.state.lang),
            )
            return
        save_feedback(report.url_defanged, report.classification, useful)
        QMessageBox.information(
            self, APP_NAME, T("Feedback registrado.", self.state.lang)
        )


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
        self.dismiss_onboarding_button = QPushButton(T("Não mostrar novamente", self.state.lang), self.onboarding_frame)
        self.dismiss_onboarding_button.clicked.connect(self._dismiss_onboarding)
        onboarding_layout.addWidget(self.onboarding_label)
        onboarding_layout.addWidget(self.dismiss_onboarding_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.onboarding_frame)

        metrics_layout = QHBoxLayout()
        self.metric_cards = [
            MetricCard(T("Análises", self.state.lang), "0", self),
            MetricCard(T("Seguras", self.state.lang), "0", self),
            MetricCard(T("Suspeitas", self.state.lang), "0", self),
            MetricCard(T("Maliciosas", self.state.lang), "0", self),
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

        history_header = QLabel(T("Histórico persistido", self.state.lang))
        history_header.setObjectName("sectionTitle")
        layout.addWidget(history_header)

        controls = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(T("Buscar URL...", self.state.lang))
        self.search_input.textChanged.connect(self._refresh_history_table)
        self.class_filter = QComboBox(self)
        self.class_filter.addItem(T("Todas", self.state.lang), "all")
        self.class_filter.addItem(T("Segura", self.state.lang), "safe")
        self.class_filter.addItem(T("Suspeita", self.state.lang), "suspicious")
        self.class_filter.addItem(T("Maliciosa", self.state.lang), "malicious")
        self.class_filter.currentIndexChanged.connect(self._reset_and_refresh_history)
        controls.addWidget(self.search_input, 3)
        controls.addWidget(self.class_filter, 1)
        layout.addLayout(controls)

        self.history_table = QTableWidget(0, 4, self)
        self.history_table.setHorizontalHeaderLabels([
            "URL",
            T("Classificação", self.state.lang),
            "Score",
            "Data",
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        pagination = QHBoxLayout()
        self.prev_history_button = QPushButton(T("Anterior", self.state.lang), self)
        self.prev_history_button.clicked.connect(partial(self._change_history_page, -1))
        self.history_page_label = QLabel(self)
        self.next_history_button = QPushButton(T("Próxima", self.state.lang), self)
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
        self.onboarding_label.setText(T(
            "Bem-vindo ao CyberURL Analyst. Fluxo recomendado: Anatomia, Análise, Quiz, Cenários e Glossário.",
            self.state.lang,
        ))
        self.onboarding_frame.setVisible(not self.state.onboarding_dismissed)

        stats = self.state.get_stats()
        values = [
            str(stats["analysis_count"]),
            str(stats["safe_count"]),
            str(stats["suspicious_count"]),
            str(stats["malicious_count"]),
        ]
        titles = [
            T("Análises", self.state.lang),
            T("Seguras", self.state.lang),
            T("Suspeitas", self.state.lang),
            T("Maliciosas", self.state.lang),
        ]
        for card, title, value in zip(self.metric_cards, titles, values):
            card.set_title(title)
            card.set_value(value)

        progress = self.state.get_progress()
        threats = progress.get("threats_identified", {})
        progress_html = [
            f"<h3>{T('Progresso de aprendizado', self.state.lang)}</h3>",
            f"<p>{T('Quizzes concluídos', self.state.lang)}: <b>{progress.get('quiz_rounds', 0)}</b> | {T('Melhor quiz', self.state.lang)}: <b>{int(progress.get('quiz_best_accuracy', 0) * 100)}%</b></p>",
            f"<p>{T('Cenários concluídos', self.state.lang)}: <b>{progress.get('scenarios_completed', 0)}</b> | {T('Melhor cenário', self.state.lang)}: <b>{int(progress.get('scenarios_best_accuracy', 0) * 100)}%</b></p>",
        ]
        if any(threats.values()):
            progress_html.append("<ul>")
            for key, value in sorted(threats.items(), key=lambda item: item[1], reverse=True)[:6]:
                progress_html.append(f"<li>{key}: <b>{value}</b></li>")
            progress_html.append("</ul>")
        else:
            progress_html.append(f"<p style='color:#999'>{T('Ainda sem progresso registrado.', self.state.lang)}</p>")
        self.progress_browser.setHtml("".join(progress_html))

        earned_badges = self.state.get_badges()
        locked_badges = [badge for badge in BADGE_DEFINITIONS if badge["id"] not in earned_badges]
        badge_html = [f"<h3>{T('Conquistas', self.state.lang)}</h3>"]
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
            badge_html.append(f"<p style='color:#999'>{T('Nenhuma conquista liberada ainda.', self.state.lang)}</p>")
        if locked_badges:
            badge_html.append(f"<p style='color:#888'>{T('Restantes', self.state.lang)}: {len(locked_badges)}</p>")
        self.badges_browser.setHtml("".join(badge_html))

        self.quick_guide_browser.setHtml(
            f"<h3>{T('Guia rápido', self.state.lang)}</h3>"
            "<ul>"
            f"<li><b>{T('Anatomia', self.state.lang)}</b> - {T('decompõe a URL em partes.', self.state.lang)}</li>"
            f"<li><b>{T('Análise', self.state.lang)}</b> - {T('executa heurísticas, datasets e ML.', self.state.lang)}</li>"
            f"<li><b>{T('Relatório', self.state.lang)}</b> - {T('exporta o último resultado.', self.state.lang)}</li>"
            f"<li><b>{T('Quiz', self.state.lang)}</b> - {T('pratica com perguntas didaticas.', self.state.lang)}</li>"
            f"<li><b>{T('Cenários', self.state.lang)}</b> - {T('simula golpes reais.', self.state.lang)}</li>"
            "</ul>"
        )
        self._refresh_history_table()

    def _refresh_history_table(self):
        history = self.state.get_persistent_history()
        search = self.search_input.text().strip().lower()
        class_filter = self.class_filter.currentData()
        if search:
            history = [item for item in history if search in item.get("url", "").lower()]
        if class_filter != "all":
            history = [item for item in history if item.get("classification") == class_filter]

        total_pages = max(1, (len(history) + self.HISTORY_PAGE_SIZE - 1) // self.HISTORY_PAGE_SIZE)
        self._history_page = min(self._history_page, total_pages - 1)
        start = self._history_page * self.HISTORY_PAGE_SIZE
        page_items = history[start:start + self.HISTORY_PAGE_SIZE]

        self.history_table.setRowCount(len(page_items))
        for row, item in enumerate(page_items):
            timestamp = time.strftime("%d/%m %H:%M", time.localtime(item.get("timestamp", 0)))
            classification = item.get("classification", "")
            # feminine=True: concorda com "URL" na tabela de histórico.
            classification_label = verdict_label(
                classification, classification, self.state.lang, feminine=True
            )
            self.history_table.setItem(row, 0, _readonly_item(item.get("url", "")))
            self.history_table.setItem(row, 1, _readonly_item(f"{item.get('emoji', '')} {classification_label}"))
            self.history_table.setItem(row, 2, _readonly_item(str(item.get("score", "-"))))
            self.history_table.setItem(row, 3, _readonly_item(timestamp))

        self.history_page_label.setText(T(
            "Página {current} de {total} ({count} registros)",
            self.state.lang,
        ).format(current=self._history_page + 1, total=total_pages, count=len(history)))
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
        self.url_input.setPlaceholderText(T("https://www.exemplo.com/página?q=teste", self.state.lang))
        self.analyze_button = QPushButton(T("Analisar anatomia", self.state.lang), self)
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

        compare_group = QGroupBox(T("Comparação visual", self.state.lang))
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

        self.browser_bar.setHtml(f"<p style='color:#888'>{T('Cole uma URL e clique em analisar.', self.state.lang)}</p>")
        self.breakdown_browser.setHtml(f"<p style='color:#888'>{T('A decomposição visual aparecerá aqui.', self.state.lang)}</p>")
        self.components_browser.setHtml(f"<p style='color:#888'>{T('Os componentes estruturados da URL aparecerão aqui.', self.state.lang)}</p>")
        self.diff_browser.setHtml(f"<p style='color:#888'>{T('A comparação de domínios aparecerá aqui.', self.state.lang)}</p>")

    def _analyze(self):
        raw_url = self.url_input.text().strip()
        sanitized = sanitize_input(raw_url)
        messages = []
        if sanitized.warnings:
            messages.extend(sanitized.warnings)
        if sanitized.removed_items:
            messages.append(T("Itens sensíveis removidos", self.state.lang) + ": " + ", ".join(sanitized.removed_items))
        if not sanitized.is_valid_url:
            self.status_label.setText("\n".join(messages or [T("URL inválida.", self.state.lang)]))
            return

        unlock_badge("anatomy_first")
        parser = get_parser()
        components = parser.parse(sanitized.sanitized_input)
        parts = parser.get_visual_breakdown(sanitized.sanitized_input)

        self.status_label.setText("\n".join(messages) or T("Estrutura da URL analisada com sucesso.", self.state.lang))
        self.browser_bar.set_url(sanitized.sanitized_input)
        self.breakdown_browser.setHtml(build_visual_breakdown_html(parts))

        details = [f"<h3>{T('Componentes', self.state.lang)}</h3><ul>"]
        if components.scheme:
            details.append(f"<li><b>{T('Protocolo', self.state.lang)}:</b> {components.scheme}</li>")
        if components.subdomain:
            details.append(f"<li><b>{T('Subdomínio', self.state.lang)}:</b> {components.subdomain}</li>")
        if components.is_ip:
            details.append(f"<li><b>IP:</b> {components.ip_address}</li>")
        elif components.domain:
            details.append(f"<li><b>{T('Domínio', self.state.lang)}:</b> {components.domain}</li>")
        if components.tld:
            details.append(f"<li><b>TLD:</b> .{components.tld}</li>")
        if components.port:
            details.append(f"<li><b>{T('Porta', self.state.lang)}:</b> {components.port}</li>")
        if components.path and components.path != "/":
            details.append(f"<li><b>Path:</b> {components.path}</li>")
        if components.query:
            details.append(f"<li><b>Query:</b> ?{components.query}</li>")
        if components.fragment:
            details.append(f"<li><b>{T('Fragmento', self.state.lang)}:</b> #{components.fragment}</li>")
        if components.registered_domain:
            details.append(f"<li><b>{T('Domínio registrado', self.state.lang)}:</b> {components.registered_domain}</li>")
        details.append("</ul>")
        self.components_browser.setHtml("".join(details))

    def _refresh_compare(self):
        legit = self.legit_input.text().strip()
        suspect = self.suspect_input.text().strip()
        if not legit or not suspect:
            self.diff_browser.setHtml(f"<p style='color:#888'>{T('Informe uma URL legítima e outra suspeita.', self.state.lang)}</p>")
            return

        self.legit_bar.set_url(legit)
        self.suspect_bar.set_url(suspect)
        left_html, right_html, similarity, message = build_domain_diff(legit, suspect)
        self.diff_browser.setHtml(
            f"<h3>{T('Diff de domínio', self.state.lang)}</h3>"
            f"<p><b>{T('Legítima', self.state.lang)}:</b> <code>{left_html}</code></p>"
            f"<p><b>Suspeita:</b> <code>{right_html}</code></p>"
            f"<p><b>{T('Similaridade', self.state.lang)}:</b> {similarity}% - {message}</p>"
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
        self.feedback_yes_button = QPushButton(T("👍 Análise útil", self.state.lang), self.single_tab)
        self.feedback_no_button = QPushButton(T("👎 Precisa melhorar", self.state.lang), self.single_tab)
        self.feedback_yes_button.clicked.connect(partial(self._send_feedback, True))
        self.feedback_no_button.clicked.connect(partial(self._send_feedback, False))
        feedback_row.addWidget(self.feedback_yes_button)
        feedback_row.addWidget(self.feedback_no_button)
        layout.addLayout(feedback_row)

        session_label = _section_label(T("Histórico da sessão", self.state.lang), self.single_tab)
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
        self.batch_input.setPlaceholderText(T("Uma URL por linha", self.state.lang))
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
            details.append(T("Itens sensíveis removidos", self.state.lang) + ": " + ", ".join(execution.removed_items))
        if execution.from_cache and execution.report is not None:
            details.append(T("Resultado carregado do cache local.", self.state.lang))

        if execution.error:
            return status_banner_fragment(
                T("Não foi possível concluir a análise", self.state.lang),
                execution.error,
                tone="danger",
                items=details,
                icon="⛔",
            )

        if execution.report is not None:
            tone = verdict_tone(execution.report.classification, default="info")
            title = T("Resultado recuperado do cache", self.state.lang) if execution.from_cache else T("Análise concluída", self.state.lang)
            message = (
                T("O painel abaixo resume os principais sinais encontrados nesta URL.", self.state.lang)
                if not execution.from_cache
                else T("Este resultado veio do cache local para acelerar a consulta.", self.state.lang)
            )
            return status_banner_fragment(title, message, tone=tone, items=details, icon="✅")

        return status_banner_fragment(
            T("Nenhuma análise executada", self.state.lang),
            T("Informe uma URL para iniciar a verificação.", self.state.lang),
            tone="info",
            icon="ℹ️",
        )

    def _refresh_intro_panels(self):
        self.intro_browser.setHtml(
            page_intro_fragment(
                T("Analisar com contexto", self.state.lang),
                T("Compare o resultado, o score e os sinais detalhados antes de tomar uma decisão.", self.state.lang),
                bullets=[
                    T("Use a aba individual para investigar uma URL em profundidade.", self.state.lang),
                    T("Use a aba em lote para triagem rápida de várias entradas.", self.state.lang),
                    T("Considere o relatório como apoio didático, não como veredito absoluto.", self.state.lang),
                ],
                kicker=T("Análise guiada", self.state.lang),
                tone="info",
            )
        )
        self.single_intro_browser.setHtml(
            page_intro_fragment(
                T("Inspeção individual", self.state.lang),
                T("Ideal para entender porque uma URL parece segura, suspeita ou maliciosa.", self.state.lang),
                bullets=[
                    T("Cole a URL completa.", self.state.lang),
                    T("Leia o resumo e depois desça para os fatores analisados.", self.state.lang),
                ],
                kicker=T("Fluxo recomendado", self.state.lang),
                tone="success",
            )
        )
        self.batch_intro_browser.setHtml(
            page_intro_fragment(
                T("Triagem em lote", self.state.lang),
                T("Boa para limpar listas grandes e identificar rapidamente os casos que merecem revisão manual.", self.state.lang),
                bullets=[
                    T("Use uma URL por linha.", self.state.lang),
                    T("O resultado prioriza velocidade e consolidação visual.", self.state.lang),
                ],
                kicker=T("Triagem", self.state.lang),
                tone="warning",
            )
        )

    def _analyze_single(self):
        execution = run_analysis(self.single_url_input.text().strip(), state=self.state)
        self.single_status.setHtml(self._compose_status_fragment(execution))
        if execution.report is not None:
            source_label = T("Cache local", self.state.lang) if execution.from_cache else T("Processado agora", self.state.lang)
            self.single_summary.setHtml(report_summary_fragment(execution.report, source_label))
            self.single_report.set_report(execution.report)
        else:
            self.single_summary.setHtml(
                empty_state_html(
                    T("Sem resumo para exibir.", self.state.lang),
                    T("Quando a análise terminar, score, fatores e consultas externas aparecerão aqui.", self.state.lang),
                )
            )
            self.single_report.setHtml(
                empty_state_html(
                    T("Nenhum relatório disponível.", self.state.lang),
                    T("Revise a URL informada e tente novamente.", self.state.lang),
                )
            )
        self._refresh_session_history()

    def _analyze_batch(self):
        urls = [line.strip() for line in self.batch_input.toPlainText().splitlines() if line.strip()]
        if not urls:
            self.batch_status.setHtml(
                status_banner_fragment(
                    T("Nada para analisar", self.state.lang),
                    T("Informe pelo menos uma URL para iniciar a triagem em lote.", self.state.lang),
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
                    f"<div class='kicker'>{T('Análise', self.state.lang)} {index}/{len(urls)}</div>"
                    f"{render_report_fragment(execution.report)}"
                    "</div>"
                )
            else:
                errors.append(f"{url}: {execution.error or T('falha ao analisar', self.state.lang)}")

        if errors:
            self.batch_status.setHtml(
                status_banner_fragment(
                    T("Triagem concluída com ressalvas", self.state.lang),
                    T("{success} de {total} URLs geraram relatório.", self.state.lang).format(success=len(urls) - len(errors), total=len(urls)),
                    tone="warning",
                    items=errors[:8],
                    icon="⚠️",
                )
            )
        else:
            self.batch_status.setHtml(
                status_banner_fragment(
                    T("Triagem concluída", self.state.lang),
                    T("{total} URLs analisadas com sucesso.", self.state.lang).format(total=len(urls)),
                    tone="success",
                    icon="✅",
                )
            )
        self.batch_results.setHtml(
            "<hr>".join(html_chunks)
            or empty_state_html(
                T("Nenhum resultado disponível.", self.state.lang),
                T("As URLs sem análise concluída ficarão listadas no banner acima.", self.state.lang),
            )
        )
        self._refresh_session_history()

    def _handle_state_change(self, event: str):
        if event in {"analysis", "report"}:
            self._refresh_from_state()

    def _refresh_from_state(self):
        self._refresh_intro_panels()
        if self.state.last_report is not None:
            self.single_status.setHtml(
                status_banner_fragment(
                    T("Último resultado carregado", self.state.lang),
                    T("O relatório abaixo corresponde à análise mais recente da sessão.", self.state.lang),
                    tone="info",
                    icon="📌",
                )
            )
            self.single_summary.setHtml(report_summary_fragment(self.state.last_report, T("Última análise", self.state.lang)))
            self.single_report.set_report(self.state.last_report)
        else:
            self.single_status.setHtml(
                status_banner_fragment(
                    T("Pronto para analisar", self.state.lang),
                    T("Cole uma URL e use o painel para investigar sinais de risco.", self.state.lang),
                    tone="info",
                    icon="🧭",
                )
            )
            self.single_summary.setHtml(
                empty_state_html(
                    T("O resumo rápido aparecerá aqui.", self.state.lang),
                    T("Depois da análise você verá score, quantidade de fatores e consultas externas.", self.state.lang),
                )
            )
            self.single_report.setHtml(
                empty_state_html(
                    T("Nenhum relatório disponível.", self.state.lang),
                    T("Use a aba individual para gerar um relatório detalhado desta URL.", self.state.lang),
                )
            )

        self.batch_status.setHtml(
            status_banner_fragment(
                T("Fila em lote pronta", self.state.lang),
                T("Cole uma lista de URLs para gerar relatórios consolidados nesta aba.", self.state.lang),
                tone="info",
                icon="📚",
            )
        )
        self.batch_results.setHtml(
            empty_state_html(
                T("Nenhum lote analisado ainda.", self.state.lang),
                T("Os relatórios em lote serão empilhados aqui em blocos visuais.", self.state.lang),
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
        self.export_text_button = QPushButton(T("Baixar TXT", self.state.lang), self)
        self.export_text_button.clicked.connect(self._export_text)
        self.export_html_button = QPushButton(T("Baixar HTML", self.state.lang), self)
        self.export_html_button.clicked.connect(self._export_html)
        self.feedback_yes_button = QPushButton(T("👍 Análise útil", self.state.lang), self)
        self.feedback_no_button = QPushButton(T("👎 Precisa melhorar", self.state.lang), self)
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
                    T("Relatórios exportáveis", self.state.lang),
                    T("report.placeholder", self.state.lang),
                    bullets=[
                        T("Exporte em TXT para compartilhar rapidamente.", self.state.lang),
                        T("Exporte em HTML quando quiser um relatório mais apresentável.", self.state.lang),
                        T("Registre feedback para melhorar a ferramenta.", self.state.lang),
                    ],
                    kicker=T("Centro de relatórios", self.state.lang),
                    tone="info",
                )
            )
            self.report_summary.setHtml(
                empty_state_html(
                    T("Nenhum resumo disponível.", self.state.lang),
                    T("Assim que uma URL for analisada, o painel acima mostrará score e volume de sinais.", self.state.lang),
                )
            )
            self.report_viewer.setHtml(
                empty_state_html(
                    T("Nenhum relatório disponível.", self.state.lang),
                    T("Faça a análise de uma URL na página anterior para habilitar exportação e feedback.", self.state.lang),
                )
            )
        else:
            self.report_intro.setHtml(
                status_banner_fragment(
                    T("Relatório pronto para exportação", self.state.lang),
                    T("Revise o resumo, exporte nos formatos desejados e registre se a análise foi útil.", self.state.lang),
                    tone="success",
                    items=[
                        f"{T('Classificação', self.state.lang)}: {report.classification_label}",
                        f"Score atual: {report.score}/100",
                    ],
                    icon="📄",
                )
            )
            self.report_summary.setHtml(report_summary_fragment(report, T("Pronto para exportar", self.state.lang)))
            self.report_viewer.set_report(report)

    def _export_text(self):
        report = self.state.last_report
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, T("Salvar relatório TXT", self.state.lang), "relatorio.txt", "Text (*.txt)")
        if not file_path:
            return
        content = get_report_generator().format_text_report(report)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _export_html(self):
        report = self.state.last_report
        if report is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, T("Salvar relatório HTML", self.state.lang), "relatorio.html", "HTML (*.html)")
        if not file_path:
            return
        content = get_report_generator().format_html_report(report)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(content)


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
        control_row.addWidget(QLabel(T("Dificuldade:", self.state.lang)))
        self.difficulty_combo = QComboBox(self)
        self.difficulty_combo.addItem(T("Auto", self.state.lang), "auto")
        self.difficulty_combo.addItem(T("Iniciante", self.state.lang), "iniciante")
        self.difficulty_combo.addItem(T("Intermediário", self.state.lang), "intermediario")
        self.difficulty_combo.addItem(T("Avançado", self.state.lang), "avancado")
        control_row.addWidget(self.difficulty_combo)
        control_row.addStretch(1)
        layout.addLayout(control_row)

        metrics_layout = QHBoxLayout()
        self.quiz_metric_cards = [
            MetricCard(T("Acertos", self.state.lang), "0", self),
            MetricCard(T("Sequência", self.state.lang), "0", self),
            MetricCard(T("Precisão", self.state.lang), "0%", self),
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
                T("Treinamento gamificado", self.state.lang),
                T("Responda dez perguntas para praticar reconhecimento de URLs maliciosas sem perder o contexto da URL analisada.", self.state.lang),
                bullets=[
                    T("O modo Auto ajusta a dificuldade ao seu ritmo.", self.state.lang),
                    T("Acompanhe progresso, precisão e sequência em tempo real.", self.state.lang),
                ],
                kicker=T("Aprendizado ativo", self.state.lang),
                tone="info",
            )
        )
        layout.addWidget(intro_browser)

        button_row = QHBoxLayout()
        self.quiz_start_button = QPushButton(T("quiz.btn_start", self.state.lang), self.intro_page)
        self.quiz_start_button.clicked.connect(self._start_round)
        self.quiz_reset_button = QPushButton(T("Resetar", self.state.lang), self.intro_page)
        self.quiz_reset_button.clicked.connect(self._reset_round)
        button_row.addWidget(self.quiz_start_button)
        button_row.addWidget(self.quiz_reset_button)
        layout.addLayout(button_row)

        leaderboard_label = _section_label(T("Leaderboard", self.state.lang), self.intro_page)
        layout.addWidget(leaderboard_label)
        self.leaderboard_table = QTableWidget(0, 5, self.intro_page)
        self.leaderboard_table.setHorizontalHeaderLabels([
            T("Nome", self.state.lang),
            T("Precisão", self.state.lang),
            T("Acertos", self.state.lang),
            T("Dificuldade", self.state.lang),
            "Data",
        ])
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
        self.leaderboard_name_input.setText(T("Jogador", self.state.lang))
        form.addRow(T("Nome para o leaderboard:", self.state.lang), self.leaderboard_name_input)
        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.save_leaderboard_button = QPushButton(T("Salvar no leaderboard", self.state.lang), self.results_page)
        self.save_leaderboard_button.clicked.connect(self._save_leaderboard)
        self.export_quiz_button = QPushButton(T("Exportar resultado CSV", self.state.lang), self.results_page)
        self.export_quiz_button.clicked.connect(self._export_quiz_result)
        self.restart_quiz_button = QPushButton(T("Nova rodada", self.state.lang), self.results_page)
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
            self.leaderboard_table.setItem(row, 3, _readonly_item(self._difficulty_label(entry.get("difficulty", ""))))
            self.leaderboard_table.setItem(row, 4, _readonly_item(date_text))

    def _difficulty_code(self) -> str:
        selected = self.difficulty_combo.currentData()
        if selected == "auto":
            return self.engine.get_suggested_difficulty()
        return selected or "iniciante"

    def _difficulty_label(self, code: str) -> str:
        mapping = {
            "iniciante": T("Iniciante", self.state.lang),
            "intermediario": T("Intermediário", self.state.lang),
            "avancado": T("Avançado", self.state.lang),
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
            T("Questão {current}/{total} - {difficulty}", self.state.lang).format(
                current=self.question_number,
                total=QUIZ_QUESTIONS_PER_ROUND,
                difficulty=self._difficulty_label(question.difficulty),
            )
        )
        self.question_browser_bar.set_url(question.url_display or question.url_defanged)
        self.question_context.setText(question.scenario_context)
        self.question_context.setVisible(bool(question.scenario_context))
        self.question_text.setText(question.question_text)

        _clear_layout(self.options_layout)
        self._checklist_boxes = []
        if question.question_type == "binary":
            row = QHBoxLayout()
            safe_button = QPushButton(T("🟢 SEGURA", self.state.lang), self.options_widget)
            malicious_button = QPushButton(T("🔴 MALICIOSA", self.state.lang), self.options_widget)
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
            confirm_button = QPushButton(T("Confirmar", self.state.lang), self.options_widget)
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
            f"<p>{T('Pontuação parcial', self.state.lang)}: {int(feedback.partial_score * 100)}%</p>"
            if feedback.partial_score and feedback.partial_score < 1.0
            else ""
        )
        self.question_feedback.setHtml(
            status_banner_fragment(
                T("Resposta correta", self.state.lang) if feedback.is_correct else T("Resposta incorreta", self.state.lang),
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
            message = T("Excelente desempenho.", self.state.lang)
        elif stats.accuracy >= 0.7:
            message = T("Bom trabalho.", self.state.lang)
        elif stats.accuracy >= 0.5:
            message = T("Resultado razoável.", self.state.lang)
        else:
            message = T("Vale praticar mais um pouco.", self.state.lang)

        self.results_browser.setHtml(
            status_banner_fragment(
                T('quiz.final', self.state.lang),
                message,
                tone="success" if stats.accuracy >= 0.7 else "warning",
                items=[
                    f"{T('Acertos', self.state.lang)}: {stats.correct_answers}/{stats.total_questions}",
                    f"{T('Precisão', self.state.lang)}: {int(stats.accuracy * 100)}%",
                    f"{T('Melhor sequência', self.state.lang)}: {stats.best_streak}",
                    f"{T('Dificuldade', self.state.lang)}: {self._difficulty_label(self.completed_difficulty)}",
                ],
                icon="🏁",
            )
        )
        self.stack.setCurrentWidget(self.results_page)
        self._refresh_metrics()

    def _save_leaderboard(self):
        if self._saved_to_leaderboard:
            QMessageBox.information(self, APP_NAME, T("Resultado já salvo.", self.state.lang))
            return
        stats = self.engine.get_statistics()
        save_leaderboard_entry(
            self.leaderboard_name_input.text().strip() or T("Jogador", self.state.lang),
            stats.correct_answers,
            stats.total_questions,
            stats.accuracy,
            self.completed_difficulty,
            stats.best_streak,
        )
        self._saved_to_leaderboard = True
        self._refresh_leaderboard()
        QMessageBox.information(self, APP_NAME, T("Resultado salvo no leaderboard.", self.state.lang))

    def _export_quiz_result(self):
        stats = self.engine.get_statistics()
        file_path, _ = QFileDialog.getSaveFileName(self, T("Salvar resultado do quiz", self.state.lang), "quiz_resultado.csv", "CSV (*.csv)")
        if not file_path:
            return
        lines = [",".join([
            T("Acertos", self.state.lang),
            "Total",
            T("Precisão", self.state.lang),
            T("Sequência", self.state.lang),
            T("Dificuldade", self.state.lang),
        ])]
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
        controls.addWidget(QLabel(T("Categoria:", self.state.lang)))
        self.category_combo = QComboBox(self)
        for category in SCENARIO_CATEGORIES:
            self.category_combo.addItem(T(category, self.state.lang), category)
        controls.addWidget(self.category_combo)
        self.presentation_checkbox = QCheckBox(T("Modo apresentação", self.state.lang), self)
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
                T("Treinamento por cenários", self.state.lang),
                T("Examine mensagens, e-mails e abordagens suspeitas e decida se clicaria ou não antes de ver a explicação.", self.state.lang),
                bullets=[
                    T("Use Modo apresentação para telas maiores ou aula expositiva.", self.state.lang),
                    T("Os alertas explicam exatamente o que entregou o golpe.", self.state.lang),
                ],
                kicker=T("Simulações", self.state.lang),
                tone="warning",
            )
        )
        layout.addWidget(intro)
        self.start_scenario_button = QPushButton(T("Iniciar simulação", self.state.lang), self.scenario_intro_page)
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
        self.next_scenario_button = QPushButton(T("Próximo", self.state.lang), self.scenario_page)
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
        self.export_scenario_button = QPushButton(T("Exportar resultado", self.state.lang), self.scenario_results_page)
        self.export_scenario_button.clicked.connect(self._export_scenario_result)
        self.restart_scenario_button = QPushButton(T("Nova simulação", self.state.lang), self.scenario_results_page)
        self.restart_scenario_button.clicked.connect(self._reset_scenarios)
        button_row.addWidget(self.export_scenario_button)
        button_row.addWidget(self.restart_scenario_button)
        layout.addLayout(button_row)
        self.stack.addWidget(self.scenario_results_page)

    def _filtered_scenarios(self) -> list[dict]:
        category = self.category_combo.currentData()
        if category == "Todos":
            return SCENARIOS
        return [scenario for scenario in SCENARIOS if scenario["category"] == category]

    def _start_scenarios(self):
        scenarios = self._filtered_scenarios()
        if not scenarios:
            QMessageBox.information(self, APP_NAME, T("Não há cenários para a categoria selecionada.", self.state.lang))
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
            f"{scenario['category_icon']} {T(scenario['category'], self.state.lang)} - {scenario['channel_icon']} {T(scenario['channel'], self.state.lang)} "
            f"({self.scenario_index + 1}/{len(scenarios)})"
        )
        font_size = "18px" if self.presentation_mode else "14px"
        sender_html = f"<p><b>{T('De', self.state.lang)}:</b> {scenario['sender']}</p>" if scenario.get("sender") else ""
        subject_html = f"<p><b>{T('Assunto', self.state.lang)}:</b> {scenario['subject']}</p>" if scenario.get("subject") else ""
        self.scenario_message.setHtml(
            f"<div class='panel'>"
            f"<div class='kicker'>{T('Mensagem em análise', self.state.lang)}</div>"
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
                T("Decisão correta", self.state.lang) if correct else T("Decisão incorreta", self.state.lang),
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
            message = T("Excelente leitura dos sinais de alerta.", self.state.lang)
        elif accuracy >= 60:
            message = T("Bom trabalho. Continue praticando.", self.state.lang)
        else:
            message = T("Vale revisar os alertas mostrados em cada cenário.", self.state.lang)
        self.scenario_results_browser.setHtml(
            status_banner_fragment(
                T("Simulação concluída", self.state.lang),
                message,
                tone="success" if accuracy >= 80 else ("warning" if accuracy >= 60 else "danger"),
                items=[
                    f"{T('Decisões corretas', self.state.lang)}: {self.scenario_score}/{self.scenario_total}",
                    f"{T('Precisão', self.state.lang)}: {accuracy}%",
                ],
                icon="🎯",
            )
        )
        self.stack.setCurrentWidget(self.scenario_results_page)

    def _export_scenario_result(self):
        file_path, _ = QFileDialog.getSaveFileName(self, T("Salvar resultado da simulação", self.state.lang), "cenarios_resultado.csv", "CSV (*.csv)")
        if not file_path:
            return
        accuracy = int((self.scenario_score / max(1, self.scenario_total)) * 100)
        lines = [f"Score,Total,{T('Precisão', self.state.lang)}", f"{self.scenario_score},{self.scenario_total},{accuracy}%"]
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
        self.consent_button = QPushButton(T("Concordo com o envio de dados", self.state.lang), self)
        self.consent_button.clicked.connect(self._grant_consent)
        self.consent_state_label = QLabel(self)
        consent_row.addWidget(self.consent_button)
        consent_row.addWidget(self.consent_state_label)
        consent_row.addStretch(1)
        layout.addLayout(consent_row)

        query_row = QHBoxLayout()
        self.api_url_input = QLineEdit(self)
        self.api_url_input.setPlaceholderText(T("https://exemplo.com", self.state.lang))
        self.api_query_button = QPushButton(T("Consultar APIs", self.state.lang), self)
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
                T("Consulta a serviços externos", self.state.lang),
                T("Use esta área apenas quando fizer sentido compartilhar a URL com serviços de reputação e sandbox.", self.state.lang),
                bullets=[
                    T("O envio só é liberado após consentimento explícito.", self.state.lang),
                    T("As cotas abaixo ajudam a evitar bloqueios ou desperdício de requests.", self.state.lang),
                ],
                kicker=T("Integrações", self.state.lang),
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
            self.consent_state_label.setText(T("Consentimento registrado", self.state.lang))
            self.consent_button.setEnabled(False)
            self.api_query_button.setEnabled(True)
        else:
            self.consent_state_label.setText(T("Sem consentimento", self.state.lang))
            self.consent_button.setEnabled(True)
            self.api_query_button.setEnabled(False)

    def _refresh_quota(self):
        from ui.resources import get_api_client

        client = get_api_client()
        if client is None:
            self.quota_browser.setHtml(
                status_banner_fragment(
                    T("Módulo indisponível", self.state.lang),
                    T("As integrações externas não puderam ser carregadas nesta execução.", self.state.lang),
                    tone="warning",
                    icon="⚠️",
                )
            )
            return
        quotas = client.get_remaining_quota()
        lines = [f"<div class='panel'><div class='kicker'>{T('Cotas restantes', self.state.lang)}</div><table>"]
        for key, label in [
            ("virustotal", "VirusTotal"),
            ("urlscan", "URLScan.io"),
            ("safebrowsing", "Safe Browsing"),
        ]:
            remaining = quotas.get(key, {"minute": 0, "daily": 0})
            lines.append(
                f"<tr><th>{label}</th><td>{badge_fragment(f'{remaining['minute']} {T('req/min', self.state.lang)}', 'info')} "
                f"{badge_fragment(f'{remaining['daily']} {T('req/dia', self.state.lang)}', 'warning')}</td></tr>"
            )
        lines.append("</table></div>")
        self.quota_browser.setHtml("".join(lines))

    def _run_query(self):
        if not self.state.consent_given:
            QMessageBox.warning(self, APP_NAME, T("Você precisa consentir com o envio antes de consultar APIs externas.", self.state.lang))
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
        self.status_label.setText(T("Consultando serviços externos...", self.state.lang))
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
            return f"<p><b>{name}:</b> {T('chave não configurada.', self.state.lang)}</p>"
        if getattr(result, "success", False):
            if name == "VirusTotal":
                return (
                    f"<p><b>{name}</b>: {result.detection_ratio or T('submetido', self.state.lang)}"
                    f" | {T('Detecções', self.state.lang)}: {getattr(result, 'detections', 0)}</p>"
                )
            if name == "URLScan.io":
                result_url = getattr(result, "result_url", "")
                link = f" - <a href='{result_url}'>{result_url}</a>" if result_url else ""
                return f"<p><b>{name}</b>: {T('scan submetido', self.state.lang)}{link}</p>"
            if name == "Safe Browsing":
                if getattr(result, "is_unsafe", False):
                    threats = ", ".join(getattr(result, "threat_types", []) or [T("ameaça", self.state.lang)])
                    return f"<p><b>{name}</b>: {T('INSEGURO', self.state.lang)} - {threats}</p>"
                return f"<p><b>{name}</b>: {T('sem ameaças conhecidas.', self.state.lang)}</p>"
        return f"<p><b>{name}</b>: {getattr(result, 'error', T('erro desconhecido', self.state.lang))}</p>"

    def _display_query_results(self, bundle):
        self.api_query_button.setEnabled(self.state.consent_given)
        self.progress_bar.setValue(100)
        if bundle.error:
            self.results_browser.setHtml(
                status_banner_fragment(
                    T("Falha na consulta", self.state.lang),
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
            extras.append("<li>" + T("Itens sensíveis removidos", self.state.lang) + ": " + ", ".join(bundle.removed_items) + "</li>")
        html = [f"<div class='panel'><div class='kicker'>{T('Resultados externos', self.state.lang)}</div>"]
        html.append(f"<h3>{T('Resultados para', self.state.lang)} {bundle.url}</h3>")
        if extras:
            html.append("<ul>" + "".join(extras) + "</ul>")
        html.append(self._format_service_result("VirusTotal", bundle.vt))
        html.append(self._format_service_result("URLScan.io", bundle.us))
        html.append(self._format_service_result("Safe Browsing", bundle.sb))
        html.append("</div>")
        self.results_browser.setHtml("".join(html))
        self.status_label.setText(T("Consultas concluídas.", self.state.lang))
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
        self.table.setHorizontalHeaderLabels([
            T("Categoria", self.state.lang),
            "Dataset",
            T("Status", self.state.lang),
            T("Tamanho", self.state.lang),
            T("Atualizado", self.state.lang),
            T("Ação", self.state.lang),
        ])
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
        self.summary_label.setText(T("{available}/{total} datasets disponíveis", self.state.lang).format(available=available, total=len(status)))
        rows = list(sorted(status.items(), key=lambda item: (item[1]["category"], item[1]["name"])))
        self.table.setRowCount(len(rows))
        for row, (dataset_id, info) in enumerate(rows):
            item = _readonly_item(info["name"])
            item.setToolTip(f"{info['description']}\n{info['website']}")
            self.table.setItem(row, 0, _readonly_item(T(info["category"], self.state.lang)))
            self.table.setItem(row, 1, item)
            status_text = T("Disponível", self.state.lang) if info["exists"] else (T("Manual", self.state.lang) if info["manual"] else T("Ausente", self.state.lang))
            self.table.setItem(row, 2, _readonly_item(status_text))
            self.table.setItem(row, 3, _readonly_item(info["size_human"]))
            self.table.setItem(row, 4, _readonly_item(info["modified"] or "-"))
            if not info["manual"] and not info.get("requires_key"):
                button = QPushButton(T("Atualizar", self.state.lang) if info["exists"] else T("Baixar", self.state.lang), self.table)
                button.setObjectName("tableActionButton")
                button.clicked.connect(partial(self._download_one, dataset_id))
                self.table.setCellWidget(row, 5, _centered_cell_widget(button, self.table))
            else:
                label = QLabel(T("N/A", self.state.lang), self.table)
                self.table.setCellWidget(row, 5, _centered_cell_widget(label, self.table))

    def _download_all_impl(self, progress_callback=None):
        results = {}
        total = len(AUTO_DOWNLOADABLE)
        downloader = get_downloader()
        for index, dataset_id in enumerate(AUTO_DOWNLOADABLE, start=1):
            if progress_callback:
                progress_callback(int((index - 1) / max(1, total) * 100), T("Baixando {dataset_id}...", self.state.lang).format(dataset_id=dataset_id))

            def _dataset_progress(percent, *_):
                if progress_callback:
                    overall = ((index - 1) + (percent / 100.0)) / max(1, total)
                    progress_callback(int(overall * 100), T("Baixando {dataset_id}...", self.state.lang).format(dataset_id=dataset_id))

            results[dataset_id] = downloader.download(dataset_id, progress_callback=_dataset_progress)
        return results

    def _download_all(self):
        worker = self._track_worker(FunctionWorker(self._download_all_impl, use_progress=True))
        worker.progress.connect(self._handle_progress)
        worker.result_ready.connect(self._handle_all_downloads)
        worker.error.connect(self._handle_download_error)
        self.download_all_button.setEnabled(False)
        self.status_label.setText(T("Baixando datasets...", self.state.lang))
        worker.start()

    def _download_one(self, dataset_id: str):
        worker = self._track_worker(FunctionWorker(get_downloader().download, dataset_id, use_progress=True))
        worker.progress.connect(self._handle_progress)
        worker.result_ready.connect(self._handle_single_download)
        worker.error.connect(self._handle_download_error)
        self.status_label.setText(T("Baixando {dataset_id}...", self.state.lang).format(dataset_id=dataset_id))
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
        self.status_label.setText(T("Downloads concluídos: {success}/{total} com sucesso.", self.state.lang).format(success=success, total=len(results)))
        self.refresh_status()

    def _handle_single_download(self, result):
        self.progress_bar.setValue(100)
        reload_dataset_checker()
        if result.success:
            self.status_label.setText(T("Download concluído: {count} linhas.", self.state.lang).format(count=result.lines_count))
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
        self.search_input.setPlaceholderText(T("Buscar termo...", self.state.lang))
        self.search_input.textChanged.connect(self._refresh_results)
        self.category_combo = QComboBox(self)
        self.category_combo.addItem(T("Todas", self.state.lang), "Todas")
        for category in GLOSSARY_CATEGORIES:
            self.category_combo.addItem(T(category, self.state.lang), category)
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
        category = self.category_combo.currentData()
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
        self.count_label.setText(T("{count} termos encontrados", self.state.lang).format(count=len(filtered)))
        if not filtered:
            self.results_browser.setHtml(f"<p>{T('Nenhum termo encontrado.', self.state.lang)}</p>")
            return

        html = []
        for current_category in sorted({item["category"] for item in filtered}):
            html.append(f"<h2>{T(current_category, self.state.lang)}</h2>")
            for item in [entry for entry in filtered if entry["category"] == current_category]:
                html.append(
                    f"<div style='background:#1A1A2E;border:1px solid #2D2D45;border-radius:8px;padding:12px;margin-bottom:10px'>"
                    f"<h3>{item['term']}</h3>"
                    f"<p>{item['definition']}</p>"
                    f"<p><b>{T('Exemplo', self.state.lang)}:</b> {item.get('example', '-')}</p>"
                    f"<p><b>{T('Módulo relacionado', self.state.lang)}:</b> {item.get('related_module', '-')}</p>"
                    "</div>"
                )
        self.results_browser.setHtml("".join(html))


class SettingsPage(BasePage):
    def __init__(self, state, parent=None):
        super().__init__(state, parent)

        layout = QVBoxLayout(self)
        _apply_page_layout(layout)

        self.header = SectionHeader(f"⚙️ {T('nav.settings', self.state.lang)}")
        layout.addWidget(self.header)

        appearance_group = QGroupBox(T("Aparência", self.state.lang))
        appearance_layout = QVBoxLayout(appearance_group)
        self.theme_preview_browser = QTextBrowser(appearance_group)
        self.theme_preview_browser.setMaximumHeight(140)
        appearance_layout.addWidget(self.theme_preview_browser)
        theme_row = QHBoxLayout()
        theme_label = QLabel(T("Tema visual", self.state.lang), appearance_group)
        theme_label.setObjectName("fieldLabel")
        theme_row.addWidget(theme_label)
        self.theme_combo = QComboBox(appearance_group)
        self.theme_combo.addItem(T("settings.theme_dark", self.state.lang), "dark")
        self.theme_combo.addItem(T("settings.theme_light", self.state.lang), "light")
        theme_row.addWidget(self.theme_combo, 1)
        appearance_layout.addLayout(theme_row)
        layout.addWidget(appearance_group)

        self.trigger_section = CollapsibleSection(T("Trigger words", self.state.lang), self, expanded=False)
        self.trigger_edit = QPlainTextEdit(self.trigger_section)
        self.trigger_edit.setPlainText("\n".join(settings.TRIGGER_WORDS))
        self.trigger_section.content_layout.addWidget(self.trigger_edit)
        layout.addWidget(self.trigger_section)

        self.tld_section = CollapsibleSection(T("TLDs de risco", self.state.lang), self, expanded=False)
        self.tld_edit = QPlainTextEdit(self.tld_section)
        self.tld_edit.setPlainText("\n".join(settings.HIGH_RISK_TLDS))
        self.tld_section.content_layout.addWidget(self.tld_edit)
        layout.addWidget(self.tld_section)

        self.shortener_section = CollapsibleSection(T("Encurtadores", self.state.lang), self, expanded=False)
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

        ml_group = QGroupBox(T("Classificador ML", self.state.lang))
        ml_layout = QVBoxLayout(ml_group)
        self.ml_status_browser = QTextBrowser(ml_group)
        self.ml_status_browser.setObjectName("panelCard")
        self.ml_status_browser.setMaximumHeight(150)
        ml_layout.addWidget(self.ml_status_browser)
        self.feature_browser = QTextBrowser(ml_group)
        self.feature_browser.setObjectName("panelCard")
        self.feature_browser.setMaximumHeight(180)
        ml_layout.addWidget(self.feature_browser)
        self.train_ml_button = QPushButton(T("Treinar modelo", self.state.lang), ml_group)
        self.train_ml_button.clicked.connect(self._train_model)
        ml_layout.addWidget(self.train_ml_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(ml_group)

        feedback_group = QGroupBox(T("Feedback recebido", self.state.lang))
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
                T("Configurações prontas", self.state.lang),
                T("Ajuste o tema, revise listas heurísticas e acompanhe o estado do modelo local.", self.state.lang),
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
                    T("Modo claro", self.state.lang),
                    T("Superfícies quentes e leitura mais leve para ambientes claros ou uso prolongado durante o dia.", self.state.lang),
                    bullets=[
                        T("Melhora leitura em telas com muita luz ambiente.", self.state.lang),
                        T("Mantém contraste sem depender de branco puro.", self.state.lang),
                    ],
                    kicker=T("Tema ativo", self.state.lang),
                    tone="warning",
                )
            )
        else:
            self.theme_preview_browser.setHtml(
                page_intro_fragment(
                    T("Modo escuro", self.state.lang),
                    T("Contraste controlado e foco nos painéis de análise para reduzir fadiga visual em ambientes fechados.", self.state.lang),
                    bullets=[
                        T("Bom para leitura concentrada e investigação detalhada.", self.state.lang),
                        T("Valoriza alertas, badges e blocos de risco.", self.state.lang),
                    ],
                    kicker=T("Tema ativo", self.state.lang),
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
                T("Heurísticas aplicadas em memória", self.state.lang),
                T("As listas abaixo foram atualizadas para esta execução do aplicativo.", self.state.lang),
                tone="success",
                items=[
                    f"{T('Trigger words', self.state.lang)}: {len(settings.TRIGGER_WORDS)}",
                    f"{T('TLDs de risco', self.state.lang)}: {len(settings.HIGH_RISK_TLDS)}",
                    f"{T('Encurtadores', self.state.lang)}: {len(settings.URL_SHORTENERS)}",
                ],
                icon="✅",
            )
        )

    def _refresh_ml_status(self):
        if not ML_AVAILABLE:
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    T("Classificador indisponível", self.state.lang),
                    T("scikit-learn não está instalado. O classificador ML não pode ser usado nesta máquina.", self.state.lang),
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
                    T("Modelo pronto", self.state.lang),
                    T("Acurácia estimada: {accuracy}%.", self.state.lang).format(accuracy=f"{classifier._accuracy * 100:.1f}"),
                    tone="success",
                    icon="🧠",
                )
            )
            if hasattr(classifier, "get_feature_importance"):
                importance = classifier.get_feature_importance()
                if importance:
                    lines = [f"<h3>{T('Features mais relevantes', self.state.lang)}</h3><ul>"]
                    for name, score in importance[:10]:
                        lines.append(f"<li>{name}: {score:.3f}</li>")
                    lines.append("</ul>")
                    self.feature_browser.setHtml("".join(lines))
                else:
                    self.feature_browser.setHtml(f"<p>{T('Sem feature importance disponível.', self.state.lang)}</p>")
            else:
                self.feature_browser.setHtml(f"<p>{T('Feature importance indisponível.', self.state.lang)}</p>")
        elif MODEL_PATH and MODEL_PATH.exists():
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    T("Modelo inconsistente", self.state.lang),
                    T("Um modelo foi encontrado no disco, mas não foi carregado corretamente. Re-treine para corrigir.", self.state.lang),
                    tone="warning",
                    icon="⚠️",
                )
            )
            self.feature_browser.setHtml("")
        else:
            self.ml_status_browser.setHtml(
                status_banner_fragment(
                    T("Modelo não treinado", self.state.lang),
                    T("Use o botão abaixo para iniciar o treino local e habilitar o apoio do classificador ML.", self.state.lang),
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
                T("Total: {total} | 👍 {useful} | 👎 {not_useful}", self.state.lang).format(
                    total=len(feedback),
                    useful=useful,
                    not_useful=len(feedback) - useful,
                )
            )
        else:
            self.feedback_label.setText(T("Nenhum feedback registrado ainda.", self.state.lang))

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
                T("Treino em andamento", self.state.lang),
                T("Treinando modelo ML. Isso pode levar alguns minutos.", self.state.lang),
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
                    T("Treino concluído", self.state.lang),
                    T("O modelo foi atualizado e já pode ser usado nas próximas análises.", self.state.lang),
                    tone="success",
                    items=[
                        f"{T('Acurácia', self.state.lang)}: {result.accuracy * 100:.2f}%",
                        f"F1: {result.f1 * 100:.2f}%",
                    ],
                    icon="✅",
                )
            )
        else:
            self.settings_status.setHtml(
                status_banner_fragment(
                    T("Falha no treino", self.state.lang),
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
                T("Erro durante o treino", self.state.lang),
                message,
                tone="danger",
                icon="⛔",
            )
        )
