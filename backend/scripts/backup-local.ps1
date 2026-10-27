param([string]$Destination,[string]$MySqlDump='C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'load-env.ps1')
$backend=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if(-not $Destination){$Destination=Join-Path $backend 'var/backups'}
$destinationRoot=[IO.Path]::GetFullPath($Destination)
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$backup=Join-Path $destinationRoot ('smartprop-'+$stamp+'-'+[guid]::NewGuid().ToString('N').Substring(0,6))
$source=if($env:STORAGE_ROOT){$env:STORAGE_ROOT}else{'./var/uploads'}
$source=if([IO.Path]::IsPathRooted($source)){[IO.Path]::GetFullPath($source)}else{[IO.Path]::GetFullPath((Join-Path $backend $source))}
if($destinationRoot.StartsWith($source.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)-or $destinationRoot -eq $source){throw 'Backup destination must be outside upload storage.'}
if(-not (Test-Path -LiteralPath $MySqlDump -PathType Leaf)){throw 'mysqldump was not found.'}
$dbUri=[Uri]($env:DB_URL -replace '^jdbc:','')
if($dbUri.Host -notin @('localhost','127.0.0.1')){throw 'This helper supports local MySQL only.'}
$database=$dbUri.AbsolutePath.Trim('/')
if($database -notmatch '^smartprop(?:_it_[a-zA-Z0-9_]+)?$'){throw 'Unexpected database name.'}
# Restrict access before writing credentials or backup data.
[IO.Directory]::CreateDirectory($backup)|Out-Null
$identity=[Security.Principal.WindowsIdentity]::GetCurrent().User
$acl=Get-Acl -LiteralPath $backup
$acl.SetAccessRuleProtection($true,$false)
$rule=[Security.AccessControl.FileSystemAccessRule]::new($identity,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
$acl.AddAccessRule($rule);Set-Acl -LiteralPath $backup -AclObject $acl
$credentials=Join-Path $backup '.mysql-client.cnf'
function Escape-Option([string]$value){return $value.Replace('\','\\').Replace('"','\"').Replace("`r",'\r').Replace("`n",'\n')}
$client="[client]`nuser=`"$(Escape-Option $env:DB_USER)`"`npassword=`"$(Escape-Option $env:DB_PASSWORD)`"`nhost=$($dbUri.Host)`nport=$($dbUri.Port)`n"
$complete=$false
try {
 [IO.File]::WriteAllText($credentials,$client,[Text.UTF8Encoding]::new($false));$client=$null
 $dump=Join-Path $backup 'database.sql'
 & $MySqlDump "--defaults-extra-file=$credentials" --single-transaction --skip-lock-tables --no-tablespaces --triggers --hex-blob --set-gtid-purged=OFF "--result-file=$dump" $database
 if($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $dump) -or (Get-Item -LiteralPath $dump).Length -eq 0){throw 'Database backup failed; this folder is incomplete.'}
 # DB snapshot first, files second. Retained/immutable file keys cover all committed references in the snapshot.
 if(Test-Path -LiteralPath $source){Copy-Item -LiteralPath $source -Destination (Join-Path $backup 'uploads') -Recurse}
 $hashes=@(Get-ChildItem -LiteralPath $backup -File -Recurse | Where-Object Name -ne '.mysql-client.cnf' | ForEach-Object {[ordered]@{file=$_.FullName.Substring($backup.Length+1);sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}})
 $manifest=[ordered]@{createdAt=(Get-Date).ToUniversalTime().ToString('o');database=$database;storagePresent=(Test-Path -LiteralPath $source);files=$hashes;complete=$true}
 $manifest|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $backup 'manifest.json') -Encoding UTF8
 $complete=$true;Write-Output "Backup completed: $backup"
}finally{
 if(Test-Path -LiteralPath $credentials){Remove-Item -LiteralPath $credentials -Force}
 if(-not $complete){Write-Warning 'Backup is incomplete. Do not use it for recovery.'}
}