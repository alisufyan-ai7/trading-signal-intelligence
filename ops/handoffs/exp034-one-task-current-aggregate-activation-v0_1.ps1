# EXP-034 existing single guarded publisher: OBSERVE / owner-gated STAGE / ENABLE.
# NOT permission to run STAGE/ENABLE. No scheduler retiming, manual run,
# additional K5 scan, cloud POST or broker action from this script itself.
[CmdletBinding()]
param(
    [ValidateSet("Observe","Stage","Enable")][string]$Mode = "Observe",
    [string]$Confirm = ""
)
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$ExpectedHead = "b900796dd7075a31dd01c89639c9461ef9ee3fb1"
$TaskName = "TradingTop Product Publish"
$StableDir = "C:\ProgramData\VowSig-EXP031-HourlyPublisher"
$OldRunner = Join-Path $StableDir "guarded-task-runner.ps1"
$NewRunner = Join-Path $StableDir "current-aggregate-task-runner.ps1"
$Rollback = "C:\ProgramData\VowSig-EXP034-ActivationRollback-20261012"
$OldRollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$SourceRel = "ops/handoffs/exp034-current-crypto-aggregate-hourly-runner-v0_1.ps1"
$Source = Join-Path $Repo ($SourceRel.Replace("/", "\"))
$SourceBlob = "3992bb46df25d97678f30023324a9dfc4bf41038"
$PublisherBlob = "e3f153128d4c65c7c98cfba7427a6e892eca2e29"
$SealPin = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$PowerShellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$OldArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $OldRunner + '"'
$NewArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $NewRunner + '"'
$Scanners = @(
    "SignalProof AI-v1.1 Shadow Scan",
    "VowSig AI-v1.2.1 Expansion Shadow Scan",
    "VowSig AI-v1.3 Crypto Shadow Scan"
)

function Demand([bool]$Pass,[string]$Reason) {
    if (-not $Pass) { throw ("EXP034_ACTIVATION_HELD: " + $Reason) }
}
function Sha([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash
}
function GitOne([string[]]$GitParams) {
    $Lines = @(& git -C $Repo @GitParams)
    Demand ($LASTEXITCODE -eq 0 -and $Lines.Count -eq 1) "Git verification unavailable"
    return ([string]$Lines[0]).Trim()
}
function CheckSource {
    Demand ((GitOne @("branch","--show-current")) -ceq "main") "live branch differs"
    Demand ((GitOne @("rev-parse","HEAD")) -ceq $ExpectedHead) "live HEAD differs"
    $Dirty = @(& git -C $Repo status --porcelain --untracked-files=no)
    Demand ($LASTEXITCODE -eq 0 -and $Dirty.Count -eq 0) "live tracked checkout not clean"
    Demand ((GitOne @("rev-parse","HEAD:$SourceRel")) -ceq $SourceBlob) "new runner commit source mismatch"
    Demand ((GitOne @("hash-object","--path=$SourceRel","--",$Source)) -ceq $SourceBlob) "new runner disk source mismatch"
    Demand ((GitOne @("rev-parse","HEAD:scripts/guarded_product_publish_v0_1.py")) -ceq $PublisherBlob) "guarded publisher source mismatch"
}
function CheckSeal {
    $Seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
    $Marker = Join-Path $Repo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
    Demand (Test-Path -LiteralPath $Marker -PathType Leaf) "historic one-shot marker missing"
    Demand (Test-Path -LiteralPath $OldRollback -PathType Container) "original EXP-031 rollback missing"
    $Item = Get-Item -LiteralPath $Seal -ErrorAction Stop
    Demand ($Item.Length -eq 3048 -and (Sha $Seal) -ceq $SealPin) "historic DELAYED seal changed"
    $Snap = Get-Content -LiteralPath (Join-Path $Repo "data\public_snapshot.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $Crypto = @($Snap.validation_programs | Where-Object {$_.program_id -ceq "crypto-expansion-1"})
    Demand ($Crypto.Count -eq 1 -and $Crypto[0].status -ceq "delayed" -and
        $Crypto[0].public_signal_exposure -eq $false) "last local crypto publication is not historical DELAYED"
}
function CheckGlobalOff {
    foreach ($Scope in @("Process","User","Machine")) {
        Demand ([Environment]::GetEnvironmentVariable("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1",$Scope) -cne "1") "current crypto unexpectedly enabled outside task"
    }
}
function Task([string]$Name) {
    $FoundTasks = @(Get-ScheduledTask -TaskPath "\" -TaskName $Name -ErrorAction Stop)
    Demand ($FoundTasks.Count -eq 1) "scheduled task missing or ambiguous"
    return $FoundTasks[0]
}
function CheckPublisherTask([bool]$Staged) {
    $T = Task $TaskName
    Demand ($T.TaskPath -ceq "\" -and $T.Actions.Count -eq 1 -and
        $T.Triggers.Count -eq 1 -and
        [string]$T.Settings.MultipleInstances -ceq "IgnoreNew") "publisher task settings drifted"
    Demand ($T.Actions[0].Execute -ieq $PowerShellExe -and
        $T.Actions[0].WorkingDirectory -ieq $Repo) "publisher action differs"
    $ExpectedActionArguments = $OldArgs
    if ($Staged) { $ExpectedActionArguments = $NewArgs }
    Demand ($T.Actions[0].Arguments -ceq $ExpectedActionArguments) "publisher runner changed"
    $Trigger = $T.Triggers[0]
    Demand ($Trigger.StartBoundary -match 'T\d\d:05:00(?:\+00:00)?$' -and
        $Trigger.Repetition.Interval -ceq "PT1H") "original :05 hourly trigger changed"
    return $T
}
function OtherXml {
    [xml]$Doc = Export-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop
    $Mgr = New-Object Xml.XmlNamespaceManager($Doc.NameTable)
    $Mgr.AddNamespace("t","http://schemas.microsoft.com/windows/2004/02/mit/task")
    $Node = $Doc.SelectSingleNode("/t:Task/t:Actions",$Mgr)
    Demand ($null -ne $Node) "missing task action XML"
    [void]$Node.ParentNode.RemoveChild($Node)
    $Settings = $Doc.SelectSingleNode("/t:Task/t:Settings",$Mgr)
    Demand ($null -ne $Settings) "missing task settings XML"
    $Enabled = $Settings.SelectSingleNode("t:Enabled",$Mgr)
    if ($null -ne $Enabled) { [void]$Settings.RemoveChild($Enabled) }
    return $Doc.OuterXml
}
function StringSha([string]$Value) {
    $H = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($H.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value))).Replace("-","") }
    finally { $H.Dispose() }
}
function ScannerXml {
    $Result = @{}
    foreach ($Name in $Scanners) {
        $T = Task $Name
        Demand ([string]$T.State -ceq "Ready") "independent scanner not ready"
        $Result[$Name] = StringSha ([string](Export-ScheduledTask -TaskName $Name -TaskPath "\" -ErrorAction Stop))
    }
    return $Result
}
function CheckScanners($Before) {
    $After = ScannerXml
    foreach ($Name in $Scanners) {
        Demand ($Before[$Name] -ceq $After[$Name]) "independent scanner task definition changed"
    }
}
function CheckOldRunner {
    Demand (Test-Path -LiteralPath $OldRunner -PathType Leaf) "original EXP-031 runner absent"
    $Text = [IO.File]::ReadAllText($OldRunner)
    Demand ($Text.Contains("VOWSIG_GUARDED_PUBLISH_ENABLED") -and
        $Text.Contains("VOWSIG_CRYPTO_ASOF_ENABLED") -and
        $Text.Contains($SealPin) -and
        -not $Text.Contains("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1")) "original guarded runner drifted"
}
function CheckIdleAndWindow {
    $Info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath "\" -ErrorAction Stop
    Demand ($Info.LastTaskResult -eq 0) "publisher last result is not zero"
    foreach ($Name in @($Scanners + @($TaskName))) {
        $I = Get-ScheduledTaskInfo -TaskName $Name -TaskPath "\" -ErrorAction Stop
        Demand (($I.NextRunTime - (Get-Date)).TotalMinutes -gt 12) "a task is due in next 12 minutes"
        $OneTask = Task $Name
        Demand ([string]$OneTask.State -ceq "Ready") "another scheduled task is not ready"
    }
    $Processes = @(Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='powershell.exe' OR Name='python.exe' OR Name='pythonw.exe'" -ErrorAction Stop | Where-Object {
        $_.CommandLine -match 'run_product_publish_guarded_v0_1\.cmd|guarded_product_publish_v0_1\.py|push_public_snapshot\.py|export_guarded_'
    })
    Demand ($Processes.Count -eq 0) "publisher/export/upload already executing"
}
function DemandAdmin {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
    Demand ($Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) "administrator elevation required"
}
function CheckBackup {
    Demand (Test-Path -LiteralPath $Rollback -PathType Container) "new rollback package absent"
    $Manifest = Get-Content -LiteralPath (Join-Path $Rollback "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    Demand ($Manifest.production_head -ceq $ExpectedHead -and
        $Manifest.old_runner_sha256 -ceq (Sha $OldRunner) -and
        $Manifest.old_xml_sha256 -ceq (Sha (Join-Path $Rollback "original-task.xml")) -and
        $Manifest.saved_runner_sha256 -ceq (Sha (Join-Path $Rollback "old-runner.ps1")) -and
        $Manifest.new_runner_sha256 -ceq (Sha $NewRunner) -and
        $Manifest.other_xml_sha256 -ceq (StringSha (OtherXml))) "private recovery proof differs"
    return $Manifest
}

CheckSource
CheckSeal
CheckGlobalOff
CheckOldRunner
$BeforeScanners = ScannerXml
if ($Mode -eq "Observe") {
    $T = Task $TaskName
    $ExpectedStaged = [string]$T.State -ceq "Disabled"
    $T = CheckPublisherTask $ExpectedStaged
    if (-not $ExpectedStaged) {
        Demand ([string]$T.State -ceq "Ready") "publisher not Ready"
        Demand (-not (Test-Path -LiteralPath $NewRunner -PathType Leaf)) "unexpected new runner is already staged"
    } else {
        [void](CheckBackup)
    }
    CheckScanners $BeforeScanners
    Write-Output "EXP034_SAME_TASK_OBSERVE=PASS"
    Write-Output "EXP034_STAGING_STATE=$([string]$T.State)"
    Write-Output "EXP034_TASK_OR_LAUNCHER_MUTATION=FALSE"
    return
}
DemandAdmin
if ($Mode -eq "Stage") {
    Demand ($Confirm -ceq "APPROVE-EXP034-STAGE-SAME-TASK-ONLY") "Stage requires separate owner authorization"
    $T = CheckPublisherTask $false
    Demand ([string]$T.State -ceq "Ready") "old publisher not enabled and healthy"
    Demand (-not (Test-Path -LiteralPath $Rollback) -and
        -not (Test-Path -LiteralPath $NewRunner)) "staging already attempted"
    CheckIdleAndWindow
    $OriginalOtherHash = StringSha (OtherXml)
    $OriginalXml = [string](Export-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop)
    $OriginalRunnerHash = Sha $OldRunner
    New-Item -ItemType Directory -Path $Rollback -ErrorAction Stop | Out-Null
    & icacls.exe $Rollback /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
    Demand ($LASTEXITCODE -eq 0) "rollback folder ACL change failed"
    [IO.File]::WriteAllText((Join-Path $Rollback "original-task.xml"),$OriginalXml,[Text.Encoding]::UTF8)
    Copy-Item -LiteralPath $OldRunner -Destination (Join-Path $Rollback "old-runner.ps1") -ErrorAction Stop
    $Manifest = [ordered]@{
        production_head=$ExpectedHead
        task_name=$TaskName
        old_xml_sha256=(Sha (Join-Path $Rollback "original-task.xml"))
        old_runner_sha256=$OriginalRunnerHash
        saved_runner_sha256=(Sha (Join-Path $Rollback "old-runner.ps1"))
        other_xml_sha256=$OriginalOtherHash
        new_runner_sha256=(Sha $Source)
    }
    [IO.File]::WriteAllText((Join-Path $Rollback "manifest.json"),
        ($Manifest | ConvertTo-Json -Compress),[Text.Encoding]::UTF8)
    $T = CheckPublisherTask $false
    CheckIdleAndWindow
    Write-Output "EXP034_STAGE_MUTATION_START=TRUE"
    Disable-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop | Out-Null
    $ContainedTask = Task $TaskName
    Demand ([string]$ContainedTask.State -ceq "Disabled") "task containment uncertain"
    Copy-Item -LiteralPath $Source -Destination $NewRunner -ErrorAction Stop
    Demand ((Sha $NewRunner) -ceq $Manifest.new_runner_sha256) "new protected runner differs"
    Demand ((GitOne @("hash-object","--path=$SourceRel","--",$NewRunner)) -ceq $SourceBlob) "staged runner Git blob mismatch"
    $Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $NewArgs -WorkingDirectory $Repo
    Set-ScheduledTask -TaskName $TaskName -TaskPath "\" -Action $Action -ErrorAction Stop | Out-Null
    $T = CheckPublisherTask $true
    Demand ([string]$T.State -ceq "Disabled" -and (StringSha (OtherXml)) -ceq $OriginalOtherHash) "staged task changed unrelated settings"
    [void](CheckBackup)
    CheckScanners $BeforeScanners
    CheckSource
    Write-Output "EXP034_SAME_TASK_STAGED_DISABLED=PASS"
    Write-Output "EXP034_AUTOMATIC_PUBLICATION_PAUSED=TRUE"
    return
}
if ($Mode -eq "Enable") {
    Demand ($Confirm -ceq "APPROVE-EXP034-ENABLE-RECURRING-AGGREGATES") "Enable requires separate owner authorization"
    $T = CheckPublisherTask $true
    Demand ([string]$T.State -ceq "Disabled") "task not staged and disabled"
    [void](CheckBackup)
    Demand ((GitOne @("hash-object","--path=$SourceRel","--",$NewRunner)) -ceq $SourceBlob) "staged runner Git source differs"
    $OriginalOtherHash = StringSha (OtherXml)
    Write-Output "EXP034_ENABLE_MUTATION_START=TRUE"
    Enable-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop | Out-Null
    $T = CheckPublisherTask $true
    Demand ([string]$T.State -ceq "Ready" -and
        (StringSha (OtherXml)) -ceq $OriginalOtherHash) "task enable state/settings uncertain"
    [void](CheckBackup)
    CheckScanners $BeforeScanners
    CheckSource
    Write-Output "EXP034_SAME_TASK_CURRENT_AGGREGATE_ACTIVATED=PASS"
    Write-Output "EXP034_FIRST_NATURAL_HOURLY_CYCLE_PENDING=TRUE"
    Write-Output "EXP034_NO_MANUAL_PUBLISH_OR_K5_SCAN=TRUE"
    return
}
