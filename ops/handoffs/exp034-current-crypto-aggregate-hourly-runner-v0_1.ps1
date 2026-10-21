# EXP-034 — prospective SAME-TASK current aggregate launcher (PREPARATION ONLY).
# DO NOT install/execute until exact-SHA merge, source sync, stage and activation
# are separately authorized. Preserve old EXP-031 runner for rollback.
# This file stores NO ingestion token or private source data.
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
$ExpectedSeal = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$OneShotMarker = Join-Path $Repo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
$Command = Join-Path $Repo "scripts\run_product_publish_guarded_v0_1.cmd"
# Fail closed unless the exact publisher source tested on Windows is installed.
$PublisherRelative = "scripts/guarded_product_publish_v0_1.py"
$ExpectedPublisherGitBlob = "bb21a68a21431d94187ccd46b4b050e4eb54c418"
$PublisherPath = Join-Path $Repo ($PublisherRelative.Replace("/", "\"))

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
    # Exact committed AND disk-normalized reviewed publisher contents required.
    # Do not enable the opt-in on a still-old VPS or changed runtime source.
    $CommittedPublisherBlob = (& git -C $Repo rev-parse "HEAD:$PublisherRelative").Trim()
    if ($LASTEXITCODE -ne 0 -or $CommittedPublisherBlob -cne $ExpectedPublisherGitBlob) {
        throw "Reviewed current-aggregate publisher source not installed"
    }
    $DiskPublisherBlob = (& git -C $Repo hash-object --path="$PublisherRelative" -- $PublisherPath).Trim()
    if ($LASTEXITCODE -ne 0 -or $DiskPublisherBlob -cne $ExpectedPublisherGitBlob) {
        throw "Reviewed current-aggregate publisher disk contents changed"
    }

    # These opt-ins are LOCAL TO THIS TASK PROCESS and its children.
    # TRADINGTOP_INGEST_URL/TOKEN continue to be read from the existing .env.
    $env:VOWSIG_GUARDED_PUBLISH_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_SHA256 = $ExpectedSeal.ToLowerInvariant()
    # Research aggregate-only current-cycle opt-in. All strict source, time,
    # schema, count and crypto public-signal OFF guards remain in publisher.
    # Only this task process and children get this environment variable.
    $env:VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1 = "1"

    & $Command
    $code = $LASTEXITCODE
    if ($null -eq $code) { throw "Guarded task returned no exit code" }
    exit [int]$code
}
catch {
    # Avoid leaking private failure details and ensure exit 31 even with
    # ErrorActionPreference=Stop (Write-Error could terminate before exit).
    Write-Output "EXP034_GUARDED_HOURLY_HELD"
    exit 31
}
