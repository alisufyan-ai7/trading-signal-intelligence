# EXP-031 one authorized guarded historical publication; NO scheduler mutation.
# Makes at most ONE authenticated hosted snapshot POST. Never repeat after marker.
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Main = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
$Tree = "d24d3736d0bf6633ad0d05c4a1f1373558f813b9"
$Rollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$SealPin = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$OldSnapshot = "9FA578CD23B09773B7CA3DA00C6FD37FB2027A57CEEE96CA8F85BE213DF59160"
$Publisher = "TradingTop Product Publish"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Existing = Join-Path $Repo "data\public_snapshot.json"
$Seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
$History = Join-Path $Repo "data\guarded-snapshot-history-v0.2"
$Attempt = Join-Path $Repo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
$Scanners = @("SignalProof AI-v1.1 Shadow Scan", "VowSig AI-v1.2.1 Expansion Shadow Scan", "VowSig AI-v1.3 Crypto Shadow Scan")
$EnvNames = @("VOWSIG_GUARDED_PUBLISH_ENABLED","VOWSIG_CRYPTO_ASOF_ENABLED","VOWSIG_CRYPTO_ASOF_SHA256","PYTHONPATH","PYTHONDONTWRITEBYTECODE")
function Assert-True([bool]$Ok, [string]$Reason) {
    if (-not $Ok) { throw "STOP: $Reason" }
}
function Hash-Path([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash
}
function Git-Exact {
    $head = (& git -C $Repo rev-parse HEAD).Trim()
    $branch = (& git -C $Repo symbolic-ref --short HEAD).Trim()
    $tree = (& git -C $Repo rev-parse "HEAD^{tree}").Trim()
    $dirty = @(& git -C $Repo status --porcelain --untracked-files=all)
    Assert-True ($LASTEXITCODE -eq 0 -and $head -ceq $Main -and $branch -ceq "main" -and $tree -ceq $Tree -and $dirty.Count -eq 0) "Git checkout is not the clean approved production code"
}
function Task-Unique([string]$Name) {
    $all = @(Get-ScheduledTask -TaskName $Name -ErrorAction Stop)
    Assert-True ($all.Count -eq 1) "Task Scheduler name ambiguous: $Name"
    return $all[0]
}
function Publisher-Disabled {
    $t = Task-Unique $Publisher
    $action = '/c "' + (Join-Path $Repo "scripts\run_product_publish_task.cmd") + '"'
    Assert-True ([string]$t.State -ceq "Disabled" -and $t.TaskPath -ceq "\" -and $t.Actions.Count -eq 1 -and $t.Actions[0].Execute -ieq "cmd.exe" -and $t.Actions[0].Arguments -ceq $action -and $t.Triggers.Count -eq 1) "legacy publisher is not the unchanged Disabled task"
    $processes = @(Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe'" -ErrorAction Stop | Where-Object { $_.CommandLine -match 'run_product_publish_task\.cmd|run_product_publish_guarded_v0_1\.cmd|guarded_product_publish_v0_1\.py|export_public_snapshot\.py|push_public_snapshot\.py' })
    Assert-True ($processes.Count -eq 0) "a product publishing/export process is active"
}
function Scanner-Definitions {
    $map = [ordered]@{}
    foreach ($name in $Scanners) {
        $t = Task-Unique $name
        Assert-True ([string]$t.State -cne "Disabled") "shadow scanner unexpectedly Disabled"
        $xml = [string](Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction Stop)
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $map[$name] = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))).Replace("-","") } finally { $sha.Dispose() }
    }
    return $map
}
function Scanners-Same($Original) {
    $now = Scanner-Definitions
    foreach ($name in $Scanners) { Assert-True ($now[$name] -ceq $Original[$name]) "scanner definition changed" }
}
function Rollback-Preserved {
    Assert-True (Test-Path -LiteralPath $Rollback -PathType Container) "private pre-sync rollback folder missing"
    $m = Get-Content -LiteralPath (Join-Path $Rollback "manifest.json") -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json
    Assert-True ($m.old_git_sha -ceq "47687d8d0e21523e417899a71dddc886ecf25d73" -and $m.future_merged_git_sha -ceq $Main -and $m.task_name -ceq $Publisher -and $m.snapshot_sha256 -ceq $OldSnapshot) "rollback manifest identity changed"
    foreach ($pair in @(@("publisher-task.xml",[string]$m.task_xml_sha256),@("old-runner.cmd",[string]$m.runner_sha256),@("public_snapshot.json",[string]$m.snapshot_sha256))) {
        Assert-True ((Hash-Path (Join-Path $Rollback $pair[0])) -ceq $pair[1]) "private rollback artifact hash changed"
    }
}
function Seal-Safe {
    $item = Get-Item -LiteralPath $Seal -ErrorAction Stop
    Assert-True ($item.Length -eq 3048 -and (Hash-Path $Seal) -ceq $SealPin) "existing crypto historical seal not pinned"
    return $item.LastWriteTimeUtc
}
function Check-One-Attempt {
    Assert-True (-not (Test-Path -LiteralPath $Attempt)) "one-shot attempt already recorded: NEVER retry"
    if (Test-Path -LiteralPath $History) {
        $files = @(Get-ChildItem -LiteralPath $History -Force -ErrorAction Stop)
        Assert-True ($files.Count -eq 0) "guarded history is not empty; publication may have occurred"
    }
}
function Source-Blobs {
    foreach ($spec in @(
        @("scripts/guarded_product_publish_v0_1.py","26e6b8976536f57830347e48eba42a85d59f2848"),
        @("scripts/export_guarded_core_expansion_v0_2.py","bfb0fbe12c46afcb029abf7d42861d0a4128b4b7"),
        @("src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py","cab8b03ca1eaa0b6cfa47d2f84958514b617cfc7")
    )) {
        $blob = (& git -C $Repo hash-object -- (Join-Path $Repo $spec[0])).Trim()
        Assert-True ($LASTEXITCODE -eq 0 -and $blob -ceq $spec[1]) "source blob mismatch"
    }
}
$Helper = Join-Path $PSScriptRoot "exp031_historical_publication_contract_20261011.py"
Assert-True (Test-Path -LiteralPath $Helper -PathType Leaf) "publication read-only helper missing"
Assert-True (Test-Path -LiteralPath $Python -PathType Leaf) "Python venv missing"
Git-Exact
Publisher-Disabled
$scannersBefore = Scanner-Definitions
Rollback-Preserved
$sealTime = Seal-Safe
$beforeSha = Hash-Path $Existing
Assert-True ($beforeSha -ceq $OldSnapshot) "existing local public snapshot differs from containment"
Check-One-Attempt
Source-Blobs
$envPath = Join-Path $Repo ".env"
$envPresent = Test-Path -LiteralPath $envPath -PathType Leaf
$envHash = if ($envPresent) { Hash-Path $envPath } else { "" }

