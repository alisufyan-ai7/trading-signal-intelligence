# Durable same-user Windows Task Scheduler runner for VowSig S02.
# Installed only under C:\ProgramData\VowSig-S02-AutoBackup, never in production.
$ErrorActionPreference = "Stop"
$Base = Join-Path $env:ProgramData "VowSig-S02-AutoBackup"
$Live = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Runtime = Join-Path $Base "current"
$Python = Join-Path $Runtime ".venv\Scripts\python.exe"
$Script = Join-Path $Runtime "scripts\vowsig_s02_automatic_backup_v0_1.py"
$State = Join-Path $Base "state"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $Script -PathType Leaf)) {
    exit 3
}
$env:PYTHONPATH = Join-Path $Runtime "src"
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

& $Python -B $Script --run-once --repo-root $Live --state-dir $State
if ($LASTEXITCODE -ne 0) { exit 2 }
exit 0
