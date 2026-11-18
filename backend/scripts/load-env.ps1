param([string]$EnvFile = (Join-Path $PSScriptRoot '../../.env'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) { throw 'Root .env missing; create it from .env.example.' }
$lineNumber = 0
$settings = @{}
foreach ($line in [IO.File]::ReadAllLines((Resolve-Path -LiteralPath $EnvFile).Path)) {
    $lineNumber++
    $text = $line.Trim()
    if (-not $text -or $text.StartsWith('#')) { continue }
    if ($text -notmatch '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { throw "Invalid .env format at line $lineNumber" }
    $key = $Matches[1]
    $value = $Matches[2].Trim()
    if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
        $value = $value.Substring(1,$value.Length-2)
    }
    $settings[$key] = $value
}
foreach ($key in $settings.Keys) { [Environment]::SetEnvironmentVariable($key,$settings[$key],'Process') }
Write-Host 'Loaded root .env into this process. Secret values are hidden.'

$cloudinaryLocal = Join-Path $PSScriptRoot '../.env.cloudinary.local'
if (Test-Path -LiteralPath $cloudinaryLocal -PathType Leaf) {
    $cloudLineNumber = 0
    foreach ($line in [IO.File]::ReadAllLines((Resolve-Path -LiteralPath $cloudinaryLocal).Path)) {
        $cloudLineNumber++
        $text = $line.Trim()
        if (-not $text -or $text.StartsWith('#')) { continue }
        if ($text -notmatch '^(CLOUDINARY_CLOUD_NAME|CLOUDINARY_API_KEY|CLOUDINARY_API_SECRET)=(.*)$') {
            throw "Invalid Cloudinary setting at line $cloudLineNumber"
        }
        $cloudKey = $Matches[1]
        $cloudValue = $Matches[2].Trim()
        if ($cloudValue.Length -ge 2 -and (($cloudValue.StartsWith('"') -and $cloudValue.EndsWith('"')) -or ($cloudValue.StartsWith("'") -and $cloudValue.EndsWith("'")))) {
            $cloudValue = $cloudValue.Substring(1,$cloudValue.Length-2)
        }
        if ($cloudValue.Length -gt 0) { [Environment]::SetEnvironmentVariable($cloudKey,$cloudValue,'Process') }
    }
    Write-Host 'Loaded backend Cloudinary local settings. Secret values are hidden.'
}

# Shared local-only key for durable advisor checkpoints. Never print the value.
$checkpointLocal = Join-Path $PSScriptRoot '../../.env.chat-checkpoint.local'
if (Test-Path -LiteralPath $checkpointLocal -PathType Leaf) {
    $checkpointLines = @([IO.File]::ReadAllLines((Resolve-Path -LiteralPath $checkpointLocal).Path) | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
    if ($checkpointLines.Count -ne 1 -or $checkpointLines[0] -notmatch '^CHAT_CHECKPOINT_KEY=([A-Za-z0-9_+/-]{43,128}={0,2})$') { throw 'Invalid local checkpoint key file; expected one CHAT_CHECKPOINT_KEY entry.' }
    [Environment]::SetEnvironmentVariable('CHAT_CHECKPOINT_KEY', $Matches[1], 'Process')
    $checkpointLines = $null
    Write-Host 'Loaded shared chat checkpoint key. Secret value is hidden.'
}
