"""
QuizEngine — Lógica do quiz interativo com gamificação.
Gerencia seleção de questões, scoring, progressão e estatísticas.
Gera questões a partir dos datasets carregados e cenários pré-definidos.
"""

import random
import uuid
from dataclasses import dataclass, field

from config.settings import QUIZ_DIFFICULTY_LEVELS


@dataclass
class QuizQuestion:
    """Uma questão do quiz."""
    question_id: str
    difficulty: str               # "iniciante", "intermediario", "avancado"
    question_type: str            # "binary", "multiple_choice", "checklist", "scenario"
    url_defanged: str             # URL defanged (para logs/persistência)
    question_text: str            # Texto da pergunta
    url_display: str = ""         # URL original para exibição na UI (sem defang)
    options: list[str] = field(default_factory=list)  # Para múltipla escolha
    correct_answer: object = None  # bool, str, ou list[str]
    scenario_context: str = ""    # Contexto para cenários avançados
    explanation: str = ""         # Explicação detalhada (mostrada após resposta)
    findings: list[str] = field(default_factory=list)  # Sinais de alerta


@dataclass
class QuizFeedback:
    """Feedback para uma resposta do quiz."""
    is_correct: bool
    user_answer: object
    correct_answer: object
    explanation: str
    detailed_findings: list[str] = field(default_factory=list)
    tip: str = ""
    partial_score: float = 0.0    # Para questões de checklist (0.0 a 1.0)


@dataclass
class UserStats:
    """Estatísticas do usuário no quiz."""
    total_questions: int = 0
    correct_answers: int = 0
    wrong_answers: int = 0
    accuracy: float = 0.0
    current_streak: int = 0
    best_streak: int = 0
    by_difficulty: dict = field(default_factory=lambda: {
        "iniciante": {"total": 0, "correct": 0},
        "intermediario": {"total": 0, "correct": 0},
        "avancado": {"total": 0, "correct": 0},
    })
    level: str = "iniciante"


