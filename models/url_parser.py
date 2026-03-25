"""
URLParser — Decomposição anatômica de URLs.
Responsabilidade ÚNICA: parsing. Não faz análise de ameaça.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs

import tldextract


@dataclass
class URLComponents:
    """Componentes anatômicos de uma URL."""
    raw_url: str
    scheme: str = ""
    subdomain: str = ""
    domain: str = ""           # SLD — Second-Level Domain
    tld: str = ""              # Top-Level Domain
    registered_domain: str = ""  # domain + tld
    port: str = ""
    path: str = ""
    query: str = ""
    query_params: dict = field(default_factory=dict)
    fragment: str = ""
    is_ip: bool = False
    ip_address: str = ""


@dataclass
class URLPart:
    """
    Uma parte individual da URL para visualização com código de cores.
    Usado pelo módulo de Anatomia da URL.
    """
    text: str
    part_type: str       # scheme, subdomain, domain, tld, path, query, fragment, port
    color: str           # código hex da cor
    tooltip: str         # explicação educativa da parte


# === Cores para cada parte da URL ===
PART_COLORS = {
    "scheme":    "#4CAF50",   # Verde
    "subdomain": "#2196F3",  # Azul
    "domain":    "#FFC107",  # Amarelo/Dourado
    "tld":       "#FF9800",  # Laranja
    "port":      "#9C27B0",  # Roxo
    "path":      "#F44336",  # Vermelho
    "query":     "#F44336",  # Vermelho
    "fragment":  "#F44336",  # Vermelho
    "separator": "#9E9E9E",  # Cinza
}

# === Tooltips educativos ===
PART_TOOLTIPS = {
    "scheme": (
        "PROTOCOLO — Define como seu navegador se comunica com o servidor.\n"
        "• https:// = conexão criptografada (cadeado no navegador)\n"
        "• http:// = conexão sem criptografia (INSEGURO para dados pessoais)\n"
        "Analogia: é como escolher entre enviar uma carta em envelope "
        "lacrado (HTTPS) ou em cartão postal aberto (HTTP)."
    ),
    "subdomain": (
        "SUBDOMÍNIO — Prefixo opcional antes do domínio principal.\n"
        "• 'www' é o subdomínio mais comum e geralmente inofensivo.\n"
        "• Subdomínios longos ou com palavras como 'secure', 'login' "
        "podem ser tentativas de enganar.\n"
        "Analogia: é como o número do apartamento — indica uma "
        "divisão dentro do endereço principal."
    ),
    "domain": (
        "DOMÍNIO PRINCIPAL (SLD) — O nome do site, a parte mais importante.\n"
        "• É aqui que você deve prestar mais atenção!\n"
        "• Verifique se o nome está correto (ex.: 'google' vs 'g00gle').\n"
        "Analogia: é como o nome da rua no endereço postal — "
        "identifica o destino real."
    ),
    "tld": (
        "TLD (Top-Level Domain) — A extensão do domínio (.com, .org, .br).\n"
        "• TLDs comuns (.com, .org, .gov) são mais regulamentados.\n"
        "• TLDs exóticos (.tk, .xyz, .top) são frequentemente usados "
        "em sites maliciosos por serem gratuitos ou baratos.\n"
        "Analogia: é como o CEP — indica a 'região' do endereço."
    ),
    "port": (
        "PORTA — Número que indica qual 'porta' do servidor acessar.\n"
        "• Portas padrão (80 para HTTP, 443 para HTTPS) são omitidas.\n"
        "• Portas incomuns podem indicar servidores não-padrão.\n"
        "Analogia: é como o número da sala em um prédio comercial."
    ),
    "path": (
        "CAMINHO (Path) — Indica a página ou recurso específico no site.\n"
        "• Paths com 'login', 'verify', 'account' em sites desconhecidos "
        "são sinais de alerta.\n"
        "• Extensões como .php expostas podem indicar servidor mal configurado.\n"
        "Analogia: é como o andar e sala dentro de um prédio."
    ),
    "query": (
        "QUERY STRING — Parâmetros enviados ao servidor após o '?'.\n"
        "• Podem conter dados de busca legítimos (ex.: ?q=python).\n"
        "• Mas também podem conter códigos de rastreamento, tokens "
        "de sessão ou dados pessoais.\n"
        "⚠️ NUNCA compartilhe URLs com query strings que contenham "
        "dados sensíveis!"
    ),
    "fragment": (
        "FRAGMENTO — Seção específica da página (após o '#').\n"
        "• Geralmente inofensivo — indica uma âncora na página.\n"
        "• Não é enviado ao servidor, apenas usado pelo navegador.\n"
        "Analogia: é como um marcador de página em um livro."
    ),
}


class URLParser:
    """
    Decompõe uma URL em seus componentes anatômicos.
    Responsabilidade ÚNICA: parsing. Não faz análise de ameaça.
    """

    # Regex para detectar IP no domínio
    _IP_PATTERN = re.compile(
        r'^(\d{1,3}\.){3}\d{1,3}$'
    )

    def parse(self, raw_url: str) -> URLComponents:
        """
        Decompõe a URL em componentes estruturados.
        Retorna dataclass URLComponents com todos os campos preenchidos.
        """
        components = URLComponents(raw_url=raw_url)

        if not raw_url or not raw_url.strip():
            return components

        url = raw_url.strip()

        # Esquemas não-navegáveis (data:, javascript:) — retorna apenas scheme
        url_lower = url.lower()
        if url_lower.startswith(("data:", "javascript:")):
            components.scheme = url.split(":", 1)[0]
            components.path = url.split(":", 1)[1] if ":" in url else ""
            return components

        # Adiciona esquema padrão se ausente (para parsing correto)
        if not re.match(r'^[a-zA-Z]+://', url):
            url = f"https://{url}"

        # Parsing com urllib
        parsed = urlparse(url)
        components.scheme = parsed.scheme or ""
        components.path = parsed.path or ""
        components.query = parsed.query or ""
        components.fragment = parsed.fragment or ""
        try:
            components.port = str(parsed.port) if parsed.port else ""
        except ValueError:
            components.port = ""

        # Parse query params
        if parsed.query:
            try:
                components.query_params = parse_qs(parsed.query)
            except Exception:
                components.query_params = {}

        # Extração de domínio com tldextract
        extracted = tldextract.extract(url)
        components.subdomain = extracted.subdomain or ""
        components.domain = extracted.domain or ""
        components.tld = extracted.suffix or ""
        if hasattr(extracted, 'top_domain_under_public_suffix'):
            components.registered_domain = extracted.top_domain_under_public_suffix or ""
        else:
            components.registered_domain = extracted.registered_domain or ""

        # Detecção de IP (com validação de octetos via stdlib)
        hostname = parsed.hostname or ""
        if self._IP_PATTERN.match(hostname):
            try:
                ipaddress.ip_address(hostname)
                components.is_ip = True
                components.ip_address = hostname
                components.domain = hostname
                components.subdomain = ""
                components.tld = ""
            except ValueError:
                pass  # Formato IP mas octetos inválidos (e.g. 999.999.999.999)

        return components

    def get_visual_breakdown(self, raw_url: str) -> list[URLPart]:
        """
        Retorna lista de partes da URL com texto, tipo, cor e tooltip educativo.
        Usado para renderização visual no módulo de Anatomia.
        """
        components = self.parse(raw_url)
        parts: list[URLPart] = []

        if not raw_url or not raw_url.strip():
            return parts

        # Esquema (protocolo)
        if components.scheme:
            parts.append(URLPart(
                text=f"{components.scheme}://",
                part_type="scheme",
                color=PART_COLORS["scheme"],
                tooltip=PART_TOOLTIPS["scheme"],
            ))

        # Subdomínio
        if components.subdomain:
            parts.append(URLPart(
                text=f"{components.subdomain}.",
                part_type="subdomain",
                color=PART_COLORS["subdomain"],
                tooltip=PART_TOOLTIPS["subdomain"],
            ))

        # Domínio principal (ou IP)
        if components.is_ip:
            parts.append(URLPart(
                text=components.ip_address,
                part_type="domain",
                color=PART_COLORS["domain"],
                tooltip=(
                    "ENDEREÇO IP — Este site usa um número IP em vez de um nome.\n"
                    "⚠️ Sites legítimos NUNCA pedem que você acesse pelo IP.\n"
                    "Analogia: é como receber um convite com coordenadas GPS "
                    "em vez do nome do lugar."
                ),
            ))
        elif components.domain:
            parts.append(URLPart(
                text=components.domain,
                part_type="domain",
                color=PART_COLORS["domain"],
                tooltip=PART_TOOLTIPS["domain"],
            ))

        # TLD
        if components.tld:
            parts.append(URLPart(
                text=f".{components.tld}",
                part_type="tld",
                color=PART_COLORS["tld"],
                tooltip=PART_TOOLTIPS["tld"],
            ))

        # Porta
        if components.port:
            parts.append(URLPart(
                text=f":{components.port}",
                part_type="port",
                color=PART_COLORS["port"],
                tooltip=PART_TOOLTIPS["port"],
            ))

        # Path
        if components.path and components.path != "/":
            parts.append(URLPart(
                text=components.path,
                part_type="path",
                color=PART_COLORS["path"],
                tooltip=PART_TOOLTIPS["path"],
            ))

        # Query string
        if components.query:
            parts.append(URLPart(
                text=f"?{components.query}",
                part_type="query",
                color=PART_COLORS["query"],
                tooltip=PART_TOOLTIPS["query"],
            ))

        # Fragment
        if components.fragment:
            parts.append(URLPart(
                text=f"#{components.fragment}",
                part_type="fragment",
                color=PART_COLORS["fragment"],
                tooltip=PART_TOOLTIPS["fragment"],
            ))

        return parts
