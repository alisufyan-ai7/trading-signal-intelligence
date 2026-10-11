# EXP-031 historical crypto MVP — reversible legacy publisher containment
# PREPARED ONLY. Owner must separately authorize -Mode Contain or PreSyncRollback.
# Default -Mode Observe is read-only and produces no files or task changes.
# No Git pull, K5 scan, private SQLite access, cloud publication or broker action.
[CmdletBinding()]
param(
    [ValidateSet("Observe","Contain","PreSyncRollback")]
    [string]$Mode = "Observe",
    [string]$Confirm = "",
    [string]$EvidenceDirectory = ""
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$OldMain = "47687d8d0e21523e417899a71dddc886ecf25d73"
$MergedMain = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
$TaskName = "TradingTop Product Publish"
$OldRunnerBlob = "3c5d292338b65c65e0faa5ffe04c1fb2000efa84"
$SealPin = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$Scanners = @(
    "SignalProof AI-v1.1 Shadow Scan",
    "VowSig AI-v1.2.1 Expansion Shadow Scan",
    "VowSig AI-v1.3 Crypto Shadow Scan"
)

function Assert-OldProduction {
    $head = (& git -C $Repo rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $head -cne $OldMain) {
        throw "STOP: VPS is not at expected PRE-SYNC old production commit. No task change."
    }
    $ref = (& git -C $Repo rev-parse --abbrev-ref HEAD).Trim()
    $dirty = @(& git -C $Repo status --porcelain --untracked-files=all)
    if ($LASTEXITCODE -ne 0 -or $ref -cne "main" -or $dirty.Count -ne 0) {
        throw "STOP: old production worktree is not clean on main."
    }
    $runner = Join-Path $Repo "scripts\run_product_publish_task.cmd"
    $blob = (& git -C $Repo hash-object -- $runner).Trim()
    if ($LASTEXITCODE -ne 0 -or $blob -cne $OldRunnerBlob) {
        throw "STOP: old publisher runner contents changed."
    }
    Write-Host "VPS_OLD_MAIN_AND_RUNNER=PASS"
}

function Get-UniqueTask([string]$Name) {
    $found = @(Get-ScheduledTask -TaskName $Name -ErrorAction Stop)
    if ($found.Count -ne 1) { throw "STOP: expected exactly one scheduled task: $Name" }
    return $found[0]
}

function Get-TaskXML([string]$Name) {
    $task = Get-UniqueTask $Name
    return [string](Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Stop)
}

function Get-TextHash([string]$Value) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace("-","")
    } finally { $sha.Dispose() }
}

function Normalized-TaskDefinitionHash([string]$SourceXml) {
    # Disable-ScheduledTask may change or add <Enabled>; normalize by
    # removing that single flag from both task definitions before compare.
    # All other task settings/actions/triggers must remain byte-structurally
    # identical after XML parsing/serialization.
    [xml]$document = $SourceXml
    $ns = New-Object Xml.XmlNamespaceManager($document.NameTable)
    $ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
    $settings = $document.SelectSingleNode("/t:Task/t:Settings", $ns)
    if ($null -eq $settings) {
        throw "STOP: task XML lacks expected Settings element."
    }
    $enabled = $settings.SelectSingleNode("t:Enabled", $ns)
    if ($null -ne $enabled) { [void]$settings.RemoveChild($enabled) }
    return Get-TextHash $document.OuterXml
}

function Scanner-XMLHashes {
    $result = [ordered]@{}
    foreach ($name in $Scanners) {
        $t = Get-UniqueTask $name
        $result[$name] = Get-TextHash (Get-TaskXML $name)
        if ([string]$t.State -eq "Disabled") {
            throw "STOP: independent scanner unexpectedly disabled: $name"
        }
    }
    return $result
}

function Assert-ScannerHashes($Before) {
    foreach ($name in $Scanners) {
        $current = Get-TextHash (Get-TaskXML $name)
        if ($current -cne $Before[$name]) {
            throw "STOP: scanner task definition changed: $name"
        }
    }
    Write-Host "INDEPENDENT_SCANNER_TASK_DEFINITIONS_UNCHANGED=PASS"
}

function Active-PublisherPids {
    $procs = @(Get-CimInstance -ClassName Win32_Process -Filter "Name='cmd.exe' OR Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe'" -ErrorAction Stop)
    $patterns = "run_product_publish_task\.cmd|run_product_publish_guarded_v0_1\.cmd|guarded_product_publish_v0_1\.py|export_public_snapshot\.py|push_public_snapshot\.py"
    return @($procs | Where-Object {
        -not [string]::IsNullOrEmpty($_.CommandLine) -and
        $_.CommandLine -match $patterns
    } | ForEach-Object { [int]$_.ProcessId })
}

