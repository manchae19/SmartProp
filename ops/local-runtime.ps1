# Shared helpers: no SQL, credentials in logs, migrations or implicit process termination.
function Test-SpPort([int]$Port){$client=New-Object Net.Sockets.TcpClient;try{$client.Connect('127.0.0.1',$Port);return $true}catch{return $false}finally{$client.Dispose()}}
function Get-SpHealth([string]$Url){try{return Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 4}catch{return $null}}
function Get-SpRevision([string]$Root){
 $rag=Join-Path $Root 'ai-services/app/rag';$land=Join-Path $Root 'ai-services/app/land'
 $files=@((Join-Path $rag 'api.py'),(Join-Path $rag 'orchestrator.py'),(Join-Path $rag 'land_chat.py'),(Join-Path $land 'conversation_router.py'),(Join-Path $rag 'buyer_search.py'),(Join-Path $land 'api.py'),(Join-Path $land 'overview.py'),(Join-Path $land 'query_rules.py'),(Join-Path $land 'paths.py'))
 $stream=New-Object IO.MemoryStream;try{foreach($file in $files){$bytes=[IO.File]::ReadAllBytes($file);$stream.Write($bytes,0,$bytes.Length)};$sha=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($sha.ComputeHash($stream.ToArray())).Replace('-','').ToLowerInvariant()).Substring(0,16)}finally{$sha.Dispose()}}finally{$stream.Dispose()}
}
function Read-SpRegistry([string]$RunDirectory){$path=Join-Path $RunDirectory 'services.json';if(Test-Path -LiteralPath $path){return @(Get-Content -LiteralPath $path -Raw|ConvertFrom-Json)};return @()}
function Start-SpService([string]$Root,[string]$RunDirectory,[string]$Name,[int]$Port,[string]$Url,[string]$File,[string[]]$Arguments,[string]$WorkingDirectory){
 if(Test-SpPort $Port){
  $health=Get-SpHealth $Url;if(-not $health -or $health.StatusCode -ne 200){throw "$Name port $Port is occupied but unhealthy; no duplicate started."}
  if($Name -eq 'rag'){
   if($health.Headers['X-SmartProp-Chat-Revision'] -ne (Get-SpRevision $Root)){throw 'RAG code is stale/different. Stop the correct previous RAG process and rerun; no process was killed.'}
   $schema=Invoke-RestMethod "http://127.0.0.1:$Port/openapi.json" -TimeoutSec 5
   $landRoot=if($env:SMARTPROP_LAND_DATA_DIR){$env:SMARTPROP_LAND_DATA_DIR}else{Join-Path $Root ('SMARTPROP_DATA/raw/land_demo_hoa_xuan/'+$(if($env:SMARTPROP_LAND_DATA_VERSION){$env:SMARTPROP_LAND_DATA_VERSION}else{'HX-LAND-DEMO-20261126'}))}
   if($env:RAG_LAND_ENABLED -notmatch '^(false|0|off)$' -and (Test-Path -LiteralPath $landRoot) -and -not $schema.paths.PSObject.Properties['/land/records/{record_id}/overview']){throw 'RAG is missing the land overview endpoint.'}
  }
  Write-Host "$Name : reused healthy service on $Port (not adopted for stopping)";return
 }
 $logs=Join-Path $RunDirectory 'logs';New-Item -ItemType Directory -Force $logs|Out-Null;$stamp=Get-Date -Format 'yyyyMMdd-HHmmssfff'
 $process=Start-Process -FilePath $File -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -RedirectStandardOutput (Join-Path $logs "$Name-$stamp.out.log") -RedirectStandardError (Join-Path $logs "$Name-$stamp.err.log") -WindowStyle Hidden -PassThru
 $info=Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
 $entry=[pscustomobject]@{name=$Name;port=$Port;pid=$process.Id;created=$info.CreationDate.ToUniversalTime().ToString('o');command=$info.CommandLine;root=$Root}
 $items=@((Read-SpRegistry $RunDirectory)|Where-Object {$_ -and $_.name -ne $Name})
 $all=@($items)+@($entry)
 ConvertTo-Json -InputObject $all -Depth 4 | Set-Content -LiteralPath (Join-Path $RunDirectory 'services.json') -Encoding UTF8
 $deadline=(Get-Date).AddSeconds($(if($Name -eq 'rag'){240}else{60}))
 while((Get-Date) -lt $deadline){if(Get-SpHealth $Url){Write-Host "$Name : ready on $Port";return};if($process.HasExited){throw "$Name exited. See $logs"};Start-Sleep -Milliseconds 750}
 throw "$Name not ready. See $logs; process was not automatically killed."
}
function Enter-SpRuntimeLock([string]$Root){
 $hash=[Security.Cryptography.SHA256]::Create()
 try{$key=[BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($Root.ToLowerInvariant()))).Replace('-','')}finally{$hash.Dispose()}
 $mutex=New-Object Threading.Mutex($false,('Local\SmartProp-'+$key))
 try{$acquired=$mutex.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$acquired=$true}
 if(-not $acquired){$mutex.Dispose();throw 'Another SmartProp start/stop is in progress. Retry when it finishes.'}
 return $mutex
}
