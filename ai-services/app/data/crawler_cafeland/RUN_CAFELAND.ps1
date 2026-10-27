param([int]$MaxNew = 1000, [int]$Pages = 200)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\..\..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = 'python' }
$outputDir = Join-Path $PSScriptRoot '..\data_raw\cafeland_batch'
& $python (Join-Path $PSScriptRoot 'crawl_cafeland_danang.py') --pages $Pages --max-new $MaxNew --delay 3 --output-dir $outputDir
exit $LASTEXITCODE