class QuizEngine:
    """
    Gerencia o quiz interativo: seleção de questões, scoring, progressão.
    Gera questões a partir dos datasets e cenários pré-definidos.
    """

    def __init__(self):
        self._questions_bank: list[QuizQuestion] = []
        self._active_questions: dict[str, QuizQuestion] = {}
        self._stats = UserStats()
        self._build_question_bank()

    def generate_question(self, difficulty: str = "iniciante") -> QuizQuestion:
        """
        Gera uma questão do banco baseada no nível de dificuldade.
        Retorna QuizQuestion com todos os dados necessários.
        """
        if difficulty not in QUIZ_DIFFICULTY_LEVELS:
            difficulty = "iniciante"

        # Filtra questões pelo nível
        available = [
            q for q in self._questions_bank
            if q.difficulty == difficulty and q.question_id not in self._active_questions
        ]

        if not available:
            # Reaproveita questões se o banco acabar
            available = [q for q in self._questions_bank if q.difficulty == difficulty]

        if not available:
            available = self._questions_bank

        question = random.choice(available)
        # Gera novo ID para a instância
        instance = QuizQuestion(
            question_id=str(uuid.uuid4()),
            difficulty=question.difficulty,
            question_type=question.question_type,
            url_defanged=question.url_defanged,
            question_text=question.question_text,
            url_display=question.url_display or question.url_defanged,
            options=question.options.copy(),
            correct_answer=question.correct_answer,
            scenario_context=question.scenario_context,
            explanation=question.explanation,
            findings=question.findings.copy(),
        )
        self._active_questions[instance.question_id] = instance
        return instance

    def check_answer(self, question_id: str, answer: object) -> QuizFeedback:
        """
        Verifica a resposta do usuário e retorna feedback didático.
        """
        question = self._active_questions.get(question_id)
        if not question:
            return QuizFeedback(
                is_correct=False,
                user_answer=answer,
                correct_answer=None,
                explanation="Questão não encontrada.",
            )

        # Avalia resposta conforme tipo
        if question.question_type == "binary":
            is_correct = answer == question.correct_answer
            partial = 1.0 if is_correct else 0.0

        elif question.question_type == "multiple_choice":
            is_correct = str(answer).upper() == str(question.correct_answer).upper()
            partial = 1.0 if is_correct else 0.0

        elif question.question_type == "checklist":
            # Para checklists, calcula score parcial
            correct_set = set(question.correct_answer)
            answer_set = set(answer) if isinstance(answer, list) else set()
            if correct_set:
                hits = len(correct_set & answer_set)
                false_positives = len(answer_set - correct_set)
                partial = max(0.0, (hits - false_positives * 0.5) / len(correct_set))
                is_correct = partial >= 0.8  # 80% de acerto
            else:
                is_correct = True
                partial = 1.0
        else:
            is_correct = answer == question.correct_answer
            partial = 1.0 if is_correct else 0.0

        # Atualiza estatísticas
        self._update_stats(question.difficulty, is_correct)

        feedback = QuizFeedback(
            is_correct=is_correct,
            user_answer=answer,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            detailed_findings=question.findings,
            partial_score=partial,
            tip=self._get_tip(question),
        )

        # Remove questão ativa
        del self._active_questions[question_id]

        return feedback

    def get_statistics(self) -> UserStats:
        """Retorna estatísticas atuais do usuário."""
        return self._stats

    def reset_statistics(self):
        """Reseta estatísticas do usuário."""
        self._stats = UserStats()

    def get_suggested_difficulty(self) -> str:
        """Sugere dificuldade baseada no desempenho."""
        stats = self._stats
        if stats.total_questions < 5:
            return "iniciante"

        if stats.accuracy >= 0.85 and stats.by_difficulty["iniciante"]["total"] >= 5:
            if stats.by_difficulty["intermediario"]["total"] >= 5:
                inter_acc = (
                    stats.by_difficulty["intermediario"]["correct"] /
                    max(1, stats.by_difficulty["intermediario"]["total"])
                )
                if inter_acc >= 0.75:
                    return "avancado"
            return "intermediario"
        return "iniciante"

    def _update_stats(self, difficulty: str, correct: bool):
        """Atualiza estatísticas após resposta."""
        s = self._stats
        s.total_questions += 1
        if correct:
            s.correct_answers += 1
            s.current_streak += 1
            s.best_streak = max(s.best_streak, s.current_streak)
        else:
            s.wrong_answers += 1
            s.current_streak = 0

        s.accuracy = s.correct_answers / max(1, s.total_questions)

        if difficulty in s.by_difficulty:
            s.by_difficulty[difficulty]["total"] += 1
            if correct:
                s.by_difficulty[difficulty]["correct"] += 1

        s.level = self.get_suggested_difficulty()

    def _get_tip(self, question: QuizQuestion) -> str:
        """Retorna dica contextual baseada na questão."""
        tips = {
            "iniciante": (
                "💡 Dica: Sempre verifique se o domínio corresponde ao site "
                "oficial antes de inserir seus dados."
            ),
            "intermediario": (
                "💡 Dica: Preste atenção em detalhes visuais como letras "
                "trocadas (rn→m) e subdomínios suspeitos."
            ),
            "avancado": (
                "💡 Regra de ouro: Quando receber comunicação urgente pedindo "
                "ação imediata, PARE e verifique pelo canal oficial."
            ),
        }
        return tips.get(question.difficulty, tips["iniciante"])

    def _build_question_bank(self):
        """Constrói banco de questões pré-definidas por nível."""

        # ============================================================
        # NÍVEL INICIANTE — Questões binárias (Segura/Maliciosa)
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="init_01",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxp[://]192[.]168[.]1[.]100/netflix/login",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                url_display="http://192.168.1.100/netflix/login",
                correct_answer=False,  # False = maliciosa
                explanation=(
                    "Esta URL é MALICIOSA. Motivos:\n"
                    "1. Usa IP (192.168.1.100) em vez de domínio — a Netflix nunca "
                    "pede que você acesse pelo número IP.\n"
                    "2. Usa HTTP sem criptografia — a Netflix real SEMPRE usa HTTPS.\n"
                    "3. O path '/netflix/login' imita a marca mas está em servidor desconhecido."
                ),
                findings=[
                    "IP em vez de domínio",
                    "HTTP sem criptografia",
                    "Marca no path de servidor desconhecido",
                ],
            ),
            QuizQuestion(
                question_id="init_02",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://www.google.com/search?q=python",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,  # True = segura
                explanation=(
                    "Esta URL é SEGURA. Motivos:\n"
                    "1. Usa HTTPS (conexão criptografada).\n"
                    "2. Domínio 'google.com' é legítimo e bem estabelecido.\n"
                    "3. A query string '?q=python' é um parâmetro de busca normal."
                ),
                findings=["HTTPS ativo", "Domínio reconhecido", "Query string legítima"],
            ),
            QuizQuestion(
                question_id="init_03",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxp[://]free-iphone-winner[.]tk/claim-prize",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                url_display="http://free-iphone-winner.tk/claim-prize",
                correct_answer=False,
                explanation=(
                    "Esta URL é MALICIOSA. Motivos:\n"
                    "1. HTTP sem criptografia.\n"
                    "2. TLD '.tk' é frequentemente usado em sites maliciosos.\n"
                    "3. Palavras como 'free', 'winner', 'claim-prize' são gatilhos "
                    "clássicos de golpes."
                ),
                findings=["HTTP inseguro", "TLD de risco (.tk)", "Palavras-gatilho de golpe"],
            ),
            QuizQuestion(
                question_id="init_04",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://github.com/torvalds/linux",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,
                explanation=(
                    "Esta URL é SEGURA. Motivos:\n"
                    "1. HTTPS ativo.\n"
                    "2. 'github.com' é uma plataforma legítima e reconhecida.\n"
                    "3. O path '/torvalds/linux' aponta para um repositório público."
                ),
                findings=["HTTPS ativo", "Domínio reconhecido (GitHub)"],
            ),
            QuizQuestion(
                question_id="init_05",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxps[://]paypa1[.]com/login",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                url_display="https://paypa1.com/login",
                correct_answer=False,
                explanation=(
                    "Esta URL é MALICIOSA. Motivos:\n"
                    "1. O domínio 'paypa1' usa o número '1' no lugar da letra 'l' "
                    "para imitar 'paypal'. Isso é TYPOSQUATTING.\n"
                    "2. O domínio real do PayPal é 'paypal.com', não 'paypa1.com'.\n"
                    "3. Mesmo com HTTPS, o site é falso."
                ),
                findings=["Typosquatting (paypa1 vs paypal)", "HTTPS não garante legitimidade"],
            ),
        ])

        # ============================================================
        # NÍVEL INTERMEDIÁRIO — Múltipla escolha
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="inter_01",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]www[.]arnazon[.]com/gp/cart",
                question_text="Qual elemento torna esta URL suspeita?",
                url_display="https://www.arnazon.com/gp/cart",
                options=[
                    "A) O uso de HTTPS",
                    "B) O 'www' no subdomínio",
                    "C) O domínio 'arnazon' (com 'rn' imitando 'm')",
                    "D) O path '/gp/cart'",
                ],
                correct_answer="C",
                explanation=(
                    "O domínio 'arnazon' usa um truque visual chamado HOMÓGRAFO: "
                    "as letras 'r' e 'n' juntas (rn) parecem 'm' em certas fontes.\n\n"
                    "❌ arnazon.com (rn = falso 'm')\n"
                    "✅ amazon.com (m verdadeiro)\n\n"
                    "Esse ataque é chamado de TYPOSQUATTING — registrar domínios "
                    "que parecem visualmente com marcas famosas."
                ),
                findings=["Homógrafo visual (rn → m)", "Typosquatting de marca (Amazon)"],
            ),
            QuizQuestion(
                question_id="inter_02",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]secure-login[.]bancodobrasil-verify[.]com[.]br/auth",
                question_text="Qual é o PRINCIPAL sinal de alerta nesta URL?",
                url_display="https://secure-login.bancodobrasil-verify.com.br/auth",
                options=[
                    "A) O uso de HTTPS",
                    "B) O domínio NÃO é 'bb.com.br' (oficial do Banco do Brasil)",
                    "C) A presença de '/auth' no path",
                    "D) O TLD '.com.br'",
                ],
                correct_answer="B",
                explanation=(
                    "O domínio 'bancodobrasil-verify.com.br' IMITA o nome do "
                    "Banco do Brasil, mas NÃO é o domínio oficial (bb.com.br).\n\n"
                    "❌ bancodobrasil-verify[.]com[.]br\n"
                    "✅ bb.com.br\n\n"
                    "É como alguém colocar uma placa 'Banco do Brasil' na fachada "
                    "de uma loja falsa."
                ),
                findings=[
                    "Domínio falso imitando marca",
                    "Palavras-gatilho: 'secure', 'login', 'verify'",
                    "Excesso de hífens",
                ],
            ),
            QuizQuestion(
                question_id="inter_03",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]bit[.]ly/3xK9mPq",
                question_text="Por que URLs encurtadas exigem cautela especial?",
                url_display="https://bit.ly/3xK9mPq",
                options=[
                    "A) Porque bit.ly é um site malicioso",
                    "B) Porque o destino real está oculto — você não sabe para onde será redirecionado",
                    "C) Porque URLs curtas são sempre maliciosas",
                    "D) Porque bit.ly não usa HTTPS",
                ],
                correct_answer="B",
                explanation=(
                    "URLs encurtadas escondem o destino real. O link pode redirecionar "
                    "para qualquer site, inclusive maliciosos.\n\n"
                    "bit.ly em si não é malicioso, mas é usado tanto legitimamente "
                    "quanto por atacantes para disfarçar links perigosos.\n\n"
                    "Use serviços como 'checkshorturl.com' para revelar o destino "
                    "real antes de clicar."
                ),
                findings=["Destino oculto", "Impossível avaliar sem expandir"],
            ),
            QuizQuestion(
                question_id="inter_04",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]login[.]microsofft[.]xyz/outlook/signin",
                question_text="Quantos sinais de alerta você identifica nesta URL?",
                url_display="https://login.microsofft.xyz/outlook/signin",
                options=[
                    "A) 1 — apenas o TLD incomum",
                    "B) 2 — TLD incomum e typosquatting",
                    "C) 3 — TLD incomum, typosquatting e palavras-gatilho",
                    "D) 4 — TLD incomum, typosquatting, palavras-gatilho e subdomínio suspeito",
                ],
                correct_answer="D",
                explanation=(
                    "São 4 sinais de alerta:\n"
                    "1. TLD incomum (.xyz) — frequentemente usado em sites maliciosos.\n"
                    "2. Typosquatting — 'microsofft' (dois f's) imita 'microsoft'.\n"
                    "3. Palavras-gatilho — 'login' e 'signin' indicam página de captura.\n"
                    "4. Subdomínio — 'login' como subdomínio reforça a aparência de legitimidade."
                ),
                findings=["TLD .xyz", "Typosquatting (microsofft)", "Palavras-gatilho", "Subdomínio enganoso"],
            ),
        ])

        # ============================================================
        # NÍVEL AVANÇADO — Cenários completos com checklist
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="adv_01",
                difficulty="avancado",
                question_type="checklist",
                url_defanged="hxxps[://]banco-seguranca[.]com/verificar-conta",
                question_text="Liste TODOS os sinais de alerta que você identifica neste cenário:",
                url_display="https://banco-seguranca.com/verificar-conta",
                scenario_context=(
                    "📧 CENÁRIO: Você recebe o seguinte e-mail:\n\n"
                    "De: suporte@banco-seguranca.com\n"
                    "Assunto: ⚠️ Ação necessária: atividade suspeita\n\n"
                    "\"Prezado cliente,\n"
                    "Detectamos uma tentativa de acesso não autorizado à sua conta. "
                    "Para sua segurança, clique no link abaixo e confirme seus dados "
                    "em até 24 horas ou sua conta será bloqueada:\n\n"
                    "https://banco-seguranca.com/verificar-conta\n\n"
                    "Atenciosamente, Equipe de Segurança\""
                ),
                options=[
                    "Domínio não é o oficial do banco",
                    "Urgência artificial ('24 horas')",
                    "Ameaça de consequência ('conta bloqueada')",
                    "Pedido para 'confirmar dados' via link",
                    "Remetente genérico (não personalizado com seu nome)",
                    "E-mail do remetente usa domínio não oficial",
                ],
                correct_answer=[
                    "Domínio não é o oficial do banco",
                    "Urgência artificial ('24 horas')",
                    "Ameaça de consequência ('conta bloqueada')",
                    "Pedido para 'confirmar dados' via link",
                    "Remetente genérico (não personalizado com seu nome)",
                    "E-mail do remetente usa domínio não oficial",
                ],
                explanation=(
                    "Todos os 6 itens são sinais de alerta!\n\n"
                    "1. DOMÍNIO FALSO — 'banco-seguranca.com' não é domínio de "
                    "nenhum banco brasileiro real.\n"
                    "2. URGÊNCIA ARTIFICIAL — '24 horas' é tática de pressão.\n"
                    "3. AMEAÇA — 'conta bloqueada' gera medo e ação impulsiva.\n"
                    "4. PHISHING CLÁSSICO — bancos NUNCA pedem confirmação de dados por link.\n"
                    "5. GENÉRICO — 'Prezado cliente' em vez do seu nome real.\n"
                    "6. REMETENTE FALSO — domínio do e-mail é controlado pelo atacante."
                ),
                findings=[
                    "Domínio falso", "Urgência artificial", "Ameaça",
                    "Pedido de dados por link", "Tratamento genérico", "Remetente falso",
                ],
            ),
            QuizQuestion(
                question_id="adv_02",
                difficulty="avancado",
                question_type="checklist",
                url_defanged="hxxps[://]promo-especial[.]mercadolivre[.]deals/oferta",
                question_text="Liste TODOS os sinais de alerta neste cenário:",
                url_display="https://promo-especial.mercadolivre.deals/oferta",
                scenario_context=(
                    "📱 CENÁRIO: Você recebe o seguinte SMS:\n\n"
                    "\"MERCADO LIVRE: Parabéns! Você foi selecionado para nossa "
                    "promoção exclusiva. Resgate seu prêmio de R$ 500 em créditos "
                    "clicando aqui: https://promo-especial.mercadolivre.deals/oferta\n"
                    "Válido por 2 horas!\""
                ),
                options=[
                    "TLD '.deals' não é o oficial (.com.br)",
                    "Promessa de prêmio não solicitado",
                    "Urgência artificial ('2 horas')",
                    "Domínio diferente do oficial (mercadolivre.com.br)",
                    "SMS não é canal oficial para promoções",
                    "Subdomínio 'promo-especial' com hífens",
                ],
                correct_answer=[
                    "TLD '.deals' não é o oficial (.com.br)",
                    "Promessa de prêmio não solicitado",
                    "Urgência artificial ('2 horas')",
                    "Domínio diferente do oficial (mercadolivre.com.br)",
                    "SMS não é canal oficial para promoções",
                    "Subdomínio 'promo-especial' com hífens",
                ],
                explanation=(
                    "Todos os 6 itens são sinais de smishing (phishing por SMS)!\n\n"
                    "1. TLD ERRADO — O Mercado Livre usa 'mercadolivre.com.br', não '.deals'.\n"
                    "2. PRÊMIO FALSO — Promoções legítimas não pedem que você 'resgate' por link.\n"
                    "3. URGÊNCIA — '2 horas' impede reflexão.\n"
                    "4. DOMÍNIO FALSO — Apesar de conter 'mercadolivre', o domínio real é outro.\n"
                    "5. SMS SUSPEITO — Empresas usam app e e-mail, não SMS com links.\n"
                    "6. HÍFENS — 'promo-especial' é construído para parecer legítimo."
                ),
                findings=[
                    "TLD errado", "Prêmio falso", "Urgência",
                    "Domínio falso", "Canal suspeito (SMS)", "Hífens no subdomínio",
                ],
            ),
        ])

        # ============================================================
        # NÍVEL INICIANTE — Questões binárias extras
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="init_06",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxps[://]netflix-conta-suspensa[.]com/reativar",
                url_display="https://netflix-conta-suspensa.com/reativar",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA. O domínio 'netflix-conta-suspensa.com' NÃO é da Netflix.\n"
                    "O domínio real é 'netflix.com'. Palavras como 'conta-suspensa' e "
                    "'reativar' são gatilhos emocionais típicos de phishing."
                ),
                findings=["Domínio falso", "Palavras-gatilho", "Imita marca"],
            ),
            QuizQuestion(
                question_id="init_07",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://stackoverflow.com/questions/12345",
                url_display="https://stackoverflow.com/questions/12345",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,
                explanation=(
                    "SEGURA. 'stackoverflow.com' é um site legítimo e reconhecido "
                    "mundialmente para perguntas sobre programação. HTTPS ativo."
                ),
                findings=["HTTPS ativo", "Domínio reconhecido"],
            ),
            QuizQuestion(
                question_id="init_08",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxp[://]correios-rastreio[.]xyz/pacote",
                url_display="http://correios-rastreio.xyz/pacote",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA. Os Correios usam 'correios.com.br', não '.xyz'.\n"
                    "HTTP sem criptografia + TLD de risco (.xyz) + nome que imita marca."
                ),
                findings=["Domínio falso", "TLD de risco (.xyz)", "HTTP inseguro"],
            ),
            QuizQuestion(
                question_id="init_09",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://www.gov.br/receitafederal",
                url_display="https://www.gov.br/receitafederal",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,
                explanation=(
                    "SEGURA. O domínio 'gov.br' é o domínio oficial do governo brasileiro.\n"
                    "HTTPS ativo. O path '/receitafederal' é legítimo."
                ),
                findings=["HTTPS ativo", "Domínio governamental (.gov.br)"],
            ),
            QuizQuestion(
                question_id="init_10",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxps[://]mercadolivre-oferta[.]shop/produto",
                url_display="https://mercadolivre-oferta.shop/produto",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA. O Mercado Livre usa 'mercadolivre.com.br', não '.shop'.\n"
                    "Hífens no domínio + TLD '.shop' + imitação de marca."
                ),
                findings=["Domínio falso", "TLD suspeito (.shop)", "Imita marca"],
            ),
            QuizQuestion(
                question_id="init_11",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://www.wikipedia.org/wiki/Phishing",
                url_display="https://www.wikipedia.org/wiki/Phishing",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,
                explanation=(
                    "SEGURA. 'wikipedia.org' é uma enciclopédia online reconhecida mundialmente.\n"
                    "HTTPS ativo. O path '/wiki/Phishing' é conteúdo educacional."
                ),
                findings=["HTTPS ativo", "Domínio reconhecido"],
            ),
            QuizQuestion(
                question_id="init_12",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxps[://]detran-multas-pagar[.]com/pix",
                url_display="https://detran-multas-pagar.com/pix",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA. O DETRAN usa domínios '.gov.br', não '.com'.\n"
                    "'multas-pagar' + '/pix' são gatilhos típicos de golpe financeiro."
                ),
                findings=["Domínio falso (deveria ser .gov.br)", "Palavras-gatilho", "PIX suspeito"],
            ),
            QuizQuestion(
                question_id="init_13",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxp[://]10[.]0[.]0[.]1:8080/admin",
                url_display="http://10.0.0.1:8080/admin",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA/SUSPEITA. URL com endereço IP privado em vez de domínio.\n"
                    "Porta não-padrão (8080) + HTTP sem criptografia + path '/admin'."
                ),
                findings=["IP privado", "HTTP inseguro", "Porta não-padrão"],
            ),
            QuizQuestion(
                question_id="init_14",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="https://www.linkedin.com/in/joao-silva",
                url_display="https://www.linkedin.com/in/joao-silva",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=True,
                explanation=(
                    "SEGURA. 'linkedin.com' é a rede profissional legítima.\n"
                    "HTTPS ativo. O path '/in/joao-silva' é um perfil público."
                ),
                findings=["HTTPS ativo", "Domínio reconhecido (LinkedIn)"],
            ),
            QuizQuestion(
                question_id="init_15",
                difficulty="iniciante",
                question_type="binary",
                url_defanged="hxxps[://]nubank-pix-estorno[.]com/devolver",
                url_display="https://nubank-pix-estorno.com/devolver",
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                correct_answer=False,
                explanation=(
                    "MALICIOSA. O Nubank usa 'nubank.com.br', não 'nubank-pix-estorno.com'.\n"
                    "'pix-estorno' e '/devolver' são gatilhos de golpe do PIX."
                ),
                findings=["Domínio falso", "Golpe do PIX", "Palavras-gatilho"],
            ),
        ])

        # ============================================================
        # NÍVEL INTERMEDIÁRIO — Múltipla escolha extras
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="inter_05",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]suporte[.]apple-id-verify[.]com/recovery",
                url_display="https://suporte.apple-id-verify.com/recovery",
                question_text="Qual é o domínio REAL registrado desta URL?",
                options=[
                    "A) apple.com",
                    "B) apple-id-verify.com",
                    "C) suporte.apple-id-verify.com",
                    "D) id-verify.com",
                ],
                correct_answer="B",
                explanation=(
                    "O domínio registrado é 'apple-id-verify.com'. "
                    "'suporte' é apenas um subdomínio controlado pelo dono de 'apple-id-verify.com'.\n\n"
                    "❌ apple-id-verify.com (domínio falso)\n"
                    "✅ apple.com (domínio real da Apple)\n\n"
                    "REGRA: Sempre leia o domínio de TRÁS para frente — "
                    "o que importa é o que vem antes do TLD."
                ),
                findings=["Subdomínio enganoso", "Domínio falso com nome de marca"],
            ),
            QuizQuestion(
                question_id="inter_06",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]g00gle[.]com/search",
                url_display="https://g00gle.com/search",
                question_text="Que tipo de ataque esta URL representa?",
                options=[
                    "A) DGA (Domain Generation Algorithm)",
                    "B) Typosquatting com substituição de letras por números",
                    "C) Open Redirect",
                    "D) URL Encoding abusivo",
                ],
                correct_answer="B",
                explanation=(
                    "Typosquatting: 'g00gle' usa zeros (0) no lugar de 'o'.\n"
                    "Em certas fontes, '0' e 'o' são quase idênticos.\n\n"
                    "❌ g00gle.com\n"
                    "✅ google.com"
                ),
                findings=["Typosquatting (0 → o)", "Domínio falso"],
            ),
            QuizQuestion(
                question_id="inter_07",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]itau[.]com[.]br[.]secure-banking[.]net/login",
                url_display="https://itau.com.br.secure-banking.net/login",
                question_text="Qual é o domínio REAL desta URL?",
                options=[
                    "A) itau.com.br",
                    "B) secure-banking.net",
                    "C) com.br.secure-banking.net",
                    "D) banking.net",
                ],
                correct_answer="B",
                explanation=(
                    "O domínio real é 'secure-banking.net'. Tudo antes "
                    "('itau.com.br') são subdomínios controlados pelo atacante.\n\n"
                    "É a técnica mais perigosa: o usuário vê 'itau.com.br' no "
                    "início e assume que é legítimo."
                ),
                findings=[
                    "Subdomínio imitando domínio real",
                    "Domínio registrado é outro",
                    "Palavras-gatilho: 'secure', 'login'",
                ],
            ),
            QuizQuestion(
                question_id="inter_08",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]encurtador[.]com/aB3xY",
                url_display="https://encurtador.com/aB3xY",
                question_text="Qual a MELHOR ação ao receber uma URL encurtada de fonte desconhecida?",
                options=[
                    "A) Clicar — se tem HTTPS é seguro",
                    "B) Expandir usando serviço como checkshorturl.com antes de clicar",
                    "C) Ignorar — URLs curtas são sempre maliciosas",
                    "D) Copiar e colar no navegador em vez de clicar",
                ],
                correct_answer="B",
                explanation=(
                    "A melhor ação é EXPANDIR a URL para ver o destino real.\n"
                    "URLs encurtadas não são necessariamente maliciosas, mas "
                    "escondem o destino. Expandir permite avaliar antes de acessar."
                ),
                findings=["Destino oculto", "Verificar antes de clicar"],
            ),
            QuizQuestion(
                question_id="inter_09",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]192[.]168[.]0[.]1/config",
                url_display="https://192.168.0.1/config",
                question_text="O que indica o uso de IP (192.168.0.1) em vez de domínio?",
                options=[
                    "A) É mais seguro que usar domínio",
                    "B) É um endereço de rede local — pode ser legítimo para configurar roteadores",
                    "C) É sempre malicioso",
                    "D) É um servidor do Google",
                ],
                correct_answer="B",
                explanation=(
                    "IPs da faixa 192.168.x.x são endereços de rede LOCAL.\n"
                    "Acessar 192.168.0.1 para configurar o roteador é normal.\n"
                    "Mas IPs públicos em links de e-mail/SMS são muito suspeitos."
                ),
                findings=["IP privado (rede local)", "Contexto define legitimidade"],
            ),
            QuizQuestion(
                question_id="inter_10",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]www[.]banco-do-brasil-seguro[.]ml/verificar",
                url_display="https://www.banco-do-brasil-seguro.ml/verificar",
                question_text="Quantos sinais de alerta você identifica?",
                options=[
                    "A) 1 — apenas o domínio suspeito",
                    "B) 2 — domínio suspeito e TLD de risco",
                    "C) 3 — domínio suspeito, TLD de risco e palavras-gatilho",
                    "D) 4 — domínio suspeito, TLD .ml, palavras-gatilho e excesso de hífens",
                ],
                correct_answer="D",
                explanation=(
                    "4 sinais:\n"
                    "1. Domínio falso (BB usa bb.com.br)\n"
                    "2. TLD .ml (gratuito, alto risco)\n"
                    "3. 'seguro' e 'verificar' = palavras-gatilho\n"
                    "4. Excesso de hífens no domínio"
                ),
                findings=["Domínio falso", "TLD .ml", "Palavras-gatilho", "Hífens excessivos"],
            ),
            QuizQuestion(
                question_id="inter_11",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]docs[.]google[.]com/forms/d/e/1FAIpQ/viewform",
                url_display="https://docs.google.com/forms/d/e/1FAIpQ/viewform",
                question_text="Esta URL do Google Forms é automaticamente segura?",
                options=[
                    "A) Sim — google.com é sempre seguro",
                    "B) Não — Google Forms pode ser usado para phishing por qualquer pessoa",
                    "C) Sim — HTTPS garante segurança",
                    "D) Não — docs.google.com é um domínio falso",
                ],
                correct_answer="B",
                explanation=(
                    "Google Forms é uma ferramenta LEGÍTIMA, mas qualquer pessoa "
                    "pode criar um formulário falso pedindo dados sensíveis.\n\n"
                    "O domínio é real (google.com), mas o CONTEÚDO pode ser "
                    "malicioso. Plataforma legítima ≠ conteúdo legítimo."
                ),
                findings=["Plataforma legítima com conteúdo malicioso", "Forms = coleta de dados"],
            ),
            QuizQuestion(
                question_id="inter_12",
                difficulty="intermediario",
                question_type="multiple_choice",
                url_defanged="hxxps[://]xn--80ak6aa92e[.]com",
                url_display="https://xn--80ak6aa92e.com",
                question_text="O que o prefixo 'xn--' indica no domínio?",
                options=[
                    "A) É um domínio criptografado",
                    "B) É um domínio internacionalizado (IDN) — pode ser ataque homógrafo",
                    "C) É um domínio de teste",
                    "D) É um subdomínio especial",
                ],
                correct_answer="B",
                explanation=(
                    "'xn--' indica Punycode — representação ASCII de domínios com "
                    "caracteres Unicode (cirílico, grego, etc.).\n\n"
                    "Atacantes usam para criar domínios visualmente idênticos "
                    "aos legítimos usando caracteres de outros alfabetos."
                ),
                findings=["IDN/Punycode", "Possível ataque homógrafo"],
            ),
        ])

        # ============================================================
        # NÍVEL AVANÇADO — Cenários e checklists extras
        # ============================================================
        self._questions_bank.extend([
            QuizQuestion(
                question_id="adv_03",
                difficulty="avancado",
                question_type="checklist",
                url_defanged="hxxps[://]pix-devolucao-nubank[.]com/estorno",
                url_display="https://pix-devolucao-nubank.com/estorno",
                question_text="Liste TODOS os sinais de alerta neste cenário:",
                scenario_context=(
                    "📱 CENÁRIO: Você recebe uma ligação:\n\n"
                    "\"Aqui é da Central de Segurança do Nubank. Identificamos "
                    "um PIX de R$ 980,00 feito da sua conta agora. Se não foi você, "
                    "precisamos cancelar AGORA. Acesse o link que enviei por SMS "
                    "para confirmar o estorno:\n\n"
                    "https://pix-devolucao-nubank.com/estorno\""
                ),
                options=[
                    "Domínio não é nubank.com.br",
                    "Ligação não solicitada pedindo ação urgente",
                    "PIX não pode ser 'estornado' por link",
                    "Pressão para agir 'AGORA'",
                    "SMS com link após ligação = engenharia social",
                    "Banco nunca pede acesso a link por telefone",
                ],
                correct_answer=[
                    "Domínio não é nubank.com.br",
                    "Ligação não solicitada pedindo ação urgente",
                    "PIX não pode ser 'estornado' por link",
                    "Pressão para agir 'AGORA'",
                    "SMS com link após ligação = engenharia social",
                    "Banco nunca pede acesso a link por telefone",
                ],
                explanation=(
                    "Golpe do PIX combinando vishing (ligação) + smishing (SMS):\n\n"
                    "1. DOMÍNIO FALSO — Nubank usa 'nubank.com.br'\n"
                    "2. LIGAÇÃO NÃO SOLICITADA — bancos não ligam pedindo ações\n"
                    "3. PIX FALSO — estornos são feitos pelo app, não por link\n"
                    "4. URGÊNCIA — 'AGORA' impede reflexão\n"
                    "5. MULTI-CANAL — ligação + SMS aumenta credibilidade\n"
                    "6. REGRA DE OURO — bancos NUNCA pedem acesso a links por telefone"
                ),
                findings=[
                    "Domínio falso", "Vishing", "Golpe do PIX",
                    "Urgência", "Multi-canal", "Regra de ouro violada",
                ],
            ),
            QuizQuestion(
                question_id="adv_04",
                difficulty="avancado",
                question_type="checklist",
                url_defanged="hxxps[://]vagas-home-office[.]com/cadastro",
                url_display="https://vagas-home-office.com/cadastro",
                question_text="Liste TODOS os sinais de alerta neste cenário:",
                scenario_context=(
                    "📧 CENÁRIO: Você recebe e-mail com oferta de emprego:\n\n"
                    "De: rh@vagas-home-office.com\n"
                    "Assunto: Vaga Home Office — R$ 8.000/mês — Sem experiência\n\n"
                    "\"Olá!\n"
                    "Estamos selecionando pessoas para trabalho remoto.\n"
                    "Salário: R$ 8.000/mês | Jornada: 4h/dia\n"
                    "Sem experiência necessária. Vagas limitadas!\n\n"
                    "Cadastre-se agora: https://vagas-home-office.com/cadastro\n\n"
                    "Restam apenas 3 vagas!\""
                ),
                options=[
                    "Salário irrealisticamente alto para 4h sem experiência",
                    "Domínio genérico (não é de empresa real)",
                    "'Vagas limitadas' / 'Restam 3 vagas' = urgência artificial",
                    "Remetente de domínio desconhecido",
                    "Sem nome da empresa contratante",
                    "Sem detalhes da função/cargo",
                ],
                correct_answer=[
                    "Salário irrealisticamente alto para 4h sem experiência",
                    "Domínio genérico (não é de empresa real)",
                    "'Vagas limitadas' / 'Restam 3 vagas' = urgência artificial",
                    "Remetente de domínio desconhecido",
                    "Sem nome da empresa contratante",
                    "Sem detalhes da função/cargo",
                ],
                explanation=(
                    "Golpe de falsa vaga de emprego:\n\n"
                    "1. SALÁRIO IRREAL — R$ 8k por 4h sem experiência é isca\n"
                    "2. DOMÍNIO GENÉRICO — não pertence a empresa real\n"
                    "3. URGÊNCIA — 'vagas limitadas' pressiona cadastro rápido\n"
                    "4. REMETENTE — domínio do e-mail não é de empresa conhecida\n"
                    "5. SEM EMPRESA — vagas reais identificam a empresa\n"
                    "6. SEM DETALHES — não descreve a função nem requisitos"
                ),
                findings=[
                    "Salário isca", "Domínio genérico", "Urgência",
                    "Remetente suspeito", "Sem empresa", "Sem detalhes",
                ],
            ),
            QuizQuestion(
                question_id="adv_05",
                difficulty="avancado",
                question_type="multiple_choice",
                url_defanged="hxxps[://]receita-federal-gov[.]com/regularizar-cpf",
                url_display="https://receita-federal-gov.com/regularizar-cpf",
                question_text="Por que esta URL é perigosa MESMO tendo 'gov' no nome?",
                options=[
                    "A) Porque 'receita-federal-gov.com' NÃO é .gov.br — é um .com qualquer",
                    "B) Porque HTTPS não garante segurança",
                    "C) Porque a Receita Federal não tem site",
                    "D) Porque URLs com hífens são sempre maliciosas",
                ],
                correct_answer="A",
                explanation=(
                    "O TLD é '.com', não '.gov.br'. Qualquer pessoa pode "
                    "registrar um domínio '.com' com 'gov' no nome.\n\n"
                    "❌ receita-federal-gov.com (TLD .com — qualquer um registra)\n"
                    "✅ gov.br/receitafederal (TLD .gov.br — controlado pelo governo)\n\n"
                    "A palavra 'gov' no NOME do domínio não tem nenhum valor. "
                    "O que importa é o TLD .gov.br."
                ),
                findings=["TLD .com vs .gov.br", "Nome enganoso"],
            ),
            QuizQuestion(
                question_id="adv_06",
                difficulty="avancado",
                question_type="multiple_choice",
                url_defanged="hxxps[://]site[.]com/redirect?url=hxxps[://]evil[.]com",
                url_display="https://site.com/redirect?url=https://evil.com",
                question_text="Que vulnerabilidade esta URL explora?",
                options=[
                    "A) SQL Injection",
                    "B) Open Redirect — redireciona para evil.com via site legítimo",
                    "C) Cross-Site Scripting (XSS)",
                    "D) Buffer Overflow",
                ],
                correct_answer="B",
                explanation=(
                    "Open Redirect: o parâmetro '?url=' faz o site legítimo "
                    "redirecionar para evil.com.\n\n"
                    "O atacante usa a reputação de 'site.com' para fazer a "
                    "URL parecer segura, mas o destino real é 'evil.com'."
                ),
                findings=["Open Redirect", "Parâmetro de redirecionamento", "Destino malicioso"],
            ),
            QuizQuestion(
                question_id="adv_07",
                difficulty="avancado",
                question_type="multiple_choice",
                url_defanged="hxxps[://]xjk3mf9d2v[.]net/payload",
                url_display="https://xjk3mf9d2v.net/payload",
                question_text="O domínio 'xjk3mf9d2v.net' sugere qual tipo de ameaça?",
                options=[
                    "A) Typosquatting de marca conhecida",
                    "B) DGA (Domain Generation Algorithm) — domínio gerado por malware",
                    "C) Domínio legítimo encurtado",
                    "D) Subdomínio de CDN (Content Delivery Network)",
                ],
                correct_answer="B",
                explanation=(
                    "DGA: 'xjk3mf9d2v' é uma sequência aleatória sem sentido, "
                    "típica de domínios gerados automaticamente por malware.\n\n"
                    "Malware usa DGA para criar milhares de domínios, tornando "
                    "mais difícil bloquear a comunicação com servidores de controle."
                ),
                findings=["Alta entropia", "DGA", "Domínio sem sentido"],
            ),
        ])

    def add_questions_from_dataset(self, urls_malicious: list[str],
                                   urls_safe: list[str]):
        """
        Adiciona questões binárias a partir de listas de URLs.
        URLs maliciosas devem estar no formato defanged.
        URLs seguras podem estar no formato original.
        """
        for url in urls_malicious[:20]:
            self._questions_bank.append(QuizQuestion(
                question_id=f"ds_mal_{uuid.uuid4().hex[:8]}",
                difficulty="iniciante",
                question_type="binary",
                url_defanged=url,
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                url_display=url.replace("hxxp", "http").replace("[://]", "://").replace("[.]", "."),
                correct_answer=False,
                explanation="Esta URL foi identificada como maliciosa em datasets públicos de segurança.",
                findings=["Presente em dataset de ameaças"],
            ))

        for url in urls_safe[:20]:
            self._questions_bank.append(QuizQuestion(
                question_id=f"ds_safe_{uuid.uuid4().hex[:8]}",
                difficulty="iniciante",
                question_type="binary",
                url_defanged=url,
                question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                url_display=url,
                correct_answer=True,
                explanation="Este domínio está presente no Majestic Million (top 1M domínios legítimos).",
                findings=["Domínio reconhecido"],
            ))

    def load_from_dataset_manager(self):
        """
        Gera questões automaticamente a partir dos datasets baixados.
        Usa o DatasetManager para obter amostras de URLs reais.
        """
        try:
            from models.dataset_manager import DatasetManager
            from models.defanger import URLDefanger
            defanger = URLDefanger()

            mgr = DatasetManager()
            mgr.load_all()

            mal_sample = mgr.get_malicious_sample(50)
            leg_sample = mgr.get_legitimate_sample(50)

            added = 0
            for url in mal_sample:
                defanged = defanger.defang(url)
                self._questions_bank.append(QuizQuestion(
                    question_id=f"auto_mal_{uuid.uuid4().hex[:8]}",
                    difficulty=random.choice(["iniciante", "intermediario"]),
                    question_type="binary",
                    url_defanged=defanged,
                    url_display=url,
                    question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                    correct_answer=False,
                    explanation=(
                        "Esta URL foi identificada como MALICIOSA em feeds públicos "
                        "de segurança (URLhaus/OpenPhish/PhishTank). "
                        "Analise o domínio, protocolo e path para identificar os sinais."
                    ),
                    findings=["Presente em feed de ameaças"],
                ))
                added += 1

            for domain in leg_sample:
                self._questions_bank.append(QuizQuestion(
                    question_id=f"auto_safe_{uuid.uuid4().hex[:8]}",
                    difficulty="iniciante",
                    question_type="binary",
                    url_defanged=f"https://{domain}",
                    url_display=f"https://{domain}",
                    question_text="Analise a URL abaixo. Esta URL é SEGURA ou MALICIOSA?",
                    correct_answer=True,
                    explanation=(
                        f"O domínio '{domain}' está presente no ranking dos domínios "
                        "mais populares do mundo (Tranco/Majestic). "
                        "É um endereço bem estabelecido."
                    ),
                    findings=["Domínio no Top 1M mundial"],
                ))
                added += 1

            return added
        except Exception:
            return 0
