$projectRoot = Split-Path $PSScriptRoot -Parent

$javaHome = if ($env:JAVA_HOME -and (Test-Path -LiteralPath (Join-Path $env:JAVA_HOME 'bin\java.exe'))) {
    $env:JAVA_HOME
} else {
    'D:\SoftWare\Android\jdk-21.0.13+9'
}
$sdkRoot = if ($env:ANDROID_HOME -and (Test-Path -LiteralPath $env:ANDROID_HOME)) {
    $env:ANDROID_HOME
} else {
    'D:\SoftWare\Android\Sdk'
}
$gradleHome = if ($env:GRADLE_HOME -and (Test-Path -LiteralPath $env:GRADLE_HOME)) {
    $env:GRADLE_HOME
} else {
    'D:\SoftWare\Android\gradle-8.14.3'
}

if (-not (Test-Path -LiteralPath (Join-Path $javaHome 'bin\java.exe'))) {
    throw "JDK 21 not found: $javaHome"
}
if (-not (Test-Path -LiteralPath (Join-Path $sdkRoot 'platforms\android-36\android.jar'))) {
    throw "Android SDK 36 not found: $sdkRoot"
}

$env:JAVA_HOME = $javaHome
$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$env:GRADLE_HOME = $gradleHome
$env:GRADLE_USER_HOME = 'D:\SoftWare\Android\GradleCache'

