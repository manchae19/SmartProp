param([string]$PythonCommand='py')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$service=Join-Path $root 'ai-services'
$python=Join-Path $service '.venv/Scripts/python.exe'
if(-not(Test-Path -LiteralPath $python)){
    & $PythonCommand -3.14 -m venv (Join-Path $service '.venv')
    if($LASTEXITCODE -ne 0){throw 'Create the ai-services Python 3.14 environment first.'}
}
& $python -m pip install -r (Join-Path $service 'requirements-dev.txt')
if($LASTEXITCODE -ne 0){throw 'Valuation dependency setup failed.'}
Write-Output 'Canonical v6 runtime ready: ai-services/run_api.py. No second model bundle is installed.'
