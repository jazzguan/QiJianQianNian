$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'android-env.ps1')

$gradle = Join-Path $env:GRADLE_HOME 'bin\gradle.bat'
if (-not (Test-Path -LiteralPath $gradle)) {
    $gradle = Join-Path $projectRoot 'android\gradlew.bat'
}

& $gradle -p (Join-Path $projectRoot 'android') assembleDebug --no-daemon
if ($LASTEXITCODE -ne 0) { throw 'Android APK build failed' }

$apk = Join-Path $projectRoot 'android\app\build\outputs\apk\debug\app-debug.apk'
if (-not (Test-Path -LiteralPath $apk)) { throw 'APK output was not created' }
Write-Host "APK: $apk"

