<#
.SYNOPSIS
  Agenda a coleta automática de inteligência no Windows Task Scheduler.

.DESCRIPTION
  Cria uma tarefa no Windows Task Scheduler que roda o coletor.py
  diariamente no horário especificado.

  Requer execução como Administrador (ou ao menos permissão para criar tarefas).

.EXAMPLE
  .\agendar_coleta.ps1 -Hora 8 -Minuto 0
  .\agendar_coleta.ps1 -Hora 8 -Minuto 0 -Modelo "qwen2.5:7b" -Uninstall
#>

param(
    [int]$Hora = 8,
    [int]$Minuto = 0,
    [string]$Modelo = "qwen2.5:1.5b",
    [switch]$Uninstall,
    [string]$TaskName = "AgentePetrobras-Coleta"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ColetorPy = Join-Path $ProjectRoot "cli_python\coletor\coletor.py"
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "coleta_$(Get-Date -Format 'yyyy-MM-dd').log"

if (!(Test-Path $ColetorPy)) {
    Write-Error "Coletor não encontrado em: $ColetorPy"
    exit 1
}

if ($Uninstall) {
    Write-Host "Removendo tarefa '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarefa removida." -ForegroundColor Green
    exit 0
}

# Cria diretório de logs
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Script action — model via AGENTE_LOCAL_MODEL (lido por local_llm.py)
$Action = New-ScheduledTaskAction -Execute "powershell" -Argument @"
-Command `$env:AGENTE_LOCAL_MODEL='$Modelo'; `$env:PYTHONIOENCODING='utf-8'; python \"$ColetorPy\" --max-tokens 12000
"@ -WorkingDirectory $ProjectRoot

# Horário
$Trigger = New-ScheduledTaskTrigger -Daily -At "$($Hora.ToString('00')):$($Minuto.ToString('00'))"

# Executar mesmo sem usuário logado
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

try {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description "Coleta automática de inteligência do AgentePetrobras" `
        -Force

    Write-Host "Tarefa '$TaskName' criada com sucesso!" -ForegroundColor Green
    Write-Host "  Horário: $($Hora.ToString('00')):$($Minuto.ToString('00')) diariamente" -ForegroundColor Cyan
    Write-Host "  Modelo:  $Modelo" -ForegroundColor Cyan
    Write-Host "  Script:  $ColetorPy" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Para testar manualmente:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "Para ver logs:" -ForegroundColor Yellow
    Write-Host "  Get-Content '$LogFile' -Tail 20" -ForegroundColor White
    Write-Host ""
    Write-Host "Para desinstalar:" -ForegroundColor Yellow
    Write-Host "  .\agendar_coleta.ps1 -Uninstall" -ForegroundColor White

    # Mostra a tarefa criada
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State, Triggers, Actions
}
catch {
    Write-Error "Erro ao criar tarefa: $_"
    Write-Host ""
    Write-Host "Dica: Execute o PowerShell como Administrador e tente novamente." -ForegroundColor Yellow
    exit 1
}
#>
