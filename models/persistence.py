"""
Persistência de dados — histórico de análises, leaderboard do quiz e feedback.
Armazena em arquivos JSON no diretório data/.
"""

import json
import os
import tempfile
import time
from pathlib import Path

from config.settings import DATA_DIR
from utils.logger import setup_logger

logger = setup_logger("persistence")


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    """
    Lê um JSON do disco, devolvendo `default` se algo der errado.

    O fallback silencioso existe para a UI nunca quebrar por um arquivo
    corrompido — mas a falha É registrada. Antes, um único byte inválido
    zerava histórico/leaderboard/progresso sem deixar rastro nenhum.
    """
    _ensure_data_dir()
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        logger.warning(
            "Falha ao ler %s (%s: %s). Usando valor padrão — "
            "os dados salvos podem estar corrompidos.",
            path.name, type(e).__name__, e,
        )
        return default


# =====================================================================
# Histórico de Análises
# =====================================================================
HISTORY_FILE = DATA_DIR / "analysis_history.json"


def load_history() -> list[dict]:
    """Carrega histórico de análises do disco."""
    return _load_json(HISTORY_FILE, [])


def _atomic_write(path: Path, data):
    """Escrita atômica: grava em arquivo temporário e renomeia."""
    _ensure_data_dir()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, str(path))
    except Exception as e:
        # Não propaga: falhar ao salvar não deve derrubar a UI. Mas registra —
        # uma escrita perdida em silêncio parece perda de dados para o usuário.
        logger.error(
            "Falha ao gravar %s (%s: %s). As alterações não foram salvas.",
            path.name, type(e).__name__, e,
        )
        try:
            os.unlink(tmp)
        except OSError:
            pass


def save_history(history: list[dict]):
    """Salva histórico de análises no disco (últimos 200)."""
    _atomic_write(HISTORY_FILE, history[:200])


def add_history_entry(url_defanged: str, classification: str,
                      emoji: str, score: int):
    """Adiciona uma entrada ao histórico persistido."""
    history = load_history()
    entry = {
        "url": url_defanged[:80],
        "classification": classification,
        "emoji": emoji,
        "score": score,
        "timestamp": time.time(),
    }
    history.insert(0, entry)
    save_history(history)
    return entry


# =====================================================================
# Leaderboard do Quiz
# =====================================================================
LEADERBOARD_FILE = DATA_DIR / "quiz_leaderboard.json"


def load_leaderboard() -> list[dict]:
    """Carrega leaderboard do quiz."""
    return _load_json(LEADERBOARD_FILE, [])


def save_leaderboard_entry(name: str, correct: int, total: int,
                           accuracy: float, difficulty: str,
                           best_streak: int):
    """Salva resultado de uma rodada no leaderboard."""
    _ensure_data_dir()
    lb = load_leaderboard()
    entry = {
        "name": name,
        "correct": correct,
        "total": total,
        "accuracy": round(accuracy, 3),
        "difficulty": difficulty,
        "best_streak": best_streak,
        "timestamp": time.time(),
    }
    lb.insert(0, entry)
    lb = lb[:50]  # Mantém top 50
    _atomic_write(LEADERBOARD_FILE, lb)
    return entry


# =====================================================================
# Feedback do Usuário
# =====================================================================
FEEDBACK_FILE = DATA_DIR / "user_feedback.json"


def load_feedback() -> list[dict]:
    """Carrega feedback dos usuários."""
    return _load_json(FEEDBACK_FILE, [])


def save_feedback(url_defanged: str, classification: str,
                  was_useful: bool, comment: str = ""):
    """Salva feedback de uma análise."""
    _ensure_data_dir()
    fb = load_feedback()
    entry = {
        "url": url_defanged[:80],
        "classification": classification,
        "useful": was_useful,
        "comment": comment[:200],
        "timestamp": time.time(),
    }
    fb.insert(0, entry)
    fb = fb[:500]
    _atomic_write(FEEDBACK_FILE, fb)
    return entry


# =====================================================================
# Estatísticas agregadas
# =====================================================================
STATS_FILE = DATA_DIR / "session_stats.json"


def load_stats() -> dict:
    """Carrega estatísticas agregadas."""
    _ensure_data_dir()
    defaults = {
        "analysis_count": 0, "safe_count": 0,
        "suspicious_count": 0, "malicious_count": 0,
    }
    data = _load_json(STATS_FILE, None)
    if isinstance(data, dict):
        defaults.update(data)
    return defaults


def save_stats(stats: dict):
    """Salva estatísticas agregadas."""
    _atomic_write(STATS_FILE, stats)


# =====================================================================
# Preferências de Interface
# =====================================================================
UI_PREFERENCES_FILE = DATA_DIR / "ui_preferences.json"

_DEFAULT_UI_PREFERENCES = {
    "theme": "dark",
}


def load_ui_preferences() -> dict:
    """Carrega preferências persistidas da interface."""
    _ensure_data_dir()
    preferences = dict(_DEFAULT_UI_PREFERENCES)
    data = _load_json(UI_PREFERENCES_FILE, None)
    if isinstance(data, dict):
        preferences.update(data)
    return preferences


