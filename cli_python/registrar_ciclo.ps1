<#
.SYNOPSIS
  Registra o ciclo evolutivo do AgentePetrobras no Task Scheduler (Windows).
.DESCRIPTION
  Cria uma tarefa que roda 'python ciclo_evolutivo.py' diariamente no horário
  escolhido. Com os dados de prática acumulados (Elo/SM-2/erros), o ciclo
  analisa eficácia, gerencia experimentos A/B e — quando há outcomes reais
  suficientes — evolui os overlays do prompt (gate anti-Goodhart).
  Rode UMA vez (não precisa admin para tarefa do usuário atual).
.PARAMETER Hora
  Horário da execução diária (HH:mm). Padrão: 03:00 (madrugada).
.PARAMETER NoEvolve
  Se presente, roda o ciclo sem reescrever overlays (só análise/relatório).
.PARAMETER Remover
  Remove a tarefa agendada.
.EXAMPLE
  ./registrar_ciclo.ps1                 # diário às 03:00
  ./registrar_ciclo.ps1 -Hora "02:30"  # diário às 02:30
  ./registrar_ciclo.ps1 -NoEvolve      # só análise/relatório
  ./registrar_ciclo.ps1 -Remover       # remove a tarefa
#>
param(
  [string]$Hora = "03:00",
  [switch]$NoEvolve,
  [switch]$Remover
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "AgentePetrobras_CicloEvolutivo"
$LogDir = Join-Path $PSScriptRoot "dados\logs"
$Ciclo = Join-Path $PSScriptRoot "ciclo_evolutivo.py"

if ($Remover) {
  if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa '$NomeTarefa' removida." -ForegroundColor Yellow
  } else {
    Write-Host "Tarefa '$NomeTarefa' nao existe."
  }
  return
}

# Resolve o python (preferir o venv do projeto, depois o do PATH)
$VenvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
  $Python = (Resolve-Path $VenvPy).Path
} else {
  $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
  if (-not $Python) { $Python = (Get-Command py -ErrorAction SilentlyContinue).Source }
}
if (-not $Python) { throw "Python nao encontrado (nem .venv nem PATH)." }
if (-not (Test-Path $Ciclo)) { throw "ciclo_evolutivo.py nao encontrado em $Ciclo" }

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

$flags = ""
if ($NoEvolve) { $flags = " --no-evolve" }
$LogPattern = Join-Path $LogDir "ciclo_DATA.log"

# Comando: roda o ciclo e grava log datado
$Inner = "`$log = '$LogDir\ciclo_' + (Get-Date -Format 'yyyy-MM-dd') + '.log'; " +
         "& '$Python' '$Ciclo'$flags 2>&1 | Out-File -Encoding utf8 `$log"
$Acao = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -Command `"$Inner`""
$Gatilho = New-ScheduledTaskTrigger -Daily -At $Hora
$Config = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $NomeTarefa -Action $Acao -Trigger $Gatilho `
  -Settings $Config -Description "Ciclo evolutivo diario do AgentePetrobras" -Force | Out-Null

Write-Host "Tarefa '$NomeTarefa' registrada para rodar diariamente as $Hora." -ForegroundColor Green
Write-Host "Python: $Python"
Write-Host "Logs em: $LogPattern"
Write-Host "Remover com: ./registrar_ciclo.ps1 -Remover"
