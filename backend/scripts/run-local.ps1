param([ValidateRange(1024,65535)][int]$Port=8080, [ValidateSet('NIO','NIO2')][string]$Transport='NIO', [switch]$Valuation)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'load-env.ps1')
$backendPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$jar=Join-Path $backendPath 'target/smartprop-backend-0.1.0.jar'
if(-not (Test-Path -LiteralPath $jar)) { throw 'Build first: .\scripts\run-maven.ps1 -B verify' }
$java=if($env:JAVA_HOME){Join-Path $env:JAVA_HOME 'bin/java.exe'}else{(Get-Command java -ErrorAction Stop).Source}
Push-Location -LiteralPath $backendPath
try {
    & $java -jar $jar "--server.port=$Port" "--app.server.transport=$Transport" ("--app.valuation.enabled="+$Valuation.ToString().ToLowerInvariant()) --spring.flyway.enabled=false --spring.sql.init.mode=never --spring.jpa.hibernate.ddl-auto=validate --app.seed.enabled=false --app.database-seed.enabled=false
    if($LASTEXITCODE -ne 0){throw "Backend exited with code $LASTEXITCODE"}
} finally { Pop-Location }
