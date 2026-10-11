# EXP-031 GUARDED HOURLY SAME-TASK CUTOVER — PREPARATION ONLY.
# Observe is read-only; Stage and Enable require separate owner authorization.
[CmdletBinding()]
param(
    [ValidateSet("Observe","Stage","Enable")][string]$Mode = "Observe",
    [string]$Confirm = ""
)
$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Main = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
$Tree = "d24d3736d0bf6633ad0d05c4a1f1373558f813b9"
$TaskName = "TradingTop Product Publish"
$Rollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$StableDir = "C:\ProgramData\VowSig-EXP031-HourlyPublisher"
$StableFile = Join-Path $StableDir "guarded-task-runner.ps1"
$SourceFile = Join-Path $PSScriptRoot "exp031-guarded-hourly-task-runner-20261011.ps1"
$PSExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$NewArgs = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $StableFile + '"'
$OldArgs = '/c "' + (Join-Path $Repo "scripts\run_product_publish_task.cmd") + '"'
$SealPin = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$Scanners = @("SignalProof AI-v1.1 Shadow Scan", "VowSig AI-v1.2.1 Expansion Shadow Scan", "VowSig AI-v1.3 Crypto Shadow Scan")

function Demand([bool]$ok, [string]$message) {
    if (-not $ok) { throw "STOP: $message" }
}
function Sha([string]$path) {
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash
}
function Check-Git {
    $h = (& git -C $Repo rev-parse HEAD).Trim()
    $t = (& git -C $Repo rev-parse "HEAD^{tree}").Trim()
    $b = (& git -C $Repo symbolic-ref --short HEAD).Trim()
    $dirty = @(& git -C $Repo status --porcelain --untracked-files=all)
    Demand ($LASTEXITCODE -eq 0 -and $h -ceq $Main -and $t -ceq $Tree -and $b -ceq "main" -and $dirty.Count -eq 0) "production source is not clean exact merged release"
}
function Task-One([string]$name) {
    $found = @(Get-ScheduledTask -TaskName $name -ErrorAction Stop)
    Demand ($found.Count -eq 1) "missing/ambiguous task: $name"
    return $found[0]
}
function Check-Idle {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='cmd.exe' OR Name='python.exe' OR Name='pythonw.exe' OR Name='py.exe'" -ErrorAction Stop | Where-Object {
        $_.CommandLine -match 'run_product_publish_task\.cmd|run_product_publish_guarded_v0_1\.cmd|guarded_product_publish_v0_1\.py|export_public_snapshot\.py|push_public_snapshot\.py'
    })
    Demand ($procs.Count -eq 0) "publisher/export/upload process is running"
}
function Scan-Fingerprints {
    $d = [ordered]@{}
    foreach ($name in $Scanners) {
        $task = Task-One $name
        Demand ([string]$task.State -cne "Disabled") "independent scanner disabled: $name"
        $xml = [string](Export-ScheduledTask -TaskName $task.TaskName -TaskPath $task.TaskPath -ErrorAction Stop)
        $hash = [Security.Cryptography.SHA256]::Create()
        try { $d[$name] = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($xml))).Replace("-","") }
        finally { $hash.Dispose() }
    }
    return $d
}
function Check-Scanners($before) {
    $after = Scan-Fingerprints
    foreach ($name in $Scanners) { Demand ($after[$name] -ceq $before[$name]) "scanner definition changed: $name" }
}
function Check-Rollback {
    Demand (Test-Path -LiteralPath $Rollback -PathType Container) "original rollback directory absent"
    $m = Get-Content -LiteralPath (Join-Path $Rollback "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    Demand ($m.old_git_sha -ceq "47687d8d0e21523e417899a71dddc886ecf25d73" -and $m.future_merged_git_sha -ceq $Main -and $m.task_name -ceq $TaskName -and $m.snapshot_sha256 -ceq "9FA578CD23B09773B7CA3DA00C6FD37FB2027A57CEEE96CA8F85BE213DF59160") "rollback manifest changed"
    foreach ($pair in @(@("publisher-task.xml",[string]$m.task_xml_sha256), @("old-runner.cmd",[string]$m.runner_sha256), @("public_snapshot.json",[string]$m.snapshot_sha256))) {
        Demand ((Sha (Join-Path $Rollback $pair[0])) -ceq $pair[1]) "rollback evidence hash changed: $($pair[0])"
    }
}
function Check-Prior-Release {
    $seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
    $item = Get-Item -LiteralPath $seal -ErrorAction Stop
    Demand ($item.Length -eq 3048 -and (Sha $seal) -ceq $SealPin) "historic seal changed"
    $marker = Join-Path $Repo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
    Demand (Test-Path -LiteralPath $marker -PathType Leaf) "one-shot publication evidence absent"
    $snapshot = Get-Content -LiteralPath (Join-Path $Repo "data\public_snapshot.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $programs = @($snapshot.validation_programs)
    Demand ($programs.Count -eq 3) "last accepted snapshot missing third program"
    $ids = @($programs | ForEach-Object { $_.program_id } | Sort-Object -Unique)
    Demand (($ids -join ",") -ceq "core-ai-shadow,crypto-expansion-1,market-expansion-1") "program IDs changed"
    $crypto = @($programs | Where-Object { $_.program_id -ceq "crypto-expansion-1" })
    Demand ($crypto.Count -eq 1 -and $crypto[0].status -ceq "delayed" -and
        $crypto[0].title -like "*DELAYED*2026-10-11T12:07:21.257601+00:00*" -and
        $crypto[0].public_signal_exposure -eq $false -and
        $crypto[0].health.broker_execution_disabled -eq $true) "historical crypto is not explicitly DELAYED"
}
function Check-Task($task) {
    Demand ($task.TaskPath -ceq "\" -and $task.Triggers.Count -eq 1 -and
        [string]$task.Settings.MultipleInstances -ceq "IgnoreNew") "task identity/settings drifted"
}
function Old-Action($task) {
    return ($task.Actions.Count -eq 1 -and $task.Actions[0].Execute -ieq "cmd.exe" -and $task.Actions[0].Arguments -ceq $OldArgs)
}
function New-Action($task) {
    return ($task.Actions.Count -eq 1 -and $task.Actions[0].Execute -ieq $PSExe -and
        $task.Actions[0].Arguments -ceq $NewArgs -and $task.Actions[0].WorkingDirectory -ieq $Repo)
}
function Task-OtherXml {
    [xml]$xml = Export-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop
    $ns = New-Object Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
    $actions = $xml.SelectSingleNode("/t:Task/t:Actions", $ns)
    Demand ($null -ne $actions) "Task XML Actions missing"
    [void]$actions.ParentNode.RemoveChild($actions)
    return $xml.OuterXml
}
function Runner-Hash {
    Demand (Test-Path -LiteralPath $SourceFile -PathType Leaf) "handoff runner missing"
    return (Sha $SourceFile)
}
function Check-Stable {
    Demand (Test-Path -LiteralPath $StableFile -PathType Leaf) "installed runner missing"
    Demand ((Sha $StableFile) -ceq (Runner-Hash)) "installed guarded runner modified"
}
function Require-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    Demand ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) "administrator elevation required"
}

