# 🛡️ CyberURL Analyst v3.0

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Ferramenta educacional para análise de URLs e domínios maliciosos com interface desktop em PyQt6.

O projeto combina heurísticas, datasets públicos, WHOIS, classificação opcional por Machine Learning e módulos de aprendizagem para explicar por que um link parece seguro, suspeito ou malicioso.

> ⚠️ Uso exclusivamente educacional. O projeto não substitui antivírus, EDR, firewall, SOC ou validações de segurança corporativas.

---

<img width="1943" height="1067" alt="image" src="https://github.com/user-attachments/assets/b73d7416-2836-4de6-99eb-46caadf8d95e" />


## Visão geral

- Interface desktop em PyQt6, sem dependência de navegador
- Temas claro e escuro com persistência local e alternância rápida na sidebar
- Build de executável com PyInstaller
- Análise local offline por padrão
- Consulta opcional a VirusTotal, URLScan.io e Google Safe Browsing
- 10 módulos na interface: Dashboard, Anatomia, Análise, Relatório, Quiz, Cenários, APIs, Datasets, Glossário e Configurações
- 128 testes automatizados validados localmente

---

## Requisitos

- Python 3.11 ou superior
- Windows 10/11 para gerar `.exe` com PyInstaller
- Linux ou macOS também são suportados para desenvolvimento e execução da aplicação Python

### Dependências principais

```txt
PyQt6>=6.8.0
requests>=2.31.0
python-dotenv>=1.0.0
tldextract>=5.1.0
validators>=0.22.0
python-whois>=0.9.4
keyring>=25.0.0
scikit-learn>=1.4.0
joblib>=1.3.0
Pillow>=10.0.0
Jinja2>=3.1.0
```

---

## Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd CyberUrl_Analyst
```

### 2. Crie e ative um ambiente virtual

```bash
# Criar
python -m venv venv

# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat

# Linux/macOS
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o `.env` se quiser APIs externas ou senha de acesso

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Variáveis mais importantes:

- `VIRUSTOTAL_API_KEY`
- `URLSCAN_API_KEY`
- `GOOGLE_SAFE_BROWSING_API_KEY`
- `PHISHTANK_API_KEY`
- `CYBERURL_PASSWORD`

Se o `.env` não existir, a aplicação continua funcionando com análise local.

---

## Execução

### Rodar em modo de desenvolvimento

```bash
python app.py
```

A aplicação abre uma janela desktop com navegação lateral, idioma configurável, alternância rápida de tema na sidebar e persistência local em `data/`.

### Gerar executável com PyInstaller

```bash
pip install -r requirements-dev.txt
python build.py
```

Saída esperada no Windows:

```txt
dist/CyberURL_Analyst/
```

Observações:

- O PyInstaller gera artefato nativo para o sistema onde o build roda.
- Para gerar `.exe`, execute o build em Windows.
- O script já empacota assets, templates, locales, cenários e amostras de datasets.

---

## Módulos da Interface

| # | Módulo | Descrição |
|---|--------|-----------|
| 0 | 🏠 Dashboard | Estatísticas, progresso, histórico persistido e conquistas |
| 1 | 🔍 Anatomia | Decomposição visual da URL e comparação entre domínios |
| 2 | 🛡️ Análise | URL única ou lote, com heurísticas, datasets, WHOIS e ML |
| 3 | 📊 Relatório | Visualização e exportação do último relatório em TXT/HTML |
| 4 | ❓ Quiz | Treinamento gamificado com leaderboard |
| 5 | 🎭 Cenários | Simulações de phishing com feedback didático |
| 6 | 🔌 APIs | Consulta opcional a serviços externos com consentimento |
| 7 | 📦 Datasets | Status e download de bases públicas de segurança |
| 8 | 📖 Glossário | Referência rápida de termos, golpes e conceitos |
| 9 | ⚙️ Configurações | Listas customizáveis, status do ML e feedback recebido |

