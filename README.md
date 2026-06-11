# AgentePetrobras

Preparador autônomo para concursos Petrobras (banca CESGRANRIO), com **LLM local** via Ollama, web search integrado e dashboard Streamlit.

## Arquitetura

```
cli_python/
├── agente.py          # CLI coach — loop interativo com perfil, métricas, streaming
├── coletor/
│   ├── coletor.py     # Coleta periódica de inteligência (7 beats)
│   └── fontes.json    # Configuração dos beats de pesquisa
├── local_llm.py       # Wrapper OpenAI-compatible para Ollama + tool calling
├── local_web.py       # Web search (DuckDuckGo → HTML → Google) + fetch
├── metricas.py        # Streak, IC, projeção de nota, painel
├── perfil.py          # Persistência do perfil do candidato
├── dashboard.py       # Dashboard web Streamlit
└── dados/             # Perfil, sessões, histórico (persistência local)

tests/                 # 171 testes (pytest, 3 workers paralelos)
docs/                  # Benchmark de desempenho e qualidade
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

Comandos no chat: `/sessao` `/painel` `/relatorio` `/perfil` `/salvar` `/limpar` `/reset` `/sair`

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
| `NO_COLOR` | — | Desativa cores no terminal |

## Testes

```powershell
# Todos os testes (paralelo, 3 workers)
python -m pytest tests/ -n 3

# Com cobertura
python -m pytest tests/ --cov=cli_python

# Apenas unitários
python -m pytest tests/test_unit.py
```

**Cobertura atual:** ~85% (core), 171 testes.

## Estrutura de dados

```
dados/
├── perfil_candidato.json   # Perfil do candidato (cargo, fase, histórico de acertos)
├── sessoes.json             # Sessões de estudo registradas
├── historico_conversa.json  # Histórico do chat
└── relatorios/              # Relatórios semanais (.md)

Obsidian_Vault/Petrobras/
├── _RESUMO_INTEL.md         # Mapa de conteúdo da coleta
├── Inteligencia/            # Notas .md de cada beat
└── ...
```

## GPU

- **GTX 1050 (3GB VRAM)**: `qwen2.5:1.5b` GPU nativo (22 tok/s)
- **7B via Docker**: layer splitting, GPU parcial + CPU (3.6 tok/s)
- **7B CPU**: 0.85 tok/s — inviável para uso real
