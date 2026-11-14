param([ValidateRange(1024,65535)][int]$Port=8001)
$ErrorActionPreference='Stop'
$ai=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$root=[IO.Path]::GetFullPath((Join-Path $ai '..'))
$python=Join-Path $root '.scratch/rag-venv/Scripts/python.exe'
$e5=Join-Path $root '.scratch/rag-models/multilingual-e5-small'
$corpus=Join-Path $root '.scratch/rag-data/public-corpus.json'
$index=Join-Path $root '.scratch/rag-data/faiss'
if(-not (Test-Path -LiteralPath $python)){throw 'RAG venv missing: prepare .scratch/rag-venv first.'}
if(-not (Test-Path -LiteralPath (Join-Path $e5 'config.json'))){throw 'Pinned E5 snapshot missing.'}
if(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue){throw "Port $Port is already in use; do not start a second RAG server."}
$null=Invoke-RestMethod 'http://127.0.0.1:8080/api/v1/amenities/summary' -TimeoutSec 15
$model=(Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 6).models | Where-Object name -eq 'qwen3:4b-instruct' | Select-Object -First 1
if(-not $model){throw 'Install the approved qwen3:4b-instruct model in Ollama first.'}
$env:RAG_LLM_PROVIDER='ollama';$env:RAG_OLLAMA_URL='http://127.0.0.1:11434'
$env:RAG_OLLAMA_MODEL='qwen3:4b-instruct';$env:RAG_OLLAMA_DIGEST=$model.digest
$env:RAG_OLLAMA_KEEP_ALIVE_SECONDS='300';$env:RAG_E5_PATH=$e5
$env:RAG_INDEX_DIR=$index;$env:RAG_CORPUS_PATH=$corpus
$env:RAG_DOCUMENT_CORPUS_PATH=Join-Path $root '.scratch/rag-data/documents-corpus.json'
$env:RAG_BACKEND_URL='http://127.0.0.1:8080';$env:RAG_BACKEND_TIMEOUT_SECONDS='30'
$env:RAG_RESEARCH_ENABLED='false';$env:RAG_SQL_ENABLED='false'
$env:HF_HUB_OFFLINE='1';$env:TRANSFORMERS_OFFLINE='1';$env:TOKENIZERS_PARALLELISM='false'
$env:PYTHONPATH=$ai
function Run-Python([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments){
    $previous=$ErrorActionPreference;$ErrorActionPreference='Continue'
    try{& $python @Arguments;if($LASTEXITCODE -ne 0){throw "RAG command failed with exit code $LASTEXITCODE"}}
    finally{$ErrorActionPreference=$previous}
}
Push-Location -LiteralPath $root
try{
    # A fresh PUBLIC API snapshot expires after 24h. No crawl, import, SQL or database writes.
    Run-Python -Arguments @('-X','utf8',(Join-Path $ai 'scripts/build_rag_corpus.py'),'--output',$corpus)
    Run-Python -Arguments @('-X','utf8',(Join-Path $ai 'scripts/build_rag_index.py'),'--corpus',$corpus,'--e5-path',$e5,'--output',$index)
    Write-Host "Starting public RAG on 127.0.0.1:$Port. Research and direct SQL are disabled."
    Set-Location -LiteralPath $ai
    Run-Python -Arguments @('-X','utf8','-m','uvicorn','rag_main:app','--host','127.0.0.1','--port',[string]$Port,'--no-proxy-headers')
}finally{Pop-Location}