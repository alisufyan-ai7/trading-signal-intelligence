param(
    [switch]$UpgradePip
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project virtual environment not found: $python"
}

Push-Location $repoRoot
try {
    if ($UpgradePip) {
        & $python -m pip install --upgrade pip
    }

    & $python -m pip install -e ".[app]"
    if ($LASTEXITCODE -ne 0) { throw "App dependency installation failed" }

    & $python -c "import fastapi, uvicorn; print('fastapi=' + fastapi.__version__ + ' uvicorn=' + uvicorn.__version__)"
    if ($LASTEXITCODE -ne 0) { throw "App dependency import check failed" }

    Write-Host "Beta app environment ready."
    Write-Host "Run: $python scripts\run_beta_app.py"
}
finally {
    Pop-Location
}
