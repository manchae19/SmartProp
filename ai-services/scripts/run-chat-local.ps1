param(
    [ValidateRange(1024, 65535)][int]$Port = 8001,
    [string]$BackendUrl = 'http://127.0.0.1:8080',
    [string]$OllamaUrl = 'http://127.0.0.1:11434',
    [string]$PythonPath = '',
    [string]$E5Path = '',
    [string]$DataDir = '',
    [ValidateRange(0, 300)][int]$KeepAliveSeconds = 0,
    [switch]$CheckOnly,
    [switch]$ForceRefresh
)
$ErrorActionPreference = 'Stop'

$ai = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$root = [IO.Path]::GetFullPath((Join-Path $ai '..'))
$mainRoot = $root
if ($env:SMARTPROP_MAIN_ROOT) {
    $mainRoot = [IO.Path]::GetFullPath($env:SMARTPROP_MAIN_ROOT)
} else {
    $candidate = [IO.Path]::GetFullPath((Join-Path $root '..\..'))
    if (Test-Path -LiteralPath (Join-Path $candidate '.scratch')) { $mainRoot = $candidate }
}

function Resolve-ExistingPath([string]$Primary, [string]$Fallback, [string]$Label) {
    if (Test-Path -LiteralPath $Primary) { return [IO.Path]::GetFullPath($Primary) }
    if (Test-Path -LiteralPath $Fallback) { return [IO.Path]::GetFullPath($Fallback) }
    throw "$Label missing. Tried '$Primary' and '$Fallback'."
}

$python = if ($PythonPath) { $PythonPath } else {
    Resolve-ExistingPath (Join-Path $root '.scratch/rag-venv/Scripts/python.exe') (Join-Path $mainRoot '.scratch/rag-ollama-venv/Scripts/python.exe') 'RAG Python runtime'
}
$e5 = if ($E5Path) { $E5Path } else {
    Resolve-ExistingPath (Join-Path $root '.scratch/rag-models/multilingual-e5-small') (Join-Path $mainRoot '.scratch/rag-models/multilingual-e5-small') 'E5 snapshot'
}
$data = if ($DataDir) { [IO.Path]::GetFullPath($DataDir) } else {
    Resolve-ExistingPath (Join-Path $root '.scratch/rag-data') (Join-Path $mainRoot '.scratch/rag-data') 'RAG data directory'
}
if (-not (Test-Path -LiteralPath (Join-Path $e5 'config.json'))) { throw "E5 snapshot is incomplete: '$e5'." }
if (-not (Test-Path -LiteralPath $python)) { throw "RAG Python runtime missing: '$python'." }

if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use. Stop the existing RAG process first; never reuse a RAG process across backend swaps."
}

Write-Host "RAG preflight: backend=$BackendUrl port=$Port data=$data"

# 1. Backend must be live and expose the public amenities catalog.
try {
    $summary = Invoke-RestMethod -Uri "$BackendUrl/api/v1/amenities/summary" -TimeoutSec 15
} catch {
    throw "Backend unavailable at $BackendUrl. Start Spring Boot before RAG. Detail: $($_.Exception.Message)"
}
if (-not $summary.catalogVersion) { throw "Backend amenities summary is invalid at $BackendUrl." }

# 2. Recommendation contract must be V1.1; this is required by the RAG tool layer.
$probeBody = @{ budgetVnd = 3000000000; purpose = 'LIVING'; propertyType = 'ALL'; limit = 1 } | ConvertTo-Json -Compress
try {
    $rec = Invoke-RestMethod -Uri "$BackendUrl/api/v1/recommendations" -Method Post -ContentType 'application/json' -Body $probeBody -TimeoutSec 25
} catch {
    throw "Recommendation preflight failed at $BackendUrl. Start backend with APP_RECOMMENDATION_V11_ENABLED=true. Detail: $($_.Exception.Message)"
}
if ($rec.method -ne 'HEURISTIC_V1_1' -or $rec.mode -ne 'SAFE') {
    throw "Backend Recommendation returned method='$($rec.method)' mode='$($rec.mode)'. RAG requires HEURISTIC_V1_1/SAFE. Set APP_RECOMMENDATION_V11_ENABLED=true and restart backend."
}

