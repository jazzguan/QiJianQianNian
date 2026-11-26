<#
用途：把三维重建需要的代码和权重一次装齐，省掉每台新机器重复踩网络坑。
用法：
    .\scripts\fetch_weights.ps1                     # 全装，直连 Hugging Face
    .\scripts\fetch_weights.ps1 -SkipHunyuan        # 只装 TripoSR + Meshroom
    .\scripts\fetch_weights.ps1 -Mirror "https://hf-mirror.com"   # 走国内镜像

装完的东西：
    backend/TripoSR/                         TripoSR 源码（setup_triposr.py 负责）
    backend/cache/huggingface/               TripoSR 权重，约 1.6GB
    backend/cache/hf_cache/                  Hunyuan3D-2mini 权重，约 3.6GB
    backend/cache/Meshroom-2023.3.0/         Meshroom 便携版，约 2.6GB（zip 1.4GB）
#>
param(
    [switch]$SkipTripoSR,
    [switch]$SkipHunyuan,
    [switch]$SkipMeshroom,
    [string]$Mirror = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$cache = Join-Path $root 'backend\cache'
New-Item -ItemType Directory -Force -Path $cache | Out-Null

$venv = Join-Path $root 'backend\.venv\Scripts\python.exe'
function Invoke-Py {
    param([string[]]$Arguments)
    if (Test-Path -LiteralPath $venv) {
        & $venv @Arguments
    } elseif (Get-Command conda -ErrorAction SilentlyContinue) {
        & conda run --no-capture-output -n qjqn-gpu python @Arguments
    } else {
        throw '没找到 backend\.venv 或 conda，先按 README 建好 Python 环境'
    }
    if ($LASTEXITCODE -ne 0) { throw "Python 步骤失败，退出码 $LASTEXITCODE" }
}

function Show-Size($path) {
    if (Test-Path -LiteralPath $path) {
        $sum = (Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        '{0:N0} MB' -f ($sum / 1MB)
    } else { '不存在' }
}

$mirrorArg = if ($Mirror) { @('--mirror', $Mirror) } else { @() }

Write-Output "==> 项目根：$root"
Write-Output "==> HF 镜像：$(if ($Mirror) { $Mirror } else { '直连' })"

if (-not $SkipTripoSR) {
    if (Test-Path -LiteralPath (Join-Path $root 'backend\TripoSR\tsr\system.py')) {
        Write-Output '[1/3] TripoSR 源码已存在，跳过'
    } else {
        Write-Output '[1/3] 下载 TripoSR 源码并打 CPU 适配补丁'
        Invoke-Py -Arguments @('backend\setup_triposr.py')
    }

    Write-Output '[1/3] 下载 TripoSR 权重（约 1.6GB，断了重跑会续上）'
    Invoke-Py -Arguments (@(
        'backend\fetch_hf_weights.py',
        '--repo', 'stabilityai/TripoSR',
        '--home', (Join-Path $cache 'huggingface')
    ) + $mirrorArg)
    Write-Output ('    cache/huggingface = ' + (Show-Size (Join-Path $cache 'huggingface')))
}

if (-not $SkipHunyuan) {
    Write-Output '[2/3] 下载 Hunyuan3D-2mini 形状权重（约 3.6GB，只取 hunyuan3d-dit-v2-mini 子目录）'
    Invoke-Py -Arguments (@(
        'backend\fetch_hf_weights.py',
        '--repo', 'tencent/Hunyuan3D-2mini',
        '--home', (Join-Path $cache 'hf_cache'),
        '--allow', 'hunyuan3d-dit-v2-mini/*'
    ) + $mirrorArg)
    Write-Output ('    cache/hf_cache = ' + (Show-Size (Join-Path $cache 'hf_cache')))
}

if (-not $SkipMeshroom) {
    $dest = Join-Path $cache 'Meshroom-2023.3.0'
    $exe = Join-Path $dest 'meshroom_batch.exe'
    if (Test-Path -LiteralPath $exe) {
        Write-Output '[3/3] Meshroom 已存在，跳过'
    } else {
        $zip = Join-Path $cache 'Meshroom-2023.3.0-win64.zip'
        $url = 'https://github.com/alicevision/Meshroom/releases/download/v2023.3.0/Meshroom-2023.3.0-win64.zip'
        if (-not (Test-Path -LiteralPath $zip)) {
            Write-Output '[3/3] 下载 Meshroom 便携版（约 1.4GB），中断后重跑会续传'
            & curl.exe -L -C - --retry 5 --retry-delay 3 -o $zip $url
            if ($LASTEXITCODE -ne 0) { throw 'Meshroom 下载失败，检查网络后重跑' }
        }
        Write-Output '[3/3] 解压 Meshroom'
        & (Join-Path $env:SystemRoot 'System32\tar.exe') -xf $zip -C $cache
        if (-not (Test-Path -LiteralPath $exe)) { throw "解压后没找到 $exe" }
    }
    Write-Output ('    cache/Meshroom-2023.3.0 = ' + (Show-Size $dest))
}

Write-Output ''
Write-Output '完成。启动后端后看一眼 http://127.0.0.1:8000/health，'
Write-Output 'triposrInstalled / hunyuanInstalled / meshroomInstalled 三个都为 true 就齐了。'