def save_ui_preferences(preferences: dict):
    """Salva preferências persistidas da interface."""
    payload = dict(_DEFAULT_UI_PREFERENCES)
    payload.update(preferences or {})
    _atomic_write(UI_PREFERENCES_FILE, payload)


# =====================================================================
# Progresso de Aprendizado
# =====================================================================
PROGRESS_FILE = DATA_DIR / "learning_progress.json"

_DEFAULT_PROGRESS = {
    "threats_identified": {
        "typosquatting": 0, "dga": 0, "tld_risco": 0,
        "ip_em_url": 0, "http_inseguro": 0, "url_encurtada": 0,
        "subdominio_enganoso": 0, "palavras_gatilho": 0,
        "dominio_falso": 0, "open_redirect": 0,
        "homografo": 0, "url_encoding": 0,
    },
    "quiz_rounds": 0,
    "quiz_best_accuracy": 0.0,
    "scenarios_completed": 0,
    "scenarios_best_accuracy": 0.0,
    "analyses_performed": 0,
    "total_study_time_sec": 0,
}


def load_progress() -> dict:
    """Carrega progresso de aprendizado."""
    _ensure_data_dir()
    progress = dict(_DEFAULT_PROGRESS)
    progress["threats_identified"] = dict(_DEFAULT_PROGRESS["threats_identified"])
    data = _load_json(PROGRESS_FILE, None)
    if isinstance(data, dict):
        progress.update(data)
        # Merge threat keys
        saved_threats = data.get("threats_identified", {})
        progress["threats_identified"] = dict(
            _DEFAULT_PROGRESS["threats_identified"]
        )
        if isinstance(saved_threats, dict):
            progress["threats_identified"].update(saved_threats)
    return progress


def save_progress(progress: dict):
    """Salva progresso de aprendizado."""
    _atomic_write(PROGRESS_FILE, progress)


def increment_threat(threat_type: str):
    """Incrementa contador de um tipo de ameaça identificado."""
    p = load_progress()
    if threat_type in p["threats_identified"]:
        p["threats_identified"][threat_type] += 1
    save_progress(p)


def update_quiz_progress(accuracy: float):
    """Atualiza progresso do quiz."""
    p = load_progress()
    p["quiz_rounds"] = p.get("quiz_rounds", 0) + 1
    if accuracy > p.get("quiz_best_accuracy", 0):
        p["quiz_best_accuracy"] = round(accuracy, 3)
    save_progress(p)


def update_scenario_progress(score: int, total: int):
    """Atualiza progresso dos cenários."""
    p = load_progress()
    p["scenarios_completed"] = p.get("scenarios_completed", 0) + 1
    acc = score / max(1, total)
    if acc > p.get("scenarios_best_accuracy", 0):
        p["scenarios_best_accuracy"] = round(acc, 3)
    save_progress(p)


# =====================================================================
# Sistema de Conquistas (Badges)
# =====================================================================
BADGES_FILE = DATA_DIR / "badges.json"

BADGE_DEFINITIONS = [
    {"id": "first_analysis", "icon": "🔍", "name": "Primeira Análise",
     "desc": "Analisou sua primeira URL"},
    {"id": "ten_analyses", "icon": "🔟", "name": "Analista Dedicado",
     "desc": "Analisou 10 URLs"},
    {"id": "fifty_analyses", "icon": "💯", "name": "Analista Experiente",
     "desc": "Analisou 50 URLs"},
    {"id": "quiz_complete", "icon": "❓", "name": "Quiz Concluído",
     "desc": "Completou uma rodada do quiz"},
    {"id": "quiz_perfect", "icon": "🌟", "name": "Quiz Perfeito",
     "desc": "100% de acerto em uma rodada do quiz"},
    {"id": "quiz_advanced", "icon": "🧠", "name": "Nível Avançado",
     "desc": "Completou quiz no nível avançado"},
    {"id": "scenario_complete", "icon": "🎭", "name": "Simulação Completa",
     "desc": "Completou uma simulação de cenários"},
    {"id": "scenario_ace", "icon": "🏆", "name": "Detetive Digital",
     "desc": "80%+ de acerto nos cenários"},
    {"id": "glossary_explorer", "icon": "📖", "name": "Estudioso",
     "desc": "Visitou o glossário"},
    {"id": "anatomy_first", "icon": "🔬", "name": "Anatomista",
     "desc": "Analisou anatomia de uma URL"},
]


def load_badges() -> list[str]:
    """Carrega lista de IDs de badges conquistados."""
    return _load_json(BADGES_FILE, [])


def unlock_badge(badge_id: str) -> bool:
    """Desbloqueia um badge. Retorna True se foi novo."""
    badges = load_badges()
    if badge_id in badges:
        return False
    badges.append(badge_id)
    _atomic_write(BADGES_FILE, badges)
    return True


def get_badge_info(badge_id: str) -> dict | None:
    """Retorna informações de um badge pelo ID."""
    for b in BADGE_DEFINITIONS:
        if b["id"] == badge_id:
            return b
    return None
