<#
.SYNOPSIS
  Registra a coleta diária de inteligência do AgentePetrobras no Task Scheduler.
.DESCRIPTION
  Cria uma tarefa que roda 'python coletor.py --all' todo dia no horário escolhido.
  Rode este script UMA vez (PowerShell normal já basta; não precisa admin para
  tarefa do usuário atual).
.PARAMETER Hora
  Horário da execução diária (formato HH:mm). Padrão: 07:00.
.PARAMETER Modelo
  Nome do modelo LLM (ex: qwen2.5:7b para Docker ou qwen2.5:1.5b para nativo).
.PARAMETER Docker
  Se presente, tenta iniciar o container Docker ollama-gpu antes da coleta.
.PARAMETER Remover
  Remove a tarefa agendada.
.EXAMPLE
  ./registrar_tarefa.ps1                     # diária às 07:00, 1.5B
  ./registrar_tarefa.ps1 -Hora "21:30"       # diária às 21:30
  ./registrar_tarefa.ps1 -Docker             # com GPU (7B) via Docker
  ./registrar_tarefa.ps1 -Remover            # remove a tarefa
#>
param(
  [string]$Hora = "07:00",
  [string]$Modelo = "qwen2.5:1.5b",
  [switch]$Docker,
  [switch]$Remover
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "AgentePetrobras_ColetaDiaria"
$LogDir = Join-Path $PSScriptRoot "..\dados\logs"
$LogFile = Join-Path $LogDir "coleta_$(Get-Date -Format 'yyyy-MM-dd').log"
$Coletor = Join-Path $PSScriptRoot "coletor.py"

if ($Remover) {
  if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa '$NomeTarefa' removida." -ForegroundColor Yellow
  } else {
    Write-Host "Tarefa '$NomeTarefa' não existe."
  }
  return
}

# Resolve o python (preferir o do ambiente atual)
$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) { $Python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $Python) { throw "Python não encontrado no PATH." }

if (-not (Test-Path $Coletor)) { throw "coletor.py não encontrado em $Coletor" }

# Monta comando: trata Docker / modelo / log
$CmdArgs = @()
if ($Docker) {
  $CmdArgs += "-NoProfile -Command `"docker start ollama-gpu 2>`$null;"
  $CmdArgs += "`$env:AGENTE_LLM_BASE_URL = 'http://[::1]:11434';"
  $CmdArgs += "`$env:AGENTE_LOCAL_MODEL = 'qwen2.5:7b';"
  $CmdArgs += "python `"`"$Coletor`"`" --all"
  $CmdArgs += "2>&1 | Out-File -Encoding utf8 `"`"$LogFile`"`";"
  $CmdArgs += "Start-Sleep -Seconds 30`""
  $Executor = "powershell"
} else {
  $env:AGENTE_LOCAL_MODEL = $Modelo
  $CmdArgs = "`"$Coletor`" --all"
  $Executor = $Python
}

Write-Host "Executor : $Executor"
Write-Host "Script   : $Coletor --all"
Write-Host "Horário  : diariamente às $Hora"
Write-Host "Modelo   : $Modelo"
if ($Docker) { Write-Host "Docker   : ollama-gpu (inicia antes)" }
Write-Host "Log      : $LogFile"

# Cria diretório de logs
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Garante que o diretório de trabalho seja o do coletor (fontes.json / .env)
$Acao    = New-ScheduledTaskAction -Execute $Executor -Argument $CmdArgs -WorkingDirectory $PSScriptRoot
$Gatilho = New-ScheduledTaskTrigger -Daily -At $Hora
$Config  = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
             -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 2)

if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
}

Register-ScheduledTask -TaskName $NomeTarefa -Action $Acao -Trigger $Gatilho `
  -Settings $Config -Description "Coleta diária de inteligência (CESGRANRIO/Petrobras) -> Obsidian" | Out-Null

Write-Host "`nTarefa '$NomeTarefa' registrada." -ForegroundColor Green
Write-Host "Testar agora:  Start-ScheduledTask -TaskName $NomeTarefa"
Write-Host "Status:        Get-ScheduledTask -TaskName $NomeTarefa | Get-ScheduledTaskInfo"
Write-Host "Log:           $LogFile"
Write-Host "Remover:       ./registrar_tarefa.ps1 -Remover"
