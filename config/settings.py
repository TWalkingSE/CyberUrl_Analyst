"""
Configurações centrais do CyberURL Analyst.
Paths, limites, flags e constantes do projeto.
"""

from pathlib import Path

# === Diretórios do projeto ===
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
ASSETS_DIR = BASE_DIR / "assets"

# Diretório de dados persistentes (histórico, leaderboard, feedback)
DATA_DIR = BASE_DIR / "data"

# === Datasets — Amostras locais (incluídas no repositório) ===
PHISHTANK_SAMPLE = DATASETS_DIR / "phishtank_sample.csv"
URLHAUS_SAMPLE = DATASETS_DIR / "urlhaus_sample.csv"
MAJESTIC_MILLION_SAMPLE = DATASETS_DIR / "majestic_million_sample.csv"

# === Datasets — Arquivos baixados (downloads/) ===
DATASETS_DOWNLOAD_DIR = DATASETS_DIR / "downloads"

# Registro centralizado de todos os datasets suportados
# Cada entrada: (id, nome, categoria, url_download, formato, arquivo_local, requer_auth, notas)
DATASET_REGISTRY = {
    # --- Feeds de URLs maliciosas ---
    "phishtank": {
        "name": "PhishTank",
        "category": "malicious",
        "url": "http://data.phishtank.com/data/{api_key}/online-valid.csv",
        "format": "csv",
        "file": "phishtank_online.csv",
        "requires_key": True,
        "key_env": "PHISHTANK_API_KEY",
        "url_column": "url",
        "description": "Banco de URLs de phishing verificadas pela comunidade.",
        "license": "Gratuito com registro",
        "website": "https://phishtank.org",
    },
    "urlhaus_full": {
        "name": "URLhaus (Full)",
        "category": "malicious",
        "url": "https://urlhaus.abuse.ch/downloads/csv_recent/",
        "format": "csv",
        "file": "urlhaus_recent.csv",
        "requires_key": False,
        "key_env": "",
        "url_column": "url",
        "description": "URLs de distribuição de malware (últimos 30 dias).",
        "license": "CC0",
        "website": "https://urlhaus.abuse.ch",
        "skip_header_lines": 9,  # URLhaus CSV tem 9 linhas de comentário
    },
    "urlhaus_txt": {
        "name": "URLhaus (Text)",
        "category": "malicious",
        "url": "https://urlhaus.abuse.ch/downloads/text_recent/",
        "format": "txt",
        "file": "urlhaus_urls.txt",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "Lista simples de URLs de malware (uma por linha).",
        "license": "CC0",
        "website": "https://urlhaus.abuse.ch",
    },
    "openphish": {
        "name": "OpenPhish",
        "category": "malicious",
        "url": "https://openphish.com/feed.txt",
        "format": "txt",
        "file": "openphish_feed.txt",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "Feed de ~500 URLs de phishing detectadas automaticamente.",
        "license": "Community feed gratuito",
        "website": "https://openphish.com",
    },
    # --- Domínios legítimos ---
    "tranco": {
        "name": "Tranco List (Top 1M)",
        "category": "legitimate",
        "url": "https://tranco-list.eu/top-1m.csv.zip",
        "format": "csv_zip",
        "file": "tranco_top1m.csv",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "Top 1M domínios (substituto moderno do Alexa).",
        "license": "Gratuito, aberto",
        "website": "https://tranco-list.eu",
    },
    "majestic": {
        "name": "Majestic Million",
        "category": "legitimate",
        "url": "https://downloads.majestic.com/majestic_million.csv",
        "format": "csv",
        "file": "majestic_million.csv",
        "requires_key": False,
        "key_env": "",
        "url_column": "Domain",
        "description": "Top 1M domínios por backlinks.",
        "license": "Gratuito",
        "website": "https://majestic.com/reports/majestic-million",
    },
    "umbrella": {
        "name": "Cisco Umbrella Top 1M",
        "category": "legitimate",
        "url": "https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip",
        "format": "csv_zip",
        "file": "umbrella_top1m.csv",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "Top 1M domínios por resolução DNS (Cisco).",
        "license": "Gratuito",
        "website": "https://umbrella.cisco.com",
    },
    # --- DGA ---
    "dga_netlab360": {
        "name": "360 Netlab DGA Feed",
        "category": "dga",
        "url": "https://data.netlab.360.com/feeds/dga/dga.txt",
        "format": "txt",
        "file": "netlab360_dga.txt",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "Feed de domínios DGA rastreados (59+ famílias).",
        "license": "Gratuito para pesquisa",
        "website": "https://data.netlab.360.com/dga/",
    },
    # --- Datasets que requerem ação manual do usuário ---
    "phiusiil": {
        "name": "PhiUSIIL (UCI/Kaggle)",
        "category": "ml_features",
        "url": "",
        "format": "csv",
        "file": "phiusiil.csv",
        "requires_key": True,
        "key_env": "KAGGLE_KEY",
        "url_column": "",
        "description": "235K URLs com 54+ features (requer download manual do Kaggle/UCI).",
        "license": "CC BY 4.0",
        "website": "https://archive.ics.uci.edu/dataset/967",
        "manual": True,
    },
    "dga_kaggle": {
        "name": "DGA Dataset (Kaggle)",
        "category": "dga",
        "url": "",
        "format": "csv",
        "file": "dga_kaggle.csv",
        "requires_key": True,
        "key_env": "KAGGLE_KEY",
        "url_column": "",
        "description": "160K domínios DGA rotulados (requer download manual do Kaggle).",
        "license": "Aberto",
        "website": "https://www.kaggle.com/datasets/cgivre/dga-dataset",
        "manual": True,
    },
    "huggingface_phishing": {
        "name": "Phishing Dataset (HuggingFace)",
        "category": "multimodal",
        "url": "",
        "format": "parquet",
        "file": "hf_phishing/",
        "requires_key": False,
        "key_env": "",
        "url_column": "",
        "description": "800K+ URLs + 18K e-mails + 5.9K SMS (requer 'pip install datasets').",
        "license": "Aberto",
        "website": "https://huggingface.co/datasets/ealvaradob/phishing-dataset",
        "manual": True,
    },
}

