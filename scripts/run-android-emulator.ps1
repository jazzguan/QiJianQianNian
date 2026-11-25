param(
    [switch]$Build
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$androidRoot = 'D:\SoftWare\Android'
$sdkRoot = Join-Path $androidRoot 'Sdk'
$userRoot = Join-Path $androidRoot 'UserHome'
$avdName = 'Qijian_Pixel_7_API_36'
$emulator = Join-Path $sdkRoot 'emulator\emulator.exe'
$adb = Join-Path $sdkRoot 'platform-tools\adb.exe'
$apk = Join-Path $projectRoot 'android\app\build\outputs\apk\debug\app-debug.apk'

$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$env:ANDROID_USER_HOME = $userRoot
$env:ANDROID_AVD_HOME = Join-Path $userRoot 'avd'

if ($Build) {
    Push-Location $projectRoot
    try {
        npm run android:apk
        if ($LASTEXITCODE -ne 0) { throw 'APK build failed.' }
    }
    finally {
        Pop-Location
    }
}

foreach ($required in @($emulator, $adb)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Missing Android component: $required"
    }
}

function Get-EmulatorSerial {
    $line = & $adb devices |
        Where-Object { $_ -match '^(emulator-\d+)\s+device$' } |
        Select-Object -First 1
    if ($line -and $line -match '^(emulator-\d+)') { return $Matches[1] }
    return $null
}

$serial = Get-EmulatorSerial
if (-not $serial) {
    Write-Host 'Starting Pixel 7 emulator...'
    Start-Process -FilePath $emulator -ArgumentList @(
        '-avd', $avdName,
        '-gpu', 'auto',
        '-no-boot-anim',
        '-netdelay', 'none',
        '-netspeed', 'full'
    )
    for ($attempt = 0; $attempt -lt 90 -and -not $serial; $attempt++) {
        Start-Sleep -Seconds 2
        $serial = Get-EmulatorSerial
    }
}

if (-not $serial) { throw 'Emulator startup timed out.' }

Write-Host 'Waiting for Android to finish booting...'
for ($attempt = 0; $attempt -lt 120; $attempt++) {
    $booted = (& $adb -s $serial shell getprop sys.boot_completed).Trim()
    if ($booted -eq '1') { break }
    Start-Sleep -Seconds 2
}
if ($booted -ne '1') { throw 'Android boot timed out.' }

if (-not (Test-Path -LiteralPath $apk)) {
    throw 'APK not found. Run npm run android:apk first.'
}

Write-Host 'Installing and opening QiJianQianNian...'
& $adb -s $serial install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
& $adb -s $serial shell am force-stop cn.qijianqiannian.app
& $adb -s $serial shell am start -n 'cn.qijianqiannian.app/.MainActivity'
if ($LASTEXITCODE -ne 0) { throw 'App launch failed.' }

Write-Host 'Done: QiJianQianNian is open in the emulator.'
