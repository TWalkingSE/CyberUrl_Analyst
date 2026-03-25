"""
Página Quiz Interativo — Treinamento gamificado com leaderboard.
"""

import time

import streamlit as st

from config.settings import QUIZ_QUESTIONS_PER_ROUND
from models.quiz_engine import QuizEngine
from models.persistence import load_leaderboard, save_leaderboard_entry, update_quiz_progress, unlock_badge
from views.helpers import T, render_browser_bar


def page_quiz():
    st.title(f"❓ {T('nav.quiz')}")

    if st.session_state.quiz_engine is None:
        st.session_state.quiz_engine = QuizEngine()
        try:
            st.session_state.quiz_engine.load_from_dataset_manager()
        except Exception:
            pass

    engine = st.session_state.quiz_engine

    c1, c2 = st.columns([3, 1])
    with c2:
        diff = st.selectbox(
            T("quiz.level"),
            ["Auto", "Iniciante", "Intermediário", "Avançado"],
            key="q_diff",
        )
    dmap = {
        "Iniciante": "iniciante",
        "Intermediário": "intermediario",
        "Avançado": "avancado",
    }
    if diff == "Auto":
        suggested = engine.get_suggested_difficulty()
        _LABELS = {"iniciante": "Iniciante", "intermediario": "Intermediário", "avancado": "Avançado"}
        with c2:
            st.caption(f"🎯 Sugerido: {_LABELS.get(suggested, suggested)}")
        diff = _LABELS.get(suggested, "Iniciante")

    stats = engine.get_statistics()
    m1, m2, m3 = st.columns(3)
    m1.metric("🌟 Acertos", stats.correct_answers)
    m2.metric("🔥 Sequência", stats.current_streak)
    m3.metric("🎯 Precisão", f"{int(stats.accuracy * 100)}%")
    st.progress(
        min(st.session_state.quiz_q_num, QUIZ_QUESTIONS_PER_ROUND)
        / QUIZ_QUESTIONS_PER_ROUND
    )

    if not st.session_state.quiz_running:
        ca, cb = st.columns(2)
        with ca:
            if st.button(
                f"▶️ {T('quiz.btn_start')}",
                type="primary", key="btn_qs",
            ):
                engine.reset_statistics()
                st.session_state.quiz_q_num = 1
                st.session_state.quiz_running = True
                st.session_state.quiz_answered = False
                st.session_state.quiz_question = engine.generate_question(
                    dmap[diff]
                )
                st.rerun()
        with cb:
            if st.button("🔄 Resetar", key="btn_qr"):
                engine.reset_statistics()
                st.session_state.quiz_q_num = 0
                st.session_state.quiz_running = False
                st.session_state.quiz_answered = False
                st.rerun()

        # Leaderboard
        lb = load_leaderboard()
        if lb:
            st.divider()
            st.subheader("🏅 Leaderboard")
            for i, e in enumerate(
                sorted(lb, key=lambda x: x.get("accuracy", 0), reverse=True)[:10],
                1,
            ):
                ts = time.strftime(
                    "%d/%m", time.localtime(e.get("timestamp", 0))
                )
                st.markdown(
                    f"**{i}.** {e.get('name', 'Anon')} — "
                    f"{int(e.get('accuracy', 0) * 100)}% "
                    f"({e.get('correct', 0)}/{e.get('total', 0)}) — "
                    f"{e.get('difficulty', '')} — {ts}"
                )
        return

    if st.session_state.quiz_q_num > QUIZ_QUESTIONS_PER_ROUND:
        _render_quiz_results(engine, dmap[diff])
        return

    q = st.session_state.quiz_question
    if q is None:
        q = engine.generate_question(dmap[diff])
        st.session_state.quiz_question = q

    st.markdown(
        f"**Questão {st.session_state.quiz_q_num}/{QUIZ_QUESTIONS_PER_ROUND}**"
        f" — {q.difficulty.capitalize()}"
    )
    if q.scenario_context:
        st.markdown(f"> {q.scenario_context}")
    render_browser_bar(q.url_display or q.url_defanged)
    st.markdown(q.question_text)

    if not st.session_state.quiz_answered:
        _render_quiz_input(q, engine, dmap[diff])

    if st.session_state.quiz_answered and "_qfb" in st.session_state:
        fb = st.session_state._qfb
        if fb.is_correct:
            st.success(f"✅ {T('quiz.correct')}\n\n{fb.explanation}")
        else:
            st.error(f"❌ {T('quiz.incorrect')}\n\n{fb.explanation}")
        if fb.tip:
            st.info(fb.tip)
        if st.button(f"{T('quiz.btn_next')} →", key="btn_nq"):
            st.session_state.quiz_q_num += 1
            st.session_state.quiz_answered = False
            st.session_state.quiz_question = engine.generate_question(
                dmap[diff]
            )
            del st.session_state._qfb
            st.rerun()


