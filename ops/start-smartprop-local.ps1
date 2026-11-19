param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$EnvFile = '',
    [string]$PythonExe = '',
    [ValidateSet('dev','standard-migrations','hybrid-local-existing-v13')][string]$BackendProfile = 'standard-migrations',
    [string]$ImagecheckPythonExe = '',
    [string]$RunDirectory = $(Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')).Path '.local-run')
)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path $Root).Path
if (-not $EnvFile) { $EnvFile = Join-Path $Root '.env' }
if (-not $PythonExe) { $PythonExe = if($env:SMARTPROP_PYTHON){$env:SMARTPROP_PYTHON}else{Join-Path $Root '.scratch/rag-venv/Scripts/python.exe'} }
if (-not $ImagecheckPythonExe) {
    $candidate = Join-Path (Split-Path $PythonExe) 'pythonw.exe'
    if (Test-Path -LiteralPath $candidate) { $ImagecheckPythonExe = $candidate }
    else { $ImagecheckPythonExe = $PythonExe }
}
New-Item -ItemType Directory -Force -Path $RunDirectory | Out-Null

function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}
function Test-Url([string]$Url) {
    try { $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 3; return ($response.StatusCode -eq 200) }
    catch { return $false }
}
function Wait-Url([string]$Url, [int]$Seconds = 40) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) { return $true }
        Start-Sleep -Milliseconds 750
    }
    return $false
}
function Set-EnvFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Missing environment file: $Path" }
    Get-Content -LiteralPath $Path | ForEach-Object {
        if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            Set-Item -Path ("Env:" + $matches[1]) -Value ($matches[2].Trim().Trim('"').Trim("'"))
        }
    }
}

if (-not (Test-Port 3306)) { throw 'MySQL 3306 is not listening; start MySQL before SmartProp.' }

# RAG Chat is an existing required service; do not start a second copy here.
if (-not (Test-Url 'http://127.0.0.1:8001/chat/health')) {
    throw 'RAG Chat 8001 is not ready. Start the existing RAG Chat service first.'
}

# Imagecheck: never start a second copy on 18001.
if (Test-Url 'http://127.0.0.1:18001/image-duplicates/health') {
    Write-Output 'Imagecheck 18001: already healthy'
} elseif (Test-Port 18001) {
    throw 'Port 18001 is occupied but imagecheck health is not configured; refusing to start a duplicate.'
} else {
    if (-not (Test-Path -LiteralPath $ImagecheckPythonExe)) { throw "Python executable not found: $ImagecheckPythonExe" }
    # Image metadata comes from the public Backend API, not a database credential.
    $env:RAG_SQL_ENABLED = 'false'
    $env:RAG_BACKEND_URL = 'http://127.0.0.1:8080'
    $env:RAG_IMAGE_BACKEND_URL = 'http://127.0.0.1:8080'
    $imageLog = Join-Path $RunDirectory 'imagecheck-18001.log'
    $imageErr = Join-Path $RunDirectory 'imagecheck-18001.err.log'
    $process = Start-Process -FilePath $ImagecheckPythonExe -ArgumentList @('-m','uvicorn','imagecheck_main:app','--host','127.0.0.1','--port','18001','--no-proxy-headers') -WorkingDirectory (Join-Path $Root 'ai-services') -RedirectStandardOutput $imageLog -RedirectStandardError $imageErr -PassThru -WindowStyle Hidden
    $process.Id | Set-Content (Join-Path $RunDirectory 'imagecheck.pid')
    if (-not (Wait-Url 'http://127.0.0.1:18001/image-duplicates/health' 25)) {
        throw "Imagecheck 18001 failed health check. See $imageErr"
    }
    Write-Output 'Imagecheck 18001: started'
}

