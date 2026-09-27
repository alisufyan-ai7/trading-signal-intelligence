param(
    [string]$IngestUrl = "https://tradingtop-early-access-production.up.railway.app/api/internal/snapshot"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot ".env"

$secureToken = Read-Host "Enter the SAME TRADINGTOP_INGEST_TOKEN configured in Railway" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
try {
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Ingestion token cannot be empty."
}

$lines = @()
if (Test-Path $envFile) {
    $lines = @(Get-Content $envFile)
}

$keys = @("TRADINGTOP_INGEST_URL", "TRADINGTOP_INGEST_TOKEN")
$filtered = foreach ($line in $lines) {
    $drop = $false
    foreach ($key in $keys) {
        if ($line -match ("^" + [regex]::Escape($key) + "=")) {
            $drop = $true
            break
        }
    }
    if (-not $drop) {
        $line
    }
}

$filtered += "TRADINGTOP_INGEST_URL=$IngestUrl"
$filtered += "TRADINGTOP_INGEST_TOKEN=$token"

[System.IO.File]::WriteAllLines($envFile, [string[]]$filtered)

Write-Host "Cloud ingestion configured in local .env"
Write-Host "URL: $IngestUrl"
Write-Host "Token: saved (not displayed)"
Write-Host ""
Write-Host "Next:"
Write-Host ".\.venv\Scripts\python.exe scripts\export_public_snapshot.py"
Write-Host ".\.venv\Scripts\python.exe scripts\push_public_snapshot.py"
