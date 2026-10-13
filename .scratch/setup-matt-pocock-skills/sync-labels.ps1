$ErrorActionPreference = 'Stop'
$setupRepo = 'manchae19/SmartProp'
$setupGh = Join-Path $PSScriptRoot 'tools/gh-2.102.0/bin/gh.exe'
if (-not (Test-Path -LiteralPath $setupGh)) { throw 'Portable GitHub CLI not found.' }
$setupLabels = @(
    @{ name='needs-triage'; color='FBCA04'; description='Can nguoi phu trach danh gia issue' },
    @{ name='needs-info'; color='D876E3'; description='Dang cho bo sung thong tin' },
    @{ name='ready-for-agent'; color='0E8A16'; description='Yeu cau da ro, agent co the trien khai' },
    @{ name='ready-for-human'; color='1D76DB'; description='Can nguoi truc tiep xu ly' },
    @{ name='wontfix'; color='FFFFFF'; description='Da quyet dinh khong thuc hien' }
)
$setupOriginalGhToken = $env:GH_TOKEN
$setupOriginalInteractive = $env:GCM_INTERACTIVE
$setupOriginalPrompt = $env:GIT_TERMINAL_PROMPT
$setupCredentialLines = $null
$setupTemporaryToken = $null
try {
    & $setupGh auth status --hostname github.com *> $null
    if ($LASTEXITCODE -ne 0) {
        $env:GCM_INTERACTIVE = 'Never'
        $env:GIT_TERMINAL_PROMPT = '0'
        # Reuse Git's existing GitHub login for this operation. Keep the token in memory only.
        $setupCredentialLines = @('protocol=https','host=github.com','','') |
            git -c credential.interactive=never credential fill 2>$null
        if ($LASTEXITCODE -eq 0) {
            $setupPasswordLine = $setupCredentialLines | Where-Object { $_ -like 'password=*' } | Select-Object -First 1
            if ($setupPasswordLine) { $setupTemporaryToken = $setupPasswordLine.Substring(9) }
        }
        if (-not $setupTemporaryToken) {
            throw 'GitHub CLI needs authentication; no existing noninteractive Git credential is available.'
        }
        $env:GH_TOKEN = $setupTemporaryToken
    }
    $setupBeforeJson = & $setupGh label list --repo $setupRepo --limit 1000 --json name,color,description
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read repository labels.' }
    $setupBefore = $setupBeforeJson | ConvertFrom-Json
    $setupKnown = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($setupItem in $setupBefore) { [void]$setupKnown.Add($setupItem.name) }
    $setupCreated = @()
    foreach ($setupLabel in $setupLabels) {
        if ($setupKnown.Contains($setupLabel.name)) {
            Write-Output "Already present: $($setupLabel.name)"
            continue
        }
        & $setupGh label create $setupLabel.name --repo $setupRepo --color $setupLabel.color --description $setupLabel.description
        if ($LASTEXITCODE -ne 0) { throw "Failed creating label: $($setupLabel.name)" }
        $setupCreated += $setupLabel.name
        Write-Output "Created: $($setupLabel.name)"
    }
    $setupAfterJson = & $setupGh label list --repo $setupRepo --limit 1000 --json name,color,description
    if ($LASTEXITCODE -ne 0) { throw 'Cannot verify repository labels.' }
    $setupAfter = $setupAfterJson | ConvertFrom-Json
    $setupNames = @($setupAfter | ForEach-Object { $_.name })
    foreach ($setupLabel in $setupLabels) {
        if ($setupNames -notcontains $setupLabel.name) { throw "Missing label: $($setupLabel.name)" }
    }
    $setupReport = [ordered]@{
        verified = $true
        repository = $setupRepo
        checked_at_utc = [DateTime]::UtcNow.ToString('o')
        required_labels = @($setupLabels | ForEach-Object { $_.name })
        created_labels = $setupCreated
        existing_labels_preserved = $true
    }
    $setupReport | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'labels-verification.json') -Encoding UTF8
    Write-Output 'PASS: all five triage labels verified on GitHub.'
}
finally {
    $env:GH_TOKEN = $setupOriginalGhToken
    $env:GCM_INTERACTIVE = $setupOriginalInteractive
    $env:GIT_TERMINAL_PROMPT = $setupOriginalPrompt
    $setupCredentialLines = $null
    $setupPasswordLine = $null
    $setupTemporaryToken = $null
}
