# EXP-031 — OWNER-APPROVED EXACT-SHA VPS SOURCE SYNC ONLY
# No Task Scheduler writes, publisher invocation, environment edits, SQLite access,
# new crypto capture, provider/broker operations, notifications or cloud POST.
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Old = "47687d8d0e21523e417899a71dddc886ecf25d73"
$New = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
$Tree = "d24d3736d0bf6633ad0d05c4a1f1373558f813b9"
$Rollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$SealHash = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$OldRunnerBlob = "3c5d292338b65c65e0faa5ffe04c1fb2000efa84"
$PublisherName = "TradingTop Product Publish"
$ScannerNames = @(
 "SignalProof AI-v1.1 Shadow Scan",
 "VowSig AI-v1.2.1 Expansion Shadow Scan",
 "VowSig AI-v1.3 Crypto Shadow Scan"
)
function Get-Hash([string]$Path) {
 return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash
}
function Assert-CleanHead([string]$Expected) {
 $root = (& git -C $Repo rev-parse --show-toplevel).Trim()
 $branch = (& git -C $Repo symbolic-ref --short HEAD).Trim()
 $head = (& git -C $Repo rev-parse HEAD).Trim()
 $status = @(& git -C $Repo status --porcelain --untracked-files=all)
 if ($LASTEXITCODE -ne 0 -or
     [IO.Path]::GetFullPath($root).TrimEnd('\') -ine [IO.Path]::GetFullPath($Repo).TrimEnd('\') -or
     $branch -cne "main" -or $head -cne $Expected -or $status.Count -ne 0) {
     throw "STOP: production Git worktree does not match required clean exact HEAD"
 }
}
function Get-TaskUnique([string]$Name) {
 $tasks = @(Get-ScheduledTask -TaskName $Name -ErrorAction Stop)
 if ($tasks.Count -ne 1) { throw "STOP: task identity ambiguous: $Name" }
 return $tasks[0]
}
function Assert-PublisherDisabled {
 $task = Get-TaskUnique $PublisherName
 $expectedAction = '/c "' + (Join-Path $Repo "scripts\run_product_publish_task.cmd") + '"'
 if ([string]$task.State -cne "Disabled" -or $task.TaskPath -cne "\" -or
     $task.Actions.Count -ne 1 -or $task.Actions[0].Execute -ine "cmd.exe" -or
     $task.Actions[0].Arguments -cne $expectedAction -or
     $task.Triggers.Count -ne 1 -or
     [string]$task.Settings.MultipleInstances -cne "IgnoreNew") {
     throw "STOP: old Product Publish task not the audited DISABLED task"
 }
 $processes = @(Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe' OR Name='powershell.exe' OR Name='pwsh.exe'" -ErrorAction Stop |
     Where-Object { $_.CommandLine -match 'run_product_publish_task\.cmd|run_product_publish_guarded_v0_1\.cmd|guarded_product_publish_v0_1\.py|export_public_snapshot\.py|push_public_snapshot\.py|export_guarded_core_expansion_v0_2\.py' })
 if ($processes.Count -ne 0) { throw "STOP: publisher/export/push process active" }
}
function Get-ScannerFingerprints {
 $out = [ordered]@{}
 foreach ($name in $ScannerNames) {
     $task = Get-TaskUnique $name
     if ([string]$task.State -eq "Disabled") { throw "STOP: scanner is disabled: $name" }
     $xml = [string](Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Stop)
     $sha = [Security.Cryptography.SHA256]::Create()
     try {
         $bytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))
         $out[$name] = [BitConverter]::ToString($bytes).Replace("-", "")
     } finally { $sha.Dispose() }
 }
 return $out
}
function Assert-ScannerFingerprints($Before) {
 $after = Get-ScannerFingerprints
 foreach ($name in $ScannerNames) {
     if ($Before[$name] -cne $after[$name]) {
         throw "STOP: independent scanner definition drifted: $name"
     }
 }
}
function Confirm-LocalRollback {
 if (-not (Test-Path -LiteralPath $Rollback -PathType Container)) {
     throw "STOP: private rollback evidence directory missing"
 }
 $m = Get-Content -LiteralPath (Join-Path $Rollback "manifest.json") -Raw -Encoding UTF8 -ErrorAction Stop | ConvertFrom-Json
 if ($m.schema_version -ne 1 -or $m.old_git_sha -cne $Old -or
     $m.future_merged_git_sha -cne $New -or
     $m.task_name -cne $PublisherName -or $m.task_path -cne "\" -or
     $m.old_runner_blob -cne $OldRunnerBlob) {
     throw "STOP: private rollback manifest identity changed"
 }
 foreach ($item in @(
     @("publisher-task.xml", [string]$m.task_xml_sha256),
     @("old-runner.cmd", [string]$m.runner_sha256),
     @("public_snapshot.json", [string]$m.snapshot_sha256)
 )) {
     if ((Get-Hash (Join-Path $Rollback $item[0])) -cne $item[1]) {
         throw "STOP: private rollback file SHA mismatch: $($item[0])"
     }
 }
 $runner = (& git -C $Repo hash-object -- (Join-Path $Repo "scripts\run_product_publish_task.cmd")).Trim()
 if ($LASTEXITCODE -ne 0 -or $runner -cne $OldRunnerBlob) {
     throw "STOP: production original publisher command changed"
 }
 return $m
}

