param(
    [Parameter(Mandatory=$true)][string]$ClientJson,
    [string]$FrontendOrigin='http://127.0.0.1:5173',
    [switch]$Enable,
    [switch]$RedirectVerifiedInConsole
)
$ErrorActionPreference='Stop'
if(-not(Test-Path -LiteralPath $ClientJson -PathType Leaf)){throw 'OAuth JSON file not found. Keep this file outside the repository.'}
$oauth=Get-Content -LiteralPath $ClientJson -Raw -Encoding UTF8 | ConvertFrom-Json
if(-not $oauth.web){throw 'Google OAuth client must be a Web application, not a desktop/installed client.'}
$web=$oauth.web
if(-not $web.client_id -or -not $web.client_id.EndsWith('.apps.googleusercontent.com') -or -not $web.client_secret){throw 'OAuth Client ID or Client Secret is missing.'}
if($web.auth_uri -notin @('https://accounts.google.com/o/oauth2/auth','https://accounts.google.com/o/oauth2/v2/auth') -or $web.token_uri -ne 'https://oauth2.googleapis.com/token'){throw 'Unexpected OAuth provider endpoints.'}
$origin=$null
if(-not [Uri]::TryCreate($FrontendOrigin,[UriKind]::Absolute,[ref]$origin) -or $origin.UserInfo -or $origin.Query -or $origin.Fragment -or $origin.AbsolutePath -ne '/' -or $FrontendOrigin.EndsWith('/')){throw 'FrontendOrigin must be an origin without a path, query, user info or trailing slash.'}
$loopback=$origin.Scheme -eq 'http' -and $origin.Host -in @('127.0.0.1','localhost')
if(-not($loopback -or $origin.Scheme -eq 'https')){throw 'Google login requires HTTPS or a loopback development origin.'}
$redirect=$FrontendOrigin+'/api/v1/auth/oauth2/callback/google'
if(@($web.redirect_uris) -notcontains $redirect -and -not $RedirectVerifiedInConsole){throw 'Callback URI is not listed in this JSON. Add it in Google Cloud, download updated JSON or explicitly confirm RedirectVerifiedInConsole after saving the Console change.'}
if($Enable -and $env:REFRESH_ENABLED -ne 'true'){throw 'Persistent sessions must be configured before enabling Google login.'}
$allowed=@($env:CORS_ORIGINS -split ',' | ForEach-Object { $_.Trim() })
if($Enable -and $allowed -notcontains $FrontendOrigin){throw 'FrontendOrigin is not in the existing CORS_ORIGINS configuration.'}
if($Enable -and (($loopback -and $env:REFRESH_SECURE_COOKIE -ne 'false') -or (-not $loopback -and $env:REFRESH_SECURE_COOKIE -ne 'true'))){throw 'Refresh cookie Secure setting does not match the frontend origin.'}
# Credentials are passed only through the current process environment, never command-line arguments or output.
$env:GOOGLE_CLIENT_ID=[string]$web.client_id
$env:GOOGLE_CLIENT_SECRET=[string]$web.client_secret
$env:GOOGLE_FRONTEND_ORIGIN=$FrontendOrigin
$env:GOOGLE_REDIRECT_URI=$redirect
$env:GOOGLE_LOGIN_ENABLED=if($Enable){'true'}else{'false'}
$oauth=$null;$web=$null
Write-Output ('Google OAuth settings loaded; secrets hidden. Frontend: '+$FrontendOrigin)
Write-Output ('Callback: '+$redirect)
Write-Output 'No database migration or role change was performed. Backend readiness still requires the approved schema.'