Check-Git
Check-Rollback
Check-Prior-Release
$scanBefore = Scan-Fingerprints
$task = Task-One $TaskName
Check-Task $task
Write-Host "EXP031_EXACT_RELEASE_AND_PRIOR_HISTORICAL_CARD=PASS"
Write-Host "PRODUCT_PUBLISHER_STATE=$($task.State)"
if (Old-Action $task) { Write-Host "PUBLISHER_ACTION=legacy" }
elseif (New-Action $task) { Write-Host "PUBLISHER_ACTION=guarded" }
else { throw "STOP: unexpected publisher action; no mutation" }

if ($Mode -eq "Observe") {
    Write-Host "EXP031_HOURLY_CUTOVER_READONLY_OBSERVE=PASS"
    Write-Host "TASK_MUTATION=False"
    Write-Host "CLOUD_PUBLICATION=False"
    return
}
Require-Admin
Check-Idle

if ($Mode -eq "Stage") {
    Demand ($Confirm -ceq "APPROVE-EXP031-STAGE-GUARDED-TASK-ONLY") "Stage not explicitly authorized"
    Demand ([string]$task.State -ceq "Disabled" -and (Old-Action $task)) "old action must be Disabled"
    Demand (-not (Test-Path -LiteralPath $StableDir)) "stable runner path already exists; no overwrite"
    Demand (Test-Path -LiteralPath $PSExe -PathType Leaf) "Windows PowerShell absent"
    $hash = Runner-Hash
    $beforeXml = Task-OtherXml
    New-Item -ItemType Directory -Path $StableDir -ErrorAction Stop | Out-Null
    & icacls.exe $StableDir /inheritance:r /grant:r '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-11:(OI)(CI)RX' | Out-Null
    Demand ($LASTEXITCODE -eq 0) "protected runner folder ACL failure"
    Copy-Item -LiteralPath $SourceFile -Destination $StableFile -ErrorAction Stop
    Check-Stable
    Demand ((Sha $StableFile) -ceq $hash) "runner copy changed"
    $fresh = Task-One $TaskName
    Demand ([string]$fresh.State -ceq "Disabled" -and (Old-Action $fresh)) "task changed during staging"
    $action = New-ScheduledTaskAction -Execute $PSExe -Argument $NewArgs -WorkingDirectory $Repo
    Set-ScheduledTask -TaskName $TaskName -TaskPath "\" -Action $action -ErrorAction Stop | Out-Null
    $after = Task-One $TaskName
    Demand ([string]$after.State -ceq "Disabled" -and (New-Action $after)) "INDETERMINATE: task action or Disabled state did not persist"
    Demand ((Task-OtherXml) -ceq $beforeXml) "INDETERMINATE: unrelated Task Scheduler XML changed"
    Check-Stable
    Check-Scanners $scanBefore
    Check-Git
    Write-Host "EXP031_GUARDED_SAME_TASK_STAGED=PASS"
    Write-Host "PRODUCT_PUBLISHER_STATE=Disabled"
    Write-Host "AUTOMATIC_PUBLICATION_RESUMED=False"
    return
}
if ($Mode -eq "Enable") {
    Demand ($Confirm -ceq "APPROVE-EXP031-ENABLE-GUARDED-HOURLY-ONLY") "Enable not explicitly authorized"
    Demand ([string]$task.State -ceq "Disabled" -and (New-Action $task)) "guarded task must first be staged and Disabled"
    Check-Stable
    $beforeXml = Task-OtherXml
    Enable-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop | Out-Null
    $after = Task-One $TaskName
    Demand ([string]$after.State -ceq "Ready" -and (New-Action $after)) "INDETERMINATE: guarded publisher not Ready"
    Demand ((Task-OtherXml) -ceq $beforeXml) "INDETERMINATE: unrelated task XML changed"
    Check-Scanners $scanBefore
    Write-Host "EXP031_GUARDED_HOURLY_RESUMED=PASS"
    Write-Host "FIRST_NATURAL_PUBLISH_CYCLE_PENDING=TRUE"
    Write-Host "MANUAL_RUN_SCHEDULED_TASK=False"
    return
}
