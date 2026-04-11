"""
Sanitização de entradas do usuário.
Detecta dados pessoais, limpa entradas e garante segurança antes do processamento.
"""

import re
import hashlib
from dataclasses import dataclass, field


@dataclass
class SanitizationResult:
    """Resultado da sanitização de uma entrada."""
    original_input: str
    sanitized_input: str
    is_valid_url: bool
    personal_data_found: bool
    warnings: list[str] = field(default_factory=list)
    removed_items: list[str] = field(default_factory=list)


# === Padrões regex para dados pessoais ===
_EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
)
_CPF_PATTERN = re.compile(
    r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',
)
_TOKEN_PATTERN = re.compile(
    r'(?:token|session|sid|jwt|auth|apikey|secret|password|pwd|passwd)'
    r'[=:]\'?\s*[A-Za-z0-9_\-\.]{16,}',
    re.IGNORECASE,
)
_CREDENTIAL_PATTERN = re.compile(
    r'(?:user|username|login|email|senha|pass)[:=][^\s&]+',
    re.IGNORECASE,
)

# === Padrão básico de URL ===
_URL_PATTERN = re.compile(
    r'^https?://[^\s/$.?#].[^\s]*$',
    re.IGNORECASE,
)

_URL_LOOSE_PATTERN = re.compile(
    r'^(?:https?://|hxxps?\[://\])?'
    r'(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}'
    r'(?:[/\?#].*)?$',
    re.IGNORECASE,
)


def sanitize_input(raw_input: str) -> SanitizationResult:
    """
    Sanitiza a entrada do usuário antes de qualquer processamento.

    1. Remove espaços em branco nas extremidades.
    2. Detecta e remove dados pessoais (e-mail, CPF, tokens, credenciais).
    3. Valida formato básico de URL.
    4. Retorna resultado com warnings e itens removidos.
    """
    warnings = []
    removed_items = []
    personal_data_found = False

    # Passo 1: Limpeza básica
    cleaned = raw_input.strip()

    # Passo 2: Detecção de dados pessoais
    for label, pattern in [
        ("E-mail", _EMAIL_PATTERN),
        ("CPF", _CPF_PATTERN),
        ("Token/Credencial", _TOKEN_PATTERN),
        ("Credencial de acesso", _CREDENTIAL_PATTERN),
    ]:
        matches = pattern.findall(cleaned)
        if matches:
            personal_data_found = True
            for match in matches:
                removed_items.append(f"{label}: {_mask(match)}")
                cleaned = cleaned.replace(match, f"[{label.upper()}_REMOVIDO]")
            warnings.append(
                f"⚠️ {label} detectado(a) na URL. "
                f"Por segurança, os dados foram removidos antes da análise."
            )

    # Passo 3: Validação de formato
    is_valid = bool(
        _URL_PATTERN.match(cleaned) or _URL_LOOSE_PATTERN.match(cleaned)
    )
    # Adiciona esquema padrão se ausente (necessário para APIs externas)
    if is_valid and cleaned and not cleaned.startswith(("http://", "https://", "hxxp", "ftp://")):
        cleaned = f"https://{cleaned}"
        warnings.append(
            "ℹ️ Protocolo não especificado. Adicionado 'https://' automaticamente."
        )
    elif not is_valid and cleaned:
        if not cleaned.startswith(("http://", "https://", "hxxp", "ftp://")):
            test = f"https://{cleaned}"
            if _URL_PATTERN.match(test) or _URL_LOOSE_PATTERN.match(test):
                cleaned = test
                is_valid = True
                warnings.append(
                    "ℹ️ Protocolo não especificado. Adicionado 'https://' automaticamente."
                )

    if not is_valid and cleaned:
        warnings.append(
            "⚠️ A entrada não parece ser uma URL válida. "
            "Verifique o formato (ex.: https://exemplo.com)."
        )

    return SanitizationResult(
        original_input=raw_input,
        sanitized_input=cleaned,
        is_valid_url=is_valid,
        personal_data_found=personal_data_found,
        warnings=warnings,
        removed_items=removed_items,
    )


def hash_url(url: str) -> str:
    """Retorna hash SHA-256 da URL para uso em logs seguros."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _mask(value: str) -> str:
    """Mascara parcialmente um valor sensível para exibição em warnings."""
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-3:]
