param([string]$Output)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'load-env.ps1')
$backend=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if(-not $Output){$Output=Join-Path $backend ('var/storage-audit-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.tsv')}
$source=if($env:STORAGE_ROOT){$env:STORAGE_ROOT}else{'./var/uploads'}
$source=if([IO.Path]::IsPathRooted($source)){[IO.Path]::GetFullPath($source)}else{[IO.Path]::GetFullPath((Join-Path $backend $source))}
$driver=Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE '.m2/repository/com/mysql/mysql-connector-j') -Filter '*.jar' -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if(-not $driver){throw 'Build backend first to cache the MySQL JDBC driver.'}
$java=if($env:JAVA_HOME){Join-Path $env:JAVA_HOME 'bin/java.exe'}else{(Get-Command java -ErrorAction Stop).Source}
& $java -cp $driver.FullName (Join-Path $PSScriptRoot 'StorageAudit.java') $source ([IO.Path]::GetFullPath($Output))
if($LASTEXITCODE -ne 0){throw 'Storage audit failed.'}
Write-Output "Read-only report: $Output"