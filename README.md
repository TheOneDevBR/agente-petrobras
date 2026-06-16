# AgentePetrobras — Preparador autoevolutivo (CESGRANRIO/CEBRASPE)

Sistema de estudo para concursos da Petrobras com **LLM local** (Ollama), banco de
**~1120 questões reais**, **prática de recuperação espaçada** (a técnica de maior
efeito comprovado), **RAG sobre apostilas**, monitoramento de novidades e
**autoevolução**. Funciona como **app web** (React + FastAPI) e também por **CLI**.

> Ancorado em evidência (Dunlosky 2013; Hattie & Donoghue 2021; *testing effect*
> g≈0,70): a ação padrão do app é **praticar** (recall ativo + espaçamento), com
> coach socrático explicando o porquê e o RAG das apostilas dando contexto.

## Arquitetura

```
Frontend (React/Vite)  ──HTTP──►  Backend (FastAPI)        ──►  LLM local (Ollama)
 src/components/                   cli_python/api.py             local_llm.py
 ├─ Plano de Hoje                  ├─ /pratica/*  (loop)         │
 ├─ Praticar (recall + voz)        ├─ /simulado/*                ├─ treino.py   (banco)
 ├─ Simulado (cronometrado)        ├─ /maestria · /plano-hoje    ├─ coaching.py (Elo)
 ├─ Maestria (Elo)                 ├─ /intel      (radar)        ├─ sm2.py      (espaçada)
 ├─ Radar (novidades)              ├─ /perguntar  (coach+RAG)    ├─ rag.py      (apostilas)
 ├─ Dashboard ao vivo              └─ CORS p/ o frontend         ├─ erros.py    (C/A/B/T)
 └─ Coach Chat                                                   └─ evolucao/   (5 camadas 🧬)

CLI/Batch: agente.py (coach) · coletor/ (inteligência) · importar_questoes.py
           (provas→exercícios) · instagram.py (radar) · ciclo_evolutivo.py
Automação: rotina_noturna.ps1  (coletor + radar + ciclo, agendado)

Persistência local (gitignored): dados/  ·  Obsidian_Vault/  ·  rag_index/
```

### O ciclo de aprendizagem

```
Plano de Hoje ─► Praticar (adaptativo ~75%) ─► feedback (porquê + coach + apostila)
      ▲                     │                          │
      │                     ├─ SM-2 agenda revisão ──► servida primeiro
      │                     ├─ erro C/A/B/T
      └──── Elo atualizado ─┘ ──► coach prioriza o foco real ──► ciclo evolutivo (afina)
```

## Guia de uso ponta a ponta (do zero ao estudo)

### 1. Instalar (uma vez)

```powershell
cd "<projeto>"

# Python isolado (recomendado)
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r cli_python/requirements.txt
playwright install chromium          # opcional — render de páginas JS

# LLM local (Ollama)
ollama pull qwen2.5:1.5b             # chat rápido
ollama pull qwen2.5:7b               # coleta/ciclo (qualidade) — requer GPU 2.4GB+

# Frontend
npm install
```

> ⚠ Use `127.0.0.1:11434` em vez de `localhost` se tiver Docker + Ollama nativo
> (IPv6 do wslrelay não encaminha `/v1/chat/completions`). 7B com GPU via Docker:
> `docker compose up -d`.

### 2. Ligar o backend (API + Ollama)

```powershell
ollama serve                                       # se ainda não estiver rodando
.\.venv\Scripts\python.exe cli_python/api.py       # API em http://127.0.0.1:8000
```

### 3. Ligar o app web

```powershell
npm run dev                                        # http://localhost:5173
```

No navegador, faça o **Diagnóstico Inicial** (aba *Coach Chat*) — isso cria seu
perfil e **desbloqueia as abas operacionais**.

### 4. Estudar (fluxo diário)

1. **Plano de Hoje** — revisões devidas + foco (ponto fraco) + meta → "Começar".
2. **Praticar** — recall espaçado adaptativo (~75% de acerto); feedback com o
   *porquê* + trecho da apostila (RAG); classifique o erro (C/A/B/T). Atalhos
   **A–E** / **Enter**; **modo voz** opcional (🔊).
3. **Simulado** — prova cronometrada, relatório por disciplina.
4. **Maestria** — domínio (Elo) por disciplina, revisões de hoje.
5. **Radar** — novidades (editais/Instagram) captadas automaticamente.

### 5. Manter atualizado e afinar sozinho

```powershell
./cli_python/rotina_noturna.ps1 -Registrar         # coletor + radar + ciclo, diário
```

### Carregar exercícios (provas → questões)

