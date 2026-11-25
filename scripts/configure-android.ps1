param([string]$BackendIp)
$ErrorActionPreference = 'Stop'

if (-not $BackendIp) {
    $route = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
        Where-Object { $_.NextHop -ne '0.0.0.0' } |
        Sort-Object RouteMetric |
        Select-Object -First 1
    if ($route) {
        $BackendIp = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notlike '169.254.*' } |
            Select-Object -ExpandProperty IPAddress -First 1
    }
}

if (-not $BackendIp) {
    $ipconfigText = (ipconfig | Out-String)
    $matches = [regex]::Matches($ipconfigText, 'IPv4[^:]*:\s*(\d{1,3}(?:\.\d{1,3}){3})')
    $BackendIp = $matches |
        ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -notlike '127.*' -and $_ -notlike '169.254.*' } |
        Select-Object -First 1
}

if (-not $BackendIp -or $BackendIp -notmatch '^\d{1,3}(\.\d{1,3}){3}$') {
    throw 'Could not detect a LAN IPv4. Run: npm run android:configure -- 192.168.x.x'
}

$target = Join-Path (Split-Path $PSScriptRoot -Parent) '.env.android'
$content = "VITE_BACKEND_ORIGIN=http://${BackendIp}:8000`n"
[System.IO.File]::WriteAllText($target, $content, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Android backend: http://${BackendIp}:8000"
