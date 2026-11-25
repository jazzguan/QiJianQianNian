$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'android-env.ps1')

$studio = if ($env:CAPACITOR_ANDROID_STUDIO_PATH -and (Test-Path -LiteralPath $env:CAPACITOR_ANDROID_STUDIO_PATH)) {
    $env:CAPACITOR_ANDROID_STUDIO_PATH
} else {
    'D:\SoftWare\android-studio\bin\studio64.exe'
}
if (-not (Test-Path -LiteralPath $studio)) { throw "Android Studio not found: $studio" }

Start-Process -FilePath $studio -ArgumentList (Join-Path $projectRoot 'android')

