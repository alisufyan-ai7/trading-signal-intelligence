# EXP-031 — task-scoped successor process launcher (PREPARATION).
# Copy to protected ProgramData only after separate Stage approval.
# This file stores NO ingestion token or private source data.
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
$ExpectedSeal = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$OneShotMarker = Join-Path $Repo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
$Command = Join-Path $Repo "scripts\run_product_publish_guarded_v0_1.cmd"

try {
    if (-not (Test-Path -LiteralPath $OneShotMarker -PathType Leaf)) {
        throw "Historical one-shot release marker absent"
    }
    $item = Get-Item -LiteralPath $Seal -ErrorAction Stop
    if ($item.Length -ne 3048 -or
        (Get-FileHash -LiteralPath $Seal -Algorithm SHA256).Hash -cne $ExpectedSeal) {
        throw "Pinned historical crypto seal differs from approved bytes"
    }
    if (-not (Test-Path -LiteralPath $Command -PathType Leaf)) {
        throw "Reviewed guarded command missing"
    }

    # These opt-ins are LOCAL TO THIS TASK PROCESS and its children.
    # TRADINGTOP_INGEST_URL/TOKEN continue to be read from the existing .env.
    $env:VOWSIG_GUARDED_PUBLISH_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_SHA256 = $ExpectedSeal.ToLowerInvariant()

    & $Command
    $code = $LASTEXITCODE
    if ($null -eq $code) { throw "Guarded task returned no exit code" }
    exit [int]$code
}
catch {
    Write-Error ("EXP031_GUARDED_HOURLY_HELD: " + $_.Exception.Message)
    exit 31
}
