$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'dist/index.html')) {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
}
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
& .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
