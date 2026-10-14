$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$comparisonPython = Join-Path $projectRoot 'backend/.venv-morphology/Scripts/python.exe'
if (!(Test-Path -LiteralPath $comparisonPython)) {
    python -m venv backend/.venv-morphology
    if ($LASTEXITCODE -ne 0) { throw '无法创建 Python 环境' }
    & $comparisonPython -m pip install -r backend/requirements-morphology.txt
    if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败' }
}
if (!(Test-Path -LiteralPath 'node_modules')) {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' }
}
npm run build
if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
Write-Host '形态对比：http://127.0.0.1:8001/comparison'
$running = $null
try { $running = Invoke-RestMethod -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 2 } catch {}
if ($running) {
    if ($running.module -eq 'morphology') { return }
    throw '8001端口已被其他服务占用'
}
& $comparisonPython -m uvicorn app.morphology_app:app --app-dir backend --host 127.0.0.1 --port 8001
