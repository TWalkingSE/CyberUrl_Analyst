"""
HeuristicAnalyzer — Análise baseada em features extraídas da URL.
Não acessa rede. Não exibe nada. Apenas calcula score de ameaça.
"""

import base64 as b64lib
import math
import re
from dataclasses import dataclass, field
from urllib.parse import unquote

from config.settings import (
    HEURISTIC_WEIGHTS,
    TRIGGER_WORDS,
    URL_SHORTENERS,
    HIGH_RISK_TLDS,
    COMMON_TLDS,
    SCORE_SAFE_MAX,
    SCORE_SUSPICIOUS_MAX,
    KEYBOARD_NEIGHBORS,
    DANGEROUS_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    REDIRECT_PARAMS,
    SUSPICIOUS_PORTS,
)
from models.url_parser import URLComponents


@dataclass
class Finding:
    """Um achado individual da análise heurística."""
    factor: str            # Identificador do fator (ex.: "ip_instead_of_domain")
    severity: str          # "critical", "warning", "info", "safe"
    weight: int            # Peso no score final
    title: str             # Título curto (ex.: "IP em vez de domínio")
    explanation: str       # Explicação didática completa
    analogy: str           # Analogia do cotidiano
    tip: str               # Dica de proteção
    confidence: float = 1.0  # Confiança 0.0–1.0 na detecção


@dataclass
class AnalysisResult:
    """Resultado completo da análise heurística."""
    score: int                            # 0–100
    classification: str                   # "safe", "suspicious", "malicious"
    classification_label: str             # "Seguro", "Suspeito", "Malicioso"
    classification_emoji: str             # 🟢, 🟡, 🔴
    findings: list[Finding] = field(default_factory=list)
    features: dict = field(default_factory=dict)