# Datasets auto-baixáveis (sem autenticação)
AUTO_DOWNLOADABLE = [
    k for k, v in DATASET_REGISTRY.items()
    if not v.get("requires_key") and not v.get("manual") and v.get("url")
]

# Chunk size para carregamento de datasets grandes
DATASET_CHUNK_SIZE = 10_000
DATASET_DOWNLOAD_TIMEOUT = 300  # segundos (5 min, arquivos podem ter 50MB+)

# === Limites de API (tier gratuito) ===
VIRUSTOTAL_RATE_LIMIT = 4          # requisições por minuto
VIRUSTOTAL_DAILY_LIMIT = 500       # requisições por dia
URLSCAN_PRIVATE_DAILY_LIMIT = 100  # scans privados por dia
SAFEBROWSING_DAILY_LIMIT = 10_000  # requisições por dia

# === Análise heurística — pesos dos fatores ===
HEURISTIC_WEIGHTS = {
    "ip_instead_of_domain": 30,
    "http_no_encryption": 15,
    "typosquatting": 25,
    "suspicious_tld": 10,
    "excessive_subdomains": 10,
    "url_shortener": 12,
    "homoglyph_detected": 20,
    "suspicious_keywords": 10,
    "excessive_hyphens": 7,
    "excessive_length": 8,
    "php_extension_exposed": 5,
    "suspicious_query_string": 5,
    "random_subdomain_entropy": 12,
    "dataset_phishtank_match": 15,
    "dataset_urlhaus_match": 15,
    # === Novos fatores v1.1 ===
    "brand_in_path": 20,
    "punycode_idn": 22,
    "brand_as_subdomain": 18,
    "url_encoding_abuse": 12,
    "base64_payload": 15,
    "dga_domain": 18,
    "double_extension": 14,
    "open_redirect": 12,
    "data_uri": 25,
    "domain_too_young": 15,
    "keyboard_typosquatting": 20,
    "domain_entropy": 14,
    "suspicious_port": 8,
}

