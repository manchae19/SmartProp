$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$runtime=Join-Path $root 'backend/var/valuation-v6-runtime'
$python=Join-Path $runtime 'python/python.exe'
[IO.Directory]::CreateDirectory($runtime)|Out-Null
function Download-Verified([string]$Url,[string]$Destination,[string]$Sha256){
 if(-not(Test-Path -LiteralPath $Destination)){Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Destination}
 if((Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Sha256){throw "Checksum mismatch: $Destination"}
}
Download-Verified 'https://www.python.org/ftp/python/3.14.8/python-3.14.8-embed-amd64.zip' (Join-Path $runtime 'python-3.14.8-embed-amd64.zip') 'a93abe456ab01bd96d7a085b3cdb6566b3063f4241360d114142fbdb07f0a310'
if(-not(Test-Path -LiteralPath $python)){Expand-Archive -LiteralPath (Join-Path $runtime 'python-3.14.8-embed-amd64.zip') -DestinationPath (Join-Path $runtime 'python')}
[IO.File]::WriteAllText((Join-Path $runtime 'python/python314._pth'),"python314.zip`n.`nLib/site-packages`nimport site`n",[Text.UTF8Encoding]::new($false))
Download-Verified 'https://files.pythonhosted.org/packages/8a/6a/19e9fe04fca059ccf770861c7d5721ab4c2aebc539889e97c7977528a53b/pip-24.0-py3-none-any.whl' (Join-Path $runtime 'pip-24.0.whl') 'ba0d021a166865d2265246961bec0152ff124de910c5cc39f1156ce3fa7c69dc'
# Vendored dependencies; no global Python/pip/PATH/registry installation.
$previousErrorPreference=$ErrorActionPreference
try {
 $ErrorActionPreference='Continue'
 & $python -c "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pip',run_name='__main__')" (Join-Path $runtime 'pip-24.0.whl') install --require-hashes --only-binary=:all: --no-compile --disable-pip-version-check --target (Join-Path $runtime 'python/Lib/site-packages') -r (Join-Path $root 'frontend/integrations/valuation-v6/requirements-windows.lock')
 $pipExit=$LASTEXITCODE
} finally { $ErrorActionPreference=$previousErrorPreference }
if($pipExit -ne 0){throw 'Private valuation dependency setup failed'}
Write-Output 'Private valuation runtime ready. Start with backend/scripts/run-valuation.ps1.'
