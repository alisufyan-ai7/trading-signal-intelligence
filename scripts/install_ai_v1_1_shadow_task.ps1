param(
    [string]$TaskName = "SignalProof AI-v1.1 Shadow Scan",
    [string]$LegacyTaskName = "SignalProof AI-v1 Shadow Scan",
    [switch]$ConfirmActivatedRuntime
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmActivatedRuntime) {
    throw "Refusing AI-v1.1 task installation. Re-run with -ConfirmActivatedRuntime only after owner-approved v1.1 activation is committed and verified."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_ai_v1_1_shadow_task.cmd"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$verifier = Join-Path $repoRoot "scripts\verify_ai_v1_1_runtime.py"

if (-not (Test-Path $runner)) { throw "Task runner not found: $runner" }
if (-not (Test-Path $python)) { throw "Python venv executable not found: $python" }
if (-not (Test-Path $verifier)) { throw "Runtime verifier not found: $verifier" }

$existingV11 = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existingV11) {
    throw "AI-v1.1 task already exists. Stop for review rather than overwriting it."
}

$legacy = Get-ScheduledTask -TaskName $LegacyTaskName -ErrorAction SilentlyContinue
if ($null -eq $legacy) {
    throw "Legacy AI-v1.0 task must remain present and Disabled during v1.1 installation."
}
$legacyInfo = Get-ScheduledTaskInfo -TaskName $LegacyTaskName
if ([string]$legacy.State -eq "Running") {
    throw "Legacy AI-v1.0 task is still Running; refuse parallel v1.1 installation."
}
if ([string]$legacy.State -ne "Disabled") {
    throw "Legacy AI-v1.0 task must be Disabled before v1.1 installation. Current state: $($legacy.State)"
}

Write-Host "Verifying activation-only AI-v1.1 runtime before task registration..."
& $python $verifier --activation-only
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.1 activation/runtime verification failed. Scheduler was not installed."
}

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(2)
if ($nextRun -le $now) {
    $nextRun = $nextRun.AddHours(1)
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Activated SignalProof AI-v1.1 shadow inference with MT5 rates synchronization. H1 cadence near minute 02. Broker execution disabled."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$taskDef = Get-ScheduledTask -TaskName $TaskName

[pscustomobject]@{
    TaskName = $TaskName
    State = $taskDef.State
    NextRunTime = $taskInfo.NextRunTime
    LastRunTime = $taskInfo.LastRunTime
    LastTaskResult = $taskInfo.LastTaskResult
    Runner = $runner
    WorkingDirectory = $repoRoot
    LegacyTaskName = $LegacyTaskName
    LegacyTaskState = if ($null -ne $legacy) { [string]$legacy.State } else { "NotFound" }
    BrokerExecutionEnabled = $false
    Note = "Interactive logon required: keep this Windows user logged in and MT5 available."
} | Format-List