# === Palavras-gatilho de phishing ===
TRIGGER_WORDS = [
    "login", "verify", "account", "secure", "update", "bank",
    "confirm", "suspend", "alert", "password", "credential",
    "authenticate", "validate", "restore", "unlock", "expire",
    "urgent", "immediately", "billing", "invoice", "payment",
    "signin", "sign-in", "log-in", "webscr", "cmd",
]

# === Encurtadores de URL conhecidos ===
URL_SHORTENERS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "is.gd", "buff.ly", "rebrand.ly", "cutt.ly", "shorturl.at",
    "tiny.cc", "lnkd.in", "rb.gy", "qr.ae", "adf.ly",
]

# === TLDs de risco elevado ===
HIGH_RISK_TLDS = [
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "club",
    "work", "date", "racing", "win", "bid", "stream",
    "download", "loan", "men", "click", "link", "gdn",
    "review", "country", "science", "party", "cricket",
]

# === TLDs comuns (baixo risco) ===
COMMON_TLDS = [
    "com", "org", "net", "edu", "gov", "mil",
    "com.br", "org.br", "gov.br", "edu.br",
    "co.uk", "co.jp", "de", "fr", "eu", "io",
]

# === Thresholds de classificação ===
SCORE_SAFE_MAX = 25          # 0–25 = Seguro
SCORE_SUSPICIOUS_MAX = 65    # 26–65 = Suspeito
# 66–100 = Malicioso

# === Quiz ===
QUIZ_QUESTIONS_PER_ROUND = 10
QUIZ_DIFFICULTY_LEVELS = ["iniciante", "intermediario", "avancado"]

# === Disclaimer obrigatório ===
DISCLAIMER_TEXT = (
    "📋 Esta análise é educacional e baseada em heurísticas e datasets "
    "públicos. Não substitui soluções profissionais de segurança. "
    "Em caso de dúvida, não clique e consulte um profissional."
)

# === Logging ===
LOG_FILE = BASE_DIR / "cyberurl_analyst.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# === Layout de teclado QWERTY para detecção de typosquatting por proximidade ===
KEYBOARD_NEIGHBORS = {
    'q': 'wa', 'w': 'qeas', 'e': 'wrds', 'r': 'etdf', 't': 'ryfg',
    'y': 'tugh', 'u': 'yijh', 'i': 'uojk', 'o': 'iplk', 'p': 'ol',
    'a': 'qwsz', 's': 'awedxz', 'd': 'serfcx', 'f': 'drtgvc',
    'g': 'ftyhbv', 'h': 'gyujnb', 'j': 'huiknm', 'k': 'jiolm',
    'l': 'kop', 'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb',
    'b': 'vghn', 'n': 'bhjm', 'm': 'njk',
    '0': '9', '1': '2', '2': '13', '3': '24', '4': '35',
    '5': '46', '6': '57', '7': '68', '8': '79', '9': '80',
}

# === Extensões perigosas para detecção de extensão dupla ===
DANGEROUS_EXTENSIONS = [
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".msi",
    ".js", ".vbs", ".wsf", ".ps1", ".jar", ".py", ".sh",
    ".dll", ".sys", ".cpl", ".hta", ".inf", ".reg",
]

# === Extensões de documento (usadas em extensão dupla) ===
DOCUMENT_EXTENSIONS = [
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".csv", ".rtf", ".odt", ".jpg", ".png", ".gif",
    ".mp3", ".mp4", ".avi", ".zip", ".rar",
]

# === Padrões de open redirect ===
REDIRECT_PARAMS = [
    "redirect", "redirect_uri", "redirect_url", "return", "return_url",
    "returnto", "next", "url", "goto", "target", "redir", "destination",
    "continue", "forward", "out", "view", "link", "to",
]

# === Portas suspeitas (não padrão para HTTP/HTTPS) ===
SUSPICIOUS_PORTS = [
    "81", "82", "88", "443", "1080", "3128", "4443", "8000",
    "8008", "8080", "8081", "8443", "8888", "9090", "9443",
]

# === WHOIS ===
DOMAIN_YOUNG_DAYS = 30  # Domínios com menos de X dias são suspeitos

# === Análise cache ===
ANALYSIS_CACHE_MAX_SIZE = 500

# === UI ===
APP_NAME = "CyberURL Analyst"
APP_VERSION = "2.1.0"
