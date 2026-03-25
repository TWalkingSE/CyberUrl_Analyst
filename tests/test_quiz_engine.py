"""Testes unitários para o módulo QuizEngine."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from models.quiz_engine import QuizEngine


class TestQuizEngine(unittest.TestCase):
    """Testes para QuizEngine."""

    def setUp(self):
        self.engine = QuizEngine()

    def test_generate_question_iniciante(self):
        q = self.engine.generate_question("iniciante")
        self.assertIsNotNone(q)
        self.assertEqual(q.difficulty, "iniciante")
        self.assertTrue(q.question_id)
        self.assertTrue(q.url_defanged)
        self.assertTrue(q.question_text)

    def test_generate_question_intermediario(self):
        q = self.engine.generate_question("intermediario")
        self.assertEqual(q.difficulty, "intermediario")

    def test_generate_question_avancado(self):
        q = self.engine.generate_question("avancado")
        self.assertEqual(q.difficulty, "avancado")

    def test_generate_question_invalid_difficulty(self):
        q = self.engine.generate_question("nonexistent")
        self.assertIsNotNone(q)
        self.assertEqual(q.difficulty, "iniciante")

    def test_check_answer_correct(self):
        q = self.engine.generate_question("iniciante")
        feedback = self.engine.check_answer(q.question_id, q.correct_answer)
        self.assertTrue(feedback.is_correct)
        self.assertTrue(feedback.explanation)

    def test_check_answer_wrong(self):
        q = self.engine.generate_question("iniciante")
        wrong_answer = not q.correct_answer if isinstance(q.correct_answer, bool) else "Z"
        feedback = self.engine.check_answer(q.question_id, wrong_answer)
        self.assertFalse(feedback.is_correct)

    def test_check_answer_nonexistent_question(self):
        feedback = self.engine.check_answer("nonexistent", True)
        self.assertFalse(feedback.is_correct)

    def test_statistics_update(self):
        q = self.engine.generate_question("iniciante")
        self.engine.check_answer(q.question_id, q.correct_answer)

        stats = self.engine.get_statistics()
        self.assertEqual(stats.total_questions, 1)
        self.assertEqual(stats.correct_answers, 1)
        self.assertGreater(stats.accuracy, 0)

    def test_statistics_streak(self):
        for _ in range(3):
            q = self.engine.generate_question("iniciante")
            self.engine.check_answer(q.question_id, q.correct_answer)

        stats = self.engine.get_statistics()
        self.assertEqual(stats.current_streak, 3)
        self.assertEqual(stats.best_streak, 3)

    def test_reset_statistics(self):
        q = self.engine.generate_question("iniciante")
        self.engine.check_answer(q.question_id, q.correct_answer)
        self.engine.reset_statistics()

        stats = self.engine.get_statistics()
        self.assertEqual(stats.total_questions, 0)
        self.assertEqual(stats.correct_answers, 0)

    def test_suggested_difficulty_starts_iniciante(self):
        self.assertEqual(self.engine.get_suggested_difficulty(), "iniciante")

    def test_checklist_answer(self):
        q = self.engine.generate_question("avancado")
        if q.question_type == "checklist":
            feedback = self.engine.check_answer(q.question_id, q.correct_answer)
            self.assertTrue(feedback.is_correct)
            self.assertGreaterEqual(feedback.partial_score, 0.8)

    def test_add_questions_from_dataset(self):
        initial_count = len(self.engine._questions_bank)
        self.engine.add_questions_from_dataset(
            urls_malicious=["hxxp[://]evil[.]com/bad"],
            urls_safe=["https://google.com"],
        )
        self.assertGreater(len(self.engine._questions_bank), initial_count)


if __name__ == "__main__":
    unittest.main()
