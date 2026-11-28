[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$MySqlBin,
    [string]$PlaywrightCore,
    [string]$BrowserExecutable,
    [string]$OpenSsl,
    [ValidateRange(49152,65535)][int]$MySqlPort = 51953,
    [ValidateRange(49152,65535)][int]$FrontendPort = 51955,
    [switch]$FullRegression
)

$ErrorActionPreference = 'Stop'
if ($MySqlPort -eq $FrontendPort) { throw 'Select distinct fixture ports' }
foreach ($port in @($MySqlPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Fixture port $port is already in use"
    }
}
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('smartprop-pr48-runtime-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $fixture | Out-Null
$data = Join-Path $fixture 'data'
$exe = Join-Path $MySqlBin 'mysqld.exe'
$mysql = Join-Path $MySqlBin 'mysql.exe'
$argsSql = @('--no-defaults','--protocol=TCP','--host=127.0.0.1',"--port=$MySqlPort",
    '--user=root','--batch','--raw','--skip-column-names')
$processId = $null
$previous = @{}

function Set-FixtureEnv([string]$name, [string]$value) {
    if (!$previous.ContainsKey($name)) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

try {
    $init = Join-Path $fixture 'init.log'
    $serverLog = Join-Path $fixture 'mysql.log'
    $setup = Start-Process -FilePath $exe -ArgumentList "--no-defaults --initialize-insecure --datadir=""$data"" --log-error=""$init""" -WindowStyle Hidden -PassThru -Wait
    if ($setup.ExitCode -ne 0) { throw 'MySQL fixture could not initialize' }
    Start-Process -FilePath $exe -ArgumentList "--no-defaults --bind-address=127.0.0.1 --port=$MySqlPort --datadir=""$data"" --log-error=""$serverLog"" --skip-log-bin --mysqlx=OFF" -WindowStyle Hidden
    $listener = $null
    for ($attempt = 0; $attempt -lt 24; $attempt++) {
        $listener = @(Get-NetTCPConnection -LocalPort $MySqlPort -State Listen -ErrorAction SilentlyContinue)
        if ($listener.Count -gt 0) { break }
        Start-Sleep -Milliseconds 500
    }
    if ($listener.Count -ne 1 -or $listener[0].LocalAddress -ne '127.0.0.1') { throw 'Wrong fixture listener' }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener[0].OwningProcess)"
    if ($process.Name -ne 'mysqld.exe' -or !$process.CommandLine.Contains($fixture)) { throw 'Wrong fixture process' }
    $processId = $listener[0].OwningProcess
    $identity = & $mysql @argsSql -e 'SELECT @@server_uuid,@@datadir,@@port'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot identify fixture MySQL' }
    $uuid, $actualDir, $actualPort = $identity -split "\t"
    $resolvedDir = (Resolve-Path -LiteralPath $data).Path.TrimEnd('\')
    if ($actualPort -ne "$MySqlPort" -or (Resolve-Path -LiteralPath $actualDir).Path.TrimEnd('\') -ne $resolvedDir) {
        throw 'Wrong MySQL datadir or port'
    }

    $marker = [guid]::NewGuid().ToString('N')
    $legacy = [guid]::NewGuid().ToString('N')
    $password = [guid]::NewGuid().ToString('N')
    @"
CREATE DATABASE smartprop_pr48_runtime CHARACTER SET utf8mb4;
CREATE DATABASE smartprop_pr40_test CHARACTER SET utf8mb4;
CREATE USER 'pr48_fixture'@'127.0.0.1' IDENTIFIED BY '$password';
GRANT ALL ON smartprop_pr48_runtime.* TO 'pr48_fixture'@'127.0.0.1';
CREATE TABLE smartprop_pr48_runtime.pr48_isolation_marker(marker VARCHAR(32) NOT NULL);
INSERT INTO smartprop_pr48_runtime.pr48_isolation_marker VALUES ('$marker');
CREATE TABLE smartprop_pr40_test.pr40_isolation_marker(marker VARCHAR(32) NOT NULL);
INSERT INTO smartprop_pr40_test.pr40_isolation_marker VALUES ('$legacy');
"@ | & $mysql @argsSql
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create fixture schemas' }

    foreach ($name in @('DB_URL','DB_USER','DB_PASSWORD','SPRING_DATASOURCE_URL','SPRING_PROFILES_ACTIVE',
        'SPRING_FLYWAY_ENABLED','PR48_TLS_CERT','PR48_TLS_KEY')) { Set-FixtureEnv $name $null }
    $vars = @{
        PR48_RUNTIME = 'true'; PR48_DB_PORT = "$MySqlPort"; PR48_FRONTEND_PORT = "$FrontendPort"
        PR48_DB_UUID = $uuid; PR48_DB_DATADIR = $resolvedDir; PR48_DB_MARKER = $marker; PR48_DB_PASSWORD = $password
        PR48_STORAGE_ROOT = (Join-Path $fixture 'uploads')
        SMARTPROP_PR40_TEST_DB = "$MySqlPort/smartprop_pr40_test"; SMARTPROP_PR40_FIXTURE_MARKER = $legacy
    }
    foreach ($entry in $vars.GetEnumerator()) { Set-FixtureEnv $entry.Key $entry.Value }
    if ($PlaywrightCore) { Set-FixtureEnv 'PR40_BROWSER_PLAYWRIGHT' ((Resolve-Path -LiteralPath $PlaywrightCore).Path) }
    if ($BrowserExecutable) { Set-FixtureEnv 'PR40_BROWSER_EXECUTABLE' ((Resolve-Path -LiteralPath $BrowserExecutable).Path) }
    if ($OpenSsl) {
        $cert = Join-Path $fixture 'fixture-cert.pem'
        $key = Join-Path $fixture 'fixture-key.pem'
        $tlsLog = Join-Path $fixture 'tls.log'
        $opensslArgs = 'req -x509 -newkey rsa:2048 -sha256 -nodes -days 1 ' +
            "-keyout ""$key"" -out ""$cert"" -subj ""/CN=127.0.0.1"" -addext ""subjectAltName=IP:127.0.0.1"""
        $tls = Start-Process -FilePath $OpenSsl -ArgumentList $opensslArgs -RedirectStandardError $tlsLog -WindowStyle Hidden -Wait -PassThru
        if ($tls.ExitCode -ne 0) { throw 'Cannot generate local browser TLS fixture' }
        Set-FixtureEnv 'PR48_TLS_CERT' $cert
        Set-FixtureEnv 'PR48_TLS_KEY' $key
    }
    Write-Output "Verified the fixture process on loopback port $MySqlPort and a dedicated test datadir."
    Push-Location (Join-Path $repo 'backend')
    try {
        $tests = if ($FullRegression) { 'Test*,*Test,*Tests,*TestCase,GoogleLinkBrowserRuntimeIT' } else { 'GoogleLinkBrowserRuntimeIT' }
        & .\mvnw.cmd -B "-Dtest=$tests" test
        $testExit = $LASTEXITCODE
    } finally { Pop-Location }
    if ($testExit -ne 0) { exit $testExit }
} finally {
    if ($processId -ne $null) {
        $running = Get-NetTCPConnection -LocalPort $MySqlPort -State Listen -ErrorAction SilentlyContinue
        if ($running -and $running.OwningProcess -eq $processId) {
            & (Join-Path $MySqlBin 'mysqladmin.exe') --no-defaults --protocol=TCP --host=127.0.0.1 "--port=$MySqlPort" --user=root shutdown
        }
    }
    foreach ($entry in $previous.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
    }
    Write-Output "Local fixture diagnostics: $fixture"
}
