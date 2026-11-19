param(
  [Parameter(Mandatory=$true)][ValidateSet('Backend','Rag','Frontend')][string]$Service,
  [string]$RuntimeRoot=''
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if(-not $RuntimeRoot){$RuntimeRoot=$root}
$port=switch($Service){'Backend'{18080}'Rag'{18081}'Frontend'{15173}}
if(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue){throw "Port $port already running; do not start a second instance."}
if($Service -eq 'Backend'){
  $profile=Join-Path $env:TEMP 'smartprop-integration-runtime.local.json'
  if(-not(Test-Path -LiteralPath $profile)){throw 'Prepare isolated MySQL and local runtime credentials first; see ops/INTEGRATION_REVIEW.md.'}
  $config=Get-Content -LiteralPath $profile -Raw | ConvertFrom-Json
  if($config.DB_URL -ne 'jdbc:mysql://127.0.0.1:13307/smartprop_integration_20261117?connectionTimeZone=UTC'){throw 'Refusing a non-isolated database target.'}
  foreach($entry in $config.PSObject.Properties){[Environment]::SetEnvironmentVariable($entry.Name,[string]$entry.Value,'Process')}
  $env:PORT='18080';$env:SPRING_DATASOURCE_URL=$config.DB_URL;$env:SPRING_DATASOURCE_USERNAME=$config.DB_USER;$env:SPRING_DATASOURCE_PASSWORD=$config.DB_PASSWORD
  $env:CORS_ORIGINS='http://127.0.0.1:15173';$env:APP_RECOMMENDATION_V11_ENABLED='true'
  $env:GEOCODING_ENABLED='false';$env:GOOGLE_LOGIN_ENABLED='false';$env:APP_IMAGE_ANALYSIS_ENABLED='false'
  $env:REFRESH_ENABLED='true';$env:REFRESH_SECURE_COOKIE='false'
  $env:STORAGE_ROOT=Join-Path $env:TEMP 'smartprop-integration-uploads'
  Set-Location -LiteralPath $root
  & java -jar backend/target/smartprop-backend-0.1.0.jar
}elseif($Service -eq 'Rag'){
  $python=Join-Path $RuntimeRoot '.scratch/rag-venv/Scripts/python.exe'
  $model=Join-Path $RuntimeRoot '.scratch/rag-models/multilingual-e5-small'
  if(-not(Test-Path -LiteralPath $python) -or -not(Test-Path -LiteralPath (Join-Path $model 'config.json'))){throw 'Pinned RAG runtime/E5 model is missing; supply -RuntimeRoot with the prepared runtime.'}
  $state=Join-Path $env:TEMP 'smartprop-integration-rag-20261117'
  New-Item -ItemType Directory -Force -Path $state | Out-Null
  $env:RAG_BACKEND_URL='http://127.0.0.1:18080';$env:RAG_BACKEND_TIMEOUT_SECONDS='30'
  $env:RAG_LLM_PROVIDER='ollama';$env:RAG_E5_PATH=$model;$env:RAG_CORPUS_PATH=Join-Path $state 'public-corpus.json';$env:RAG_INDEX_DIR=Join-Path $state 'index'
  $env:RAG_SQL_ENABLED='false';$env:RAG_RESEARCH_ENABLED='false';$env:HF_HUB_OFFLINE='1';$env:TRANSFORMERS_OFFLINE='1'
  Set-Location -LiteralPath (Join-Path $root 'ai-services')
  & $python -X utf8 -B scripts/build_rag_corpus.py --output $env:RAG_CORPUS_PATH
  if($LASTEXITCODE -ne 0){throw 'Cannot build isolated public corpus.'}
  & $python -X utf8 -B -m uvicorn rag_main:app --host 127.0.0.1 --port 18081 --no-proxy-headers
}else{
  $env:SMARTPROP_DEV_API_TARGET='http://127.0.0.1:18080';$env:SMARTPROP_DEV_CHAT_TARGET='http://127.0.0.1:18081';$env:SMARTPROP_DEV_PORT='15173'
  Set-Location -LiteralPath (Join-Path $root 'frontend')
  & node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 15173 --strictPort
}
