"""Glossary content reused by the PyQt6 glossary page."""

GLOSSARY = [
    {
        "term": "Phishing",
        "category": "Ataques",
        "definition": (
            "Tecnica de engenharia social que usa mensagens falsas "
            "(e-mail, SMS, sites) para enganar vitimas e roubar dados "
            "sensíveis como senhas, cartoes de credito e CPF."
        ),
        "example": "E-mail falso do 'banco' pedindo para clicar em um link e confirmar dados.",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Spear Phishing",
        "category": "Ataques",
        "definition": (
            "Phishing direcionado a uma pessoa ou organizacao especifica, "
            "usando informacoes pessoais da vitima para parecer legitimo."
        ),
        "example": "E-mail para o RH usando o nome real do diretor, pedindo atualizacao de dados.",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Smishing",
        "category": "Ataques",
        "definition": (
            "Phishing via SMS. Mensagens de texto fraudulentas com links "
            "maliciosos ou pedidos de dados."
        ),
        "example": "SMS: 'CORREIOS: seu pacote foi retido. Pague a taxa: https://correios-taxa.com'",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Vishing",
        "category": "Ataques",
        "definition": (
            "Phishing por voz (Voice phishing). Ligacoes telefonicas "
            "fraudulentas fingindo ser bancos, empresas ou orgaos publicos."
        ),
        "example": "Ligacao: 'Aqui e do banco, detectamos compra suspeita. Confirme seu cartao.'",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Quishing",
        "category": "Ataques",
        "definition": (
            "Phishing via QR Code. Codigos QR maliciosos colados sobre "
            "os legitimos em multas, cardapios ou estacionamentos."
        ),
        "example": "QR Code falso colado sobre o verdadeiro em um parquimetro, redirecionando para site de pagamento falso.",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "BEC (Business Email Compromise)",
        "category": "Ataques",
        "definition": (
            "Ataque onde o criminoso se passa por executivo ou fornecedor "
            "da empresa para autorizar transferencias financeiras."
        ),
        "example": "E-mail do 'CEO' pedindo transferencia urgente de R$ 50.000 para novo fornecedor.",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Typosquatting",
        "category": "URLs",
        "definition": (
            "Registro de dominios com erros de digitacao de marcas famosas "
            "para capturar usuarios que erram o endereco."
        ),
        "example": "gooogle.com, paypa1.com, arnazon.com (rn imitando m).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Homografo (IDN Homograph)",
        "category": "URLs",
        "definition": (
            "Uso de caracteres visualmente identicos de outros alfabetos "
            "(cirilico, grego) para criar dominios falsos indistinguiveis."
        ),
        "example": "аpple.com (o 'а' e cirilico) vs apple.com (o 'a' e latino).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "URL Shortener (Encurtador)",
        "category": "URLs",
        "definition": (
            "Servico que transforma URLs longas em curtas (bit.ly, tinyurl). "
            "Esconde o destino real, dificultando a avaliacao de seguranca."
        ),
        "example": "bit.ly/3xK9mPq - impossivel saber para onde leva sem expandir.",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "Open Redirect",
        "category": "URLs",
        "definition": (
            "Vulnerabilidade onde um site legitimo redireciona para qualquer "
            "URL via parametro, permitindo uso em phishing."
        ),
        "example": "google.com/redirect?url=https://site-malicioso.com",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "URL Encoding Abusivo",
        "category": "URLs",
        "definition": (
            "Uso excessivo de codificacao percentual (%XX) na URL para "
            "ofuscar o destino real e evadir filtros."
        ),
        "example": "%68%74%74%70%73://banco.com -> decodifica para https://banco.com",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Data URI / JavaScript URI",
        "category": "URLs",
        "definition": (
            "Esquemas de URL que executam codigo diretamente no navegador "
            "em vez de acessar um servidor."
        ),
        "example": "data:text/html,<script>alert('hack')</script>",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "Protocolo (Scheme)",
        "category": "Anatomia",
        "definition": (
            "Parte inicial da URL que define como a comunicacao acontece. "
            "HTTPS usa criptografia; HTTP transmite dados em texto aberto."
        ),
        "example": "https:// (seguro) vs http:// (inseguro)",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Dominio (Domain)",
        "category": "Anatomia",
        "definition": (
            "Nome que identifica o servidor na internet. E a parte mais "
            "importante para verificar a legitimidade de um site."
        ),
        "example": "Em https://www.banco.com.br/login, o dominio e 'banco.com.br'.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Subdominio",
        "category": "Anatomia",
        "definition": (
            "Prefixo antes do dominio principal. Atacantes usam subdominios "
            "para inserir nomes de marcas e enganar vitimas."
        ),
        "example": "login.banco.site-malicioso.com - 'login.banco' e subdominio de 'site-malicioso.com'.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "TLD (Top-Level Domain)",
        "category": "Anatomia",
        "definition": (
            "Extensao final do dominio (.com, .br, .org). Alguns TLDs "
            "como .tk, .ml, .xyz sao frequentemente usados em sites maliciosos."
        ),
        "example": ".com.br (confiavel) vs .tk (alto risco gratuito).",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Query String",
        "category": "Anatomia",
        "definition": (
            "Parametros apos o '?' na URL. Podem conter dados de rastreamento, "
            "redirecionamentos ou payloads maliciosos codificados."
        ),
        "example": "?redirect=https://evil.com ou ?token=base64encodedpayload",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "DGA (Domain Generation Algorithm)",
        "category": "Deteccao",
        "definition": (
            "Algoritmo usado por malware para gerar dominios aleatorios "
            "automaticamente, dificultando bloqueio por listas negras."
        ),
        "example": "xk3jf8sd2p.com, q9m4nv7bz.net - dominios sem sentido gerados por robos.",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "Entropia",
        "category": "Deteccao",
        "definition": (
            "Medida de aleatoriedade em uma string. Dominios legitimos "
            "tem baixa entropia (palavras reais); DGA/malware tem alta entropia."
        ),
        "example": "google.com (baixa entropia) vs xk3jf8sd2p.com (alta entropia).",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "Heuristica",
        "category": "Deteccao",
        "definition": (
            "Regras baseadas em padroes conhecidos para detectar ameacas "
            "sem depender de listas. Analisa caracteristicas da URL."
        ),
        "example": "Se URL tem IP + HTTP + marca no path -> provavelmente maliciosa.",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "WHOIS",
        "category": "Deteccao",
        "definition": (
            "Protocolo para consultar informacoes de registro de dominios. "
            "Dominios muito jovens (< 30 dias) sao mais suspeitos."
        ),
        "example": "evil-bank.com registrado ha 2 dias -> altamente suspeito.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Defanging",
        "category": "Deteccao",
        "definition": (
            "Tecnica de seguranca que modifica URLs maliciosas para "
            "torna-las nao clicaveis em relatorios e comunicacoes."
        ),
        "example": "https://evil.com -> hxxps[://]evil[.]com",
        "related_module": "🛡️ Analise",
    },
    {
        "term": "HTTPS / TLS / SSL",
        "category": "Seguranca",
        "definition": (
            "Protocolo de comunicacao criptografada. O cadeado no navegador "
            "indica que a conexao e segura, mas NAO garante que o site e legitimo."
        ),
        "example": "https://paypa1.com tem cadeado verde mas e site falso.",
        "related_module": "🔍 Anatomia",
    },
    {
        "term": "Engenharia Social",
        "category": "Seguranca",
        "definition": (
            "Manipulacao psicologica para convencer pessoas a realizar acoes "
            "ou revelar informacoes confidenciais. Base de todos os tipos de phishing."
        ),
        "example": "Criar urgencia ('24 horas'), medo ('conta bloqueada') ou ganancia ('premio gratis').",
        "related_module": "🎭 Cenarios",
    },
    {
        "term": "Sandboxing",
        "category": "Seguranca",
        "definition": (
            "Tecnica de executar programas ou abrir links em ambiente "
            "isolado para verificar se sao maliciosos sem risco."
        ),
        "example": "Abrir link suspeito em maquina virtual antes de acessar no computador real.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "IoC (Indicator of Compromise)",
        "category": "Seguranca",
        "definition": (
            "Evidencia tecnica de que um sistema foi comprometido. "
            "URLs, IPs, hashes de arquivo e dominios sao IoCs comuns."
        ),
        "example": "URL de phishing confirmada, IP de servidor C2, hash de malware.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "PhishTank",
        "category": "Inteligencia",
        "definition": (
            "Base de dados colaborativa de URLs de phishing confirmadas. "
            "Alimentada por contribuicoes da comunidade de seguranca."
        ),
        "example": "URL reportada e verificada por multiplos analistas como phishing.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "URLhaus",
        "category": "Inteligencia",
        "definition": (
            "Projeto do abuse.ch que coleta e compartilha URLs usadas "
            "para distribuicao de malware."
        ),
        "example": "URLs que distribuem trojans, ransomware ou droppers.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "Majestic Million / Tranco",
        "category": "Inteligencia",
        "definition": (
            "Listas dos dominios mais populares do mundo (top 1 milhao). "
            "Usadas como referencia de dominios legitimos."
        ),
        "example": "google.com, facebook.com, github.com - presenca na lista indica legitimidade.",
        "related_module": "📦 Datasets",
    },
    {
        "term": "VirusTotal",
        "category": "Inteligencia",
        "definition": (
            "Servico que analisa URLs e arquivos usando dezenas de "
            "antivirus e mecanismos de deteccao simultaneamente."
        ),
        "example": "Submeter URL e ver que 8/90 engines detectam como maliciosa.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Safe Browsing (Google)",
        "category": "Inteligencia",
        "definition": (
            "API do Google que verifica URLs contra listas de sites "
            "de phishing e malware. Usada nativamente pelo Chrome."
        ),
        "example": "Tela vermelha 'Site enganoso a frente' no Chrome.",
        "related_module": "🔌 APIs",
    },
    {
        "term": "Random Forest",
        "category": "Machine Learning",
        "definition": (
            "Algoritmo de ML que usa multiplas arvores de decisao para "
            "classificar URLs. Cada arvore 'vota' e a maioria vence."
        ),
        "example": "25 features da URL -> Random Forest -> 87% chance de ser maliciosa.",
        "related_module": "⚙️ Configuracoes",
    },
    {
        "term": "Feature (Caracteristica)",
        "category": "Machine Learning",
        "definition": (
            "Atributo numerico extraido da URL para alimentar o modelo ML. "
            "Comprimento, entropia, quantidade de digitos, etc."
        ),
        "example": "url_length=87, entropy=4.2, digit_ratio=0.15, has_ip=1",
        "related_module": "⚙️ Configuracoes",
    },
    {
        "term": "Acuracia / F1-Score",
        "category": "Machine Learning",
        "definition": (
            "Metricas de desempenho do modelo. Acuracia = % de acertos total. "
            "F1 = equilibrio entre precisao e recall (evita falsos positivos/negativos)."
        ),
        "example": "Acuracia 95%, F1 93% - bom desempenho geral.",
        "related_module": "⚙️ Configuracoes",
    },
]

GLOSSARY_CATEGORIES = sorted({item["category"] for item in GLOSSARY})