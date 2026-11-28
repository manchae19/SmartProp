# WP04 disposable runtime

Run from an isolated Windows worktree containing the WP04 branch. Use JDK 21, Node 24 with the frontend dependencies, MySQL 8.0 executables, a Python 3.12+ environment with the repository's AI dependencies, and Chromium with Playwright. The launcher expects a local copy of the four V1.3 files pinned by `ai-services/artifacts/v1_3.manifest.json`. It checks byte sizes and SHA-256 before starting services. Supply a local artifact directory with `--artifacts` if it lives outside `ai-services/artifacts/v1_3`.

## Start

Run in PowerShell at the worktree root. Set `$mysqlBin` to the directory containing `mysqld.exe`, `mysql.exe` and `mysqladmin.exe`. Activate the Python environment first.

```powershell
Push-Location backend
.\mvnw.cmd -o -B -DskipTests package
$buildExit = $LASTEXITCODE
Pop-Location
if ($buildExit -ne 0) { throw 'Spring Boot package failed' }
python -X utf8 -B frontend/tests/wp04/browser/tools/fixture_runtime.py --mysql-bin $mysqlBin
```

Leave that terminal running. The launcher binds MySQL, Spring, FastAPI and Vite to loopback on ports 54041–54044 and checks that the unused proxy ports 54045–54046 are free. It initializes a new datadir, checks process ownership and database identity, applies the existing SQL to V23 and seeds only synthetic accounts and listings. The pre-migration identity marker uses a separate schema so the application schema stays empty until Flyway applies V1?V23 with auto-baseline disabled. The temporary marker SELECT grant is revoked before runtime; the normal fixture marker is then created in the application schema. Python 3.12 or newer is required by the pinned XGBoost 3.4.1 package. It creates all credentials at startup. `.smartprop/wp04-fixture/runtime.json` contains listener metadata and paths to the per-run private fixture files. Keep that directory local.

## Browser validation

Use a second PowerShell at the worktree root after the launcher reports ready. Set `CHROME` to a Chromium executable and `PLAYWRIGHT_PATH` to an available Playwright package directory if resolution from the frontend does not find it.

```powershell
$runtimeFile = (Resolve-Path .smartprop/wp04-fixture/runtime.json).Path
$runtime = Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json
if ($runtime.state -ne 'ready') { throw 'Fixture is not ready' }
$accounts = Get-Content -LiteralPath $runtime.credentials_file -Raw | ConvertFrom-Json
$out = Join-Path $runtime.root 'browser-results'
New-Item -ItemType Directory -Path $out -Force | Out-Null

$env:WP04_APP = $runtime.stack.react
$env:WP04_BASE = $runtime.stack.react
$env:WP04_API = $runtime.stack.spring
$env:WP04_AI = $runtime.stack.valuation
$env:WP04_RUNTIME_FILE = $runtimeFile
$env:WP04_FIXTURE_EMAIL = $accounts.accounts.broker
$env:WP04_ADMIN_EMAIL = $accounts.accounts.admin
$env:WP04_BUYER_EMAIL = $accounts.accounts.buyer
$env:WP04_FIXTURE_PASSWORD = $accounts.password
$env:WP04_OUTPUT_DIR = $out
$env:WP04_FAILURE_REPORT = Join-Path $out 'failure-results.json'
$env:WP04_AUTH_REPORT = Join-Path $out 'auth-results.json'

Push-Location frontend
try {
  foreach ($suite in 'reactive-authorization','failure-isolation','runtime-surfaces','surfaces') {
    node "tests/wp04/browser/$suite.mjs"
    if ($LASTEXITCODE -ne 0) { throw "$suite failed" }
  }
} finally {
  Pop-Location
  Remove-Item Env:WP04_FIXTURE_PASSWORD -ErrorAction SilentlyContinue
  Remove-Variable accounts
}
```

The failure runner requests an outage using control files inside the owned run directory. The launcher verifies the FastAPI listener before stopping it and checks that a different owned PID serves the recovered endpoint. The component runner reads the same run's failure report. A new launcher run provides a fresh outage control pair. Repeated login attempts against the same run are subject to the application's normal rate limit.

## Isolated MySQL integration

