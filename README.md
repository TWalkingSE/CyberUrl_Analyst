# 🛡️ CyberURL Analyst v2.1

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?logo=streamlit&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

**Ferramenta educacional de análise de URLs e domínios maliciosos.**

Desenvolvida em Python com Streamlit, o CyberURL Analyst detecta, analisa e **ensina** usuários a identificar ameaças em URLs e domínios. O objetivo não é apenas mostrar *o quê* é perigoso, mas explicar *por quê* — formando pessoas que sabem se proteger sozinhas.

<img width="2522" height="967" alt="image" src="https://github.com/user-attachments/assets/b7f76419-6176-4322-b302-abcf5b70bf53" />



> ⚠️ Esta ferramenta é **exclusivamente educacional**. Não substitui soluções profissionais de segurança (antivírus, firewalls, SOC).

---

## 📋 Índice

- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Execução](#️-execução)
- [Módulos da Interface](#-módulos-da-interface)
- [Como Usar — Guia Rápido](#-como-usar--guia-rápido)
- [Datasets — Download e Configuração](#-datasets--download-e-configuração)
- [APIs Externas (Opcional)](#-apis-externas-opcional)
- [Arquitetura do Projeto](#️-arquitetura-do-projeto)
- [Motor de Análise — O Que É Detectado](#-motor-de-análise--o-que-é-detectado)
- [Guardrails de Segurança](#-guardrails-de-segurança)
- [Testes](#-testes)
- [Contribuindo](#-contribuindo)
- [Legislação e Licença](#-legislação-e-licença)

---

## 📋 Requisitos

- **Python 3.10+**
- **Sistema operacional:** Windows 10/11, Linux ou macOS
- **Conexão com internet** (apenas para download de datasets e APIs externas — a análise local funciona 100% offline)

### Dependências Python

```
streamlit>=1.32.0     # Interface web
requests>=2.31.0      # Chamadas HTTP (downloads e APIs)
python-dotenv>=1.0.0  # Carregamento de variáveis de ambiente (.env)
tldextract>=5.1.0     # Extração precisa de domínio e TLD
validators>=0.22.0    # Validação de URLs
python-whois>=0.9.4   # Consulta WHOIS para idade do domínio
keyring>=25.0.0       # Armazenamento seguro de credenciais
scikit-learn>=1.4.0   # Classificador ML (opcional)
joblib>=1.3.0         # Persistência do modelo ML
Pillow>=10.0.0        # Manipulação de imagens
Jinja2>=3.1.0         # Templates HTML para relatórios
```

---

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd CyberUrl_Analyst
```

### 2. Crie e ative um ambiente virtual

```bash
# Criar
python -m venv venv

# Ativar — Windows (PowerShell)
venv\Scripts\activate

# Ativar — Windows (CMD)
venv\Scripts\activate.bat

# Ativar — Linux/macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. (Opcional) Configure chaves de API

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Edite o arquivo `.env` com suas chaves (veja seção [APIs Externas](#-apis-externas-opcional)).

---

## ▶️ Execução

```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501` com a sidebar de navegação e 9 módulos disponíveis.

### Docker (opcional)

```bash
docker-compose up --build
```

---

## 🧩 Módulos da Interface

| # | Módulo | Descrição |
|---|--------|-----------|
| 0 | 🏠 **Dashboard** | Painel inicial com estatísticas consolidadas: análises realizadas, distribuição seguro/suspeito/malicioso, top findings, evolução no quiz, status dos datasets. |
| 1 | 🔍 **Anatomia da URL** | Decomposição visual de URLs com código de cores (protocolo, subdomínio, domínio, TLD, path, query). Tooltips educativos explicam cada parte. |
| 2 | 🛡️ **Motor de Análise** | Análise heurística completa com 25+ detectores + verificação contra datasets + WHOIS. Suporta URL única e **análise em lote** (batch). Mantém **histórico** e **cache**. |
| 3 | 📊 **Relatório Didático** | Relatório visual com veredicto (semáforo), explicações ponto a ponto, analogias, dicas, **comparação lado a lado** e **exportação HTML**. Auto-preenchido a partir do Motor de Análise. |
| 4 | ❓ **Quiz Interativo** | Treinamento gamificado com 3 níveis. Questões binárias, múltipla escolha e cenários com checklist. **Geração automática de questões** a partir dos datasets baixados. |
| 5 | 🎭 **Simulador de Cenários** | 5 cenários realistas de phishing (bancário, SMS/smishing, corporativo, redes sociais, e-mail legítimo). O usuário decide "clicaria ou não?" e recebe análise completa. |
| 6 | 🔌 **APIs Externas** | Painel para consultar VirusTotal, URLScan.io e Google Safe Browsing. Exige consentimento, implementa rate limiting e fallback. |
| 7 | 📦 **Datasets** | Gerenciamento visual de 11 datasets. Download automático com **barra de progresso em tempo real**, status de cada dataset, links para sites oficiais. |
| 8 | ⚙️ **Configurações** | **Wordlists customizáveis** (trigger words, marcas, TLDs, encurtadores), **tema escuro/claro**, preferências de idioma (PT/EN/ES). |

---

## 🎯 Como Usar — Guia Rápido

### Analisar uma URL

1. Abra o módulo **🛡️ Motor de Análise**
2. Cole a URL no campo de entrada (aba "URL Única")
3. Clique em **Analisar URL** (ou pressione Enter)
4. O resultado aparece com:
   - **Gauge visual** (0–100) com classificação Seguro/Suspeito/Malicioso
   - **URL defanged** (formato seguro hxxps[://])
   - **Lista de findings** com explicações, analogias e dicas
   - **Recomendações** de ação
5. O relatório é enviado automaticamente para o módulo **📊 Relatório Didático**

### Analisar várias URLs de uma vez

1. No Motor de Análise, clique na aba **Batch (Múltiplas)**
2. Cole várias URLs (uma por linha)
3. Clique em **Analisar Todas**
4. Cada URL é analisada sequencialmente e aparece no **histórico** lateral

### Aprender com o Quiz

1. Abra o módulo **❓ Quiz Interativo**
2. Selecione o nível de dificuldade
3. Clique em **Iniciar Quiz**
4. Classifique URLs como Seguras ou Maliciosas
5. Receba feedback imediato com explicação de cada resposta

### Praticar com Cenários Reais

1. Abra o módulo **🎭 Simulador de Cenários**
2. Selecione a categoria (Todos, Bancário, SMS, etc.)
3. Clique em **Iniciar Simulação**
4. Leia o cenário (e-mail/SMS simulado) e decida: "Clicaria?"
5. Veja a análise completa com todos os sinais de alerta

---

## 📦 Datasets — Download e Configuração

O projeto usa datasets públicos de segurança para alimentar a análise. O sistema funciona em 3 camadas:

1. **Amostras locais** (incluídas no repositório) — pequenas, para funcionar sem downloads
2. **Downloads automáticos** — datasets públicos sem autenticação, baixados pelo app
3. **Downloads manuais** — datasets que requerem API key ou conta em plataforma

### Download Automático (recomendado)

1. Abra o app → módulo **📦 Datasets**
2. Clique em **⬇️ Baixar Todos (Auto)**
3. O sistema baixará automaticamente os 7 datasets públicos disponíveis

| Dataset | Categoria | Tamanho | O que contém |
|---------|-----------|---------|-------------|
| **URLhaus (CSV)** | Maliciosas | ~3.7 MB | 19K+ URLs de malware (últimos 30 dias) |
| **URLhaus (Text)** | Maliciosas | ~790 KB | Lista simples de URLs de malware |
| **OpenPhish** | Maliciosas | ~15 KB | ~300-500 URLs de phishing (atualizado 12/12h) |
| **Tranco Top 1M** | Legítimas | ~20 MB | Top 1M domínios (substituto do Alexa) |
| **Majestic Million** | Legítimas | ~77 MB | Top 1M domínios por backlinks |
| **Cisco Umbrella** | Legítimas | ~22 MB | Top 1M domínios por DNS |
| **360 Netlab DGA** | DGA | variável | Domínios gerados por malware (59+ famílias) |

### Downloads que Requerem API Key

| Dataset | Como obter a chave | Variável no `.env` |
|---------|--------------------|--------------------|
| **PhishTank** | Registre-se em [phishtank.org/api_register.php](https://phishtank.org/api_register.php) | `PHISHTANK_API_KEY` |

Após configurar a chave no `.env`, use o botão **� Baixar** no painel de Datasets.

### Downloads Manuais (Plataformas Externas)

Estes datasets precisam ser baixados manualmente e colocados na pasta `datasets/downloads/`:

| Dataset | Onde baixar | Arquivo esperado |
|---------|-------------|------------------|
| **PhiUSIIL** (235K URLs, 54 features) | [UCI ML Repository](https://archive.ics.uci.edu/dataset/967) ou [Kaggle](https://www.kaggle.com/) | `datasets/downloads/phiusiil.csv` |
| **DGA Dataset** (160K domínios DGA) | [Kaggle](https://www.kaggle.com/datasets/cgivre/dga-dataset) | `datasets/downloads/dga_kaggle.csv` |
| **HuggingFace Phishing** (800K+ URLs + SMS) | Requer `pip install datasets` | Ver instrução abaixo |

**HuggingFace Phishing Dataset** (URLs + e-mails + SMS):
```bash
pip install datasets
python -c "from datasets import load_dataset; ds = load_dataset('ealvaradob/phishing-dataset', 'sms', trust_remote_code=True); print(ds)"
```

### Estrutura de Diretórios dos Datasets

```
datasets/
├── phishtank_sample.csv          # Amostra local (20 URLs) — inclusa no repo
├── urlhaus_sample.csv            # Amostra local (10 URLs) — inclusa no repo
├── majestic_million_sample.csv   # Amostra local (40 domínios) — inclusa no repo
└── downloads/                    # Datasets baixados (NÃO versionados)
    ├── urlhaus_recent.csv        # URLhaus completo
    ├── urlhaus_urls.txt          # URLhaus texto
    ├── openphish_feed.txt        # OpenPhish feed
    ├── tranco_top1m.csv          # Tranco Top 1M
    ├── majestic_million.csv      # Majestic Million completo
    ├── umbrella_top1m.csv        # Cisco Umbrella
    ├── netlab360_dga.txt         # 360 Netlab DGA
    ├── phishtank_online.csv      # PhishTank (requer API key)
    ├── phiusiil.csv              # PhiUSIIL (download manual)
    └── dga_kaggle.csv            # DGA Kaggle (download manual)
```

> **Nota:** A pasta `datasets/downloads/` está no `.gitignore`. Datasets grandes (dezenas de MB) nunca são versionados.

---

## 🔌 APIs Externas (Opcional)

O sistema funciona 100% offline com análise heurística + datasets. APIs externas são **enriquecimento opcional**.

| API | Tier Gratuito | O que faz | Variável no `.env` |
|-----|---------------|-----------|---------------------|
| **VirusTotal v3** | 4 req/min, 500/dia | Verifica URL contra 70+ antivírus | `VIRUSTOTAL_API_KEY` |
| **URLScan.io** | 100 scans privados/dia | Scan em sandbox com screenshot | `URLSCAN_API_KEY` |
| **Google Safe Browsing v4** | 10.000 req/dia | Verificação seguro/inseguro | `GOOGLE_SAFE_BROWSING_API_KEY` |

### Como configurar

1. Registre-se no serviço desejado e obtenha a API key
2. Edite o arquivo `.env`:
   ```
   VIRUSTOTAL_API_KEY=sua_chave_aqui
   URLSCAN_API_KEY=sua_chave_aqui
   GOOGLE_SAFE_BROWSING_API_KEY=sua_chave_aqui
   ```
3. No app, vá ao módulo **🔌 APIs Externas** e cole a URL para consultar

> **Consentimento:** Na primeira consulta, o app exibirá um diálogo informando que a URL será enviada para servidores externos. Você precisa aprovar antes de prosseguir.

---

## 🏗️ Arquitetura do Projeto

Padrão **Model-View** com separação clara entre lógica de negócio e interface gráfica.

```
CyberUrl_Analyst/
│
├── app.py                           # Ponto de entrada — Router, auth, sidebar
├── .env.example                     # Template de chaves de API
├── requirements.txt                 # Dependências Python
├── Dockerfile                       # Build Docker
├── docker-compose.yml               # Deploy com Docker Compose
│
├── .streamlit/
│   └── config.toml                  # Configuração do Streamlit (tema, servidor)
│
├── views/                           # CAMADA VIEW — Páginas Streamlit (v2.0)
│   ├── __init__.py                  # Exporta todas as páginas
│   ├── resources.py                 # Recursos cacheados (parser, analyzer, ML, etc.)
│   ├── helpers.py                   # Helpers de UI (T(), render_finding, run_analysis)
│   ├── page_dashboard.py            # Dashboard com gráficos e histórico paginado
│   ├── page_anatomy.py              # Decomposição visual de URLs
│   ├── page_analysis.py             # Motor de análise (URL única e batch)
│   ├── page_report.py               # Relatório didático com exportação
│   ├── page_quiz.py                 # Quiz interativo com leaderboard
│   ├── page_scenarios.py            # Simulador de cenários de phishing
│   ├── page_apis.py                 # APIs externas com rate limiting
│   ├── page_datasets.py             # Gerenciamento de datasets
│   └── page_settings.py             # Configurações, ML, feedback
│
├── config/
│   └── settings.py                  # Configurações centrais (pesos, TLDs, datasets, UI)
│
├── models/                          # CAMADA MODEL — Lógica de negócio
│   ├── url_parser.py                # Decomposição anatômica de URLs (tldextract)
│   ├── heuristic_analyzer.py        # 25+ detectores heurísticos com explicações
│   ├── dataset_checker.py           # Verificação contra datasets carregados
│   ├── dataset_manager.py           # Gerenciador centralizado de múltiplos datasets
│   ├── api_client.py                # Integração VirusTotal/URLScan/SafeBrowsing
│   ├── defanger.py                  # Conversão URL → formato seguro (hxxps[://])
│   ├── whois_checker.py             # Consulta WHOIS para idade do domínio
│   ├── quiz_engine.py               # Lógica do quiz (questões, scoring, progressão)
│   ├── report_generator.py          # Geração de relatórios estruturados
│   ├── persistence.py               # Persistência JSON (histórico, stats, leaderboard)
│   ├── scenarios.py                 # Dados dos cenários de phishing
│   ├── ml_classifier.py             # Classificador ML (Random Forest)
│   └── analysis_cache.py            # Cache LRU para evitar re-análise
│
├── utils/
│   ├── sanitizer.py                 # Sanitização de entradas (PII, formato)
│   ├── logger.py                    # Logging seguro com rotação automática
│   ├── rate_limiter.py              # Controle de rate limit para APIs
│   ├── dataset_downloader.py        # Download de datasets com progresso
│   └── i18n.py                      # Internacionalização (PT/EN/ES)
│
├── datasets/                        # Amostras locais + downloads
│   ├── *_sample.csv                 # Amostras (versionadas)
│   └── downloads/                   # Datasets completos (NÃO versionados)
│
├── data/                            # Dados persistentes (gitignored)
│   ├── analysis_history.json
│   ├── session_stats.json
│   ├── quiz_leaderboard.json
│   └── user_feedback.json
│
├── build.py                         # Script de empacotamento (experimental)
│
└── tests/                           # 102 testes (92 unitários + 10 integração)
    ├── test_defanger.py
    ├── test_url_parser.py
    ├── test_heuristic_analyzer.py
    ├── test_quiz_engine.py
    ├── test_v11_features.py
    └── test_app_integration.py      # Testes de integração Streamlit
```

### Regra de Ouro da Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│  A camada VIEW nunca recebe URLs no formato original.        │
│                                                              │
│  Model (URL original) ──► Defanger ──► View (URL defanged)   │
│                                                              │
│  Se uma URL é classificada como "suspicious" ou "malicious", │
│  ela SÓ existe no formato original dentro da camada Model.   │
│  A View SEMPRE recebe o formato defanged via URLDefanger.    │
└──────────────────────────────────────────────────────────────┘
```

### Integração entre Módulos

```
Motor de Análise ──(session_state)──► Relatório Didático
       │
       ├── Heuristic Analyzer (25+ detectores)
       ├── Dataset Checker (amostras + downloads + DGA)
       ├── WHOIS Checker (idade do domínio)
       ├── ML Classifier (Random Forest)
       └── Analysis Cache (LRU, SHA-256 keyed)
```

---

## 🔬 Motor de Análise — O Que É Detectado

O motor heurístico analisa **25+ fatores** em cada URL, agrupados por categoria:

### Detecção Básica
- **IP em vez de domínio** — sites legítimos nunca usam IP direto
- **HTTP sem criptografia** — conexão insegura
- **Porta não-padrão** — portas como 8080, 8888 indicam servidores atípicos
- **Comprimento excessivo** — URLs muito longas escondem destino real
- **Extensão de arquivo exposta** — `.php`, `.asp`, `.cgi` visíveis

### Detecção de Phishing e Impersonação
- **Typosquatting** — domínios similares a marcas (paypa1.com, arnazon.com)
- **Typosquatting por teclado** — erros de digitação intencionais (googke.com)
- **Marca no path** — `/paypal/login` em servidor desconhecido
- **Marca como subdomínio** — `paypal.evil-site.com`
- **Homógrafos Unicode** — caracteres cirílicos/gregos imitando letras latinas (~70 caracteres mapeados)
- **Punycode/IDN** — domínios internacionalizados usados para enganar
- **Palavras-gatilho** — login, verify, secure, account, urgent, etc.
- **Excesso de hífens** — domínios com muitos hífens são suspeitos

### Detecção Avançada
- **DGA (Domain Generation Algorithm)** — domínios aleatórios gerados por malware (entropia + n-gramas + proporção consoante/vogal)
- **Entropia do domínio** — sequências aleatórias de caracteres
- **Entropia do subdomínio** — subdomínios gerados automaticamente
- **URL encoding abusivo** — excesso de `%XX` para ofuscar
- **Base64 em query strings** — payloads codificados escondidos
- **Extensão dupla** — `nota.pdf.exe` (lobo vestido de ovelha)
- **Open redirect** — `?redirect=https://evil.com`
- **Data URI / javascript:** — esquemas que executam código no navegador

### Verificação contra Datasets
- **PhishTank** — URL/domínio em banco de phishing confirmado
- **URLhaus** — URL/domínio em banco de malware
- **Majestic/Tranco/Umbrella** — domínio em listas de sites legítimos
- **DGA feeds** — domínio em feeds de DGA conhecidos

### Enriquecimento
- **WHOIS** — idade do domínio (< 30 dias = suspeito)
- **TLD de risco** — extensões como .tk, .ml, .xyz, .gq
- **Encurtadores de URL** — bit.ly, tinyurl, t.co (destino oculto)

### Classificação ML (Random Forest)
- **Modelo treinado** com até 100K URLs do dataset PhiUSIIL (235K amostras disponíveis)
- **25 features numéricas** extraídas da URL (comprimento, entropia, dígitos, TLD, subdomínios, etc.)
- **Predição com probabilidade** — retorna % de chance de ser maliciosa
- **Complementar à heurística** — quando ambos concordam, a confiança é maior
- **Treinamento via UI** — botão "🧠 Treinar Modelo" no módulo ⚙️ Configurações
- **Modelo persistido** — salvo em `models/trained_model.joblib`, carregado automaticamente

#### Como treinar o modelo ML

1. Baixe o dataset **PhiUSIIL** do [Kaggle](https://www.kaggle.com/) ou [UCI](https://archive.ics.uci.edu/dataset/967) e coloque em `datasets/downloads/`
2. Abra o app → módulo **⚙️ Configurações**
3. Role até a seção **🤖 Classificador ML**
4. Clique em **🧠 Treinar Modelo**
5. Aguarde ~30-60 segundos (extrai features de 100K URLs)
6. O modelo será salvo e usado automaticamente em todas as análises futuras

Cada finding inclui: **explicação didática**, **analogia do cotidiano**, **dica de proteção** e **score de confiança** (0.0–1.0).

---

## 🔒 Guardrails de Segurança

| Guardrail | Implementação |
|-----------|---------------|
| **Defanging automático** | URLs suspeitas/maliciosas exibidas como `hxxps[://]example[.]com` |
| **Links não-clicáveis** | URLs maliciosas exibidas como texto, sem hiperlinks |
| **Sanitização de entrada** | Detecção automática de e-mail, CPF, tokens, credenciais na URL |
| **Análise offline por padrão** | Nenhuma conexão externa sem consentimento explícito do usuário |
| **Logging seguro** | URLs registradas como hash SHA-256, nunca em texto puro |
| **Rate limiting** | Controle local de cotas por minuto/dia para cada API |
| **Chaves seguras** | API keys em `.env` (gitignored), nunca hardcoded |
| **Consentimento para APIs** | Diálogo antes de enviar URL para servidores externos |
| **Anti-uso ofensivo** | Sem exportação em massa de URLs, sem geração de phishing |
| **Disclaimer permanente** | Toda análise inclui aviso educacional |

---

## 🧪 Testes

122 testes unitários cobrindo todos os modelos:

```bash
# Com unittest (incluso no Python)
python -m unittest discover -s tests -v

# Ou com pytest (se instalado)
pip install pytest
python -m pytest tests/ -v
```

### Cobertura de Testes

| Arquivo de Teste | O que testa | Qtd |
|------------------|-------------|-----|
| `test_defanger.py` | Defanging, refanging, roundtrip | 14 |
| `test_url_parser.py` | Parsing de URLs, breakdown visual | 9 |
| `test_heuristic_analyzer.py` | Classificação, features, findings | 14 |
| `test_quiz_engine.py` | Quiz, scoring, estatísticas | 13 |
| `test_v11_features.py` | Novos detectores v1.1+ (brand in path, DGA, etc.) | 42 |
| `test_improvements.py` | Melhorias v2.1 (persistence, sanitizer, i18n, Jinja2, API) | 20 |

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um **fork** do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/minha-feature`)
3. Commit suas alterações (`git commit -m 'feat: minha feature'`)
4. Push para a branch (`git push origin feature/minha-feature`)
5. Abra um **Pull Request**

### Antes de enviar

```bash
# Rode os testes
python -m pytest tests/ -v
```

---

## 📜 Legislação e Licença

Este projeto é distribuído sob a licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

Esta ferramenta é exclusivamente para fins **educacionais e de pesquisa**. O uso para fins ofensivos é ilegal e antiético.

### Legislação Brasileira Aplicável

- **Lei 12.737/2012** (Lei Carolina Dieckmann) — tipifica crimes informáticos
- **Lei 13.709/2018** (LGPD) — proteção de dados pessoais
- **Lei 12.965/2014** (Marco Civil da Internet) — princípios de uso da internet

### Datasets e Licenças

| Dataset | Licença |
|---------|---------|
| PhishTank | Gratuito com registro |
| URLhaus | CC0 |
| OpenPhish | Community feed gratuito |
| Tranco | Gratuito, aberto |
| Majestic Million | Gratuito |
| Cisco Umbrella | Gratuito |
| PhiUSIIL | CC BY 4.0 |

> Verifique a licença atualizada de cada dataset antes de uso comercial. Todos permitem uso acadêmico.

---

## 📦 Empacotamento como Executável (Experimental)

> ⚠️ Streamlit não tem suporte oficial ao PyInstaller. Para deploy, prefira **Docker** (`docker-compose up`) ou execução direta (`streamlit run app.py`).

```bash
pip install pyinstaller
python build.py
```