class HeuristicAnalyzer:
    """
    Analisa features extraídas da URL para calcular score de ameaça.
    Não acessa rede. Não exibe nada. Apenas calcula.
    """

    # Tabela expandida de homógrafos Unicode (confusables)
    _HOMOGLYPHS = {
        # Cirílico → Latim
        'а': 'a', 'в': 'b', 'с': 'c', 'ԁ': 'd', 'е': 'e',
        'ғ': 'f', 'ɡ': 'g', 'һ': 'h', 'і': 'i', 'ј': 'j',
        'к': 'k', 'ӏ': 'l', 'м': 'm', 'п': 'n', 'о': 'o',
        'р': 'p', 'ԛ': 'q', 'г': 'r', 'ѕ': 's', 'т': 't',
        'у': 'y', 'ѵ': 'v', 'ԝ': 'w', 'х': 'x', 'ү': 'y',
        'з': 'z',
        # Grego → Latim
        'α': 'a', 'β': 'b', 'ε': 'e', 'η': 'n', 'ι': 'i',
        'κ': 'k', 'ν': 'v', 'ο': 'o', 'ρ': 'p', 'τ': 't',
        'υ': 'u', 'χ': 'x',
        # Unicode especiais → Latim
        'ɑ': 'a', 'ℓ': 'l', 'ⅰ': 'i', 'ⅿ': 'm',
        'ᴏ': 'o', 'ᴜ': 'u', 'ꮪ': 's', 'ꭰ': 'a',
        'ⅾ': 'd', 'ⅽ': 'c', 'ℊ': 'g', 'ℎ': 'h',
        'ℯ': 'e', 'ℴ': 'o', 'ℬ': 'B', 'ℰ': 'E',
        'ℱ': 'F', 'ℋ': 'H', 'ℐ': 'I', 'ℒ': 'L',
        'ℳ': 'M', 'ℛ': 'R',
        # Números / letras confusas
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
    }

    # Marcas conhecidas para detecção de typosquatting
    _KNOWN_BRANDS = [
        "google", "facebook", "amazon", "apple", "microsoft",
        "netflix", "paypal", "instagram", "twitter", "linkedin",
        "whatsapp", "telegram", "spotify", "dropbox", "github",
        "yahoo", "outlook", "hotmail", "gmail", "icloud",
        "bancodobrasil", "itau", "bradesco", "santander", "nubank",
        "caixa", "bb", "mercadolivre", "mercadopago", "picpay",
    ]

    def analyze(self, components: URLComponents) -> AnalysisResult:
        """
        Analisa os componentes da URL e retorna resultado com score,
        classificação e lista de findings com explicações didáticas.
        """
        features = self.extract_features(components)
        findings = self._evaluate_features(features, components)

        # Calcula score total (capped em 100)
        raw_score = sum(f.weight for f in findings if f.severity != "safe")
        score = min(100, max(0, raw_score))

        # Classificação
        if score <= SCORE_SAFE_MAX:
            classification = "safe"
            label = "Seguro"
            emoji = "🟢"
        elif score <= SCORE_SUSPICIOUS_MAX:
            classification = "suspicious"
            label = "Suspeito"
            emoji = "🟡"
        else:
            classification = "malicious"
            label = "Malicioso"
            emoji = "🔴"

        return AnalysisResult(
            score=score,
            classification=classification,
            classification_label=label,
            classification_emoji=emoji,
            findings=findings,
            features=features,
        )

    def extract_features(self, components: URLComponents) -> dict:
        """
        Extrai features quantificáveis da URL para análise.
        Retorna dicionário com todas as features detectadas.
        """
        full_url = components.raw_url
        domain = components.domain.lower() if components.domain else ""
        subdomain = components.subdomain.lower() if components.subdomain else ""
        tld = components.tld.lower() if components.tld else ""
        path = components.path.lower() if components.path else ""
        query = components.query.lower() if components.query else ""

        # Contagem de subdomínios
        subdomain_parts = [s for s in subdomain.split(".") if s] if subdomain else []
        num_subdomains = len(subdomain_parts)

        # Palavras-gatilho encontradas
        all_text = f"{subdomain} {domain} {path} {query}"
        found_triggers = [w for w in TRIGGER_WORDS if w in all_text]

        # Hífens no domínio
        hyphen_count = domain.count("-") + subdomain.count("-")

        # Entropia do subdomínio
        subdomain_entropy = self._shannon_entropy(subdomain) if subdomain else 0.0

        # Detecção de homógrafos
        homoglyphs_found = self._detect_homoglyphs(domain + subdomain)

        # Detecção de typosquatting
        typosquatting_matches = self._detect_typosquatting(domain)

        # Verificação de encurtador
        registered = components.registered_domain.lower() if components.registered_domain else ""
        is_shortener = registered in URL_SHORTENERS or domain in [
            s.split(".")[0] for s in URL_SHORTENERS
        ]

        # TLD risk
        tld_risk = tld in HIGH_RISK_TLDS
        tld_common = tld in COMMON_TLDS

        # Extensão de arquivo exposta
        has_php = ".php" in path
        has_suspicious_ext = any(ext in path for ext in [".php", ".asp", ".cgi", ".exe"])

        # === Novas features v1.1 ===

        # Detecção de marca no path
        brand_in_path = self._detect_brand_in_path(path, domain)

        # Detecção de Punycode/IDN
        punycode_info = self._detect_punycode(full_url, domain, subdomain)

        # Detecção de marca como subdomínio
        brand_as_subdomain = self._detect_brand_as_subdomain(subdomain, domain)

        # URL encoding abusivo
        percent_count, decoded_url = self._count_percent_encoding(full_url)

        # Base64 em query strings
        base64_found = self._detect_base64(query)

        # DGA no domínio principal
        domain_entropy = self._shannon_entropy(domain) if domain else 0.0
        is_dga_domain = self._is_dga_domain(domain, domain_entropy)

        # Extensão dupla
        double_ext = self._detect_double_extension(path)

        # Open redirect
        open_redirect = self._detect_open_redirect(components.query_params)

        # Data URI / javascript:
        is_data_uri = full_url.lower().startswith(("data:", "javascript:"))

        # Keyboard proximity typosquatting
        keyboard_typo = self._detect_keyboard_typosquatting(domain)

        # Porta suspeita
        is_suspicious_port = components.port in SUSPICIOUS_PORTS

        return {
            "url_length": len(full_url),
            "is_ip": components.is_ip,
            "scheme": components.scheme,
            "is_https": components.scheme == "https",
            "is_http": components.scheme == "http",
            "num_subdomains": num_subdomains,
            "subdomain_text": subdomain,
            "subdomain_entropy": round(subdomain_entropy, 2),
            "domain_text": domain,
            "tld_text": tld,
            "tld_is_risky": tld_risk,
            "tld_is_common": tld_common,
            "path_text": path,
            "query_text": query,
            "trigger_words_found": found_triggers,
            "hyphen_count": hyphen_count,
            "homoglyphs_found": homoglyphs_found,
            "typosquatting_matches": typosquatting_matches,
            "is_shortener": is_shortener,
            "has_php_extension": has_php,
            "has_suspicious_extension": has_suspicious_ext,
            "has_port": bool(components.port),
            "port": components.port,
            # === Novas features v1.1 ===
            "brand_in_path": brand_in_path,
            "punycode_info": punycode_info,
            "brand_as_subdomain": brand_as_subdomain,
            "percent_encoding_count": percent_count,
            "decoded_url": decoded_url,
            "base64_found": base64_found,
            "domain_entropy": round(domain_entropy, 2),
            "is_dga_domain": is_dga_domain,
            "double_extension": double_ext,
            "open_redirect": open_redirect,
            "is_data_uri": is_data_uri,
            "keyboard_typo_matches": keyboard_typo,
            "is_suspicious_port": is_suspicious_port,
        }

    def _evaluate_features(self, features: dict, components: URLComponents) -> list[Finding]:
        """Avalia cada feature e gera findings com explicações didáticas."""
        findings: list[Finding] = []

        # === IP em vez de domínio ===
        if features["is_ip"]:
            findings.append(Finding(
                factor="ip_instead_of_domain",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["ip_instead_of_domain"],
                title="IP em vez de domínio",
                explanation=(
                    f"Esta URL usa um endereço IP ({components.ip_address}) "
                    "em vez de um nome de domínio. Sites legítimos NUNCA pedem "
                    "que você acesse pelo número IP."
                ),
                analogy=(
                    "É como receber uma carta que, em vez do endereço do banco, "
                    "tem apenas coordenadas GPS. Ninguém faz isso legitimamente."
                ),
                tip=(
                    "Se um link contém apenas números no lugar do nome do site, "
                    "NÃO clique. Acesse o site oficial digitando o endereço no navegador."
                ),
            ))

        # === HTTP sem criptografia ===
        if features["is_http"]:
            findings.append(Finding(
                factor="http_no_encryption",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["http_no_encryption"],
                title="HTTP sem criptografia",
                explanation=(
                    "Esta URL usa HTTP (sem o 'S'). Isso significa que TUDO que você "
                    "digitar (inclusive senhas) será transmitido em texto puro, visível "
                    "para qualquer pessoa na mesma rede."
                ),
                analogy=(
                    "É como enviar uma carta em um cartão postal aberto — qualquer "
                    "pessoa no caminho pode ler o conteúdo."
                ),
                tip=(
                    "Nunca insira dados pessoais em sites que usam apenas HTTP. "
                    "Procure sempre o cadeado (HTTPS) no navegador."
                ),
            ))

        # === HTTPS presente (informativo) ===
        if features["is_https"]:
            findings.append(Finding(
                factor="https_present",
                severity="safe",
                weight=0,
                title="HTTPS presente",
                explanation=(
                    "A conexão é criptografada. Porém, HTTPS NÃO significa que "
                    "o site é seguro — apenas que a conexão é privada. Um site de "
                    "phishing pode ter HTTPS."
                ),
                analogy=(
                    "É como um ladrão usando um carro blindado — o carro é seguro, "
                    "o motorista não."
                ),
                tip=(
                    "HTTPS é necessário, mas não suficiente. Sempre verifique "
                    "o domínio, não apenas o cadeado."
                ),
            ))

        # === Typosquatting ===
        if features["typosquatting_matches"]:
            for brand, similarity in features["typosquatting_matches"]:
                findings.append(Finding(
                    factor="typosquatting",
                    severity="critical",
                    weight=HEURISTIC_WEIGHTS["typosquatting"],
                    title=f"Possível typosquatting: imita '{brand}'",
                    explanation=(
                        f"O domínio '{features['domain_text']}' é visualmente similar "
                        f"a '{brand}' (similaridade: {similarity}%). Isso pode ser uma "
                        "tentativa de imitar uma marca conhecida."
                    ),
                    analogy=(
                        "É como alguém colocar uma placa com o nome de uma loja famosa "
                        "na fachada de uma loja falsa para enganar clientes."
                    ),
                    tip=(
                        f"O site oficial de '{brand}' tem um domínio diferente. "
                        "Na dúvida, digite o endereço diretamente no navegador em "
                        "vez de clicar em links."
                    ),
                ))
                break  # Reporta apenas o match mais relevante

        # === Homógrafos ===
        if features["homoglyphs_found"]:
            findings.append(Finding(
                factor="homoglyph_detected",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["homoglyph_detected"],
                title="Caracteres homógrafos detectados",
                explanation=(
                    "A URL contém caracteres Unicode que se parecem com letras "
                    "comuns mas são diferentes. Isso é um truque visual para "
                    "enganar o usuário."
                ),
                analogy=(
                    "É como alguém trocar a letra 'O' por um zero '0' em um "
                    "documento — parece igual, mas é falso."
                ),
                tip=(
                    "Preste atenção em letras que parecem estranhas ou em fontes "
                    "diferentes. Na dúvida, digite o endereço manualmente."
                ),
            ))

        # === TLD de risco ===
        if features["tld_is_risky"]:
            findings.append(Finding(
                factor="suspicious_tld",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["suspicious_tld"],
                title=f"TLD de risco elevado (.{features['tld_text']})",
                explanation=(
                    f"O TLD '.{features['tld_text']}' é frequentemente usado em sites "
                    "maliciosos por ser gratuito ou muito barato para registrar."
                ),
                analogy=(
                    "É como um endereço em uma região conhecida por golpes — não "
                    "significa que todos sejam golpistas, mas exige mais cautela."
                ),
                tip=(
                    "TLDs como .tk, .ml, .xyz são usados legitimamente às vezes, "
                    "mas exigem atenção redobrada. Prefira sites com TLDs comuns "
                    "(.com, .com.br, .org)."
                ),
            ))
        elif features["tld_is_common"]:
            findings.append(Finding(
                factor="common_tld",
                severity="safe",
                weight=0,
                title=f"TLD comum (.{features['tld_text']})",
                explanation=(
                    f"O TLD '.{features['tld_text']}' é um dos mais utilizados e "
                    "regulamentados."
                ),
                analogy="",
                tip="",
            ))

        # === Excesso de subdomínios ===
        if features["num_subdomains"] > 2:
            findings.append(Finding(
                factor="excessive_subdomains",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["excessive_subdomains"],
                title=f"Excesso de subdomínios ({features['num_subdomains']})",
                explanation=(
                    f"A URL possui {features['num_subdomains']} níveis de subdomínio. "
                    "Isso é incomum e pode indicar tentativa de esconder o domínio real."
                ),
                analogy=(
                    "É como um endereço postal com muitos redirecionamentos — "
                    "dificulta saber onde você realmente está indo."
                ),
                tip=(
                    "Preste atenção no domínio principal (a parte logo antes do TLD). "
                    "Subdomínios longos podem ser usados para disfarçar o destino real."
                ),
            ))

        # === Encurtador de URL ===
        if features["is_shortener"]:
            findings.append(Finding(
                factor="url_shortener",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["url_shortener"],
                title="URL encurtada detectada",
                explanation=(
                    "Esta URL usa um serviço de encurtamento. O destino real está "
                    "oculto — você não sabe para onde será redirecionado."
                ),
                analogy=(
                    "É como entrar em um táxi que não mostra o destino no "
                    "taxímetro — você não sabe para onde está sendo levado."
                ),
                tip=(
                    "Use serviços como 'checkshorturl.com' para revelar o destino "
                    "real de URLs encurtadas antes de clicar."
                ),
            ))

        # === Palavras-gatilho ===
        if features["trigger_words_found"]:
            words = ", ".join(features["trigger_words_found"][:5])
            findings.append(Finding(
                factor="suspicious_keywords",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["suspicious_keywords"],
                title=f"Palavras-gatilho detectadas: {words}",
                explanation=(
                    f"A URL contém palavras frequentemente usadas em phishing: {words}. "
                    "Atacantes usam esses termos para criar senso de urgência ou "
                    "legitimidade falsa."
                ),
                analogy=(
                    "Sites legítimos raramente precisam dizer que são 'seguros' "
                    "ou 'verificados' no endereço. É como um restaurante com "
                    "um letreiro dizendo 'COMIDA NÃO ENVENENADA'."
                ),
                tip=(
                    "Desconfie de URLs que contêm palavras como 'login', 'verify', "
                    "'secure' ou 'update' em combinação com domínios desconhecidos."
                ),
            ))

        # === Excesso de hífens ===
        if features["hyphen_count"] >= 3:
            findings.append(Finding(
                factor="excessive_hyphens",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["excessive_hyphens"],
                title=f"Excesso de hífens no domínio ({features['hyphen_count']})",
                explanation=(
                    "Domínios legítimos raramente usam hífens. Atacantes os usam "
                    "para criar nomes que pareçam oficiais."
                ),
                analogy=(
                    "É como um documento com muitas emendas e rasuras — "
                    "pode indicar falsificação."
                ),
                tip=(
                    "Compare o domínio com o site oficial da empresa. "
                    "Domínios com muitos hífens são frequentemente falsos."
                ),
            ))

        # === Comprimento excessivo da URL ===
        if features["url_length"] > 100:
            findings.append(Finding(
                factor="excessive_length",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["excessive_length"],
                title=f"URL muito longa ({features['url_length']} caracteres)",
                explanation=(
                    "URLs excessivamente longas são frequentemente usadas para "
                    "esconder o destino real ou incluir códigos de rastreamento."
                ),
                analogy=(
                    "É como um endereço tão comprido que você não consegue "
                    "ler até o final — o que está escondido no fim?"
                ),
                tip=(
                    "URLs legítimas costumam ser curtas e legíveis. "
                    "Desconfie de URLs que parecem código embaralhado."
                ),
            ))

        # === Extensão .php exposta ===
        if features["has_suspicious_extension"]:
            findings.append(Finding(
                factor="php_extension_exposed",
                severity="info",
                weight=HEURISTIC_WEIGHTS["php_extension_exposed"],
                title="Extensão de arquivo exposta no path",
                explanation=(
                    "Sites modernos raramente mostram a extensão do arquivo na URL "
                    "(.php, .asp, .cgi). Isso pode indicar servidor mal configurado "
                    "ou montado às pressas."
                ),
                analogy=(
                    "É como ver a fiação elétrica exposta em uma loja — "
                    "pode indicar uma construção feita às pressas."
                ),
                tip=(
                    "Extensões expostas não são necessariamente perigosas, mas "
                    "combinadas com outros sinais, aumentam a suspeita."
                ),
            ))

        # === Entropia alta no subdomínio ===
        if features["subdomain_entropy"] > 3.5 and features["subdomain_text"]:
            if features["subdomain_text"] not in ("www", "mail", "ftp", "smtp"):
                findings.append(Finding(
                    factor="random_subdomain_entropy",
                    severity="warning",
                    weight=HEURISTIC_WEIGHTS["random_subdomain_entropy"],
                    title="Subdomínio com alta entropia (possível geração automática)",
                    explanation=(
                        f"O subdomínio '{features['subdomain_text']}' possui alta "
                        f"entropia ({features['subdomain_entropy']}), o que indica "
                        "strings aleatórias típicas de geração automática por malware."
                    ),
                    analogy=(
                        "É como receber uma carta de um endereço com nome da rua "
                        "formado por letras aleatórias — claramente não é um endereço real."
                    ),
                    tip=(
                        "Subdomínios com sequências aleatórias de caracteres são "
                        "um forte indicativo de URLs geradas automaticamente por botnets."
                    ),
                ))

        # === Query string suspeita ===
        if features["query_text"]:
            suspicious_params = any(
                kw in features["query_text"]
                for kw in ["token", "session", "id=", "redirect", "url=", "next=", "redir"]
            )
            if suspicious_params:
                findings.append(Finding(
                    factor="suspicious_query_string",
                    severity="info",
                    weight=HEURISTIC_WEIGHTS["suspicious_query_string"],
                    title="Query string com parâmetros suspeitos",
                    explanation=(
                        "A query string contém parâmetros que podem ser usados "
                        "para rastreamento ou redirecionamento malicioso."
                    ),
                    analogy=(
                        "É como um envelope que contém instruções secretas além "
                        "da carta principal — pode ser usado para fins ocultos."
                    ),
                    tip=(
                        "Parâmetros como 'redirect', 'url=', 'token' na URL podem "
                        "ser usados para rastrear cliques ou redirecionar para sites perigosos."
                    ),
                ))

        # ================================================================
        # === NOVOS FATORES v1.1 ===
        # ================================================================

        # === Marca detectada no path ===
        if features["brand_in_path"]:
            brand_path = features["brand_in_path"]
            findings.append(Finding(
                factor="brand_in_path",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["brand_in_path"],
                title=f"Marca '{brand_path}' encontrada no path de domínio não-oficial",
                explanation=(
                    f"O path da URL contém a marca '{brand_path}', mas o domínio "
                    f"'{features['domain_text']}' NÃO pertence a essa marca. "
                    "Isso é uma tática clássica de phishing: usar o nome da marca "
                    "em uma subpasta de um servidor controlado pelo atacante."
                ),
                analogy=(
                    "É como um golpista montando uma barraca com a logomarca "
                    "de uma loja famosa dentro de um galpão abandonado — "
                    "o nome está lá, mas o lugar é falso."
                ),
                tip=(
                    f"O site oficial de '{brand_path}' tem seu próprio domínio. "
                    "Se a marca aparece apenas no caminho (path) da URL, "
                    "é quase certamente uma imitação."
                ),
                confidence=0.85,
            ))

        # === Punycode/IDN ===
        if features["punycode_info"]:
            puny = features["punycode_info"]
            findings.append(Finding(
                factor="punycode_idn",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["punycode_idn"],
                title="Domínio internacionalizado (IDN/Punycode) detectado",
                explanation=(
                    f"O domínio contém Punycode ('{puny['raw']}' → '{puny['decoded']}'). "
                    "Nomes de domínio internacionalizados podem usar caracteres "
                    "de outros alfabetos que se parecem com letras latinas, "
                    "enganando visualmente o usuário."
                ),
                analogy=(
                    "É como um documento escrito com letras que parecem "
                    "portuguesas mas na verdade são de outro idioma — "
                    "visualmente iguais, tecnicamente diferentes."
                ),
                tip=(
                    "Se você ver 'xn--' no início de um domínio, é Punycode. "
                    "Isso não é necessariamente malicioso, mas exige atenção "
                    "redobrada. Compare com o domínio oficial da marca."
                ),
                confidence=0.90,
            ))

        # === Marca como subdomínio de domínio alheio ===
        if features["brand_as_subdomain"]:
            brand_sub = features["brand_as_subdomain"]
            findings.append(Finding(
                factor="brand_as_subdomain",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["brand_as_subdomain"],
                title=f"Marca '{brand_sub}' usada como subdomínio",
                explanation=(
                    f"A marca '{brand_sub}' aparece como subdomínio, mas o domínio "
                    f"principal é '{features['domain_text']}.{features['tld_text']}'. "
                    "Qualquer pessoa pode criar subdomínios com nomes de marcas "
                    "em seus próprios domínios. Isso NÃO indica que é o site oficial."
                ),
                analogy=(
                    "É como um prédio qualquer que coloca 'Banco do Brasil' "
                    "na placa do interfone — o nome está lá, mas o prédio "
                    "não pertence ao banco."
                ),
                tip=(
                    "Sempre olhe o domínio PRINCIPAL (a parte logo antes do TLD). "
                    "Subdomínios são controlados pelo dono do domínio principal, "
                    "não pela marca que aparece neles."
                ),
                confidence=0.90,
            ))

        # === URL encoding abusivo ===
        if features["percent_encoding_count"] > 5:
            findings.append(Finding(
                factor="url_encoding_abuse",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["url_encoding_abuse"],
                title=f"Excesso de URL encoding ({features['percent_encoding_count']} ocorrências)",
                explanation=(
                    f"A URL contém {features['percent_encoding_count']} caracteres codificados "
                    "em percent-encoding (%XX). Isso pode ser usado para ofuscar "
                    "o destino real da URL ou esconder caracteres maliciosos."
                ),
                analogy=(
                    "É como uma mensagem escrita em código para esconder "
                    "o verdadeiro conteúdo — se precisam esconder, por quê?"
                ),
                tip=(
                    "URLs legítimas raramente precisam de muito percent-encoding. "
                    "Excesso de caracteres como %20, %2F, %3A pode indicar "
                    "tentativa de ofuscação."
                ),
                confidence=0.70,
            ))

        # === Base64 em query strings ===
        if features["base64_found"]:
            findings.append(Finding(
                factor="base64_payload",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["base64_payload"],
                title="Possível payload Base64 detectado na query string",
                explanation=(
                    "A URL contém o que parece ser uma string codificada em Base64 "
                    "nos parâmetros. Isso pode esconder payloads maliciosos, "
                    "redirecionamentos ou código executável."
                ),
                analogy=(
                    "É como receber um pacote com um compartimento secreto — "
                    "o conteúdo visível parece normal, mas há algo escondido dentro."
                ),
                tip=(
                    "Strings longas de caracteres aleatórios em URLs são "
                    "suspeitas. Podem conter redirecionamentos ocultos "
                    "ou dados maliciosos codificados."
                ),
                confidence=0.65,
            ))

        # === DGA no domínio principal ===
        if features["is_dga_domain"]:
            findings.append(Finding(
                factor="dga_domain",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["dga_domain"],
                title="Domínio com padrão de geração algorítmica (DGA)",
                explanation=(
                    f"O domínio '{features['domain_text']}' possui alta entropia "
                    f"({features['domain_entropy']}) e padrões consistentes com "
                    "Domain Generation Algorithm (DGA). Malwares usam DGA para "
                    "gerar domínios automaticamente, dificultando bloqueio."
                ),
                analogy=(
                    "É como um criminoso que muda de endereço todo dia usando "
                    "uma fórmula matemática — os endereços são aleatórios "
                    "e servem apenas para dificultar o rastreamento."
                ),
                tip=(
                    "Domínios com sequências aleatórias de letras e números "
                    "(ex.: 'xk4m9z2q.com') são típicos de botnets e malware. "
                    "Sites legítimos sempre usam nomes legíveis."
                ),
                confidence=0.75,
            ))
        elif features["domain_entropy"] > 3.8 and len(features["domain_text"]) > 6:
            if not features["tld_is_common"] or features["tld_is_risky"]:
                findings.append(Finding(
                    factor="domain_entropy",
                    severity="warning",
                    weight=HEURISTIC_WEIGHTS["domain_entropy"],
                    title=f"Domínio com alta entropia ({features['domain_entropy']})",
                    explanation=(
                        f"O domínio '{features['domain_text']}' possui alta aleatoriedade "
                        "em seus caracteres, o que pode indicar geração automática."
                    ),
                    analogy=(
                        "É como um endereço formado por letras jogadas ao acaso — "
                        "difícil de lembrar e provavelmente não é um negócio real."
                    ),
                    tip=(
                        "Domínios legítimos costumam ser palavras reais ou "
                        "abreviações reconhecíveis. Sequências aleatórias são suspeitas."
                    ),
                    confidence=0.60,
                ))

        # === Extensão dupla ===
        if features["double_extension"]:
            doc_ext, danger_ext = features["double_extension"]
            findings.append(Finding(
                factor="double_extension",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["double_extension"],
                title=f"Extensão dupla perigosa detectada ({doc_ext}{danger_ext})",
                explanation=(
                    f"O path contém uma extensão dupla '{doc_ext}{danger_ext}'. "
                    "Isso é um truque clássico: o arquivo parece ser um documento "
                    f"({doc_ext}), mas na verdade é um executável ({danger_ext}). "
                    "O Windows pode ocultar a extensão real e exibir apenas a primeira."
                ),
                analogy=(
                    "É como um lobo vestido de ovelha — por fora parece um "
                    "documento inofensivo, por dentro é um programa perigoso."
                ),
                tip=(
                    "NUNCA baixe arquivos com extensão dupla (ex.: 'nota.pdf.exe'). "
                    "Ative a exibição de extensões de arquivo no Windows para "
                    "ver a extensão real."
                ),
                confidence=0.95,
            ))

        # === Open redirect ===
        if features["open_redirect"]:
            param_name = features["open_redirect"]
            findings.append(Finding(
                factor="open_redirect",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["open_redirect"],
                title=f"Possível open redirect (parâmetro '{param_name}')",
                explanation=(
                    f"A URL contém o parâmetro '{param_name}' que aponta para outro "
                    "endereço. Isso pode ser um Open Redirect: o site legítimo "
                    "redireciona você para um site malicioso sem que você perceba."
                ),
                analogy=(
                    "É como entrar em uma loja confiável que, sem você saber, "
                    "tem uma passagem secreta que leva a um lugar perigoso."
                ),
                tip=(
                    "Verifique se a URL no parâmetro de redirecionamento "
                    "aponta para o mesmo domínio. Redirecionamentos para "
                    "domínios externos são suspeitos."
                ),
                confidence=0.70,
            ))

        # === Data URI / javascript: ===
        if features["is_data_uri"]:
            findings.append(Finding(
                factor="data_uri",
                severity="critical",
                weight=HEURISTIC_WEIGHTS["data_uri"],
                title="Data URI ou javascript: detectado",
                explanation=(
                    "Esta não é uma URL convencional — é um Data URI ou código "
                    "JavaScript inline. Isso pode executar código diretamente "
                    "no navegador sem acessar um servidor externo."
                ),
                analogy=(
                    "É como receber um pacote que contém uma armadilha "
                    "que dispara ao ser aberto — não precisa de 'endereço' "
                    "porque o perigo já está embutido."
                ),
                tip=(
                    "NUNCA cole URLs que começam com 'data:' ou 'javascript:' "
                    "no navegador. Elas podem executar código malicioso "
                    "diretamente na sua máquina."
                ),
                confidence=0.95,
            ))

        # === Keyboard proximity typosquatting ===
        if features["keyboard_typo_matches"] and not features["typosquatting_matches"]:
            for brand, score in features["keyboard_typo_matches"]:
                findings.append(Finding(
                    factor="keyboard_typosquatting",
                    severity="critical",
                    weight=HEURISTIC_WEIGHTS["keyboard_typosquatting"],
                    title=f"Typosquatting por proximidade de teclado: imita '{brand}'",
                    explanation=(
                        f"O domínio '{features['domain_text']}' pode ser um erro de "
                        f"digitação intencional de '{brand}', usando teclas vizinhas "
                        "no teclado. Atacantes registram esses domínios para capturar "
                        "vítimas que erram ao digitar."
                    ),
                    analogy=(
                        "É como colocar uma loja falsa bem na esquina de uma "
                        "loja famosa, apostando que clientes distraídos vão "
                        "entrar no lugar errado."
                    ),
                    tip=(
                        f"Verifique se digitou '{brand}' corretamente. "
                        "Use favoritos ou busca para acessar sites importantes "
                        "em vez de digitar o endereço."
                    ),
                    confidence=0.75,
                ))
                break

        # === Porta suspeita ===
        if features["is_suspicious_port"]:
            findings.append(Finding(
                factor="suspicious_port",
                severity="warning",
                weight=HEURISTIC_WEIGHTS["suspicious_port"],
                title=f"Porta não-padrão detectada (:{features['port']})",
                explanation=(
                    f"A URL usa a porta {features['port']}, que não é padrão "
                    "para HTTP (80) ou HTTPS (443). Portas incomuns podem indicar "
                    "servidores temporários montados para ataques."
                ),
                analogy=(
                    "É como um banco que atende em uma sala dos fundos "
                    "em vez do guichê principal — por que não usar a entrada normal?"
                ),
                tip=(
                    "Sites legítimos usam portas padrão (80/443). Portas como "
                    "8080, 8888, 9090 podem indicar servidores de teste ou ataques."
                ),
                confidence=0.60,
            ))

        return findings

    def _shannon_entropy(self, text: str) -> float:
        """Calcula entropia de Shannon da string."""
        if not text:
            return 0.0
        length = len(text)
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        entropy = 0.0
        for count in freq.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        return entropy

    def _detect_homoglyphs(self, text: str) -> list[str]:
        """Detecta caracteres Unicode homógrafos na string."""
        found = []
        for char in text:
            if char in self._HOMOGLYPHS:
                found.append(f"'{char}' (parece '{self._HOMOGLYPHS[char]}')")
        return found

    def _detect_typosquatting(self, domain: str) -> list[tuple[str, int]]:
        """
        Detecta possível typosquatting comparando o domínio com marcas conhecidas.
        Retorna lista de (marca, similaridade_percentual).
        """
        if not domain:
            return []

        matches = []
        domain_lower = domain.lower().replace("-", "").replace("_", "")

        for brand in self._KNOWN_BRANDS:
            if brand == domain_lower:
                continue  # Domínio exato da marca — não é typosquatting

            # Verifica se a marca está contida no domínio com caracteres extras
            if brand in domain_lower and domain_lower != brand:
                similarity = int((len(brand) / len(domain_lower)) * 100)
                if similarity >= 50:
                    matches.append((brand, similarity))
                    continue

            # Distância de Levenshtein simplificada
            distance = self._levenshtein_distance(domain_lower, brand)
            max_len = max(len(domain_lower), len(brand))
            if max_len > 0:
                similarity = int(((max_len - distance) / max_len) * 100)
                if similarity >= 75 and distance <= 3:
                    matches.append((brand, similarity))

            # Verificação de 'rn' imitando 'm' (homógrafo visual)
            rn_replaced = domain_lower.replace("rn", "m")
            if rn_replaced == brand:
                matches.append((brand, 95))

        # Ordena por similaridade (maior primeiro)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _detect_brand_in_path(self, path: str, domain: str) -> str:
        """
        Detecta marcas conhecidas no path de URLs cujo domínio não pertence à marca.
        Retorna nome da marca encontrada ou string vazia.
        """
        if not path:
            return ""
        path_lower = path.lower()
        domain_lower = domain.lower().replace("-", "").replace("_", "") if domain else ""

        for brand in self._KNOWN_BRANDS:
            if len(brand) < 3:  # Evita falsos positivos com marcas curtas ('bb')
                continue
            if brand in path_lower:
                # Não alertar se o domínio já é da marca
                if brand in domain_lower:
                    continue
                return brand
        return ""

    @staticmethod
    def _detect_punycode(url: str, domain: str, subdomain: str) -> dict:
        """
        Detecta domínios Punycode/IDN (internationalized domain names).
        Retorna dict com info ou dict vazio.
        """
        combined = f"{subdomain}.{domain}" if subdomain else domain
        if not combined:
            return {}

        # Detecta prefixo Punycode 'xn--'
        parts = combined.lower().split(".")
        for part in parts:
            if part.startswith("xn--"):
                try:
                    decoded = part.encode("ascii").decode("idna")
                except (UnicodeError, UnicodeDecodeError):
                    decoded = part
                return {"raw": part, "decoded": decoded}

        # Detecta caracteres não-ASCII no domínio (que seriam convertidos a Punycode)
        for char in combined:
            if ord(char) > 127:
                return {"raw": combined, "decoded": combined}

        return {}

    def _detect_brand_as_subdomain(self, subdomain: str, domain: str) -> str:
        """
        Detecta quando uma marca conhecida é usada como subdomínio de domínio não-relacionado.
        Ex.: paypal.evil-site.com
        """
        if not subdomain:
            return ""
        sub_parts = subdomain.lower().split(".")
        domain_lower = domain.lower().replace("-", "").replace("_", "") if domain else ""

        for part in sub_parts:
            clean_part = part.replace("-", "").replace("_", "")
            for brand in self._KNOWN_BRANDS:
                if len(brand) < 3:
                    continue
                if clean_part == brand:
                    # O domínio principal NÃO é da marca
                    if brand not in domain_lower:
                        return brand
        return ""

    @staticmethod
    def _count_percent_encoding(url: str) -> tuple[int, str]:
        """
        Conta ocorrências de percent-encoding e retorna URL decodificada.
        Retorna (contagem, url_decodificada).
        """
        count = len(re.findall(r'%[0-9A-Fa-f]{2}', url))
        try:
            decoded = unquote(url)
        except Exception:
            decoded = url
        return count, decoded

    @staticmethod
    def _detect_base64(query: str) -> list[str]:
        """
        Detecta possíveis strings Base64 em query strings.
        Retorna lista de strings suspeitas encontradas.
        """
        if not query:
            return []

        found = []
        # Padrão: sequência longa de caracteres Base64
        b64_pattern = re.compile(r'[A-Za-z0-9+/=]{20,}')
        for match in b64_pattern.finditer(query):
            candidate = match.group()
            # Verifica se é Base64 válido
            try:
                # Tenta decodificar
                padding = 4 - (len(candidate) % 4)
                if padding != 4:
                    candidate_padded = candidate + "=" * padding
                else:
                    candidate_padded = candidate
                decoded = b64lib.b64decode(candidate_padded)
                # Se decodificou e contém texto legível, é suspeito
                try:
                    text = decoded.decode("utf-8", errors="strict")
                    if len(text) > 5 and text.isprintable():
                        found.append(candidate[:30] + "...")
                except UnicodeDecodeError:
                    # Binário — pode ser payload
                    if len(decoded) > 10:
                        found.append(candidate[:30] + "...")
            except Exception:
                continue
        return found

    def _is_dga_domain(self, domain: str, entropy: float) -> bool:
        """
        Determina se um domínio parece gerado por DGA (Domain Generation Algorithm).
        Usa entropia + análise de n-gramas + proporção consoante/vogal.
        """
        if not domain or len(domain) < 6:
            return False

        # Ignora domínios que são marcas conhecidas
        domain_clean = domain.lower().replace("-", "").replace("_", "")
        if domain_clean in self._KNOWN_BRANDS:
            return False

        # Critério 1: Alta entropia
        if entropy < 3.0:
            return False

        # Critério 2: Proporção consoante/vogal anormal
        vowels = sum(1 for c in domain_clean if c in 'aeiou')
        consonants = sum(1 for c in domain_clean if c.isalpha() and c not in 'aeiou')
        digits = sum(1 for c in domain_clean if c.isdigit())

        if consonants + vowels > 0:
            vowel_ratio = vowels / (consonants + vowels)
        else:
            return False

        # DGA tende a ter proporção de vogais muito baixa ou mistura de dígitos
        has_mixed_digits = digits > 0 and (consonants + vowels) > 0
        has_abnormal_vowels = vowel_ratio < 0.15 or vowel_ratio > 0.70

        # Critério 3: Sequências de consoantes incomuns (n-gramas)
        max_consonant_seq = 0
        current_seq = 0
        for c in domain_clean:
            if c.isalpha() and c not in 'aeiou':
                current_seq += 1
                max_consonant_seq = max(max_consonant_seq, current_seq)
            else:
                current_seq = 0

        has_long_consonant_seq = max_consonant_seq >= 4

        # Score de DGA
        dga_score = 0
        if entropy > 3.5:
            dga_score += 1
        if has_mixed_digits:
            dga_score += 1
        if has_abnormal_vowels:
            dga_score += 1
        if has_long_consonant_seq:
            dga_score += 1
        if len(domain_clean) > 12:
            dga_score += 1

        return dga_score >= 3

    @staticmethod
    def _detect_double_extension(path: str) -> tuple[str, str] | None:
        """
        Detecta extensão dupla perigosa no path (ex.: file.pdf.exe).
        Retorna tupla (ext_doc, ext_perigosa) ou None.
        """
        if not path:
            return None

        # Extrai nome do arquivo do path
        segments = path.rstrip("/").split("/")
        filename = segments[-1] if segments else ""
        if not filename or "." not in filename:
            return None

        filename_lower = filename.lower()
        parts = filename_lower.split(".")
        if len(parts) < 3:  # Precisa de pelo menos nome.ext1.ext2
            return None

        # Verifica combinação documento + perigosa
        for i in range(1, len(parts) - 1):
            doc_ext = f".{parts[i]}"
            danger_ext = f".{parts[i + 1]}"
            if doc_ext in DOCUMENT_EXTENSIONS and danger_ext in DANGEROUS_EXTENSIONS:
                return (doc_ext, danger_ext)

        return None

    @staticmethod
    def _detect_open_redirect(query_params: dict) -> str:
        """
        Detecta padrões de open redirect nos parâmetros da query.
        Retorna nome do parâmetro suspeito ou string vazia.
        """
        if not query_params:
            return ""

        for param_name, values in query_params.items():
            param_lower = param_name.lower()
            if param_lower in REDIRECT_PARAMS:
                # Verifica se o valor parece uma URL
                for val in values:
                    if val.startswith(("http://", "https://", "//", "www.")):
                        return param_name
                    # URL encoding de http
                    if "%3A%2F%2F" in val.upper() or "%2F%2F" in val.upper():
                        return param_name
        return ""

    def _detect_keyboard_typosquatting(self, domain: str) -> list[tuple[str, int]]:
        """
        Detecta typosquatting baseado em proximidade de teclas no teclado QWERTY.
        Retorna lista de (marca, score_de_proximidade).
        """
        if not domain or len(domain) < 3:
            return []

        domain_lower = domain.lower().replace("-", "").replace("_", "")
        matches = []

        for brand in self._KNOWN_BRANDS:
            if brand == domain_lower or len(brand) < 3:
                continue
            if len(domain_lower) != len(brand):
                continue  # Keyboard typo geralmente mantém mesmo comprimento

            diffs = []
            for i, (dc, bc) in enumerate(zip(domain_lower, brand)):
                if dc != bc:
                    diffs.append((i, dc, bc))

            # 1 ou 2 diferenças, e TODAS são teclas vizinhas
            if 1 <= len(diffs) <= 2:
                all_neighbors = True
                for _, typed, expected in diffs:
                    neighbors = KEYBOARD_NEIGHBORS.get(expected, "")
                    if typed not in neighbors:
                        all_neighbors = False
                        break

                if all_neighbors:
                    score = 100 - (len(diffs) * 15)
                    matches.append((brand, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calcula distância de Levenshtein entre duas strings."""
        if len(s1) < len(s2):
            return HeuristicAnalyzer._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        prev_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (c1 != c2)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]
