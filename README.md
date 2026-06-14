# AgentePetrobras v5.0 — Autoevolutivo

Preparador autônomo para concursos Petrobras (banca CESGRANRIO), com **LLM local** via Ollama, web search integrado, **autoevolução em 5 camadas** e dashboard Streamlit.

## Arquitetura

```
cli_python/
├── agente.py             # CLI coach — loop interativo com perfil, métricas, streaming
├── coletor/
│   ├── coletor.py        # Coleta periódica de inteligência (13 beats)
│   └── fontes.json       # Configuração dos beats de pesquisa
├── local_llm.py          # Wrapper OpenAI-compatible para Ollama + tool calling
├── local_web.py          # Web search (DuckDuckGo → HTML → Google) + fetch
├── metricas.py           # Streak, IC, projeção de nota, painel
├── perfil.py             # Persistência do perfil do candidato
├── dashboard.py          # Dashboard web Streamlit
├── evolucao.py           # 🧬 Camada 1: Diário de decisões + outcomes
├── auto_avaliacao.py     # 🧬 Camada 2: Auto-avaliação de respostas (5 dimensões)
├── estrategia_ab.py      # 🧬 Camada 3: A/B Testing pedagógico
├── prompt_evoluivel.py   # 🧬 Camada 4: Auto-tuning do system prompt (overlays)
├── ciclo_evolutivo.py    # 🧬 Camada 5: Orquestrador de melhoria contínua
├── bootstrap_evolucao.py # Script de bootstrap do sistema evolutivo
└── dados/                # Perfil, sessões, histórico, evolução (persistência local)

tests/                    # 607 testes (pytest, 3 workers paralelos, pytest-cov)
docs/                     # Benchmark de desempenho e qualidade
```

### Fluxo

```
Agente (CLI) ──chama──> LocalLLM (Ollama) ──usa──> local_web (DDG/Google)
    │                                                    │
    ├── perfil.json ◄── perfil.py                        ▼
    ├── metricas.py (IC, streak, projeção)         Coletor (batch)
    └── dashboard.py (Streamlit)                    fontes.json → notas .md
```

## Setup

### 1. Ollama (obrigatório)

```powershell
# Modelo recomendado para chat interativo (rápido)
ollama pull qwen2.5:1.5b

# Modelo para coleta batch (qualidade superior) — requer GPU com 2.4GB+
ollama pull qwen2.5:7b
```

### 2. Docker (opcional — para 7B com GPU)

```powershell
docker compose up -d
docker exec ollama-gpu ollama pull qwen2.5:7b
```

### 3. Python

```powershell
pip install -r cli_python/requirements.txt
```

> ⚠ Use `127.0.0.1:11434` em vez de `localhost` se tiver Docker + Ollama nativo (IPv6 do wslrelay não encaminha `/v1/chat/completions`).

## Uso

### Coach interativo

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

**Cobertura atual:** 607 testes, 0 falhas, ~90s.

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
