$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "Project Python not found: $python"
}

Push-Location $repoRoot
try {
    & $python "scripts\configure_cloud_ingest.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Cloud ingest configuration failed"
    }
}
finally {
    Pop-Location
}
