<#
.SYNOPSIS
  Registra a coleta diária de inteligência do AgentePetrobras no Task Scheduler.
.DESCRIPTION
  Cria uma tarefa que roda 'python coletor.py' todo dia no horário escolhido.
  Rode este script UMA vez (PowerShell normal já basta; não precisa admin para
  tarefa do usuário atual).
.EXAMPLE
  ./registrar_tarefa.ps1                 # diária às 07:00
  ./registrar_tarefa.ps1 -Hora "21:30"   # diária às 21:30
  ./registrar_tarefa.ps1 -Remover        # remove a tarefa
#>
param(
  [string]$Hora = "07:00",
  [switch]$Remover
)

$ErrorActionPreference = "Stop"
$NomeTarefa = "AgentePetrobras_ColetaDiaria"
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

Write-Host "Python : $Python"
Write-Host "Script : $Coletor"
Write-Host "Horário: diariamente às $Hora"

# Roda a partir da pasta do coletor para achar fontes.json / .env
$Acao    = New-ScheduledTaskAction -Execute $Python -Argument "`"$Coletor`"" -WorkingDirectory $PSScriptRoot
$Gatilho = New-ScheduledTaskTrigger -Daily -At $Hora
$Config  = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
             -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 1)

if (Get-ScheduledTask -TaskName $NomeTarefa -ErrorAction SilentlyContinue) {
  Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
}

Register-ScheduledTask -TaskName $NomeTarefa -Action $Acao -Trigger $Gatilho `
  -Settings $Config -Description "Coleta diária de inteligência (CESGRANRIO/Petrobras/cursinhos) -> Obsidian + graphify" | Out-Null

Write-Host "`nTarefa '$NomeTarefa' registrada." -ForegroundColor Green
Write-Host "Testar agora:  Start-ScheduledTask -TaskName $NomeTarefa"
Write-Host "Ver status:    Get-ScheduledTask -TaskName $NomeTarefa | Get-ScheduledTaskInfo"
Write-Host "Remover:       ./registrar_tarefa.ps1 -Remover"