function Get-Legacy {
    $task = Get-UniqueTask $TaskName
    $info = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Stop
    $runner = Join-Path $Repo "scripts\run_product_publish_task.cmd"
    $expectedArgs = '/c "' + $runner + '"'
    if ($task.Actions.Count -ne 1 -or
        $task.Actions[0].Execute -ine "cmd.exe" -or
        $task.Actions[0].Arguments -cne $expectedArgs -or
        $task.Triggers.Count -ne 1 -or
        [string]$task.Settings.MultipleInstances -cne "IgnoreNew") {
        throw "STOP: legacy publisher task contract differs from audited baseline."
    }
    return [pscustomobject]@{ Task = $task; Info = $info }
}

function Get-SnapshotState {
    $file = Join-Path $Repo "data\public_snapshot.json"
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "STOP: current sanitized public snapshot missing."
    }
    $item = Get-Item -LiteralPath $file
    return [pscustomobject]@{
        Path = $file
        Bytes = $item.Length
        Sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        LastWriteUtc = $item.LastWriteTimeUtc.ToString("o")
    }
}

function Assert-Seal {
    $path = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
    $item = Get-Item -LiteralPath $path -ErrorAction Stop
    if ($item.Length -ne 3048 -or
        (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -cne $SealPin) {
        throw "STOP: historical crypto seal not equal to owner-approved SHA/length."
    }
    Write-Host "HISTORICAL_CRYPTO_SEAL_PRESERVED=PASS"
}

function Assert-NoPublisherProcess {
    $pids = @(Active-PublisherPids)
    if ($pids.Count -ne 0) {
        throw "STOP: publisher/export/push process may be active. No forced termination."
    }
    Write-Host "NO_PUBLISHER_PROCESS_OBSERVED=PASS"
}

function Verify-Evidence($Folder) {
    if (-not (Test-Path -LiteralPath $Folder -PathType Container)) {
        throw "STOP: private rollback directory unavailable."
    }
    $manifest = Get-Content -LiteralPath (Join-Path $Folder "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or
        $manifest.old_git_sha -cne $OldMain -or
        $manifest.old_runner_blob -cne $OldRunnerBlob -or
        $manifest.task_name -cne $TaskName) {
        throw "STOP: unexpected rollback manifest."
    }
    foreach ($spec in @(
        @("publisher-task.xml", [string]$manifest.task_xml_sha256),
        @("old-runner.cmd", [string]$manifest.runner_sha256),
        @("public_snapshot.json", [string]$manifest.snapshot_sha256)
    )) {
        $p = Join-Path $Folder $spec[0]
        if ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash -cne $spec[1]) {
            throw "STOP: private rollback evidence hash mismatch: $($spec[0])"
        }
    }
    return $manifest
}

Assert-OldProduction
Assert-Seal
$legacy = Get-Legacy
$snapshot = Get-SnapshotState
$scannerHashes = Scanner-XMLHashes

Write-Host "LEGACY_STATE=$($legacy.Task.State)"
Write-Host "LEGACY_LAST_RESULT=$($legacy.Info.LastTaskResult)"
Write-Host "LEGACY_NEXT_RUN_UTC=$($legacy.Info.NextRunTime.ToUniversalTime().ToString('o'))"
Write-Host "LEGACY_TASK_PATH=$($legacy.Task.TaskPath)"
Write-Host "CURRENT_SANITIZED_SNAPSHOT_SHA256=$($snapshot.Sha256)"
Write-Host "CURRENT_SANITIZED_SNAPSHOT_BYTES=$($snapshot.Bytes)"

if ($Mode -eq "Observe") {
    Write-Host "ACTIVE_PUBLISHER_PROCESS_COUNT=$(@(Active-PublisherPids).Count)"
    Write-Host "EXP031_CONTAINMENT_OBSERVE_ONLY=PASS"
    Write-Host "TASK_MUTATION=False"
    Write-Host "GIT_SYNC=False"
    Write-Host "CLOUD_PUBLICATION=False"
    return
}

