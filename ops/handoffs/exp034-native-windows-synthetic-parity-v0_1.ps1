# EXP-034 six-module native Windows Python 3.12 SYNTHETIC parity checker.
# Only run after SHA-pinned GitHub clone and PowerShell AST bootstrap checks.
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$ReviewRepo,
 [Parameter(Mandatory=$true)][string]$LiveRepo,
 [Parameter(Mandatory=$true)][string]$ExpectedHead
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
$blobs=[ordered]@{
 "pyproject.toml"="ff6a16d0aa7e3cd03c700cbc73dcdbd854e6d2af"
 "src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py"="cab8b03ca1eaa0b6cfa47d2f84958514b617cfc7"
 "src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py"="842f5f6783998b8a1c7dfdbb59add61dfac0e197"
 "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py"="0f7c6a3af73ee3c5669e114b8903121cc1161397"
 "src/trading_signal_intelligence/product/crypto_epoch_source_producer_v0_1.py"="dc0e6637e0cdcd16fbac554e76842c79d254cdeb"
 "src/trading_signal_intelligence/product/crypto_epoch_receipt_store_v0_1.py"="afc4feeaa7ba60a6cad66e7b0ec64bd131170cf7"
 "tests/test_crypto_completed_epoch_v0_1.py"="c901ca1a529ddf6745e025b00ded82e17d94240a"
 "tests/test_crypto_epoch_bridge_v0_1.py"="e8e4012d8f53607d6f14577c5852e5b9d2c76008"
 "tests/test_crypto_epoch_source_receipt_v0_1.py"="a6673172c131770d9d2540cfd490ab382b93e5cf"
 "tests/test_crypto_asof_publication_v0_1.py"="a4c5447f2b197f4cf8afe8d446e5c0ef30f0618d"
 "tests/test_guarded_product_publish_v0_1.py"="25a4be6de1ad33921d8b4f66921cf0e2663f8783"
 "tests/test_crypto_public_validation_v0_1.py"="04322ad6496e35968bced6556f8f8bf8aed90191"
 "config/public_validation_program_schema_v1.json"="e15025f8523d941bd183717b7d397f96a5020286"
 "scripts/guarded_product_publish_v0_1.py"="26e6b8976536f57830347e48eba42a85d59f2848"
}
function CheckExit([string]$What) {
 if($LASTEXITCODE -ne 0) { throw "$What failed: exit $LASTEXITCODE" }
}
function GitOne([string]$Dir,[string[]]$GitArgs) {
 $lines=@(& git -C $Dir @GitArgs 2>&1)
 CheckExit "git"
 if($lines.Count -ne 1) { throw "unexpected Git answer" }
 return ([string]$lines[0]).Trim()
}
if($env:OS -ne "Windows_NT") {throw "Windows only"}
$ReviewRepo=(Resolve-Path -LiteralPath $ReviewRepo).Path
$LiveRepo=(Resolve-Path -LiteralPath $LiveRepo).Path
if($ExpectedHead -notmatch '^[a-f0-9]{40}$') {throw "bad HEAD argument"}
if($ReviewRepo -eq $LiveRepo -or $ReviewRepo.StartsWith($LiveRepo+"\",[StringComparison]::OrdinalIgnoreCase)) {throw "review checkout overlaps live"}
if((GitOne $ReviewRepo @("rev-parse","HEAD")) -ne $ExpectedHead) {throw "candidate mismatch"}
if((GitOne $ReviewRepo @("rev-parse","--abbrev-ref","HEAD")) -ne "HEAD") {throw "detached review required"}
$liveBefore=GitOne $LiveRepo @("rev-parse","HEAD")
$liveStateBefore=@(& git -C $LiveRepo status --porcelain --untracked-files=no)
CheckExit "live status precheck"
$dirty=@(& git -C $ReviewRepo status --porcelain --untracked-files=all)
CheckExit "review clean precheck"
if($dirty.Count -gt 0) {throw "review dirty"}
foreach($rel in $blobs.Keys) {
 $expected=$blobs[$rel]
 if((GitOne $ReviewRepo @("rev-parse","HEAD:$rel")) -ne $expected) {throw "commit blob mismatch $rel"}
 $disk=Join-Path $ReviewRepo ($rel.Replace("/","\"))
 if(-not (Test-Path -LiteralPath $disk -PathType Leaf)) {throw "missing pinned file $rel"}
 if((GitOne $ReviewRepo @("hash-object","--path=$rel","--",$disk)) -ne $expected) {throw "disk blob mismatch $rel"}
}
Write-Output "EXP034_EXACT_14_BLOBS=PASS"
$guarded=Get-Content -LiteralPath (Join-Path $ReviewRepo "scripts\guarded_product_publish_v0_1.py") -Raw
if($guarded -notmatch '(?m)^CRYPTO_WRITER_INTERLOCK_READY = False\s*$') {throw "crypto interlock mutated"}
Write-Output "CRYPTO_WRITER_INTERLOCK_DISABLED=TRUE"
$py=Join-Path $LiveRepo ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py -PathType Leaf)) {throw "existing venv missing; no install"}
& $py -B -c "import os,sys; assert os.name=='nt' and sys.version_info[:2]==(3,12); print('WINDOWS_PYTHON='+sys.version.split()[0])"
CheckExit "Python 3.12 version"
& $py -B -m pytest --version
CheckExit "existing pytest availability"
$prior=(Get-Location).Path
$keys=@("PYTHONPATH","PYTHONDONTWRITEBYTECODE","PYTEST_DISABLE_PLUGIN_AUTOLOAD","PYTEST_ADDOPTS","TMP","TEMP","TMPDIR","VOWSIG_CRYPTO_ASOF_ENABLED")
$original=@{}
foreach($key in $keys){$original[$key]=[Environment]::GetEnvironmentVariable($key,"Process")}
$scratch=Join-Path $ReviewRepo ".t"
try {
 [void](New-Item -ItemType Directory -Path $scratch -ErrorAction Stop)
 $env:PYTHONPATH=Join-Path $ReviewRepo "src"
 $env:PYTHONDONTWRITEBYTECODE="1"
 $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
 $env:PYTEST_ADDOPTS=""
 $env:TMP=$scratch
 $env:TEMP=$scratch
 $env:TMPDIR=$scratch
 $env:VOWSIG_CRYPTO_ASOF_ENABLED="0"
 Set-Location -LiteralPath $ReviewRepo
 $src=@("src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py",
        "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py",
        "src/trading_signal_intelligence/product/crypto_epoch_source_producer_v0_1.py",
        "src/trading_signal_intelligence/product/crypto_epoch_receipt_store_v0_1.py",
        "tests/test_crypto_completed_epoch_v0_1.py",
        "tests/test_crypto_epoch_bridge_v0_1.py",
        "tests/test_crypto_epoch_source_receipt_v0_1.py")
 & $py -B -c "import ast,pathlib,sys; [ast.parse(pathlib.Path(x).read_text(encoding='utf-8'),filename=x) for x in sys.argv[1:]]; print('EXP034_PYTHON_AST=PASS')" @src
 CheckExit "Python AST"
 & $py -B -c "import pathlib,sys; from trading_signal_intelligence.product import crypto_asof_seal_v0_1 as x; expected=(pathlib.Path(sys.argv[1])/'src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py').resolve(); assert pathlib.Path(x.__file__).resolve()==expected; print('REAL_CRYPTO_ALLOWLIST=PASS')" $ReviewRepo
 CheckExit "actual allowlist import"
 $tests=@("tests/test_crypto_completed_epoch_v0_1.py",
          "tests/test_crypto_epoch_bridge_v0_1.py",
          "tests/test_crypto_epoch_source_receipt_v0_1.py",
          "tests/test_crypto_asof_publication_v0_1.py",
          "tests/test_guarded_product_publish_v0_1.py",
          "tests/test_crypto_public_validation_v0_1.py")
 Write-Output "EXP034_SIX_SYNTHETIC_MODULES_STARTED=TRUE"
 & $py -B -m pytest -q -p no:cacheprovider --basetemp="$scratch\pt" @tests
 CheckExit "six-module synthetic suite"
 Write-Output "EXP034_SIX_SYNTHETIC_MODULES=PASS"
}
finally {
 Set-Location -LiteralPath $prior
 foreach($key in $keys){[Environment]::SetEnvironmentVariable($key,$original[$key],"Process")}
}
$liveAfter=GitOne $LiveRepo @("rev-parse","HEAD")
$liveStateAfter=@(& git -C $LiveRepo status --porcelain --untracked-files=no)
CheckExit "live status postcheck"
if($liveAfter -ne $liveBefore -or
   ($liveStateBefore -join [Environment]::NewLine) -ne ($liveStateAfter -join [Environment]::NewLine)) {
 throw "live tracked worktree changed"
}
if((GitOne $ReviewRepo @("rev-parse","HEAD")) -ne $ExpectedHead){throw "review checkout moved"}
Write-Output "LIVE_GIT_HEAD_AND_TRACKED_STATUS_UNCHANGED=TRUE"
Write-Output "EXP034_NATIVE_WINDOWS_SYNTHETIC_PARITY=PASS"
