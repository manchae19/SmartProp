param([Parameter(ValueFromRemainingArguments=$true)][string[]]$MavenArguments)
$ErrorActionPreference='Stop'
$backendPath=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$properties=Get-Content -LiteralPath (Join-Path $backendPath '.mvn/wrapper/maven-wrapper.properties') -Raw | ConvertFrom-StringData
if($properties.distributionUrl -notmatch '/apache-maven/([0-9.]+)/apache-maven-\1-bin.zip$') { throw 'Unsupported Maven distribution; use Maven Wrapper.' }
$version=$Matches[1]
$runtimeConfigPath=Join-Path $backendPath '../.scratch/devtools/runtime.json'
$runtimeConfig=if(Test-Path -LiteralPath $runtimeConfigPath){Get-Content -Raw -LiteralPath $runtimeConfigPath|ConvertFrom-Json}else{$null}
$cacheRoot=Join-Path ([Environment]::GetFolderPath('UserProfile')) ".m2/wrapper/dists/apache-maven-$version"
$mavenHome=Get-ChildItem -LiteralPath $cacheRoot -Directory -ErrorAction SilentlyContinue | Where-Object {Test-Path -LiteralPath (Join-Path $_.FullName 'bin/m2.conf')} | Select-Object -First 1 -ExpandProperty FullName
if(-not $mavenHome -and $env:MAVEN_HOME){$mavenHome=$env:MAVEN_HOME}
if(-not $mavenHome -and $runtimeConfig){$mavenHome=$runtimeConfig.maven}
if(-not $mavenHome) { throw 'Maven distribution is not cached. Run .\mvnw.cmd --version to download the pinned distribution first.' }
$launcher=Get-ChildItem -LiteralPath (Join-Path $mavenHome 'boot') -Filter 'plexus-classworlds-*.jar' | Select-Object -First 1 -ExpandProperty FullName
$java=if($env:JAVA_HOME){Join-Path $env:JAVA_HOME 'bin/java.exe'}elseif($runtimeConfig){Join-Path $runtimeConfig.jdk 'bin/java.exe'}else{(Get-Command java -ErrorAction Stop).Source}
if(-not (Test-Path -LiteralPath $java)) { throw 'Java executable not found; configure JAVA_HOME for JDK21.' }
Push-Location -LiteralPath $backendPath
try {
    $localRepository=[IO.Path]::GetFullPath((Join-Path $backendPath '../.scratch/m2'))
    & $java "-Dmaven.home=$mavenHome" "-Dclassworlds.conf=$mavenHome/bin/m2.conf" "-Dmaven.multiModuleProjectDirectory=$backendPath" "-Dmaven.repo.local=$localRepository" -classpath $launcher org.codehaus.plexus.classworlds.launcher.Launcher @MavenArguments
    if($LASTEXITCODE -ne 0) { throw "Maven failed with exit code $LASTEXITCODE" }
} finally { Pop-Location }