if ($Mode -eq "Contain") {
    if ($Confirm -cne "APPROVE-EXP031-CONTAIN-PUBLISHER-ONLY") {
        throw "STOP: no separate containment execution approval supplied."
    }
    if ([string]$legacy.Task.State -cne "Ready" -or
        $legacy.Info.LastTaskResult -ne 0) {
        throw "STOP: legacy publisher not Ready with successful last result."
    }
    $now = [DateTime]::UtcNow
    $next = $legacy.Info.NextRunTime.ToUniversalTime()
    if ($next -le $now.AddMinutes(10)) {
        throw "STOP: next scheduled publisher cycle is within 10 minutes."
    }
    Assert-NoPublisherProcess

    # Contain mode writes ONLY private local rollback evidence and disables
    # the single old product-publishing task. Never write inside the Git repo.
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $folder = Join-Path $env:ProgramData (
        "VowSig-EXP031-PreSyncRollback-" + $stamp + "-" +
        [guid]::NewGuid().ToString("N").Substring(0,8)
    )
    New-Item -ItemType Directory -Path $folder -ErrorAction Stop | Out-Null
    & icacls.exe $folder /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "STOP: private rollback directory ACL failed." }
    $taskXml = Get-TaskXML $TaskName
    $taskPath = Join-Path $folder "publisher-task.xml"
    [IO.File]::WriteAllText($taskPath, $taskXml, ([System.Text.UTF8Encoding]::new($false)))
    $runnerSource = Join-Path $Repo "scripts\run_product_publish_task.cmd"
    $runnerCopy = Join-Path $folder "old-runner.cmd"
    Copy-Item -LiteralPath $runnerSource -Destination $runnerCopy -ErrorAction Stop
    $snapshotCopy = Join-Path $folder "public_snapshot.json"
    Copy-Item -LiteralPath $snapshot.Path -Destination $snapshotCopy -ErrorAction Stop

    $manifest = [ordered]@{
        schema_version = 1
        created_utc = [DateTime]::UtcNow.ToString("o")
        old_git_sha = $OldMain
        future_merged_git_sha = $MergedMain
        task_name = $TaskName
        task_path = $legacy.Task.TaskPath
        old_runner_blob = $OldRunnerBlob
        task_xml_sha256 = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash
        runner_sha256 = (Get-FileHash -LiteralPath $runnerCopy -Algorithm SHA256).Hash
        snapshot_sha256 = (Get-FileHash -LiteralPath $snapshotCopy -Algorithm SHA256).Hash
        snapshot_bytes = $snapshot.Bytes
        previous_task_state = "Ready"
    }
    if ($manifest.snapshot_sha256 -cne $snapshot.Sha256) {
        throw "STOP: current public snapshot changed while copying."
    }
    $manifestPath = Join-Path $folder "manifest.json"
    [IO.File]::WriteAllText(
        $manifestPath, ($manifest | ConvertTo-Json -Depth 4),
        ([System.Text.UTF8Encoding]::new($false))
    )
    $null = Verify-Evidence $folder
    Write-Host "PRIVATE_ROLLBACK_EVIDENCE=VERIFIED"
    Write-Host "PRIVATE_EVIDENCE_DIRECTORY=$folder"

    # Recheck the live evidence and quiet scheduler before mutation.
    $again = Get-Legacy
    if ([string]$again.Task.State -cne "Ready" -or
        $again.Info.NextRunTime.ToUniversalTime() -le ([DateTime]::UtcNow.AddMinutes(10)) -or
        (Get-SnapshotState).Sha256 -cne $snapshot.Sha256 -or
        (Normalized-TaskDefinitionHash (Get-TaskXML $TaskName)) -cne (Normalized-TaskDefinitionHash $taskXml)) {
        throw "STOP: live task/snapshot drifted before containment."
    }
    Assert-NoPublisherProcess

    Disable-ScheduledTask -TaskName $again.Task.TaskName -TaskPath $again.Task.TaskPath -ErrorAction Stop | Out-Null
    $disabled = Get-Legacy
    if ([string]$disabled.Task.State -cne "Disabled") {
        throw "INDETERMINATE: publisher task is not confirmed Disabled. Do not sync Git."
    }
    Assert-NoPublisherProcess
    if ((Get-SnapshotState).Sha256 -cne $snapshot.Sha256) {
        throw "INDETERMINATE: sanitized snapshot changed during containment. Do not sync Git."
    }
    Assert-ScannerHashes $scannerHashes
    Assert-OldProduction
    Write-Host "LEGACY_PRODUCT_PUBLISH_TASK_DISABLED=PASS"
    Write-Host "EXP031_PRE_SYNC_PUBLISHER_CONTAINMENT=PASS"
    Write-Host "NEXT_STEP=Require separate owner approval before Git sync"
    Write-Host "CLOUD_PUBLICATION=False"
    return
}

if ($Mode -eq "PreSyncRollback") {
    if ($Confirm -cne "APPROVE-EXP031-PRESYNC-ROLLBACK-ONLY") {
        throw "STOP: no separate rollback execution approval supplied."
    }
    if (-not $EvidenceDirectory) {
        throw "STOP: exact private rollback evidence directory required."
    }
    $m = Verify-Evidence $EvidenceDirectory
    if ([string]$legacy.Task.State -cne "Disabled" -or
        $m.task_path -cne $legacy.Task.TaskPath -or
        (Normalized-TaskDefinitionHash (Get-TaskXML $TaskName)) -cne
          (Normalized-TaskDefinitionHash ([IO.File]::ReadAllText((Join-Path $EvidenceDirectory "publisher-task.xml")))) -or
        (Get-SnapshotState).Sha256 -cne $m.snapshot_sha256) {
        throw "STOP: pre-sync rollback conditions do not hold. No task reenable."
    }
    Assert-NoPublisherProcess
    Enable-ScheduledTask -TaskName $legacy.Task.TaskName -TaskPath $legacy.Task.TaskPath -ErrorAction Stop | Out-Null
    $enabled = Get-Legacy
    if ([string]$enabled.Task.State -cne "Ready") {
        throw "INDETERMINATE: rollback enablement did not return Ready."
    }
    Assert-ScannerHashes $scannerHashes
    Assert-OldProduction
    Write-Host "EXP031_PRESYNC_ROLLBACK=PASS"
    Write-Host "GIT_SYNC=False"
    Write-Host "CLOUD_PUBLICATION=False"
}
