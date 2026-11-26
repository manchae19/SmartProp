param([switch]$Force)
$ErrorActionPreference='Stop';$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $root 'backend/scripts/load-env.ps1')
$env:RAG_CORPUS_PATH=Join-Path $root '.scratch/rag-data/public-corpus.json';$env:RAG_INDEX_DIR=Join-Path $root '.scratch/rag-data/faiss';$env:RAG_E5_PATH=Join-Path $root '.scratch/rag-models/multilingual-e5-small';$env:RAG_BACKEND_URL='http://127.0.0.1:8080';$env:RAG_SQL_ENABLED='false';$env:RAG_RESEARCH_ENABLED='false';$env:HF_HUB_OFFLINE='1';$env:TRANSFORMERS_OFFLINE='1'
$arguments=@('-X','utf8',(Join-Path $root 'ai-services/scripts/prepare_rag_local.py'));if($Force){$arguments+='--force'}
& (Join-Path $root '.scratch/rag-venv/Scripts/python.exe') @arguments
if($LASTEXITCODE -ne 0){throw 'Public RAG preparation failed; previous corpus was kept. See error above.'}