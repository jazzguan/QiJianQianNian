param([switch]$Lan)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'dist/index.html')) {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
}
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
$listenAddress = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
if (Get-Command conda -ErrorAction SilentlyContinue) {
    & conda run --no-capture-output -n qjqn-gpu python -m uvicorn app.main:app --host $listenAddress --port 8000
} elseif (Test-Path -LiteralPath '.venv/Scripts/python.exe') {
    & .venv/Scripts/python.exe -m uvicorn app.main:app --host $listenAddress --port 8000
} else {
    throw '未找到 qjqn-gpu Conda 环境或 backend/.venv'
}
