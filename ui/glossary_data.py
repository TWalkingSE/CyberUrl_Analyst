"""Glossary content reused by the PyQt6 glossary page."""

GLOSSARY = [
    {
        "term": "Phishing",
        "category": "Ataques",
        "definition": (
            "Técnica de engenharia social que usa mensagens falsas "
            "(e-mail, SMS, sites) para enganar vítimas e roubar dados "
            "sensíveis como senhas, cartões de crédito e CPF."
        ),
        "example": "E-mail falso do 'banco' pedindo para clicar em um link e confirmar dados.",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Spear Phishing",
        "category": "Ataques",
        "definition": (
            "Phishing direcionado a uma pessoa ou organização específica, "
            "usando informações pessoais da vítima para parecer legítimo."
        ),
        "example": "E-mail para o RH usando o nome real do diretor, pedindo atualização de dados.",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Smishing",
        "category": "Ataques",
        "definition": (
            "Phishing via SMS. Mensagens de texto fraudulentas com links "
            "maliciosos ou pedidos de dados."
        ),
        "example": "SMS: 'CORREIOS: seu pacote foi retido. Pague a taxa: https://correios-taxa.com'",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Vishing",
        "category": "Ataques",
        "definition": (
            "Phishing por voz (Voice phishing). Ligações telefônicas "
            "fraudulentas fingindo ser bancos, empresas ou órgãos públicos."
        ),
        "example": "Ligação: 'Aqui é do banco, detectamos compra suspeita. Confirme seu cartão.'",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Quishing",
        "category": "Ataques",
        "definition": (
            "Phishing via QR Code. Códigos QR maliciosos colados sobre "
            "os legítimos em multas, cardápios ou estacionamentos."
        ),
        "example": "QR Code falso colado sobre o verdadeiro em um parquímetro, redirecionando para site de pagamento falso.",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "BEC (Business Email Compromise)",
        "category": "Ataques",
        "definition": (
            "Ataque onde o criminoso se passa por executivo ou fornecedor "
            "da empresa para autorizar transferências financeiras."
        ),
        "example": "E-mail do 'CEO' pedindo transferência urgente de R$ 50.000 para novo fornecedor.",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Typosquatting",
        "category": "URLs",
        "definition": (
            "Registro de domínios com erros de digitação de marcas famosas "
            "para capturar usuários que erram o endereço."
        ),
        "example": "gooogle.com, paypa1.com, arnazon.com (rn imitando m).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Homógrafo (IDN Homograph)",
        "category": "URLs",
        "definition": (
            "Uso de caracteres visualmente idênticos de outros alfabetos "
            "(cirílico, grego) para criar domínios falsos indistinguíveis."
        ),
        "example": "аpple.com (o 'а' é cirílico) vs apple.com (o 'a' é latino).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "URL Shortener (Encurtador)",
        "category": "URLs",
        "definition": (
            "Serviço que transforma URLs longas em curtas (bit.ly, tinyurl). "
            "Esconde o destino real, dificultando a avaliação de segurança."
        ),
        "example": "bit.ly/3xK9mPq - impossível saber para onde leva sem expandir.",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "Open Redirect",
        "category": "URLs",
        "definition": (
            "Vulnerabilidade onde um site legítimo redireciona para qualquer "
            "URL via parâmetro, permitindo uso em phishing."
        ),
        "example": "google.com/redirect?url=https://site-malicioso.com",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "URL Encoding Abusivo",
        "category": "URLs",
        "definition": (
            "Uso excessivo de codificação percentual (%XX) na URL para "
            "ofuscar o destino real e evadir filtros."
        ),
        "example": "%68%74%74%70%73://banco.com -> decodifica para https://banco.com",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Data URI / JavaScript URI",
        "category": "URLs",
        "definition": (
            "Esquemas de URL que executam código diretamente no navegador "
            "em vez de acessar um servidor."
        ),
        "example": "data:text/html,<script>alert('hack')</script>",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "Protocolo (Scheme)",
        "category": "Anatomia",
        "definition": (
            "Parte inicial da URL que define como a comunicação acontece. "
            "HTTPS usa criptografia; HTTP transmite dados em texto aberto."
        ),
        "example": "https:// (seguro) vs http:// (inseguro)",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Domínio (Domain)",
        "category": "Anatomia",
        "definition": (
            "Nome que identifica o servidor na internet. É a parte mais "
            "importante para verificar a legitimidade de um site."
        ),
        "example": "Em https://www.banco.com.br/login, o domínio é 'banco.com.br'.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Subdomínio",
        "category": "Anatomia",
        "definition": (
            "Prefixo antes do domínio principal. Atacantes usam subdomínios "
            "para inserir nomes de marcas e enganar vítimas."
        ),
        "example": "login.banco.site-malicioso.com - 'login.banco' é subdomínio de 'site-malicioso.com'.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "TLD (Top-Level Domain)",
        "category": "Anatomia",
        "definition": (
            "Extensão final do domínio (.com, .br, .org). Alguns TLDs "
            "como .tk, .ml, .xyz são frequentemente usados em sites maliciosos."
        ),
        "example": ".com.br (confiável) vs .tk (alto risco gratuito).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Query String",
        "category": "Anatomia",
        "definition": (
            "Parâmetros após o '?' na URL. Podem conter dados de rastreamento, "
            "redirecionamentos ou payloads maliciosos codificados."
        ),
        "example": "?redirect=https://evil.com ou ?token=base64encodedpayload",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "DGA (Domain Generation Algorithm)",
        "category": "Detecção",
        "definition": (
            "Algoritmo usado por malware para gerar domínios aleatórios "
            "automaticamente, dificultando bloqueio por listas negras."
        ),
        "example": "xk3jf8sd2p.com, q9m4nv7bz.net - domínios sem sentido gerados por robôs.",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "Entropia",
        "category": "Detecção",
        "definition": (
            "Medida de aleatoriedade em uma string. Domínios legítimos "
            "têm baixa entropia (palavras reais); DGA/malware têm alta entropia."
        ),
        "example": "google.com (baixa entropia) vs xk3jf8sd2p.com (alta entropia).",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "Heurística",
        "category": "Detecção",
        "definition": (
            "Regras baseadas em padrões conhecidos para detectar ameaças "
            "sem depender de listas. Analisa características da URL."
        ),
        "example": "Se URL tem IP + HTTP + marca no path -> provavelmente maliciosa.",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "WHOIS",
        "category": "Detecção",
        "definition": (
            "Protocolo para consultar informações de registro de domínios. "
            "Domínios muito jovens (< 30 dias) são mais suspeitos."
        ),
        "example": "evil-bank.com registrado há 2 dias -> altamente suspeito.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Defanging",
        "category": "Detecção",
        "definition": (
            "Técnica de segurança que modifica URLs maliciosas para "
            "torná-las não clicáveis em relatórios e comunicações."
        ),
        "example": "https://evil.com -> hxxps[://]evil[.]com",
        "related_module": "🛡️ Análise",
    },
    {
        "term": "HTTPS / TLS / SSL",
        "category": "Segurança",
        "definition": (
            "Protocolo de comunicação criptografada. O cadeado no navegador "
            "indica que a conexão é segura, mas NÃO garante que o site é legítimo."
        ),
        "example": "https://paypa1.com tem cadeado verde, mas é site falso.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Engenharia Social",
        "category": "Segurança",
        "definition": (
            "Manipulação psicológica para convencer pessoas a realizar ações "
            "ou revelar informações confidenciais. Base de todos os tipos de phishing."
        ),
        "example": "Criar urgência ('24 horas'), medo ('conta bloqueada') ou ganância ('prêmio grátis').",
        "related_module": "🎭 Cenários",
    },
    {
        "term": "Sandboxing",
        "category": "Segurança",
        "definition": (
            "Técnica de executar programas ou abrir links em ambiente "
            "isolado para verificar se são maliciosos sem risco."
        ),
        "example": "Abrir link suspeito em máquina virtual antes de acessar no computador real.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "IoC (Indicator of Compromise)",
        "category": "Segurança",
        "definition": (
            "Evidência técnica de que um sistema foi comprometido. "
            "URLs, IPs, hashes de arquivo e domínios são IoCs comuns."
        ),
        "example": "URL de phishing confirmada, IP de servidor C2, hash de malware.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "PhishTank",
        "category": "Inteligência",
        "definition": (
            "Base de dados colaborativa de URLs de phishing confirmadas. "
            "Alimentada por contribuições da comunidade de segurança."
        ),
        "example": "URL reportada e verificada por múltiplos analistas como phishing.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "URLhaus",
        "category": "Inteligência",
        "definition": (
            "Projeto do abuse.ch que coleta e compartilha URLs usadas "
            "para distribuição de malware."
        ),
        "example": "URLs que distribuem trojans, ransomware ou droppers.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "Majestic Million / Tranco",
        "category": "Inteligência",
        "definition": (
            "Listas dos domínios mais populares do mundo (top 1 milhão). "
            "Usadas como referência de domínios legítimos."
        ),
        "example": "google.com, facebook.com, github.com - presença na lista indica legitimidade.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "VirusTotal",
        "category": "Inteligência",
        "definition": (
            "Serviço que analisa URLs e arquivos usando dezenas de "
            "antivírus e mecanismos de detecção simultaneamente."
        ),
        "example": "Submeter URL e ver que 8/90 engines detectam como maliciosa.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Safe Browsing (Google)",
        "category": "Inteligência",
        "definition": (
            "API do Google que verifica URLs contra listas de sites "
            "de phishing e malware. Usada nativamente pelo Chrome."
        ),
        "example": "Tela vermelha 'Site enganoso à frente' no Chrome.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Random Forest",
        "category": "Machine Learning",
        "definition": (
            "Algoritmo de ML que usa múltiplas árvores de decisão para "
            "classificar URLs. Cada árvore 'vota' e a maioria vence."
        ),
        "example": "25 features da URL -> Random Forest -> 87% chance de ser maliciosa.",
        "related_module": "⚙️ Configurações",
    },
    {
        "term": "Feature (Característica)",
        "category": "Machine Learning",
        "definition": (
            "Atributo numérico extraído da URL para alimentar o modelo ML. "
            "Comprimento, entropia, quantidade de dígitos, etc."
        ),
        "example": "url_length=87, entropy=4.2, digit_ratio=0.15, has_ip=1",
        "related_module": "⚙️ Configurações",
    },
    {
        "term": "Acurácia / F1-Score",
        "category": "Machine Learning",
        "definition": (
            "Métricas de desempenho do modelo. Acurácia = % de acertos total. "
            "F1 = equilíbrio entre precisão e recall (evita falsos positivos/negativos)."
        ),
        "example": "Acurácia 95%, F1 93% - bom desempenho geral.",
        "related_module": "⚙️ Configurações",
    },
]

GLOSSARY_CATEGORIES = sorted({item["category"] for item in GLOSSARY})