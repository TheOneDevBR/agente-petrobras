# AgentePetrobras v4.0 — CLI

Preparador autônomo de alto desempenho para concursos da **Petrobras**
(banca **CESGRANRIO**). Não é um chatbot passivo: opera como treinador de
elite integrando três arquétipos — **Estrategista + Coach + Cientista** —
com diagnóstico, plano por fases, inteligência de banca, técnicas cognitivas
baseadas em evidência e gestão psicológica.

Roda no terminal, usa o SDK da Anthropic (Claude) e mantém **memória
persistente do candidato** entre sessões.

## Como funciona

| Arquivo | Papel |
|---|---|
| `AgentePetrobras_v4.md` | O system prompt v4.0 completo (§1–§15). Edite à vontade. |
| `perfil.py` | Modelo vivo do candidato (§2) — persistência em JSON + diretivas de memória. |
| `metricas.py` | Cálculos determinísticos (dias até a prova, IC, projeção de nota, streak) e o **painel**. |
| `agente.py` | CLI: streaming, histórico, registro de sessões, integração de perfil + painel. |
| `dados/` | Gerado em runtime: `perfil_candidato.json`, `historico_conversa.json`, `sessoes.json`, `relatorios/`. |

**Memória de longo prazo:** durante a conversa o agente emite diretivas
ocultas `<<ATUALIZAR_PERFIL: campo = valor>>`. O CLI as aplica, salva em
`dados/perfil_candidato.json` e injeta o perfil de volta no system prompt a
cada sessão. Assim o agente lembra cargo, fase, notas por disciplina, erro
dominante, streak, bloqueios etc.

**Métricas que não mentem (PAINEL DE CONTROLE):** contas críticas não ficam a
cargo do LLM. `metricas.py` calcula em código — e injeta no prompt — os
**dias até a prova**, o **Índice de Consistência** (§5), a **projeção de nota
ponderada por categoria** (com barras) e o **gap para a meta**. O agente é
instruído a usar esses números, não recalculá-los.

**Loop de feedback real:** o comando `/sessao` registra cada estudo
(disciplina, minutos, questões, acertos, erro dominante [C/A/B/T]). Isso
atualiza o perfil, recalcula o painel e **dispara automaticamente a análise
do coach** sobre o resultado.

## Instalação

```powershell
cd "cli_python"
pip install -r requirements.txt
copy .env.example .env      # e edite a chave
```

Defina a chave da API (uma das opções):

```powershell
# opção A: arquivo .env (recomendado)  →  ANTHROPIC_API_KEY=sk-ant-...
# opção B: variável de ambiente persistente
setx ANTHROPIC_API_KEY "sk-ant-..."   # reabra o terminal
```

## Uso

```powershell
python agente.py
```

Na **primeira execução** o agente conduz o **Diagnóstico Inicial** (§3):
realidade operacional, histórico, autoavaliação calibrada e perfil de
sabotadores — e ao final gera mapa de lacunas, equação de viabilidade,
cronograma macro, top 5 ações e âncora de identidade.

Nas sessões seguintes ele abre com o **protocolo de 3 linhas** (fase/ritmo,
maior avanço, foco do dia com meta mensurável).

### Comandos no chat

| Comando | Ação |
|---|---|
| `/sessao` | registra uma sessão de estudo → atualiza o painel e dispara a análise do coach |
| `/painel` | mostra as métricas calculadas (dias, IC, projeção de nota, gap) |
| `/relatorio` | gera relatório semanal em Markdown em `dados/relatorios/` |
| `/perfil` | mostra o modelo atual do candidato |
| `/salvar` | grava perfil + histórico + sessões |
| `/limpar` | zera o histórico da conversa (mantém perfil e sessões) |
| `/reset`  | apaga o perfil e recomeça o diagnóstico (sessões mantidas) |
| `/sair`   | encerra salvando tudo |

> Dica: peça ao agente para definir a **data da prova** e a **meta de
> questões por semana** logo no início — são o que ativam a contagem
> regressiva e o Índice de Consistência no painel.

## Configuração

Variáveis de ambiente opcionais:

- `AGENTE_MODELO` — padrão `claude-opus-4-8`. Para respostas mais rápidas/baratas use `claude-sonnet-4-6`.
- `AGENTE_MAX_TOKENS` — padrão `4096`.
- `NO_COLOR=1` — desativa cores ANSI.

## Coleta de inteligência (busca periódica → Obsidian + graphify)

Em [coletor/](coletor/) há um coletor autônomo que faz **buscas periódicas** em
fontes públicas (banca CESGRANRIO, carreiras Petrobras, blogs de cursinhos,
portais de concurso) com as ferramentas **web search / web fetch** da API,
grava o resultado como notas no **Obsidian** e atualiza o **knowledge graph**
via `/graphify`. O agente lê esse resumo (`_RESUMO_INTEL.md`) e injeta um bloco
`[INTEL_RECENTE]` no prompt — então ele já chega na sessão sabendo de editais e
tendências novas.

```powershell
cd coletor
python coletor.py --listar          # missões configuradas (fontes.json)
python coletor.py --beat editais    # testa uma missão
./registrar_tarefa.ps1              # agenda a coleta diária (Task Scheduler)
```

Detalhes e pipeline completo em [coletor/README.md](coletor/README.md).

## Privacidade

Os dados do candidato ficam **somente** em `dados/` no seu computador, e a
inteligência coletada no seu vault Obsidian (`Obsidian_Vault/`). O `.gitignore`
já exclui `dados/` e `.env`. Só informação pública é coletada da web.
