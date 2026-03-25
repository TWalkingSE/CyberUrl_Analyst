"""
Internacionalização (i18n) — Infraestrutura de tradução.
Suporta PT-BR (padrão), EN e ES.
As views podem usar tr("chave") para obter o texto no idioma ativo.
"""

import json
import threading
from pathlib import Path
from typing import Optional

_lock = threading.Lock()
_CURRENT_LANG = "pt"

# Carrega traduções de arquivos JSON externos (locales/)
_LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


def _load_translations() -> dict:
    """Carrega traduções dos arquivos JSON em locales/."""
    translations: dict[str, dict] = {}
    if _LOCALES_DIR.is_dir():
        for f in _LOCALES_DIR.glob("*.json"):
            lang = f.stem
            try:
                translations[lang] = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                pass
    return translations


_TRANSLATIONS = _load_translations()

AVAILABLE_LANGUAGES = {
    "pt": "Português (BR)",
    "en": "English",
    "es": "Español",
}


def tr(key: str, lang: Optional[str] = None) -> str:
    """
    Retorna texto traduzido para a chave dada.
    Usa o idioma ativo ou o especificado.
    Fallback: retorna a chave se não encontrada.
    """
    with _lock:
        cur = lang or _CURRENT_LANG
    translations = _TRANSLATIONS.get(cur, _TRANSLATIONS.get("pt", {}))
    return translations.get(key, _TRANSLATIONS.get("pt", {}).get(key, key))


def set_language(lang: str):
    """Define o idioma ativo (thread-safe)."""
    global _CURRENT_LANG
    with _lock:
        if lang in _TRANSLATIONS:
            _CURRENT_LANG = lang


def get_language() -> str:
    """Retorna o idioma ativo."""
    with _lock:
        return _CURRENT_LANG
