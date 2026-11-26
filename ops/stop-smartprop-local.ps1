param([string]$Root=(Join-Path $PSScriptRoot '..'))
$ErrorActionPreference='Stop';$Root=(Resolve-Path -LiteralPath $Root).Path
. (Join-Path $PSScriptRoot 'local-runtime.ps1')
$run=Join-Path $Root '.local-run';$retained=@()
foreach($entry in @(Read-SpRegistry $run)){
 $process=Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)" -ErrorAction SilentlyContinue
 if(-not $process){Write-Host ($entry.name+': already stopped');continue}
 if($entry.root -ne $Root -or $process.CreationDate.ToUniversalTime().ToString('o') -ne $entry.created -or $process.CommandLine -ne $entry.command){Write-Warning ($entry.name+': ownership/PID changed; not stopped');$retained+=$entry;continue}
 $snapshot=@(Get-CimInstance Win32_Process);$tree=@($process);$queue=@($process.ProcessId)
 while($queue.Count){$children=@($snapshot|Where-Object {$_.ParentProcessId -in $queue});$tree+=$children;$queue=@($children | ForEach-Object {$_.ProcessId})}
 [array]::Reverse($tree)
 foreach($child in $tree){$current=Get-CimInstance Win32_Process -Filter "ProcessId=$($child.ProcessId)" -ErrorAction SilentlyContinue;if($current -and $current.CreationDate -eq $child.CreationDate){Stop-Process -Id $current.ProcessId -ErrorAction SilentlyContinue}}
 Write-Host ($entry.name+': stopped owned process tree')
}
if(Test-Path -LiteralPath $run){ConvertTo-Json -InputObject @($retained) -Depth 4 | Set-Content -LiteralPath (Join-Path $run 'services.json') -Encoding UTF8}
Write-Host 'Existing services not started by this launcher were left running. No data/cache was deleted.'