---

## Como usar

### Analisar uma URL

1. Abra o módulo `🛡️ Análise`.
2. Cole a URL na aba de análise única.
3. Clique em `Analisar URL`.
4. Veja score, classificação, fatores, recomendações e relatório.

### Exportar relatório

1. Faça uma análise.
2. Abra `📊 Relatório`.
3. Exporte em TXT ou HTML.

### Baixar datasets

1. Abra `📦 Datasets`.
2. Use `Baixar Todos` para bases públicas automáticas.
3. Bases com chave ou download manual continuam indicadas no painel.

### Treinar o modelo ML

1. Coloque o dataset de treino compatível em `datasets/downloads/`.
2. Abra `⚙️ Configurações`.
3. Clique em `Treinar modelo`.

---

## Datasets e APIs

O projeto usa três camadas de evidência:

1. Heurística local
2. Datasets públicos locais ou baixados
3. APIs externas opcionais

### Datasets incluídos no repositório

- `datasets/phishtank_sample.csv`
- `datasets/urlhaus_sample.csv`
- `datasets/majestic_million_sample.csv`

### Downloads automáticos suportados

- URLhaus CSV
- URLhaus TXT
- OpenPhish
- Tranco Top 1M
- Majestic Million
- Cisco Umbrella
- feeds DGA suportados pelo registro central

### APIs externas opcionais

| API | Uso |
|-----|-----|
| VirusTotal | Verificação contra dezenas de engines |
| URLScan.io | Scan em sandbox e link de resultado |
| Google Safe Browsing | Checagem binária de segurança |

O envio para APIs externas só acontece após consentimento explícito dentro da interface.

---

## Arquitetura

Estrutura principal atual:

```txt
CyberUrl_Analyst/
├── app.py                  # Ponto de entrada PyQt6
├── build.py                # Build do executável com PyInstaller
├── ui/                     # Interface desktop
│   ├── main_window.py
│   ├── pages.py
│   ├── helpers.py
│   ├── resources.py
│   ├── state.py
│   ├── theme.py
│   ├── widgets.py
│   ├── workers.py
│   └── glossary_data.py
├── models/                 # Lógica de negócio e domínio
├── utils/                  # Utilitários puros
├── config/                 # Configuração central
├── templates/              # Template HTML de relatório
├── locales/                # PT / EN / ES
├── datasets/               # Amostras e downloads
├── data/                   # Persistência local JSON
└── tests/                  # Suíte automatizada
```

Separação adotada:

- `models/` e `utils/` permanecem independentes da UI
- `ui/` concentra apenas interface, estado visual e workers
- relatórios continuam sendo gerados em HTML/TXT no model
- persistência local continua em JSON dentro de `data/`

---

## Testes

```bash
pip install -r requirements-dev.txt

python -m unittest discover -s tests -v
python -m pytest tests -v

coverage run -m unittest discover -s tests -v
coverage report --skip-empty
```

A suíte atual cobre parsing, heurísticas, quiz, melhorias de segurança, persistência, datasets, ML, WHOIS e smoke tests da janela PyQt6.

O workflow em `.github/workflows/ci.yml` agora executa:

- testes em Linux com Qt headless
- smoke build PyInstaller em Windows

---

## Segurança e guardrails

- URLs suspeitas são exibidas em formato defanged
- análise local por padrão, sem abrir o link
- entradas são sanitizadas para remover possíveis dados sensíveis
- logging usa hash de URL, não texto puro
- rate limiting local para APIs externas
- chaves ficam em `.env`, não no código

---

## Contribuindo

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m pytest tests -v
```

Fluxo recomendado:

1. Crie uma branch de trabalho.
2. Faça mudanças pequenas e focadas.
3. Rode a suíte antes de abrir PR.
4. Se mexer na UI, valide também `python build.py` no Windows.

---

## Licença

MIT.

Use com responsabilidade e apenas para fins defensivos e educacionais.
