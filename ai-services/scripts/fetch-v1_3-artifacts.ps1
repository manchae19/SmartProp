# Fetch and verify the pinned XGBoost V1.3 inference artifacts.
#
# The model weights (~28 MB) are NOT committed. Teammates run this once so a
# fresh clone can start the AI service with V1.3 active; without it the service
# still starts and V1.3 reports "degraded" while V6 keeps serving.
#
# Usage:
#   ./scripts/fetch-v1_3-artifacts.ps1 -BaseUrl "https://<release-or-object-store>/v1_3"
#   ($BaseUrl defaults to $env:V1_3_ARTIFACT_BASE_URL)
param(
  [string]$BaseUrl = $env:V1_3_ARTIFACT_BASE_URL,
  [string]$Dest = (Join-Path $PSScriptRoot '..\artifacts\v1_3')
)
$ErrorActionPreference = 'Stop'
if (-not $BaseUrl) { throw 'Provide -BaseUrl or set V1_3_ARTIFACT_BASE_URL (see ai-services/V1_3_ARTIFACTS.md).' }

$manifestPath = Join-Path $PSScriptRoot '..\artifacts\v1_3.manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

foreach ($file in $manifest.files) {
  $target = Join-Path $Dest $file.name
  $url = ($BaseUrl.TrimEnd('/')) + '/' + $file.name
  Write-Host "Downloading $($file.name) ..."
  Invoke-WebRequest -Uri $url -OutFile $target -UseBasicParsing
  $actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower()
  if ($actual -ne $file.sha256) {
    Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
    throw "SHA-256 mismatch for $($file.name): expected $($file.sha256), got $actual"
  }
  Write-Host "  ok ($($file.bytes) bytes, sha256 verified)"
}
Write-Host "V1.3 artifacts verified in $Dest"
