param([ValidateRange(1024,65535)][int]$Port=8000)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bundle=Join-Path $root 'ai-services'
$python=Join-Path $bundle '.venv/Scripts/python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Run backend/scripts/setup-valuation-runtime.ps1 first.'}
# The canonical predictor verifies the pinned model/schema/extractor hashes.
& $python -X utf8 (Join-Path $bundle 'run_api.py') --port $Port
if($LASTEXITCODE -ne 0){throw 'Valuation runtime stopped with an error'}
