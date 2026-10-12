# EXP-034 synthetic-only, native Windows release preflight. DO NOT invoke live publisher.
# This script may create TEMPORARY synthetic fixtures inside an isolated review clone.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ReviewRepo,
    [Parameter(Mandatory=$true)][string]$LiveRepo,
    [Parameter(Mandatory=$true)][string]$Origin,
    [Parameter(Mandatory=$true)][string]$ExpectedHead
)
$ErrorActionPreference = "Stop"
$Base = "a4f00578c00c5e23eb4fae073cf2df18c78d9a0a"
$GuardBranch = "governance/frozen-dependency-change-impact-gate-20261010"
$GuardHead = "e1fb7073100746848bce8ee0b823f5528d14b"
$GuardScriptBlob = "502d180a91ed5e9c76d967289c30f2637d58fffa"
$LauncherRel = "ops/handoffs/exp034-current-crypto-aggregate-hourly-runner-v0_1.ps1"
$LauncherBlob = "3992bb46df25d97678f30023324a9dfc4bf41038"
$ExpectedPublisherBlob = "e3f153128d4c65c7c98cfba7427a6e892eca2e29"

function GitValue([string]$At, [string[]]$GitArgs) {
    $Value = (& git -C $At @GitArgs)
    if ($LASTEXITCODE -ne 0) { throw "Git identity/source verification failed" }
    return ([string]($Value | Select-Object -First 1)).Trim()
}
function ConfirmBlob([string]$At, [string]$Relative, [string]$Blob) {
    $DiskPath = Join-Path $At ($Relative.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $DiskPath -PathType Leaf)) { throw "Pinned verifier file missing" }
    $CommitSha = GitValue $At -GitArgs @("rev-parse", "HEAD:$Relative")
    $DiskSha = GitValue $At -GitArgs @("hash-object", "--path=$Relative", "--", $DiskPath)
    if ($CommitSha -cne $Blob -or $DiskSha -cne $Blob) {
        throw "Committed or disk Git blob pin mismatch"
    }
}
function ParsePsFile([string]$File) {
    $Tokens = $null
    $ErrorsFound = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $File, [ref]$Tokens, [ref]$ErrorsFound
    )
    if ($null -ne $ErrorsFound -and $ErrorsFound.Count -gt 0) {
        throw "Native Windows PowerShell syntax check failed"
    }
}
function ConfirmSyntheticExit([string]$File, [int]$Code) {
    & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $File >$null 2>$null
    $Got = $LASTEXITCODE
    if ($Got -ne $Code) {
        throw "Isolated synthetic launcher exit mismatch (expected $Code, got $Got)"
    }
}

