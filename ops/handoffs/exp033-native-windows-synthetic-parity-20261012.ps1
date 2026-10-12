# EXP-033 exact-SHA native Windows Python 3.12 SYNTHETIC TEST HANDOFF ONLY.
# Execute from a separately SHA/PowerShell-AST-verified review clone.
# No VPS production checkout changes, ledger reads, provider calls or publisher actions.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ReviewRepo,
    [Parameter(Mandatory=$true)][string]$LiveRepo,
    [Parameter(Mandatory=$true)][string]$ExpectedReviewHead
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ExpectedMain = "a4f00578c00c5e23eb4fae073cf2df18c78d9a0a"
$ExpectedParent = "4fa1860e6df2684dc55de1f9723bdc07bde5d522"
$ExpectedChild = "a4f58ea87a3ba1b011fda212d11714daa3d0c56b"
$ExpectedBlobs = [ordered]@{
    "pyproject.toml" = "ff6a16d0aa7e3cd03c700cbc73dcdbd854e6d2af"
    "src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py" = "cab8b03ca1eaa0b6cfa47d2f84958514b617cfc7"
    "src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py" = "842f5f6783998b8a1c7dfdbb59add61dfac0e197"
    "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py" = "0f7c6a3af73ee3c5669e114b8903121cc1161397"
    "tests/test_crypto_completed_epoch_v0_1.py" = "c901ca1a529ddf6745e025b00ded82e17d94240a"
    "tests/test_crypto_epoch_bridge_v0_1.py" = "e8e4012d8f53607d6f14577c5852e5b9d2c76008"
    "tests/test_crypto_asof_publication_v0_1.py" = "a4c5447f2b197f4cf8afe8d446e5c0ef30f0618d"
    "tests/test_guarded_product_publish_v0_1.py" = "25a4be6de1ad33921d8b4f66921cf0e2663f8783"
    "tests/test_crypto_public_validation_v0_1.py" = "04322ad6496e35968bced6556f8f8bf8aed90191"
    "config/public_validation_program_schema_v1.json" = "e15025f8523d941bd183717b7d397f96a5020286"
    "scripts/guarded_product_publish_v0_1.py" = "26e6b8976536f57830347e48eba42a85d59f2848"
}
function Assert-Exit([string]$Action) {
    if ($LASTEXITCODE -ne 0) { throw "$Action exit=$LASTEXITCODE" }
}
function Git-One([string]$Root, [string[]]$Args) {
    $lines = @(& git -C $Root @Args 2>&1)
    Assert-Exit "git"
    if ($lines.Count -ne 1) { throw "unexpected git response shape" }
    return ([string]$lines[0]).Trim()
}
if ($env:OS -ne "Windows_NT") { throw "native Windows required" }
$ReviewRepo = (Resolve-Path -LiteralPath $ReviewRepo).Path
$LiveRepo = (Resolve-Path -LiteralPath $LiveRepo).Path
if ($ReviewRepo -eq $LiveRepo -or $ReviewRepo.StartsWith($LiveRepo + "\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "review checkout must be outside production"
}
if ($ExpectedReviewHead -notmatch '^[a-f0-9]{40}$') { throw "invalid reviewed SHA" }
if ((Git-One $ReviewRepo @("rev-parse", "HEAD")) -ne $ExpectedReviewHead) {
    throw "review HEAD mismatch"
}
if ((Git-One $ReviewRepo @("rev-parse", "--abbrev-ref", "HEAD")) -ne "HEAD") {
    throw "review must be detached"
}
$LiveHeadBefore = Git-One $LiveRepo @("rev-parse", "HEAD")
$LiveStatusBefore = @(& git -C $LiveRepo status --porcelain --untracked-files=no)
Assert-Exit "production tracked-status precheck"
$ReviewStatus = @(& git -C $ReviewRepo status --porcelain --untracked-files=all)
Assert-Exit "review clean checkout precheck"
if ($ReviewStatus.Count -gt 0) { throw "review worktree dirty before tests" }
foreach ($rel in $ExpectedBlobs.Keys) {
    $expected = [string]$ExpectedBlobs[$rel]
    if ((Git-One $ReviewRepo @("rev-parse", "HEAD:$rel")) -ne $expected) {
        throw "Git source blob mismatch: $rel"
    }
    $disk = Join-Path $ReviewRepo ($rel.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $disk -PathType Leaf)) { throw "missing file: $rel" }
    # --path applies Git's checked-in clean filters (Windows CRLF-safe).
    if ((Git-One $ReviewRepo @("hash-object", "--path=$rel", "--", $disk)) -ne $expected) {
        throw "worktree file mismatch: $rel"
    }
}
Write-Output "EXACT_11_SOURCE_AND_TEST_BLOBS=PASS"
Write-Output "EXPECTED_PRODUCTION_MAIN=$ExpectedMain"
Write-Output "EXPECTED_PR59_PARENT=$ExpectedParent"
Write-Output "EXPECTED_PR60_CHILD=$ExpectedChild"
Write-Output "CURRENT_REVIEW_HEAD=$ExpectedReviewHead"
$guarded = Get-Content -LiteralPath (Join-Path $ReviewRepo "scripts\guarded_product_publish_v0_1.py") -Raw
if ($guarded -notmatch '(?m)^CRYPTO_WRITER_INTERLOCK_READY = False\s*$') {
    throw "production interlock invariant changed"
}
Write-Output "FROZEN_CRYPTO_WRITER_INTERLOCK_DISABLED=TRUE"
$Python = Join-Path $LiveRepo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "existing Windows Python virtual environment absent; no installs attempted"
}
& $Python -B -c "import sys; assert sys.version_info[:2] == (3,12), 'Python 3.12 required'; print('NATIVE_WINDOWS_PYTHON='+sys.version.split()[0])"
Assert-Exit "Python version check"
& $Python -B -m pytest --version
Assert-Exit "pytest availability (no package installation)"
$PriorLocation = (Get-Location).Path
$keys = @("PYTHONPATH", "PYTHONDONTWRITEBYTECODE", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS", "TMP", "TEMP", "TMPDIR", "VOWSIG_CRYPTO_ASOF_ENABLED")
$saved = @{}
foreach ($key in $keys) { $saved[$key] = [Environment]::GetEnvironmentVariable($key, "Process") }
$scratch = Join-Path $ReviewRepo ".exp033-synthetic-only-temp"
try {
    [void](New-Item -ItemType Directory -Path $scratch -ErrorAction Stop)
    $env:PYTHONPATH = Join-Path $ReviewRepo "src"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
    $env:PYTEST_ADDOPTS = ""
    $env:TMP = $scratch
    $env:TEMP = $scratch
    $env:TMPDIR = $scratch
    $env:VOWSIG_CRYPTO_ASOF_ENABLED = "0"
    Set-Location -LiteralPath $ReviewRepo
    $source = @(
        "src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py",
        "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py",
        "tests/test_crypto_completed_epoch_v0_1.py",
        "tests/test_crypto_epoch_bridge_v0_1.py"
    )
    & $Python -B -c "import ast,pathlib,sys; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8'),filename=p) for p in sys.argv[1:]]; print('EXACT_SOURCE_AST=PASS')" @source
    Assert-Exit "native Python in-memory AST"
    & $Python -B -c "import pathlib,sys; from trading_signal_intelligence.product import crypto_asof_seal_v0_1 as m; expected=(pathlib.Path(sys.argv[1])/'src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py').resolve(); assert pathlib.Path(m.__file__).resolve()==expected; print('REAL_REPOSITORY_ALLOWLIST=PASS')" $ReviewRepo
    Assert-Exit "real as-of validator import"
    $tests = @(
        "tests/test_crypto_completed_epoch_v0_1.py",
        "tests/test_crypto_epoch_bridge_v0_1.py",
        "tests/test_crypto_asof_publication_v0_1.py",
        "tests/test_guarded_product_publish_v0_1.py",
        "tests/test_crypto_public_validation_v0_1.py"
    )
    Write-Output "NATIVE_WINDOWS_SYNTHETIC_REGRESSIONS_STARTED=TRUE"
    & $Python -B -m pytest -q -p no:cacheprovider @tests
    Assert-Exit "Windows five-module synthetic/regression suite"
    Write-Output "NATIVE_WINDOWS_SYNTHETIC_REGRESSIONS=PASS"
}
finally {
    Set-Location -LiteralPath $PriorLocation
    foreach ($key in $keys) {
        [Environment]::SetEnvironmentVariable($key, $saved[$key], "Process")
    }
}
$LiveHeadAfter = Git-One $LiveRepo @("rev-parse", "HEAD")
$LiveStatusAfter = @(& git -C $LiveRepo status --porcelain --untracked-files=no)
Assert-Exit "production tracked-status postcheck"
if ($LiveHeadBefore -ne $LiveHeadAfter -or
    ($LiveStatusBefore -join [Environment]::NewLine) -ne ($LiveStatusAfter -join [Environment]::NewLine)) {
    throw "production Git HEAD or tracked status changed; STOP"
}
if ((Git-One $ReviewRepo @("rev-parse", "HEAD")) -ne $ExpectedReviewHead) {
    throw "review HEAD changed"
}
Write-Output "PRODUCTION_HEAD_AND_TRACKED_STATUS_UNCHANGED=TRUE"
Write-Output "NO_PRODUCTION_SCHEDULER_CLOUD_OR_PUBLISHER_ACTION_REQUESTED=TRUE"
Write-Output "EXP033_NATIVE_WINDOWS_EXACT_SOURCE_SYNTHETIC_PARITY=PASS"
