# Coletor de Inteligência — AgentePetrobras

Coleta periódica e autônoma de **informação pública** (banca CESGRANRIO,
carreiras Petrobras, blogs de cursinhos, portais de concurso), grava tudo no
**Obsidian** e atualiza o **knowledge graph** via `/graphify`. O agente principal
absorve esse resumo na memória e usa para alertar sobre editais e tendências.

## Pipeline

```
Task Scheduler (diário)
  └─> python coletor.py
        ├─ web_search + web_fetch (ferramentas server-side da API Anthropic)
        │    → 1 busca + síntese por "missão" (beat) de fontes.json
        ├─ grava 1 nota Markdown por missão
        │    → Obsidian_Vault/Petrobras/Inteligencia/AAAA-MM-DD_<slug>.md
        ├─ atualiza Obsidian_Vault/Petrobras/_RESUMO_INTEL.md  (MOC/índice)
        └─ claude -p "/graphify <Petrobras> --update --obsidian"  → grafo
  agente.py injeta _RESUMO_INTEL no system prompt  → "absorção na memória"
```

Só informação **pública** é coletada (editais, gabaritos, provas, notícias,
artigos abertos de blog). Conteúdo pago de cursinho, atrás de login, não é
acessado — o valor está em detectar **novidades e tendências de cobrança**.

## Configuração

As fontes e missões ficam em [fontes.json](fontes.json). Cada `beat` vira uma
nota. Edite à vontade — mude `cargo_foco`, adicione/remova missões, ajuste os
domínios sugeridos.

Use o mesmo `.env` do agente (em `cli_python/.env`) com `ANTHROPIC_API_KEY`.
Variáveis opcionais: `AGENTE_VAULT` (caminho do vault; default
`<projeto>/Obsidian_Vault`), `AGENTE_MODELO`.

> ⚠️ As ferramentas **web search / web fetch** são server-side e podem ter
> custo adicional por busca na sua conta Anthropic. Comece testando 1 missão.

## Uso manual

```powershell
cd cli_python\coletor
python coletor.py --listar             # vê as missões
python coletor.py --beat editais       # roda só uma (bom para testar)
python coletor.py                      # roda todas + graphify
python coletor.py --no-graph           # roda todas, sem atualizar o grafo
```

## Agendamento diário (Task Scheduler)

```powershell
cd cli_python\coletor
./registrar_tarefa.ps1                 # diária às 07:00
./registrar_tarefa.ps1 -Hora "21:30"   # outro horário
Start-ScheduledTask -TaskName AgentePetrobras_ColetaDiaria   # testar agora
./registrar_tarefa.ps1 -Remover        # remover
```

A tarefa roda com seu usuário, só quando há rede, com limite de 1h.

## Saída no Obsidian

Abra a pasta `Obsidian_Vault` como vault no Obsidian. Você verá:

- `Petrobras/_RESUMO_INTEL.md` — índice (MOC) com os achados mais recentes no topo.
- `Petrobras/Inteligencia/` — uma nota datada por missão, com frontmatter,
  tags, links `[[disciplina]]` e a seção **Fontes** com as URLs.
- `graphify-out/` + HTML do grafo — gerados pelo `/graphify`.

## Como o agente usa isso

[agente.py](../agente.py) lê o topo de `_RESUMO_INTEL.md` e injeta um bloco
`[INTEL_RECENTE]` no system prompt. Assim, numa sessão normal, o agente já
sabe se há edital novo ou mudança de tendência e ajusta o plano — sem você
precisar contar.
