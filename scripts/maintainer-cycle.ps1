<#
.SYNOPSIS
  Ciclo de manutenção LOCAL e barato (0 tokens) do repo agente-petrobras.

  Roda a parte determinística do maintainer-loop sem acordar o LLM:
  sync gate -> conta fila do GitHub -> confere CI do master.
  - Tudo verde e fila vazia  -> só registra "idle" no log. Custo: 0 tokens.
  - Há issue/PR aberto OU CI vermelho -> levanta um FLAG e (opcional) escala
    para o Claude headless, que é o único momento em que se gastam tokens.

  Pensado para a Tarefa Agendada do Windows (a cada 5 min). Veja
  scripts/install-maintainer-task.ps1 para registrar/remover.
#>
$ErrorActionPreference = 'Continue'

$repo = 'TheOneDevBR/agente-petrobras'
$root = 'd:\Projetos IA\Agente de Concurso da Petrobras'
$stateDir = Join-Path $env:LOCALAPPDATA 'AgentePetrobras'
$log  = Join-Path $stateDir 'maintainer-loop.log'
$flag = Join-Path $stateDir 'needs-claude.flag'
if (-not (Test-Path $stateDir)) { New-Item -ItemType Directory -Force $stateDir | Out-Null }

$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Set-Location $root

function Log($line) { Add-Content -LiteralPath $log -Value $line -Encoding utf8 }

# --- 1. Sync gate (nunca muta se sujo / fora de master) ---
git fetch origin --quiet
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
$dirty  = [string](git status --short)
$syncState = 'ok'
if ($branch -ne 'master') { $syncState = "branch=$branch (nao-master)" }
elseif ($dirty)           { $syncState = 'worktree sujo' }
else                      { git pull --ff-only --quiet }

# --- 2. Fila do GitHub ---
try {
  $issues = gh issue list --repo $repo --state open --json number | ConvertFrom-Json
  $prs    = gh pr   list --repo $repo --state open --json number | ConvertFrom-Json
  $ni = @($issues).Count
  $np = @($prs).Count
} catch { $ni = -1; $np = -1 }   # -1 = falha de auth/rede

# --- 3. CI do master (status já computado pelo GitHub — barato) ---
try {
  $ci  = gh run list --repo $repo --branch master --limit 2 --json conclusion | ConvertFrom-Json
  $red = @($ci | Where-Object { $_.conclusion -eq 'failure' }).Count
} catch { $red = -1 }

# --- 4. Decisão ---
$work = ($ni -gt 0) -or ($np -gt 0) -or ($red -gt 0)

if ($work) {
  $msg = "$ts  WORK  sync=$syncState  issues=$ni  prs=$np  ci_red=$red"
  Set-Content -LiteralPath $flag -Value $msg -Encoding utf8
  Log $msg

  # Escalada opcional para o Claude headless (só quando HÁ trabalho => tokens
  # só nesse caso). Ative com:  setx AGENTE_AUTO_CLAUDE 1
  if ($env:AGENTE_AUTO_CLAUDE -eq '1') {
    $claude = (Get-Command claude -ErrorAction SilentlyContinue)
    if ($claude) {
      $prompt = 'Leia .claude/maintainer-loop.md e execute UM ciclo de manutencao do repo TheOneDevBR/agente-petrobras conforme o playbook. Termine com o report curto.'
      Log "$ts  -> escalando para claude headless"
      & $claude.Source -p $prompt 2>&1 | Out-Null
      Remove-Item -LiteralPath $flag -Force -ErrorAction SilentlyContinue
    } else {
      Log "$ts  -> AGENTE_AUTO_CLAUDE=1 mas 'claude' nao esta no PATH; só flag."
    }
  }
} else {
  $msg = "$ts  idle  sync=$syncState  issues=$ni  prs=$np  ci_red=$red"
  Log $msg
  if (Test-Path $flag) { Remove-Item -LiteralPath $flag -Force -ErrorAction SilentlyContinue }
}

# Log enxuto: mantém só as últimas 500 linhas
if (Test-Path $log) {
  $tail = Get-Content -LiteralPath $log -Tail 500
  Set-Content -LiteralPath $log -Value $tail -Encoding utf8
}
