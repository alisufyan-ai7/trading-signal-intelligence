# PLAN-ONLY candidate runner; NOT INSTALLED. No delete, owner-signature or task registration.
$ErrorActionPreference = "Stop"
$Base = Join-Path $env:ProgramData "VowSig-S02-GFS-PlanOnly"
$Runtime = Join-Path $Base "current"
$Python = Join-Path $Runtime ".venv\Scripts\python.exe"
$Cli = Join-Path $Runtime "scripts\vowsig_s02_gfs_plan_only_v0_1.py"
$History = Join-Path $env:ProgramData "VowSig-S02-AutoBackup\state\history.jsonl"
$OldPath = $env:PYTHONPATH
$OldUserSite = $env:PYTHONNOUSERSITE
$OldBytecode = $env:PYTHONDONTWRITEBYTECODE
try {
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Cli -PathType Leaf) -or
        -not (Test-Path -LiteralPath $History -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $Base "pending") -PathType Container) -or
        -not (Test-Path -LiteralPath (Join-Path $Base "state") -PathType Container)) {
        throw "Isolated owner-approved read-only planner runtime not installed"
    }
    $env:PYTHONPATH = Join-Path $Runtime "src"
    $env:PYTHONNOUSERSITE = "1"
    $env:PYTHONDONTWRITEBYTECODE = "1"
    & $Python -B $Cli --mode prepare --history $History --plan-root $Base --acknowledge-read-cost I_ACCEPT_READ_ONLY_CLOUD_RESTORE_COST
    if ($LASTEXITCODE -ne 0) { throw "Safe GFS planner HOLD" }
}
finally {
    $env:PYTHONPATH = $OldPath
    $env:PYTHONNOUSERSITE = $OldUserSite
    $env:PYTHONDONTWRITEBYTECODE = $OldBytecode
}
