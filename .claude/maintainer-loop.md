# Maintainer Loop — agente-petrobras

Playbook de UM ciclo de manutenção. Adaptado do padrão maintainer-orchestrator +
github-project-triage (steipete) para ESTE repositório.

## Execução (modelo local, token-free)

O loop NÃO acorda mais o LLM a cada 5 min (isso gastava tokens só pra dizer "idle").
Agora a parte determinística roda **localmente**, com 0 tokens:

- `scripts/maintainer-cycle.ps1` — sync gate + conta fila do GitHub + confere CI do
  master. Tudo verde + fila vazia → grava `idle` no log e sai. Há issue/PR ou CI
  vermelho → levanta o flag `%LOCALAPPDATA%\AgentePetrobras\needs-claude.flag`.
- `scripts/install-maintainer-task.ps1` — registra/remove a Tarefa Agendada do
  Windows `AgentePetrobras-MaintainerLoop` (a cada 5 min). `-Remove` para desinstalar.
- Log: `%LOCALAPPDATA%\AgentePetrobras\maintainer-loop.log`.
- **Tokens só são gastos quando há trabalho**: ao ver o flag, rode o Claude com o
  prompt do ciclo (abaixo), ou ative escalada automática com `setx AGENTE_AUTO_CLAUDE 1`
  (o script chama `claude -p` headless só quando o flag sobe).

As seções abaixo são o que o Claude executa quando é efetivamente chamado para um ciclo.

- Repo: `TheOneDevBR/agente-petrobras` (público) — branch principal **`master`** (não `main`).
- SO: Windows. Stack híbrida: Python (CLI/pipeline) + Frontend Vite/TS/React.
- Autonomia autorizada: **total** — pode commitar, push, abrir PR e fazer **merge**
  quando CI verde + prova. Honrar isso, mas com os portões abaixo.

## Princípios de segurança (sempre)

- **Uma** mudança bounded por ciclo. Nada de refatoração ampla.
- Nunca force-push, nunca reescrever histórico de `master`, nunca tocar `.env`/segredos.
- Antes de qualquer merge: CI verde no commit exato + testes locais passando.
- Se o worktree estiver sujo ou `master` divergir do remoto → **só reportar, não mutar**.
- Trabalho substancial (investigação grande, implementação) → delegar a subagente worker
  (Agent tool). O worker não sub-delega. Este thread é control-plane, fica leve.

## Ciclo

### 1. Sync gate
```bash
cd "d:/Projetos IA/Agente de Concurso da Petrobras"
git fetch origin
git rev-parse --abbrev-ref HEAD          # deve ser master
git status --short --branch
git pull --ff-only
```
Se não estiver em `master`, o pull falhar, ou houver mudanças não commitadas →
reportar e pular as etapas de mutação deste ciclo.

### 2. Triagem GitHub (prioridade)
```bash
gh issue list --repo TheOneDevBR/agente-petrobras --state open --limit 50 \
  --json number,title,author,labels,createdAt,updatedAt,url
gh pr list --repo TheOneDevBR/agente-petrobras --state open --limit 50 \
  --json number,title,author,isDraft,reviewDecision,mergeStateStatus,statusCheckRollup,url
```
Para cada item: classificar `Autônomo` / `Precisa do dono`.
- PR com CI verde + diff bounded + prova → revisar, garantir testes, e **fazer merge**.
- PR vermelho/conflito → corrigir no branch, push, re-rodar CI; merge quando verde.
- Issue sem PR e bounded → implementar candidato em branch, abrir PR, levar a verde, merge.
- Decisão de produto / segurança / acesso ausente → preparar PR mergeable e **parar**,
  reportar como `Precisa do dono` com URL canônica + recomendação.
Sempre imprimir a URL canônica completa do item (nunca só `#123`).

### 3. Manutenção local (quando a fila estiver vazia)
Escolher **UMA** tarefa bounded por ciclo, nesta ordem de prioridade. Se tudo verde e
nada a fazer → reportar `idle, tudo verde` e encerrar o ciclo sem mutar.

Saúde Python:
```bash
pip install -r cli_python/requirements.txt -q   # se necessário
pytest -n auto -q --timeout=120
```
Saúde Frontend:
```bash
npm ci    # se node_modules desatualizado
npm run lint
npm run build      # tsc -b && vite build (typecheck)
npm test           # vitest run
```
Se algo falhar → corrigir a causa (bounded), rodar a suíte de novo até verde.
Outras tarefas de baixo risco quando tudo passa: auditar dependências desatualizadas
(`npm outdated`, requirements), corrigir lint/typecheck pendente, docs desatualizados.

### 4. Land (autonomia total)
Quando a correção está pronta e verde:
```bash
git switch -c fix/<slug>           # nunca commitar direto experimentos em master
git add -A && git commit -m "<msg>"   # rodapé Co-Authored-By exigido
git push -u origin fix/<slug>
gh pr create --fill --base master
# aguardar CI; quando verde + prova:
gh pr merge --squash --delete-branch
```
Correções triviais/verdes podem ir direto pra `master` se preferir, mas o caminho via PR
deixa rastro de CI. Merge só com CI verde no commit exato.

Rodapé de commit:
```
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

### 5. Report (sempre, no fim do ciclo)
Formato curto:
```
Ciclo HH:MM — sync ok|bloqueado
Fila GitHub: N issues / M PRs   (ou: vazia)
Ação: <merge #X | PR aberto <url> | fix local <arquivo> | idle tudo verde | bloqueado: motivo>
Precisa do dono: <url + decisão> (se houver)
Próximo: <o que o próximo ciclo deve olhar>
```
```
