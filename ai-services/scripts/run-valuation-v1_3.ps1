# Chạy dịch vụ định giá SmartProp với V1.3.
#
# V1.3 là model chính: dịch vụ khởi động, trả options và dự đoán chỉ với bộ
# artifacts V1.3. V6 là tùy chọn và chỉ nạp khi artifacts của nó có mặt.
#
#   ./scripts/run-valuation-v1_3.ps1              # cổng 8000
#   ./scripts/run-valuation-v1_3.ps1 -Port 8010   # cổng khác
param([ValidateRange(1024, 65535)][int]$Port = 8000)
$ErrorActionPreference = 'Stop'

$service = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$artifacts = Join-Path $service 'artifacts/v1_3'
$python = Join-Path $service '.venv/Scripts/python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw 'Chưa có .venv. Tạo bằng: python -m venv .venv; .venv\Scripts\pip install -r requirements.txt'
}

# Xác minh artifacts theo manifest trước khi chạy, đúng như V1_3_ARTIFACTS.md.
$manifestPath = Join-Path $service 'artifacts/v1_3.manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Thiếu manifest: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($file in $manifest.files) {
    $path = Join-Path $artifacts $file.name
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Thiếu artifact $($file.name). Chạy ./scripts/fetch-v1_3-artifacts.ps1 -BaseUrl <host> trước."
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $file.sha256) { throw "SHA-256 không khớp cho $($file.name)" }
}

$env:SMARTPROP_V1_3_REAL_FEATURES = 'true'
$env:SMARTPROP_V1_3_MODEL_DIR = $artifacts

Write-Output "V1.3 artifacts đã xác minh. Khởi động trên cổng $Port."
& $python -X utf8 -m uvicorn main:app --host 127.0.0.1 --port $Port
if ($LASTEXITCODE -ne 0) { throw 'Dịch vụ định giá dừng với lỗi' }
