"""
Helpers puros de URL compartilhados entre os modelos.

Existe para eliminar implementações duplicadas que divergiam entre si —
notadamente a detecção de IP, que em um módulo validava os octetos e em
outro não, e a entropia de Shannon, escrita duas vezes.

Sem dependência de UI, rede ou estado global.
"""

from __future__ import annotations

import ipaddress
import math
import re

# Quatro grupos de 1–3 dígitos. É só a forma: os octetos são validados
# depois por `ipaddress`, senão "999.999.999.999" passaria como IP.
IPV4_PATTERN = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')

# Sequências percent-encoded (%2F, %3A...). Usado para medir ofuscação.
PERCENT_ENCODING_PATTERN = re.compile(r'%[0-9A-Fa-f]{2}')


def is_ipv4_address(hostname: str) -> bool:
    """
    True se `hostname` for um IPv4 válido.

    Valida os octetos além do formato — `999.999.999.999` tem a forma certa
    mas não é um endereço válido.
    """
    if not hostname or not IPV4_PATTERN.match(hostname):
        return False
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def shannon_entropy(text: str) -> float:
    """
    Entropia de Shannon (bits por caractere) da string.

    Strings aleatórias (típicas de domínios gerados por DGA) pontuam alto;
    palavras naturais pontuam baixo.
    """
    if not text:
        return 0.0
    length = len(text)
    freq: dict[str, int] = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1
    entropy = 0.0
    for count in freq.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    return entropy


def extract_domain(url: str) -> str:
    """
    Extrai o host de uma URL por manipulação de string, sem tldextract.

    Deliberadamente rápido e tolerante: é usado para indexar datasets com
    milhões de linhas, onde o custo do parsing completo não se justifica.
    Para análise de ameaça use `models.url_parser.URLParser`, que resolve
    o sufixo público corretamente.
    """
    try:
        url = url.split("://", 1)[-1]
        domain = url.split("/", 1)[0]
        domain = domain.split(":")[0]  # Remove porta
        return domain.lower()
    except Exception:
        return ""


def count_percent_encoding(text: str) -> int:
    """Conta as sequências percent-encoded na string."""
    return len(PERCENT_ENCODING_PATTERN.findall(text))
