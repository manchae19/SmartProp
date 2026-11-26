param([string]$Root=(Join-Path $PSScriptRoot '..'),[switch]$SkipValuation,[switch]$CheckOnly)
$ErrorActionPreference='Stop';$Root=(Resolve-Path -LiteralPath $Root).Path
. (Join-Path $PSScriptRoot 'local-runtime.ps1')
if($CheckOnly){& (Join-Path $PSScriptRoot 'status-smartprop-local.ps1') -Root $Root;return}
. (Join-Path $Root 'backend/scripts/load-env.ps1')
$run=Join-Path $Root '.local-run';New-Item -ItemType Directory -Force $run|Out-Null
if(-not(Test-SpPort 3306)){try{Start-Service MYSQL80 -ErrorAction Stop}catch{throw 'MySQL is stopped. In Administrator CMD run: net start MYSQL80. No database was changed.'}}
if(-not(Test-SpPort 11434)){$ollama=(Get-Command ollama -ErrorAction Stop).Source;Start-SpService $Root $run 'ollama' 11434 'http://127.0.0.1:11434/api/tags' $ollama @('serve') $Root}
$node=(Get-Command node -ErrorAction Stop).Source;$python=Join-Path $Root '.scratch/rag-venv/Scripts/python.exe'
foreach($path in @($python,(Join-Path $Root 'frontend/node_modules/vite/bin/vite.js'),(Join-Path $Root 'backend/target/smartprop-backend-0.1.0.jar'))){if(-not(Test-Path -LiteralPath $path)){throw "Missing prerequisite: $path. Follow README first-time setup; no automatic install or database reset."}}
$env:SMARTPROP_OVERVIEW_CACHE_DIR=Join-Path $run 'cache/land-overviews'
$env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:8080';$env:SMARTPROP_DEV_CHAT_TARGET='http://127.0.0.1:8001'
$ps=(Get-Command powershell -ErrorAction Stop).Source
Start-SpService $Root $run 'backend' 8080 'http://127.0.0.1:8080/actuator/health' $ps @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $Root 'backend/scripts/run-local.ps1')+'"'),'-Transport','NIO2','-Chat','-Valuation') $Root
if(-not $SkipValuation){Start-SpService $Root $run 'valuation' 8000 'http://127.0.0.1:8000/health' $ps @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $Root 'backend/scripts/run-valuation.ps1')+'"')) $Root}
Start-SpService $Root $run 'rag' 8001 'http://127.0.0.1:8001/chat/health' $ps @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $Root 'ai-services/scripts/run-chat-local.ps1')+'"')) $Root
Start-SpService $Root $run 'frontend' 5173 'http://127.0.0.1:5173/@vite/client' $node @(('"'+(Join-Path $Root 'frontend/node_modules/vite/bin/vite.js')+'"'),'--host','127.0.0.1','--port','5173','--strictPort') (Join-Path $Root 'frontend')
& (Join-Path $PSScriptRoot 'status-smartprop-local.ps1') -Root $Root
Write-Host 'Open http://127.0.0.1:5173/home ; no migration, seed or dataset import was run.'