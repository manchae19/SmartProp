param([ValidateRange(1024,65535)][int]$Port=8000)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bundle=Join-Path $root 'frontend/integrations/valuation-v6'
$python=Join-Path $root 'backend/var/valuation-v6-runtime/python/python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Run backend/scripts/setup-valuation-runtime.ps1 first.'}
$manifest=Get-Content -LiteralPath (Join-Path $bundle 'SOURCE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
$excludedTestFiles=@('tests/fixtures/v6_validation_parity.json','tests/smoke_http_v6.py','tests/test_api_v6.py')
foreach($file in $manifest.files){
 if($file.path -in $excludedTestFiles){continue} # Tests are excluded from this source distribution; runtime checks remain mandatory.
 $path=[IO.Path]::GetFullPath((Join-Path $bundle $file.path))
 if(-not $path.StartsWith($bundle+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid bundle path'}
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $file.sha256){throw ('Changed model bundle file: '+$file.path)}
}
& $python -X utf8 (Join-Path $bundle 'run_api.py') --port $Port
if($LASTEXITCODE -ne 0){throw 'Valuation runtime stopped with an error'}
