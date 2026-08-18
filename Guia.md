# 🛡️ Guia do Usuário — CyberURL Analyst Desktop

Este guia foi escrito para quem quer usar a ferramenta sem precisar entender programação.

O CyberURL Analyst analisa links e explica, em linguagem simples, por que uma URL parece segura, suspeita ou maliciosa.

> Importante: a ferramenta é educacional. Ela ajuda a aprender e revisar sinais de risco, mas não substitui antivírus ou soluções profissionais de segurança.

---

## Como abrir a ferramenta

Você tem duas formas de usar:

### Opção 1. Executável

Se alguém já gerou o executável para você, basta abrir o arquivo `.exe` dentro da pasta `dist/CyberURL_Analyst/`.

### Opção 2. Rodar pelo Python

1. Abra o terminal.
2. Entre na pasta do projeto:

   ```txt
   cd caminho/para/CyberUrl_Analyst
   ```

3. Ative o ambiente virtual:

   ```txt
   venv\Scripts\Activate.ps1
   ```

4. Instale as dependências, se ainda não fez isso:

   ```txt
   pip install -r requirements.txt
   ```

5. Abra a aplicação:

   ```txt
   python app.py
   ```

Uma janela desktop será aberta.

---

## Navegação

A janela tem um menu lateral com 10 páginas:

| Ícone | Módulo | Para que serve |
|-------|--------|---------------|
| 🏠 | Dashboard | Estatísticas, histórico e progresso |
| 🔍 | Anatomia | Mostra cada parte da URL |
| 🛡️ | Análise | Analisa um link ou uma lista de links |
| 📊 | Relatório | Exibe e exporta o último relatório |
| ❓ | Quiz | Treino gamificado |
| 🎭 | Cenários | Simulações realistas de golpes |
| 🔌 | APIs | Consulta serviços externos |
| 📦 | Datasets | Gerencia bases públicas de ameaças |
| 📖 | Glossário | Explica termos e conceitos |
| ⚙️ | Configurações | Ajustes avançados e status do modelo ML |

Na parte inferior do menu lateral existe um seletor de idioma.

---

## Módulo por módulo

### 🏠 Dashboard

Mostra:

- quantas análises já foram feitas
- quantos resultados saíram como seguro, suspeito ou malicioso
- histórico salvo no disco
- progresso no quiz e nos cenários
- conquistas liberadas

---

### 🔍 Anatomia da URL

Cole um link e clique em `Analisar anatomia`.

Você verá:

- o link como se estivesse na barra do navegador
- a decomposição por partes e cores
- protocolo, subdomínio, domínio, TLD, porta, path, query e fragmento
- uma comparação visual entre um domínio legítimo e um suspeito

Isso é útil para treinar o olho antes de clicar em links duvidosos.

---

### 🛡️ Análise

É o módulo principal.

Você pode:

- analisar uma URL única
- analisar várias URLs de uma vez
- ver o relatório na própria tela
- registrar feedback se a análise foi útil ou não

O resultado mostra:

- score de risco
- classificação final
- fatores encontrados
- recomendações do que fazer

---

### 📊 Relatório

Mostra o último resultado gerado na página de análise.

Você pode exportar em:

- TXT
- HTML

---

### ❓ Quiz

Treinamento com 10 perguntas por rodada.

Você escolhe a dificuldade ou usa o modo automático.

Ao final, a ferramenta mostra:

- acertos
- precisão
- melhor sequência
- opção de salvar no leaderboard
- opção de exportar o resultado

---

### 🎭 Cenários

Simula golpes parecidos com os do mundo real:

- e-mails falsos
- mensagens de SMS
- abordagens em apps de conversa
- situações bancárias ou corporativas

Você decide se clicaria ou não. Depois a ferramenta explica todos os sinais de alerta.

---

### 🔌 APIs Externas

Usa serviços online para obter uma segunda opinião sobre o link.

Serviços suportados:

- VirusTotal
- URLScan.io
- Google Safe Browsing

Antes de usar, você precisa concordar com o envio da URL para esses serviços.

Se não quiser usar APIs externas, tudo bem: a análise local continua funcionando.

---

### 📦 Datasets

Aqui você baixa e atualiza bases públicas usadas pela análise.

Use:

- `Baixar Todos` para os datasets automáticos
- `Atualizar` para um dataset específico

Quanto mais bases disponíveis, melhor tende a ser a verificação local.

---

### 📖 Glossário

Serve como referência rápida.

Você pode buscar termos como:

- phishing
- typosquatting
- homógrafo
- WHOIS
- DGA
- Random Forest

---

### ⚙️ Configurações

Permite:

- ajustar trigger words
- revisar TLDs de risco
- ajustar lista de encurtadores
- ver o estado do modelo ML
- treinar o classificador localmente
- ver estatísticas de feedback

---

## Perguntas frequentes

### A ferramenta abre o site que eu colei?

Não. A análise local trabalha sobre a URL e seus padrões, não sobre a navegação para o site.

### Preciso de internet?

Somente para:

- baixar datasets
- consultar APIs externas
- fazer algumas consultas online opcionais

A análise heurística local funciona offline.

### Posso proteger a ferramenta com senha?

Sim. Crie um arquivo `.env` e defina:

```txt
CYBERURL_PASSWORD=sua_senha
```

Ao abrir a aplicação, será pedida a senha.

### Posso usar no celular?

Não como aplicação nativa. Esta versão foi feita para desktop com PyQt6.

### Como gerar o executável?

No Windows:

```txt
pip install -r requirements-dev.txt
python build.py
```

---

## Dicas rápidas de segurança

1. Desconfie de urgência exagerada.
2. Verifique o domínio, não só o cadeado.
3. Links encurtados escondem o destino.
4. Cuidado com letras trocadas: `paypal.com` não é `paypa1.com`.
5. Se a dúvida continuar, não clique. Digite o endereço oficial manualmente.

---

## Novidades da versão 3.0

- interface totalmente migrada para PyQt6
- geração de executável com PyInstaller sem depender de navegador
- remoção completa da antiga interface web
- limpeza de arquivos legados da interface anterior
- CI atualizada para testes headless e smoke build do executável