```powershell
# baixa provas públicas da lista curada e gera questões no banco
python cli_python/extrair_provas_pdf.py --curado
python cli_python/extrair_provas_pdf.py --gerar-questoes
```

Suporta **CESGRANRIO** (5 alternativas) e **CEBRASPE** (Certo/Errado).

## Interfaces alternativas (CLI / Streamlit)

### Coach interativo (CLI)

```powershell
python cli_python/agente.py
```

Comandos no chat:

| Comando | Descrição |
|---------|----------|
| `/sessao` | Registra sessão de estudo |
| `/painel` | Mostra métricas (dias, IC, projeção) |
| `/simulado` | Simulado estilo CESGRANRIO |
| `/evolucao` | 🧬 Painel de autoevolução |
| `/ciclo` | 🧬 Dispara ciclo evolutivo manualmente |
| `/relatorio` | Relatório semanal (MD+HTML) |
| `/perfil` | Mostra modelo do candidato |
| `/reset` | Apaga perfil e recomeça |
| `/sair` | Encerra (salva tudo) |

### Coleta de inteligência

```powershell
# Todos os beats (batch — use 7B para qualidade)
python cli_python/coletor/coletor.py --all

# Beat específico
python cli_python/coletor/coletor.py --beat legislacao-aplicavel

# Para 1.5B (limitar tokens)
python cli_python/coletor/coletor.py --all --max-tokens 4096

# Agendar coleta noturna
powershell cli_python/coletor/registrar_tarefa.ps1 -Docker -Modelo qwen2.5:7b
```

### Dashboard web

```powershell
streamlit run cli_python/dashboard.py
```

## RAG (Retrieval-Augmented Generation)

Beats legislativos (`legislacao-aplicavel`, `temas-setor`) incluem `rag_sources` em `fontes.json` — URLs de texto real da lei (planalto.gov.br) que são baixados e injetados no prompt como contexto adicional.

### Qualidade RAG

| Configuração | Lei 13.303 — acurácia |
|---|---|
| 1.5B sem RAG | ❌ Alucinação completa |
| 1.5B com RAG | 🟡 Identifica leis corretas |
| 7B com RAG | ✅ Correta ("estatuto jurídico das empresas públicas") |

Recomendação: use `qwen2.5:7b` via Docker para beats legislativos com RAG.

## Configuração

| Variável | Default | Descrição |
|---|---|---|
| `AGENTE_LLM_BASE_URL` | `http://127.0.0.1:11434` | URL do Ollama |
| `AGENTE_LOCAL_MODEL` | `qwen2.5:1.5b` | Modelo |
| `AGENTE_VAULT` | `<projeto>/Obsidian_Vault` | Pasta do vault |
| `AGENTE_RENDER_JS` | — | `1` ativa renderização de páginas JS no coletor (Chromium headless) |
| `NO_COLOR` | — | Desativa cores no terminal |

## Renderização de páginas JavaScript (extração e absorção)

Páginas com JavaScript/SPA que o fetch simples (requests + BeautifulSoup) não
captura podem ser renderizadas com **Chromium headless via Playwright** — mesma
abordagem do `mcp-web-scraper`, porém nativa em Python (sem Go, sem ponte MCP).

```powershell
pip install playwright
playwright install chromium
```

- Uso direto: `local_web.web_fetch(url, render=True)` ou `local_web.web_fetch_render(url)`.
- No coletor: `AGENTE_RENDER_JS=1` ativa o fallback automático (quando o fetch
  simples retorna conteúdo pobre). Nesse modo o coletor busca **sequencialmente**
  (a API síncrona do Playwright não é thread-safe). Sem a variável, mantém o
  fetch paralelo rápido. Se o Playwright não estiver instalado, degrada
  graciosamente para o fetch simples.

## RAG sobre apostilas (memória de estudo do coach)

O coach pode consultar suas **apostilas** ao responder, recuperando os trechos
mais relevantes à pergunta. Usa **chromadb** com embeddings **locais** (ONNX
all-MiniLM-L6-v2 — sem API) e índice persistente em `dados/rag_index/`
(gitignored, não versiona conteúdo protegido).

```powershell
pip install chromadb

# 1. extrair as apostilas (PDF -> markdown) com o importador/opendataloader
# 2. indexar os .md (ou .txt):
python cli_python/rag.py --indexar "C:\caminho\para\materiais_extraidos"

# testar a recuperação:
python cli_python/rag.py --buscar "regras de crase" -k 4
python cli_python/rag.py --stats
```

Depois de indexar, o `agente.py` (CLI) e o endpoint `/perguntar` (API) injetam
automaticamente os trechos relevantes no prompt. Sem `chromadb` ou sem índice,
o sistema degrada graciosamente (segue sem RAG).