# 3. Ollama must be running with the approved model.
try {
    $tags = Invoke-RestMethod -Uri "$OllamaUrl/api/tags" -TimeoutSec 8
} catch {
    throw "Ollama unavailable at $OllamaUrl. Start Ollama before RAG. Detail: $($_.Exception.Message)"
}
$model = $tags.models | Where-Object { $_.name -eq 'qwen3:4b-instruct' } | Select-Object -First 1
if (-not $model) { throw "Ollama model qwen3:4b-instruct is missing at $OllamaUrl." }

function Invoke-ArtifactProbe([string]$Corpus, [string]$Index) {
    $probe = Join-Path $env:TEMP ("smartprop-rag-probe-" + $PID + ".py")
    @'
import json, os, sys, datetime
sys.path.insert(0, os.environ['SMARTPROP_AI_ROOT'])
from app.rag.knowledge import KnowledgeStore
from app.rag.embedding import E5Embedding
from app.rag.index_store import IndexStore
try:
    corpus = KnowledgeStore(os.environ['SMARTPROP_PREFLIGHT_CORPUS']).load()
    vectors, manifest = IndexStore(os.environ['SMARTPROP_PREFLIGHT_INDEX'], E5Embedding(os.environ['SMARTPROP_PREFLIGHT_E5'])).load(corpus['documents'])
    age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(corpus['builtAt'])).total_seconds() / 3600.0
    print(json.dumps({'ok': True, 'documents': len(corpus['documents']), 'builtAt': corpus['builtAt'], 'contentHash': corpus['contentHash'],
                      'ageHours': round(age, 2), 'indexVersion': manifest.get('version'), 'count': manifest.get('count'),
                      'dimensions': manifest.get('dimensions')}))
except Exception as error:
    print(json.dumps({'ok': False, 'error': type(error).__name__ + ': ' + str(error)}))
    sys.exit(1)
'@ | Set-Content -LiteralPath $probe -Encoding UTF8
    $previousPath = $env:PYTHONPATH
    $env:PYTHONPATH = $ai
    $env:SMARTPROP_AI_ROOT = $ai
    $env:SMARTPROP_PREFLIGHT_CORPUS = $Corpus
    $env:SMARTPROP_PREFLIGHT_INDEX = $Index
    $env:SMARTPROP_PREFLIGHT_E5 = $e5
    $previousError = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Push-Location -LiteralPath $ai
        try { $output = & $python -X utf8 $probe 2>&1 | Out-String } finally { Pop-Location }
    } finally {
        $ErrorActionPreference = $previousError
        $env:PYTHONPATH = $previousPath
        Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
    }
    if ($LASTEXITCODE -ne 0) { return @{ ok = $false; error = $output.Trim() } }
    try { return ($output.Trim() | ConvertFrom-Json) } catch { return @{ ok = $false; error = $output.Trim() } }
}

function Test-Artifacts([string]$Directory) {
    $corpus = Join-Path $Directory 'public-corpus.json'
    $index = Join-Path $Directory 'faiss'
    if (-not (Test-Path -LiteralPath $corpus)) { return @{ ok = $false; error = "missing $corpus" } }
    if (-not (Test-Path -LiteralPath $index)) { return @{ ok = $false; error = "missing $index" } }
    return Invoke-ArtifactProbe $corpus $index
}

