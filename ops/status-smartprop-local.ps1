param([string]$Root=(Join-Path $PSScriptRoot '..'))
$ErrorActionPreference='Stop';$Root=(Resolve-Path -LiteralPath $Root).Path
. (Join-Path $PSScriptRoot 'local-runtime.ps1')
Write-Host ('MySQL 3306: '+(Test-SpPort 3306))
foreach($item in @(@('Backend','http://127.0.0.1:8080/actuator/health'),@('Valuation','http://127.0.0.1:8000/health'),@('RAG','http://127.0.0.1:8001/chat/health'),@('Frontend','http://127.0.0.1:5173/@vite/client'),@('Ollama','http://127.0.0.1:11434/api/tags'))){$response=Get-SpHealth $item[1];Write-Host ($item[0]+': '+$(if($response){'HTTP '+$response.StatusCode}else{'NOT READY'}));if($item[0] -eq 'RAG' -and $response){Write-Host ('RAG source revision matches: '+($response.Headers['X-SmartProp-Chat-Revision'] -eq (Get-SpRevision $Root)))}}
$corpus=Join-Path $Root '.scratch/rag-data/public-corpus.json'
if(Test-Path -LiteralPath $corpus){$c=Get-Content -LiteralPath $corpus -Raw -Encoding UTF8|ConvertFrom-Json;$age=([DateTimeOffset]::UtcNow-[DateTimeOffset]::Parse($c.builtAt)).TotalHours;Write-Host ('Public corpus age hours: '+[Math]::Round($age,2));if($age -ge 24){Write-Warning 'Corpus expired. Run ops/update-rag-data.ps1; expiry checks remain enabled.'}}
Write-Host ('Local logs/cache: '+(Join-Path $Root '.local-run'))