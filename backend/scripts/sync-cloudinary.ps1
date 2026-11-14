param(
    [Parameter(Mandatory=$true)][ValidatePattern('^SP[0-9]{3,}$')][string]$ListingCode,
    [switch]$Apply,
    [long]$OperatorId,
    [int]$ExpectedVersion,
    [string]$Output,
    [string]$Jar
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'load-env.ps1')
$backend=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if(-not $Jar){$Jar=Join-Path $backend 'target/smartprop-backend-0.1.0.jar'}
if(-not (Test-Path -LiteralPath $Jar -PathType Leaf)){throw 'Build the Backend JAR first.'}
if($Apply -and ($OperatorId -lt 1 -or $ExpectedVersion -lt 1)){throw 'Apply requires OperatorId and ExpectedVersion.'}
$java=if($env:JAVA_HOME){Join-Path $env:JAVA_HOME 'bin/java.exe'}else{(Get-Command java -ErrorAction Stop).Source}
$commandArgs=@('-Dloader.main=vn.smartprop.modules.media.CloudinarySyncCommand','-cp',$Jar,'org.springframework.boot.loader.launch.PropertiesLauncher',"--listing-code=$ListingCode")
if($Apply){$commandArgs+=@('--apply',"--operator-id=$OperatorId","--expected-version=$ExpectedVersion")}
if($Output){$commandArgs+="--output=$([IO.Path]::GetFullPath($Output))"}
& $java @commandArgs
if($LASTEXITCODE -ne 0){throw 'Cloudinary command failed. No credentials were printed.'}
