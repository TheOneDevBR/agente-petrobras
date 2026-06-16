<#
.SYNOPSIS
  Rotina noturna do AgentePetrobras: coleta de inteligência + radar Instagram +
  ciclo evolutivo, numa única tarefa agendada.
.DESCRIPTION
  Sem flags, EXECUTA a rotina (coletor --all, instagram, ciclo_evolutivo),
  gravando logs datados em dados/logs. Com -Registrar, agenda esta rotina no
  Task Scheduler do Windows para rodar diariamente. Usa o .venv do projeto.
.PARAMETER Registrar
  Cria/atualiza a tarefa diária (não roda a rotina agora).
.PARAMETER Hora
  Horário da execução diária (HH:mm). Padrão: 03:00.
.PARAMETER Remover
  Remove a tarefa agendada.
.PARAMETER SemColetor / SemInstagram / SemCiclo
  Pula a etapa correspondente.
.EXAMPLE
  ./rotina_noturna.ps1 -Registrar            # agenda diária às 03:00
  ./rotina_noturna.ps1 -Registrar -Hora "02:30"
  ./rotina_noturna.ps1                        # roda agora (manual)
  ./rotina_noturna.ps1 -Remover
#>
param(
  [switch]$Registrar,
  [string]$Hora = "03:00",
  [switch]$Remover,
  [switch]$SemColetor,
  [switch]$SemInstagram,
  [switch]$SemCiclo
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "AgentePetrobras_RotinaNoturna"
$Aqui = $PSScriptRoot
$LogDir = Join-Path $Aqui "dados\logs"
$EsteScript = $MyInvocation.MyCommand.Path

# Python: preferir o .venv do projeto
$VenvPy = Join-Path $Aqui "..\.venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
  $Python = (Resolve-Path $VenvPy).Path
} else {
  $Python = (Get-Command python -ErrorAction SilentlyContinue).Source
  if (-not $Python) { $Python = (Get-Command py -ErrorAction SilentlyContinue).Source }
}

if ($Remover) {
  if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa '$NomeTarefa' removida." -ForegroundColor Yellow
  } else {
    Write-Host "Tarefa '$NomeTarefa' nao existe."
  }
  return
}

if ($Registrar) {
  if (-not $Python) { throw "Python nao encontrado (.venv ou PATH)." }
  $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$EsteScript`""
  $acao = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
  $gatilho = New-ScheduledTaskTrigger -Daily -At $Hora
  $config = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
  Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Settings $config -Description "Rotina noturna do AgentePetrobras" -Force | Out-Null
  Write-Host "Tarefa '$NomeTarefa' registrada para rodar diariamente as $Hora." -ForegroundColor Green
  Write-Host "Python: $Python"
  Write-Host "Logs em: $LogDir"
  return
}

# ── Executa a rotina ─────────────────────────────────────────────────────────
if (-not $Python) { throw "Python nao encontrado (.venv ou PATH)." }
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
$data = Get-Date -Format 'yyyy-MM-dd'

function Invoke-Etapa($nome, $scriptRel, $args) {
  $script = Join-Path $Aqui $scriptRel
  if (-not (Test-Path $script)) { Write-Host "[$nome] script ausente: $script" -ForegroundColor Yellow; return }
  $log = Join-Path $LogDir "rotina_${nome}_$data.log"
  Write-Host "[$nome] iniciando..." -ForegroundColor Cyan
  try {
    & $Python $script @args 2>&1 | Out-File -Encoding utf8 $log
    Write-Host "[$nome] ok -> $log" -ForegroundColor Green
  } catch {
    Write-Host "[$nome] erro: $_" -ForegroundColor Red
  }
}

if (-not $SemColetor)   { Invoke-Etapa "coletor"   "coletor\coletor.py"  @("--all") }
if (-not $SemInstagram) {
  if ($env:INSTAGRAM_TOKEN) { Invoke-Etapa "instagram" "instagram.py" @() }
  else { Write-Host "[instagram] pulado (sem INSTAGRAM_TOKEN)." -ForegroundColor DarkGray }
}
if (-not $SemCiclo)     { Invoke-Etapa "ciclo"     "ciclo_evolutivo.py"  @() }

Write-Host "Rotina noturna concluida ($data)." -ForegroundColor Green
