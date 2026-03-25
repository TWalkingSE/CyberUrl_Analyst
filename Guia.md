# 🛡️ Guia do Usuário — CyberURL Analyst

Este guia explica como usar o CyberURL Analyst de forma simples, mesmo que você não tenha experiência com programação ou segurança digital.

---

## O que é o CyberURL Analyst?

É uma ferramenta que analisa links (URLs) e te ajuda a identificar se são **seguros**, **suspeitos** ou **maliciosos** (perigosos). Além de mostrar o resultado, ela **explica o motivo** de cada classificação — para que você aprenda a se proteger sozinho.

> **Importante:** Esta ferramenta é educacional. Ela não substitui antivírus ou outras soluções de segurança profissionais.

---

## Como abrir a ferramenta

### Pré-requisitos

Você precisa ter instalado:
- **Python 3.10 ou superior** — [Baixe aqui](https://www.python.org/downloads/)
- As dependências do projeto (veja abaixo)

### Passo a passo

1. Abra o **terminal** (Prompt de Comando ou PowerShell no Windows)
2. Navegue até a pasta do projeto:
   ```
   cd caminho/para/CyberUrl_Analyst
   ```
3. Ative o ambiente virtual:
   ```
   # Windows (PowerShell)
   venv\Scripts\Activate.ps1

   # Windows (CMD)
   venv\Scripts\activate.bat

   # Linux/macOS
   source venv/bin/activate
   ```
4. Instale as dependências (só precisa fazer uma vez):
   ```
   pip install -r requirements.txt
   ```
5. Inicie a aplicação:
   ```
   streamlit run app.py
   ```
6. O navegador abrirá automaticamente em `http://localhost:8501`

---

## Navegação

A interface tem uma **barra lateral esquerda** (sidebar) com 9 módulos. Clique em qualquer um para navegar:

| Ícone | Módulo | Para que serve |
|-------|--------|---------------|
| 🏠 | **Dashboard** | Página inicial com estatísticas e histórico |
| 🔍 | **Anatomia da URL** | Mostra cada parte de um link com cores |
| 🛡️ | **Motor de Análise** | Analisa se um link é seguro ou perigoso |
| 📊 | **Relatório** | Relatório detalhado da última análise |
| ❓ | **Quiz** | Teste seus conhecimentos sobre links |
| 🎭 | **Cenários** | Simula situações reais de golpes |
| 🔌 | **APIs Externas** | Consulta serviços como VirusTotal |
| 📦 | **Datasets** | Gerencia bancos de dados de ameaças |
| ⚙️ | **Configurações** | Ajustes avançados |

No final da sidebar, você pode trocar o **idioma** (Português, English, Español).

---

## Módulo por módulo

### 🏠 Dashboard

A página inicial mostra:
- **Quantas análises** você já fez
- **Distribuição** das classificações (seguro/suspeito/malicioso) em gráfico
- **Histórico** das últimas análises com paginação
- **Busca e filtro** — pesquise URLs no histórico e filtre por classificação (Segura/Suspeita/Maliciosa)

Não precisa fazer nada aqui — os dados são preenchidos automaticamente conforme você usa a ferramenta.

---

### 🔍 Anatomia da URL

Aqui você aprende como um link é composto. Cole qualquer URL e clique em **Analisar Anatomia**.

A ferramenta vai separar o link em partes coloridas:
- 🟢 **Protocolo** (https://) — a forma de conexão
- 🔵 **Subdomínio** (www.) — parte antes do domínio principal
- 🟡 **Domínio** (google) — o nome do site
- 🟠 **TLD** (.com) — a extensão do domínio
- 🟣 **Porta** (:8080) — canal de comunicação (raro em sites normais)
- 🔴 **Path** (/pagina) — o caminho dentro do site
- 🔴 **Query** (?q=teste) — parâmetros enviados ao site

**Dica:** Se você recebeu um link estranho, cole aqui primeiro para entender o que cada parte significa antes de clicar.

---

### 🛡️ Motor de Análise

Este é o módulo principal. Aqui você analisa links para saber se são perigosos.

**Como usar:**
1. Cole o link no campo "URL"
2. Clique em **Analisar URL**
3. Aguarde o resultado

**O resultado mostra:**
- **Score de 0 a 100** — quanto maior, mais perigoso
  - 🟢 0–25 = **Seguro**
  - 🟡 26–65 = **Suspeito**
  - 🔴 66–100 = **Malicioso**
- **URL defanged** — o link em formato seguro (não clicável)
- **Lista de fatores** — cada problema encontrado com explicação
- **Recomendações** — o que fazer baseado no resultado

**Análise em lote:** Na aba "Batch", cole vários links (um por linha) para analisar todos de uma vez.

Após a análise, você pode dar **feedback** (👍 ou 👎) para nos ajudar a melhorar.

---

### 📊 Relatório Didático

Mostra o relatório completo da **última análise** feita no Motor de Análise. Você pode:
- **Baixar em TXT** — texto simples para compartilhar
- **Baixar em HTML** — formato visual para abrir no navegador

---

### ❓ Quiz Interativo

Teste seus conhecimentos sobre links seguros e maliciosos!

**Como funciona:**
1. Escolha o nível: **Iniciante**, **Intermediário** ou **Avançado**
2. Clique em **Iniciar Quiz**
3. Para cada URL mostrada, classifique como **Segura** ou **Maliciosa**
4. Receba feedback imediato com explicação
5. Ao final de 10 questões, veja seu resultado

**Leaderboard:** Após terminar, salve seu nome para aparecer no ranking!

Você pode **exportar** seu resultado em CSV para guardar.

---

### 🎭 Simulador de Cenários

Simula situações reais de golpes (phishing) que você pode encontrar no dia a dia:
- E-mails falsos de bancos
- Mensagens de WhatsApp com links
- SMS de promoções falsas
- Notificações falsas do governo
- E até exemplos legítimos (para treinar sua percepção)

**Como funciona:**
1. Escolha uma **categoria** (ou "Todos")
2. Opcionalmente, ative o **modo Apresentação** (fontes maiores, ideal para projetar)
3. Clique em **Iniciar Simulação**
4. Leia a mensagem simulada e decida: **"Eu clicaria neste link?"**
5. Veja a análise com todos os sinais de alerta

---

### 🔌 APIs Externas

Consulta serviços de segurança online para obter uma segunda opinião sobre um link.

**Serviços disponíveis:**
- **VirusTotal** — verifica contra 70+ antivírus
- **URLScan.io** — faz um scan visual do site
- **Google Safe Browsing** — verifica se é seguro

> **Atenção:** Este módulo envia o link para servidores externos. Você precisa concordar antes de prosseguir.

Para usar, você precisa de **chaves de API** (gratuitas). Veja o arquivo `.env.example` para saber como configurar.

---

### 📦 Datasets

Gerencia os bancos de dados usados pela ferramenta para verificar links.

- Clique em **Baixar Todos** para baixar os datasets públicos automaticamente
- Cada dataset mostra: nome, descrição, tamanho e se está atualizado
- Alguns datasets requerem download manual (indicado com 📥)

Quanto mais datasets você tiver, mais precisa será a análise.

---

### ⚙️ Configurações

Ajustes avançados:
- **Trigger Words** — palavras que indicam phishing (login, verify, urgent...)
- **TLDs de Risco** — extensões suspeitas (.tk, .xyz, .top...)
- **Encurtadores** — serviços que escondem o destino (bit.ly, tinyurl...)
- **Classificador ML** — treine um modelo de inteligência artificial para melhorar as análises

---

## Perguntas Frequentes

### A ferramenta acessa os links que eu colo?
**Não.** A análise é 100% local por padrão. O link é analisado por padrões e heurísticas, sem acessar o site. A única exceção é o módulo **APIs Externas**, que exige seu consentimento explícito.

### O que significa "URL defanged"?
É o link convertido para um formato seguro que não pode ser clicado acidentalmente. Exemplo:
- Original: `https://evil.com`
- Defanged: `hxxps[://]evil[.]com`

### Posso usar no celular?
Sim! Como é uma aplicação web, funciona em qualquer navegador, inclusive no celular. Basta acessar `http://localhost:8501` (ou o IP do computador onde está rodando).

### Preciso de internet?
Apenas para baixar datasets e usar APIs externas. A análise heurística funciona 100% offline.

### Como protejo a ferramenta com senha?
Edite o arquivo `.env` e adicione:
```
CYBERURL_PASSWORD=sua_senha_aqui
```
Ao abrir a ferramenta, será solicitada a senha.

### Como mudo o idioma?
Na barra lateral (sidebar), no final, há um seletor de idioma (🌐). Escolha entre Português, English ou Español.

---

## Glossário

| Termo | Significado |
|-------|------------|
| **URL** | Endereço de um site (ex.: https://google.com) |
| **Domínio** | Nome principal do site (ex.: google.com) |
| **TLD** | Extensão do domínio (ex.: .com, .br, .org) |
| **Phishing** | Golpe que tenta roubar seus dados fingindo ser um site legítimo |
| **Heurística** | Conjunto de regras para detectar padrões suspeitos |
| **Dataset** | Banco de dados com URLs conhecidas (maliciosas ou legítimas) |
| **Defanging** | Converter um link para formato seguro (não clicável) |
| **DGA** | Domínios gerados automaticamente por malware |
| **WHOIS** | Registro público com informações sobre quem é dono de um domínio |
| **Score** | Pontuação de risco de 0 (seguro) a 100 (malicioso) |
| **ML** | Machine Learning — inteligência artificial que aprende com dados |

---

## Dicas de Segurança

1. **Desconfie de urgência** — "Sua conta será bloqueada em 24h!" é quase sempre golpe
2. **Verifique o domínio** — `paypal.com` é diferente de `paypa1.com` (um usa L, outro usa 1)
3. **Não clique em links de SMS** — bancos legítimos nunca enviam links por SMS
4. **Olhe o protocolo** — sites seguros usam `https://` (com S)
5. **Links encurtados escondem o destino** — use esta ferramenta para verificar antes
6. **Na dúvida, não clique** — acesse o site digitando diretamente no navegador

---

## Novidades da versão 2.1

- **Busca no histórico** — agora é possível pesquisar e filtrar análises anteriores no Dashboard
- **Modo offline** — quando sem internet, a página de APIs externas mostra um aviso em vez de travar
- **Relatórios mais seguros** — a exportação HTML agora usa templates Jinja2 com auto-escape
- **Cenários atualizados** — os cenários de phishing agora são carregados de um arquivo externo (mais fácil de atualizar)
- **Traduções em JSON** — as traduções (PT/EN/ES) agora ficam em arquivos JSON separados em `locales/`
- **20 novos testes** — mais confiabilidade nas atualizações futuras
