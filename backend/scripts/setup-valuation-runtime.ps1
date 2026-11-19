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
$pipWheel=Join-Path $runtime 'pip-26.3-py3-none-any.zip'
Download-Verified 'https://files.pythonhosted.org/packages/07/25/ee8c38ae72d66b844ce8eb9711ba905dba21ca1a8a0c960057c41cd23337/pip-26.3-py3-none-any.whl' $pipWheel 'f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13'
Expand-Archive -LiteralPath $pipWheel -DestinationPath (Join-Path $runtime 'python/Lib/site-packages') -Force
# Vendored dependencies; no global Python/pip/PATH/registry installation.
& $python -m pip install --upgrade --require-hashes --only-binary=:all: --no-compile --disable-pip-version-check --target (Join-Path $runtime 'python/Lib/site-packages') -r (Join-Path $root 'ai-services/requirements-windows.lock')
if($LASTEXITCODE -ne 0){throw 'Private valuation dependency setup failed'}
Write-Output 'Private valuation runtime ready. Start with backend/scripts/run-valuation.ps1.'
