# Project-local GitHub CLI entry point. Authentication stays in Git Credential Manager.
$ErrorActionPreference = 'Stop'
$setupGh = Join-Path $PSScriptRoot 'tools/gh-2.102.0/bin/gh.exe'
if (-not (Test-Path -LiteralPath $setupGh)) { throw 'Portable GitHub CLI not found; use an installed gh instead.' }
$setupOriginalGhToken = $env:GH_TOKEN
$setupOriginalInteractive = $env:GCM_INTERACTIVE
$setupOriginalPrompt = $env:GIT_TERMINAL_PROMPT
$setupCredentialLines = $null
$setupPasswordLine = $null
try {
    & $setupGh auth status --hostname github.com *> $null
    if ($LASTEXITCODE -ne 0) {
        $env:GCM_INTERACTIVE = 'Never'
        $env:GIT_TERMINAL_PROMPT = '0'
        $setupCredentialLines = @('protocol=https','host=github.com','','') |
            git -c credential.interactive=never credential fill 2>$null
        if ($LASTEXITCODE -eq 0) {
            $setupPasswordLine = $setupCredentialLines | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
        }
        if (-not $setupPasswordLine) {
            throw 'No noninteractive GitHub login available. Authenticate GitHub CLI or Git Credential Manager first.'
        }
        $env:GH_TOKEN = $setupPasswordLine.Substring(9)
    }
    & $setupGh @args
    $setupExitCode = $LASTEXITCODE
}
finally {
    $env:GH_TOKEN = $setupOriginalGhToken
    $env:GCM_INTERACTIVE = $setupOriginalInteractive
    $env:GIT_TERMINAL_PROMPT = $setupOriginalPrompt
    $setupCredentialLines = $null
    $setupPasswordLine = $null
}
exit $setupExitCode
