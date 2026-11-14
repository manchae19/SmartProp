<#
.SYNOPSIS
    SmartProp: Script import dữ liệu crawler (Bước 14) vào MySQL qua PowerShell.
.DESCRIPTION
    Script thực thi Data Quality Gate và import 3.204 bản ghi từ file CSV vào MySQL (idempotent).
.EXAMPLE
    .\backend\scripts\import-external-listings.ps1
    .\backend\scripts\import-external-listings.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [string]$CsvPath = "",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 3306,
    [string]$Database = "smartprop",
    [string]$User = "root",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
if (-not $CsvPath) {
    $CsvPath = Join-Path $ProjectRoot "ai-services\app\data\processed\remaining_diversity_review\runs\518bbc989587326c\eligible.csv"
}

$FullCsvPath = (Resolve-Path $CsvPath).Path

$PythonExe = Join-Path $ProjectRoot "ai-services\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python.exe"
}

$ScriptPy = Join-Path $PSScriptRoot "import_external_listings.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " SMARTPROP - BƯỚC 14: IMPORT EXTERNAL LISTINGS & QUALITY GATE " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "CSV Source: $FullCsvPath"
Write-Host "Target DB:  $HostName`:$Port/$Database"

$argsList = @(
    "-X", "utf8",
    $ScriptPy,
    "--csv", $FullCsvPath,
    "--host", $HostName,
    "--port", $Port,
    "--database", $Database,
    "--user", $User
)

if ($DryRun) {
    $argsList += "--dry-run"
}

& $PythonExe @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Import stopped; inspect the error before retrying. Do not repair or recreate tables."
}