While the same fixture runs, use its restricted database account for `AdvisorPartialResultLiveIT`. The existing `ComparableSyntheticMysqlIT` creates its own tables in the empty `wp02_phase_b_fixture` schema and requires the owned port and server UUID. Run this once per fixture. The Advisor test expects loopback port 18099 to be unused.

```powershell
$r = Get-Content .smartprop/wp04-fixture/runtime.json -Raw | ConvertFrom-Json
$run = (Resolve-Path $r.root).Path
$fixtureRoot = (Resolve-Path .smartprop/wp04-fixture).Path
if ($r.state -notin 'ready','valuation-recovered' -or
    (Split-Path -Parent $run) -ne $fixtureRoot -or $r.ports.mysql -ne 54041 -or
    (Split-Path -Parent (Resolve-Path $r.db_file).Path) -ne $run) { throw 'Wrong fixture' }
$d = Get-Content -LiteralPath $r.db_file -Raw | ConvertFrom-Json
if ($d.port -ne 54041 -or $d.user -ne 'wp04_fixture' -or $d.schema -ne 'wp04_final_fixture' -or
    $d.uuid -ne $r.pids.mysql.uuid) { throw 'Wrong fixture database configuration' }
if (netstat.exe -ano -p TCP | Select-String ':18099\s+.*LISTENING') { throw 'Offline test port occupied' }
try {
  $env:MYSQL_PWD = $d.password
  $sql = 'SELECT @@server_uuid,@@port,DATABASE(),CURRENT_USER(),@@datadir,(SELECT marker FROM wp04_isolation_marker);'
  $line = & $d.mysql --no-defaults --protocol=TCP --host=127.0.0.1 --port=54041 --user=wp04_fixture --database=wp04_final_fixture -NB -e $sql
  if ($LASTEXITCODE -ne 0) { throw 'Fixture SQL check failed' }
} finally { Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue }
$uuid,$dbPort,$schema,$account,$dir,$marker = $line -split "\t"
if ($uuid -ne $d.uuid -or $dbPort -ne '54041' -or $schema -ne $d.schema -or
    $account -ne 'wp04_fixture@127.0.0.1' -or
    [IO.Path]::GetFullPath($dir).TrimEnd('\') -ne [IO.Path]::GetFullPath($d.datadir).TrimEnd('\') -or
    $marker -ne $d.marker) { throw 'Fixture SQL identity changed' }

$env:DB_URL = 'jdbc:mysql://127.0.0.1:54041/wp04_final_fixture?connectionTimeZone=UTC&allowPublicKeyRetrieval=true&useSSL=false'
$env:DB_USER = $d.user
$env:DB_PASSWORD = $d.password
$env:SPRING_PROFILES_ACTIVE = 'standard-migrations'
$env:SPRING_FLYWAY_ENABLED = 'false'
$env:WP02_FIXTURE_UUID = $d.uuid
$env:WP02_FIXTURE_PORT = '54041'
$env:JWT_SECRET = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
Push-Location backend
try {
  .\mvnw.cmd -o -B '-Dtest=AdvisorPartialResultLiveIT,ComparableSyntheticMysqlIT' test
  if ($LASTEXITCODE -ne 0) { throw 'MySQL integration suite failed' }
} finally {
  Pop-Location
  Remove-Item Env:DB_PASSWORD,Env:JWT_SECRET -ErrorAction SilentlyContinue
  Remove-Variable d, line
}
```

Use a fixture-only PowerShell session so the test environment variables do not carry over to other work.

## Stop

At the worktree root in the second shell, use the manifest from the run you started.

```powershell
$r = Get-Content .smartprop/wp04-fixture/runtime.json -Raw | ConvertFrom-Json
if ($r.state -notin 'ready','valuation-recovered' -or
    (Split-Path -Parent $r.stop_file) -ne $r.root -or
    (Split-Path -Leaf $r.stop_file) -ne 'STOP') { throw 'Unexpected fixture stop target' }
New-Item -ItemType File -Path $r.stop_file | Out-Null
```

Wait for the launcher to exit successfully and the manifest to report `stopped`. The run directory retains private diagnostics for local use. The release evidence is published separately in [final acceptance](../../../../../docs/ai/wp04-evidence/README.md).
