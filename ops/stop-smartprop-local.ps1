param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$RunDirectory = $(
        Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')).Path '.local-run'
    )
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path $Root).Path

# Only stop processes recorded by start-smartprop-local.ps1. MySQL/RAG Chat are not managed here.
foreach ($name in @('frontend', 'backend', 'imagecheck')) {
    $pidFile = Join-Path $RunDirectory ($name + '.pid')
    if (-not (Test-Path -LiteralPath $pidFile)) {
        Write-Output ($name + ': no PID file (not started by this script)')
        continue
    }
    $processId = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        & taskkill.exe /PID $processId /T /F | Out-Null
        Write-Output ($name + ': stopped PID ' + $processId)
    } else {
        Write-Output ($name + ': PID ' + $processId + ' is already gone')
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
Write-Output 'Stopped only services recorded by start-smartprop-local.ps1. MySQL and RAG Chat were not touched.'
