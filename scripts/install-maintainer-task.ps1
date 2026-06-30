<#
.SYNOPSIS
  Registra (ou remove) a Tarefa Agendada do Windows que roda o maintainer-cycle
  local a cada 5 minutos. Roda no login do usuário, sem privilégio de admin.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install-maintainer-task.ps1
  powershell -ExecutionPolicy Bypass -File scripts\install-maintainer-task.ps1 -Remove
#>
param([switch]$Remove)

$taskName = 'AgentePetrobras-MaintainerLoop'
$script   = Join-Path $PSScriptRoot 'maintainer-cycle.ps1'

if ($Remove) {
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Host "Tarefa '$taskName' removida."
  return
}

$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
  -RepetitionInterval (New-TimeSpan -Minutes 5) `
  -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
  -Settings $settings -Description 'Maintainer-loop local (token-free) do agente-petrobras: sync + fila GitHub + CI, a cada 5 min.' `
  -Force | Out-Null

Write-Host "Tarefa '$taskName' registrada - roda a cada 5 min (local, 0 tokens)."
Write-Host "Log:  $env:LOCALAPPDATA\AgentePetrobras\maintainer-loop.log"
Write-Host "Flag: $env:LOCALAPPDATA\AgentePetrobras\needs-claude.flag (aparece so quando ha trabalho)"