# Safe in-memory preview: real core/expansion reports + fixed sealed crypto.
Write-Host "EXP031_READONLY_PUBLICATION_PREFLIGHT_STARTED=TRUE"
& $Python -B $Helper preview --root $Repo
Assert-True ($LASTEXITCODE -eq 0) "read-only historic three-program preview failed"
Git-Exact
Publisher-Disabled
Scanners-Same $scannersBefore
Rollback-Preserved
Assert-True ((Hash-Path $Existing) -ceq $beforeSha) "public snapshot changed during preview"
Assert-True ((Hash-Path $Seal) -ceq $SealPin -and (Get-Item -LiteralPath $Seal).LastWriteTimeUtc -eq $sealTime) "historical seal changed during preview"
Check-One-Attempt
Write-Host "EXACT_HISTORICAL_PREPUBLICATION=PASS"

# Single-use marker is written BEFORE any authenticated POST could be attempted.
$body = [ordered]@{ schema=1; purpose="EXP031 one-shot historical public research"; time_utc=[DateTime]::UtcNow.ToString("o"); production_sha=$Main; seal_sha256=$SealPin.ToLowerInvariant(); status="ATTEMPTED_NEVER_RETRY" } | ConvertTo-Json -Compress
$file = [IO.File]::Open($Attempt,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try { $bytes = [Text.Encoding]::UTF8.GetBytes($body); $file.Write($bytes,0,$bytes.Length); $file.Flush($true) } finally { $file.Dispose() }
Write-Host "EXP031_ONE_ATTEMPT_MARKER_CREATED=PASS"

$previous = @{}
foreach ($name in $EnvNames) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,"Process") }
try {
    $env:VOWSIG_GUARDED_PUBLISH_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_ENABLED = "1"
    $env:VOWSIG_CRYPTO_ASOF_SHA256 = $SealPin.ToLowerInvariant()
    $env:PYTHONPATH = (Join-Path $Repo "src") + ";" + (Join-Path $Repo "scripts")
    $env:PYTHONDONTWRITEBYTECODE = "1"
    Write-Host "EXP031_AUTHORIZED_ONE_SHOT_POST_STARTED=TRUE"
    & $Python -B (Join-Path $Repo "scripts\guarded_product_publish_v0_1.py") --confirm RUN-GUARDED-PUBLISH-V0.1
    $publishExit = $LASTEXITCODE
} finally {
    foreach ($name in $EnvNames) { [Environment]::SetEnvironmentVariable($name,$previous[$name],"Process") }
}
if ($publishExit -ne 0) { throw "INDETERMINATE: publisher exit $publishExit; no retry" }
Write-Host "GUARDED_ONE_SHOT_PROCESS_EXIT_ZERO=PASS"

# GET-only hosted semantic verification and SHA-reconciled local accepted pair.
& $Python -B $Helper postflight --root $Repo
Assert-True ($LASTEXITCODE -eq 0) "indeterminate archive or hosted public readback; no retry"
Git-Exact
Publisher-Disabled
Scanners-Same $scannersBefore
Rollback-Preserved
Assert-True ((Hash-Path $Seal) -ceq $SealPin -and (Get-Item -LiteralPath $Seal).LastWriteTimeUtc -eq $sealTime) "historical seal changed"
Assert-True ($envPresent -eq (Test-Path -LiteralPath $envPath -PathType Leaf) -and (-not $envPresent -or (Hash-Path $envPath) -ceq $envHash)) "local env changed"
Write-Host "EXP031_ONE_SHOT_HISTORICAL_PUBLICATION=PASS"
Write-Host "PRODUCT_PUBLISH_TASK=Disabled"
Write-Host "INDEPENDENT_SCANNERS_UNCHANGED=PASS"
Write-Host "SCHEDULER_CHANGE=False"
Write-Host "BROKER_EXECUTION=False"
Write-Host "SECOND_POST_ATTEMPT=False"
