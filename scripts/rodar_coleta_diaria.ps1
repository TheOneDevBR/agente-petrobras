<#
.SYNOPSIS
  Roda a coleta de inteligência e salva log com timestamp.

.DESCRIPTION
  Script auxiliar para execução manual ou via Task Scheduler.
  Usa 7B via Docker se disponível, fallback para 1.5B.

.EXAMPLE
  .\rodar_coleta_diaria.ps1
  .\rodar_coleta_diaria.ps1 -Modelo "qwen2.5:7b"
#>

param(
    [string]$Modelo = "qwen2.5:1.5b",
    [int]$MaxTokens = 12000
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "coleta_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$env:AGENTE_LOCAL_MODEL = $Modelo
$env:PYTHONIOENCODING = 'utf-8'

Write-Host "Iniciando coleta..." -ForegroundColor Cyan
Write-Host "  Modelo: $Modelo" -ForegroundColor Gray
Write-Host "  Log:    $LogFile" -ForegroundColor Gray
Write-Host ("-" * 60)

$ColetorPy = Join-Path $ProjectRoot "cli_python\coletor\coletor.py"
python "$ColetorPy" --max-tokens $MaxTokens 2>&1 | Tee-Object -FilePath $LogFile

Write-Host ("-" * 60)
Write-Host "Coleta finalizada. Log salvo em: $LogFile" -ForegroundColor Green