## Radar Instagram (monitoramento de hashtags)

Acompanha hashtags do tema (#concursopetrobras, #cesgranrio…) para captar novos
materiais/avisos, alimentando a inteligência que o coach lê.

> ⚠️ **Sem scraping/login.** Raspar o Instagram viola os Termos e arrisca a conta.
> Este módulo usa a **API Graph oficial da Meta** (hashtags públicas).

Pré-requisitos (uma vez): conta Instagram **Business/Creator** vinculada a uma
Página do Facebook + um app em developers.facebook.com + token de acesso.

```powershell
$env:INSTAGRAM_TOKEN = "<seu_token>"
$env:INSTAGRAM_IG_USER_ID = "<id_da_conta_business>"
python cli_python/instagram.py --tags concursopetrobras,cesgranrio
```

Por **perfil** (Business Discovery — mais simples de liberar que hashtag; o
perfil-alvo precisa ser conta profissional):

```powershell
python cli_python/instagram.py --perfis cursinhox,professory,paginaconcurso
# ou via env: $env:INSTAGRAM_PERFIS = "cursinhox,professory"
```

Gera `Obsidian_Vault/Petrobras/Inteligencia/_RADAR_INSTAGRAM.md`. Sem token, o
módulo só mostra as instruções (degrada gracioso). Pode ser agendado junto ao
coletor.

## Automação noturna (uma tarefa só)

Roda **coletor + radar Instagram + ciclo evolutivo** em sequência, agendado numa
única tarefa do Windows — o app se mantém atualizado e se afina sozinho.

```powershell
# agenda diária às 03:00 (usa o .venv do projeto)
./cli_python/rotina_noturna.ps1 -Registrar
./cli_python/rotina_noturna.ps1 -Registrar -Hora "02:30"

# rodar agora (manual) / pular etapas / remover
./cli_python/rotina_noturna.ps1
./cli_python/rotina_noturna.ps1 -SemInstagram
./cli_python/rotina_noturna.ps1 -Remover
```

Logs datados em `cli_python/dados/logs/`. O radar do Instagram só roda se
`INSTAGRAM_TOKEN` estiver definido.

## Testes

```powershell
# Todos os testes (paralelo, 3 workers, com cobertura)
python -m pytest tests/ -n 3

# Sem cobertura (mais rápido)
python -m pytest tests/ -n 3 -p no:cov

# Apenas evolução
python -m pytest tests/test_evolucao.py -v

# Apenas unitários
python -m pytest tests/test_unit.py
```

**Cobertura atual:** 655 testes, 0 falhas (~60–90s no `.venv` do projeto).

## Estrutura de dados

```
dados/
├── perfil_candidato.json   # Perfil do candidato (cargo, fase, histórico de acertos)
├── sessoes.json             # Sessões de estudo registradas
├── historico_conversa.json  # Histórico do chat
├── evolucao/                # 🧬 Dados de autoevolução
│   ├── diario.json          # Diário de decisões e outcomes
│   ├── auto_avaliacao.json  # Histórico de auto-avaliação
│   ├── experimentos.json    # Experimentos A/B
│   ├── prompts/             # Overlays evolutivos (versionados)
│   └── relatorios/          # Relatórios de ciclos evolutivos
└── relatorios/              # Relatórios semanais (.md)

Obsidian_Vault/Petrobras/
├── _RESUMO_INTEL.md         # Mapa de conteúdo da coleta
├── Inteligencia/            # Notas .md de cada beat
└── ...
```

## 🧬 Autoevolução

O agente evolui autonomamente em **5 camadas**:

| Camada | Módulo | Função |
|--------|--------|--------|
| 1 | `evolucao.py` | Registra decisões e outcomes, calcula eficácia |
| 2 | `auto_avaliacao.py` | Pontua respostas em 5 dimensões (P1–P5) |
| 3 | `estrategia_ab.py` | Testa A/B entre estratégias pedagógicas |
| 4 | `prompt_evoluivel.py` | Reescreve seções do próprio prompt |
| 5 | `ciclo_evolutivo.py` | Orquestra tudo num ciclo automático |

### Bootstrap

```powershell
# Popular sistema de evolução com dados iniciais
python cli_python/bootstrap_evolucao.py

# Ver painel de evolução
python cli_python/ciclo_evolutivo.py --relatorio

# Disparar ciclo evolutivo completo
python cli_python/ciclo_evolutivo.py
```

## GPU

- **GTX 1050 (3GB VRAM)**: `qwen2.5:1.5b` GPU nativo (22 tok/s)
- **7B via Docker**: layer splitting, GPU parcial + CPU (3.6 tok/s)
- **7B CPU**: 0.85 tok/s — inviável para uso real