# All preflights are read-only except permitted Git fetch metadata.
Assert-CleanHead $Old
Assert-PublisherDisabled
$scanners = Get-ScannerFingerprints
$evidence = Confirm-LocalRollback

$seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
$sealFile = Get-Item -LiteralPath $seal -ErrorAction Stop
if ($sealFile.Length -ne 3048 -or (Get-Hash $seal) -cne $SealHash) {
 throw "STOP: pinned historical crypto seal changed"
}
$sealTime = $sealFile.LastWriteTimeUtc
$snapshot = Join-Path $Repo "data\public_snapshot.json"
$snapshotSha = Get-Hash $snapshot
if ($snapshotSha -cne $evidence.snapshot_sha256) {
 throw "STOP: contained sanitized snapshot no longer matches local source"
}
$envFile = Join-Path $Repo ".env"
$hasEnv = Test-Path -LiteralPath $envFile -PathType Leaf
$envSha = if ($hasEnv) { Get-Hash $envFile } else { "" }
$python = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
 throw "STOP: production Python environment missing"
}

$remote = @(& git -C $Repo ls-remote origin refs/heads/main)
if ($LASTEXITCODE -ne 0 -or $remote.Count -ne 1 -or
    ($remote[0] -split '\s+')[0] -cne $New) {
 throw "STOP: GitHub origin/main moved from approved SHA"
}
& git -C $Repo fetch --no-tags origin refs/heads/main
if ($LASTEXITCODE -ne 0) { throw "STOP: GitHub main fetch failed" }
$received = (& git -C $Repo rev-parse FETCH_HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $received -cne $New) {
 throw "STOP: fetched commit is not owner-approved"
}
$receivedTree = (& git -C $Repo rev-parse ($New + '^{tree}')).Trim()
if ($LASTEXITCODE -ne 0 -or $receivedTree -cne $Tree) {
 throw "STOP: downloaded release tree is not the tested code"
}
& git -C $Repo merge-base --is-ancestor $Old $New
if ($LASTEXITCODE -ne 0) { throw "STOP: Git update is not fast-forward" }

# Recheck immediately before modifying any tracked source.
Assert-CleanHead $Old
Assert-PublisherDisabled
Assert-ScannerFingerprints $scanners
if ((Get-Hash $snapshot) -cne $snapshotSha -or (Get-Hash $seal) -cne $SealHash -or
    (Get-Item -LiteralPath $seal).LastWriteTimeUtc -ne $sealTime) {
 throw "STOP: sealed research or local public snapshot drifted before sync"
}
Write-Host "EXACT_SOURCE_SYNC_PREFLIGHT=PASS"
Write-Host "PUBLISHER_STILL_DISABLED=PASS"
Write-Host "PRIVATE_ROLLBACK_EVIDENCE=PASS"
Write-Host "APPROVED_GIT_FAST_FORWARD_STARTED=TRUE"

# ONLY authorized production change: fast-forward tracked Git source.
& git -C $Repo merge --ff-only FETCH_HEAD
if ($LASTEXITCODE -ne 0) {
 throw "INDETERMINATE: Git fast-forward failed; do not retry/reset"
}

# Read-only postflight; no new publisher activation.
Assert-CleanHead $New
Assert-PublisherDisabled
Assert-ScannerFingerprints $scanners
if ((Get-Hash $snapshot) -cne $snapshotSha -or (Get-Hash $seal) -cne $SealHash -or
    (Get-Item -LiteralPath $seal).LastWriteTimeUtc -ne $sealTime) {
 throw "INDETERMINATE: sealed/sanitized file changed after sync"
}
if ($hasEnv -ne (Test-Path -LiteralPath $envFile -PathType Leaf) -or
    ($hasEnv -and (Get-Hash $envFile) -cne $envSha) -or
    -not (Test-Path -LiteralPath $python -PathType Leaf)) {
 throw "INDETERMINATE: local Python/environment preservation check failed"
}
Write-Host "EXP031_VPS_EXACT_SHA_SOURCE_SYNC=PASS"
Write-Host "PRODUCTION_MAIN=$New"
Write-Host "PRODUCTION_TREE=$Tree"
Write-Host "PRODUCT_PUBLISH_TASK=Disabled"
Write-Host "SCANNER_TASK_DEFINITIONS_UNCHANGED=PASS"
Write-Host "HISTORICAL_CRYPTO_SEAL_UNCHANGED=PASS"
Write-Host "SANITIZED_SNAPSHOT_UNCHANGED=PASS"
Write-Host "TASK_MUTATIONS=False"
Write-Host "PUBLISHER_ACTIVATION=False"
Write-Host "WEBSITE_PUBLICATION=False"