$activeCorpus = Join-Path $data 'public-corpus.json'
$activeIndex = Join-Path $data 'faiss'
$probe = Test-Artifacts $data
$reuse = $false
if ($probe.ok -and $probe.ageHours -le 24 -and $probe.count -eq $probe.documents -and $probe.dimensions -eq 384 -and -not $ForceRefresh) {
    $reuse = $true
    Write-Host ("Artifacts reused: {0} docs, age {1}h, index {2}" -f $probe.documents, $probe.ageHours, $probe.indexVersion)
} else {
    $reason = if (-not $probe.ok) { $probe.error } elseif ($probe.ageHours -gt 24) { "corpus TTL expired ($($probe.ageHours)h)" } elseif ($ForceRefresh) { 'ForceRefresh requested' } else { 'artifact/index mismatch' }
    if ($CheckOnly) { throw "Artifacts need refresh ($reason). Run without -CheckOnly to rebuild and swap safely." }
    Write-Host "Artifacts need refresh ($reason). Building into a staging directory; active artifacts stay until verified."

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $buildDir = "$data.build-$stamp"
    New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
    $env:RAG_BACKEND_URL = $BackendUrl
    $previousPath = $env:PYTHONPATH
    $env:PYTHONPATH = $ai
    Push-Location -LiteralPath $ai
    try {
        & $python -X utf8 (Join-Path $ai 'scripts/build_rag_corpus.py') --output (Join-Path $buildDir 'public-corpus.json')
        if ($LASTEXITCODE -ne 0) { throw 'Corpus rebuild failed; active artifacts were not changed.' }
        & $python -X utf8 (Join-Path $ai 'scripts/build_rag_index.py') --corpus (Join-Path $buildDir 'public-corpus.json') --e5-path $e5 --output (Join-Path $buildDir 'faiss')
        if ($LASTEXITCODE -ne 0) { throw 'FAISS rebuild failed; active artifacts were not changed.' }
    } finally {
        Pop-Location
        $env:PYTHONPATH = $previousPath
    }

    $verified = Test-Artifacts $buildDir
    if (-not $verified.ok -or $verified.ageHours -gt 24 -or $verified.count -ne $verified.documents -or $verified.dimensions -ne 384) {
        throw "New artifacts failed verification ($($verified.error)); active artifacts were not changed."
    }

    $previousDir = ''
    if (Test-Path -LiteralPath $data) {
        $previousDir = "$data.prev-$stamp"
        Move-Item -LiteralPath $data -Destination $previousDir
    }
    try {
        Move-Item -LiteralPath $buildDir -Destination $data
    } catch {
        if ($previousDir -and (Test-Path -LiteralPath $previousDir)) { Move-Item -LiteralPath $previousDir -Destination $data }
        throw "Artifact swap failed; previous artifacts restored. Detail: $($_.Exception.Message)"
    }
    Write-Host ("Artifacts refreshed: {0} docs, age {1}h, index {2}" -f $verified.documents, $verified.ageHours, $verified.indexVersion)
    if ($previousDir) { Write-Host "Previous artifacts preserved at $previousDir" }
}

if ($CheckOnly) {
    Write-Host 'PREFLIGHT PASS: backend V1.1, Ollama, corpus and index are ready. RAG was not started.'
    return
}

$env:RAG_LLM_PROVIDER = 'ollama'
$env:RAG_OLLAMA_URL = $OllamaUrl
$env:RAG_OLLAMA_MODEL = 'qwen3:4b-instruct'
$env:RAG_OLLAMA_DIGEST = $model.digest
$env:RAG_OLLAMA_KEEP_ALIVE_SECONDS = [string]$KeepAliveSeconds
$env:RAG_E5_PATH = $e5
$env:RAG_INDEX_DIR = $activeIndex
$env:RAG_CORPUS_PATH = $activeCorpus
$env:RAG_BACKEND_URL = $BackendUrl
$env:RAG_BACKEND_TIMEOUT_SECONDS = '30'
$env:RAG_RESEARCH_ENABLED = 'false'
if (-not $env:RAG_SQL_ENABLED) { $env:RAG_SQL_ENABLED = 'false' }
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:TOKENIZERS_PARALLELISM = 'false'
$env:PYTHONPATH = $ai

Write-Host "Starting RAG on 127.0.0.1:$Port (keep-alive=$KeepAliveSeconds, research=off, sql=off)."
Push-Location -LiteralPath $ai
try {
    & $python -X utf8 -m uvicorn rag_main:app --host 127.0.0.1 --port ([string]$Port) --no-proxy-headers
    if ($LASTEXITCODE -ne 0) { throw "RAG server exited with code $LASTEXITCODE." }
} finally {
    Pop-Location
}
