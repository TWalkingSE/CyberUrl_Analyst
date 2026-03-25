"""
URLDefanger — Converte URLs para formato não-clicável (defanged).
TODA URL suspeita/maliciosa DEVE passar por aqui antes de ir para a View.

Formato defanged:
  hxxps[://]example[.]com/path

A camada View NUNCA recebe URLs no formato original se classificadas
como suspeitas ou maliciosas.
"""

import re


class URLDefanger:
    """Converte URLs entre formato original e defanged (não-clicável)."""

    @staticmethod
    def defang(url: str) -> str:
        """
        Converte URL para formato não-clicável.

        Regras:
        - 'https://' → 'hxxps[://]'
        - 'http://'  → 'hxxp[://]'
        - '.' no domínio → '[.]'  (pontos no path são preservados)

        Exemplo:
            https://paypal-security.fake.com/login.php
            → hxxps[://]paypal-security[.]fake[.]com/login.php
        """
        if not url:
            return url

        # Separar protocolo do resto ANTES de substituir
        scheme = ""
        rest = url
        for proto, defanged_proto in [
            ("https://", "hxxps[://]"),
            ("http://", "hxxp[://]"),
            ("ftp://", "fxp[://]"),
        ]:
            if rest.lower().startswith(proto):
                scheme = defanged_proto
                rest = rest[len(proto):]
                break

        # Separar domínio do path (primeiro / após o domínio)
        if "/" in rest:
            domain_part, path_part = rest.split("/", 1)
            domain_part = domain_part.replace(".", "[.]")
            return scheme + domain_part + "/" + path_part
        else:
            return scheme + rest.replace(".", "[.]")

    @staticmethod
    def refang(defanged_url: str) -> str:
        """
        Reverte defang para formato original.
        USO INTERNO APENAS — NUNCA expor na UI.
        """
        if not defanged_url:
            return defanged_url

        result = defanged_url.replace("hxxps[://]", "https://")
        result = result.replace("hxxp[://]", "http://")
        result = result.replace("fxp[://]", "ftp://")
        result = result.replace("[.]", ".")
        return result

    @staticmethod
    def is_defanged(url: str) -> bool:
        """Verifica se uma URL já está no formato defanged."""
        return bool(
            re.search(r'hxxps?\[://\]', url) or
            '[.]' in url
        )