# Vision (YOLOv8 object analysis): optional, never blocks the stack.
# It runs in its own virtualenv because ultralytics pulls torchvision/opencv and
# monkeypatches PIL.Image.open; sharing the RAG venv would put duplicate scanning
# at risk. A missing venv or weights is reported, not fatal.
if (Test-Url 'http://127.0.0.1:18002/image-analysis/health') {
    Write-Output 'Vision 18002: already healthy'
} elseif (Test-Port 18002) {
    Write-Output 'Vision 18002: port occupied but health is not ready; leaving it alone'
} else {
    $visionPython = if ($env:SMARTPROP_VISION_PYTHON) { $env:SMARTPROP_VISION_PYTHON } else { Join-Path $Root '.scratch\yolov8-venv\Scripts\python.exe' }
    $visionWeights = Join-Path $Root 'ai-services\var\vision\yolov8n.pt'
    if (-not (Test-Path -LiteralPath $visionPython)) {
        Write-Output "Vision 18002: skipped (no virtualenv at $visionPython)"
    } elseif (-not (Test-Path -LiteralPath $visionWeights)) {
        Write-Output "Vision 18002: skipped (no weights at $visionWeights)"
    } else {
        $env:VISION_MODEL_DIR = Join-Path $Root 'ai-services\var\vision'
        $env:YOLO_CONFIG_DIR = Join-Path $Root '.scratch\yolov8-config'
        $visionLog = Join-Path $RunDirectory 'vision-18002.log'
        $visionErr = Join-Path $RunDirectory 'vision-18002.err.log'
        $process = Start-Process -FilePath $visionPython -ArgumentList @('-m','uvicorn','vision_main:app','--host','127.0.0.1','--port','18002','--no-proxy-headers') -WorkingDirectory (Join-Path $Root 'ai-services') -RedirectStandardOutput $visionLog -RedirectStandardError $visionErr -PassThru -WindowStyle Hidden
        $process.Id | Set-Content (Join-Path $RunDirectory 'vision.pid')
        if (-not (Wait-Url 'http://127.0.0.1:18002/image-analysis/health' 40)) {
            Write-Output "Vision 18002: started but health check failed; see $visionErr"
        } else {
            Write-Output 'Vision 18002: started'
        }
    }
}

if (Test-Url 'http://127.0.0.1:8080/actuator/health') {
    Write-Output 'Backend 8080: already healthy'
} elseif (Test-Port 8080) {
    throw 'Port 8080 is occupied but Backend health is not UP; refusing to start a duplicate.'
} else {
    $jar = Join-Path $Root 'backend\target\smartprop-backend-0.1.0.jar'
    if (-not (Test-Path -LiteralPath $jar)) { throw "Backend jar not found: $jar (run mvnw -DskipTests package first)" }
    Set-EnvFile $EnvFile
    $env:SPRING_PROFILES_ACTIVE = $BackendProfile
    $env:SMARTPROP_V1_3_MODEL_DIR = Join-Path $Root 'ai-services/artifacts/v1_3'
    $env:APP_IMAGE_SCAN_BASE_URL = 'http://127.0.0.1:18001'
    $env:PORT = '8080'
    $backendLog = Join-Path $RunDirectory 'backend-8080.log'
    $backendErr = Join-Path $RunDirectory 'backend-8080.err.log'
    $process = Start-Process -FilePath 'java' -ArgumentList @('-jar', $jar) -WorkingDirectory (Join-Path $Root 'backend') -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden
    $process.Id | Set-Content (Join-Path $RunDirectory 'backend.pid')
    if (-not (Wait-Url 'http://127.0.0.1:8080/actuator/health' 50)) {
        throw "Backend 8080 failed health check. See $backendErr"
    }
    Write-Output 'Backend 8080: started'
}

if (Test-Url 'http://127.0.0.1:5173/') {
    Write-Output 'Frontend 5173: already available'
} elseif (Test-Port 5173) {
    throw 'Port 5173 is occupied but frontend health is not available.'
} else {
    $frontendLog = Join-Path $RunDirectory 'frontend-5173.log'
    $frontendErr = Join-Path $RunDirectory 'frontend-5173.err.log'
    $process = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c','npm run dev -- --port 5173 --strictPort') -WorkingDirectory (Join-Path $Root 'frontend') -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr -PassThru -WindowStyle Hidden
    $process.Id | Set-Content (Join-Path $RunDirectory 'frontend.pid')
    if (-not (Wait-Url 'http://127.0.0.1:5173/' 35)) {
        throw "Frontend 5173 failed health check. See $frontendErr"
    }
    Write-Output 'Frontend 5173: started'
}

Write-Output 'SmartProp local services: MySQL 3306, RAG 8001, Imagecheck 18001, Backend 8080, Frontend 5173 are healthy.'
Write-Output 'Vision 18002 is optional; object analysis stays disabled unless APP_IMAGE_ANALYSIS_ENABLED=true.'