def _render_quiz_input(q, engine, diff):
    """Renderiza controles de resposta do quiz."""
    if q.question_type == "binary":
        ca, cb = st.columns(2)
        with ca:
            if st.button("🟢 SEGURA", key="qs", width="stretch"):
                st.session_state._qfb = engine.check_answer(
                    q.question_id, True
                )
                st.session_state.quiz_answered = True
                st.rerun()
        with cb:
            if st.button("🔴 MALICIOSA", key="qm", width="stretch"):
                st.session_state._qfb = engine.check_answer(
                    q.question_id, False
                )
                st.session_state.quiz_answered = True
                st.rerun()
    elif q.question_type == "multiple_choice":
        for i, opt in enumerate(q.options):
            if st.button(opt, key=f"qmc_{i}"):
                st.session_state._qfb = engine.check_answer(
                    q.question_id, chr(65 + i)
                )
                st.session_state.quiz_answered = True
                st.rerun()
    elif q.question_type == "checklist":
        sel = [o for o in q.options if st.checkbox(o, key=f"qcl_{o}")]
        if st.button("✅ Confirmar", key="qcl_ok"):
            st.session_state._qfb = engine.check_answer(q.question_id, sel)
            st.session_state.quiz_answered = True
            st.rerun()


def _render_quiz_results(engine, difficulty):
    """Renderiza resultado final do quiz."""
    st.subheader(f"🏆 {T('quiz.final')}")
    stats = engine.get_statistics()
    st.metric("Acertos", f"{stats.correct_answers}/{stats.total_questions}")
    st.metric("Precisão", f"{int(stats.accuracy * 100)}%")
    st.metric("Melhor Sequência", stats.best_streak)

    # Salvar progresso de aprendizado e badges
    update_quiz_progress(stats.accuracy)
    unlock_badge("quiz_complete")
    if stats.accuracy >= 1.0:
        unlock_badge("quiz_perfect")
    if difficulty == "avancado":
        unlock_badge("quiz_advanced")

    if stats.accuracy >= 0.9:
        st.success("🌟 Excelente!")
    elif stats.accuracy >= 0.7:
        st.info("👍 Bom trabalho!")
    elif stats.accuracy >= 0.5:
        st.warning("📚 Razoável.")
    else:
        st.error("💪 Não desanime!")

    # Salvar no leaderboard
    name = st.text_input(
        "Seu nome para o leaderboard:", value="Jogador", key="lb_name",
    )
    if st.button("💾 Salvar no Leaderboard", key="btn_lb_save"):
        save_leaderboard_entry(
            name, stats.correct_answers, stats.total_questions,
            stats.accuracy, difficulty, stats.best_streak,
        )
        st.success("Salvo!")

    # Exportar resultado
    csv_data = "Acertos,Total,Precisão,Sequência,Dificuldade\n"
    csv_data += (
        f"{stats.correct_answers},{stats.total_questions},"
        f"{int(stats.accuracy * 100)}%,{stats.best_streak},{difficulty}\n"
    )
    st.download_button(
        "📥 Exportar Resultado CSV",
        csv_data, "quiz_resultado.csv", "text/csv",
    )

    st.session_state.quiz_running = False