if (-not (Test-Path -LiteralPath $ReviewRepo -PathType Container)) { throw "Review clone missing" }
if (-not (Test-Path -LiteralPath $LiveRepo -PathType Container)) { throw "VPS checkout missing" }
if ((GitValue $ReviewRepo -GitArgs @("rev-parse", "HEAD")) -cne $ExpectedHead) {
    throw "Review HEAD mismatch"
}
if ((GitValue $LiveRepo -GitArgs @("rev-parse", "HEAD")) -cne "8ec0e82ea340682d92f9a62acf85171b7715bf5d") {
    throw "Live checkout HEAD changed; stop"
}
if ((GitValue $LiveRepo -GitArgs @("branch", "--show-current")) -cne "main") {
    throw "Live branch changed; stop"
}
$LiveChanges = @(& git -C $LiveRepo status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $LiveChanges.Count -ne 0) {
    throw "Live tracked worktree changed; stop"
}
if ((GitValue $ReviewRepo -GitArgs @("merge-base", $Base, $ExpectedHead)) -cne $Base) {
    throw "Feature is not directly based on expected main"
}
ConfirmBlob $ReviewRepo $LauncherRel $LauncherBlob
$SourceFile = Join-Path $ReviewRepo ($LauncherRel.Replace("/", "\"))
ParsePsFile $SourceFile
$Original = [System.IO.File]::ReadAllText($SourceFile)
$ActualPublisher = GitValue $ReviewRepo -GitArgs @("rev-parse", "HEAD:scripts/guarded_product_publish_v0_1.py")
if ($ActualPublisher -cne $ExpectedPublisherBlob) { throw "Reviewed publisher source drifted" }
if ($Original -notlike '*$env:VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1 = "1"*' -or
    $Original -notlike '*$env:VOWSIG_CRYPTO_ASOF_ENABLED = "1"*' -or
    $Original -notlike '*$env:VOWSIG_GUARDED_PUBLISH_ENABLED = "1"*' -or
    $Original -notlike '*$ExpectedPublisherGitBlob = "e3f153128d4c65c7c98cfba7427a6e892eca2e29"*') {
    throw "Dormant launcher source shape unexpected"
}
Write-Output "EXP034_LAUNCHER_EXACT_BLOB_AND_AST=PASS"

# Exercise only a modified COPY which points at a disposable synthetic root.
# Never invoke the as-committed script: it points to live production checkout.
$TempBase = Join-Path $ReviewRepo (".exp034-offline-" + [guid]::NewGuid().ToString("N").Substring(0,8))
$SynData = Join-Path $TempBase "data"
$SynScripts = Join-Path $TempBase "scripts"
New-Item -ItemType Directory -Force -Path $SynData, $SynScripts | Out-Null
$FakeSeal = Join-Path $SynData "crypto-research-asof-v0.1.json"
$FakeMarker = Join-Path $SynData "exp031-one-shot-historical-publication-attempt-20261011.json"
$FakeCmd = Join-Path $SynScripts "run_product_publish_guarded_v0_1.cmd"
$FakePublisher = Join-Path $SynScripts "guarded_product_publish_v0_1.py"
$Sentinel = Join-Path $TempBase "synthetic-child-invoked.txt"
$SynSeal = New-Object byte[] 3048
[System.IO.File]::WriteAllBytes($FakeSeal, $SynSeal)
$SynHash = (Get-FileHash -LiteralPath $FakeSeal -Algorithm SHA256).Hash
$ProductionLine = '$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"'
$SealLine = '$ExpectedSeal = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"'
if (-not $Original.Contains($ProductionLine) -or -not $Original.Contains($SealLine)) {
    throw "Cannot safely synthesize launcher source"
}
$SynSource = $Original.Replace($ProductionLine, ('$Repo = "' + $TempBase + '"'))
$SynSource = $SynSource.Replace($SealLine, ('$ExpectedSeal = "' + $SynHash + '"'))
if ($SynSource -ceq $Original -or $SynSource.Contains($ProductionLine)) {
    throw "Synthetic launcher root replacement failed"
}
$SynFile = Join-Path $TempBase "synthetic-launcher.ps1"
[System.IO.File]::WriteAllText($SynFile, $SynSource, [System.Text.Encoding]::UTF8)
ParsePsFile $SynFile

# Child stub is synthetic, never a real publisher. A mistaken launch is observable.
$FakeCmdBody = @'
@echo off
if not "%VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1%"=="1" exit /b 91
if not "%VOWSIG_CRYPTO_ASOF_ENABLED%"=="1" exit /b 92
if not "%VOWSIG_GUARDED_PUBLISH_ENABLED%"=="1" exit /b 93
echo SYNTHETIC_ONLY>"SYNTHETIC_SENTINEL_PATH"
exit /b 0
'@
$FakeCmdBody = $FakeCmdBody.Replace("SYNTHETIC_SENTINEL_PATH", $Sentinel)
[System.IO.File]::WriteAllText($FakeCmd, $FakeCmdBody, [System.Text.Encoding]::ASCII)

# Negative 1: no one-shot marker, no child invocation.
ConfirmSyntheticExit $SynFile 31
if (Test-Path -LiteralPath $Sentinel) { throw "Unsafe synthetic child invocation without marker" }
Write-Output "EXP034_NEGATIVE_MISSING_MARKER=PASS"

# Negative 2: malformed historic seal, no child invocation.
[System.IO.File]::WriteAllText($FakeMarker, "SYNTHETIC", [System.Text.Encoding]::ASCII)
[System.IO.File]::WriteAllBytes($FakeSeal, (New-Object byte[] 16))
ConfirmSyntheticExit $SynFile 31
if (Test-Path -LiteralPath $Sentinel) { throw "Unsafe synthetic child invocation with invalid seal" }
Write-Output "EXP034_NEGATIVE_BAD_SEAL=PASS"

# Negative 3: correct TEST seal, corrupted disk publisher => HOLD.
[System.IO.File]::WriteAllBytes($FakeSeal, $SynSeal)
[System.IO.File]::WriteAllText($FakePublisher, "SYNTHETIC MODIFIED PUBLISHER", [System.Text.Encoding]::ASCII)
ConfirmSyntheticExit $SynFile 31
if (Test-Path -LiteralPath $Sentinel) { throw "Unsafe synthetic child invocation with modified publisher" }
Write-Output "EXP034_NEGATIVE_PUBLISHER_HASH_DRIFT=PASS"

# Positive sandbox only: approved publisher bytes; synthetic child checks env.
$ReviewedPublisher = Join-Path $ReviewRepo "scripts\guarded_product_publish_v0_1.py"
Copy-Item -LiteralPath $ReviewedPublisher -Destination $FakePublisher -Force
if ((GitValue $ReviewRepo -GitArgs @("hash-object", "--path=scripts/guarded_product_publish_v0_1.py", "--", $FakePublisher)) -cne $ExpectedPublisherBlob) {
    throw "Synthetic valid publisher fixture hash mismatch"
}
ConfirmSyntheticExit $SynFile 0
if (-not (Test-Path -LiteralPath $Sentinel -PathType Leaf)) {
    throw "Synthetic child environment flags not confirmed"
}
Write-Output "EXP034_SYNTHETIC_OPT_IN_FLAGS_AND_SANDBOX=PASS"

# Use the owner-approved frozen-dependency reviewer from PR #50, pinned by
# its exact Git branch HEAD and committed+disk source blob.
$GuardRoot = Join-Path $ReviewRepo (".exp034-trusted-guard-" + [guid]::NewGuid().ToString("N").Substring(0,8))
& git clone --quiet --depth 1 --single-branch --branch $GuardBranch $Origin $GuardRoot
if ($LASTEXITCODE -ne 0) { throw "Trusted review guard clone failed" }
if ((GitValue $GuardRoot -GitArgs @("rev-parse", "HEAD")) -cne $GuardHead) {
    throw "Trusted review guard HEAD mismatch"
}
$GuardRel = "scripts/check_frozen_dependency_impact.py"
ConfirmBlob $GuardRoot $GuardRel $GuardScriptBlob
$Python = Join-Path $LiveRepo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Existing native Python unavailable" }
$PythonVersion = (& $Python --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $env:OS -cne "Windows_NT" -or
    $PythonVersion -notmatch '^Python 3\.12\.') {
    throw "Native Windows Python 3.12 required"
}
Write-Output "EXP034_NATIVE_PYTHON=$PythonVersion"
$GuardScript = Join-Path $GuardRoot ($GuardRel.Replace("/", "\"))
& $Python -B $GuardScript --repo $ReviewRepo --base $Base --head $ExpectedHead
if ($LASTEXITCODE -ne 0) { throw "Trusted frozen-dependency checker FAILED" }
Write-Output "EXP034_TRUSTED_FROZEN_DEPENDENCY_MANUAL_GATE=PASS"

# The actual live tracked worktree must remain untouched after the review.
if ((GitValue $LiveRepo -GitArgs @("rev-parse", "HEAD")) -cne "8ec0e82ea340682d92f9a62acf85171b7715bf5d") {
    throw "Production Git HEAD changed during test"
}
$AfterStatus = @(& git -C $LiveRepo status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $AfterStatus.Count -ne 0) {
    throw "Production tracked worktree changed during test"
}
Write-Output "EXP034_LIVE_SOURCE_AND_TASKS_NOT_EXECUTED=TRUE"
Write-Output "EXP034_NATIVE_WINDOWS_OFFLINE_REVIEW=PASS"
