param(
    [string]$TaskName = "VowSig AI-v1.2 Expansion Shadow Scan",
    [string]$ParallelTaskName = "SignalProof AI-v1.1 Shadow Scan",
    [switch]$ConfirmActivatedRuntime
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmActivatedRuntime) {
    throw "Refusing AI-v1.2 task installation. Re-run with -ConfirmActivatedRuntime only after owner-approved AI-v1.2 activation is committed and verified."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_ai_v1_2_shadow_task.cmd"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$verifier = Join-Path $repoRoot "scripts\verify_ai_v1_2_runtime.py"

if (-not (Test-Path $runner)) { throw "Task runner not found: $runner" }
if (-not (Test-Path $python)) { throw "Python venv executable not found: $python" }
if (-not (Test-Path $verifier)) { throw "Runtime verifier not found: $verifier" }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    throw "AI-v1.2 expansion task already exists. Stop for review rather than overwriting it."
}

$parallel = Get-ScheduledTask -TaskName $ParallelTaskName -ErrorAction SilentlyContinue
if ($null -eq $parallel) {
    throw "Parallel AI-v1.1 task must exist before AI-v1.2 installation."
}
$parallelInfo = Get-ScheduledTaskInfo -TaskName $ParallelTaskName
if ([string]$parallel.State -notin @("Ready", "Running")) {
    throw "Parallel AI-v1.1 task must be Ready or Running. Current state: $($parallel.State)"
}
if ([int64]$parallelInfo.LastTaskResult -ne 0) {
    throw "Parallel AI-v1.1 task last result must be 0. Current: $($parallelInfo.LastTaskResult)"
}

Write-Host "Verifying activation-only AI-v1.2 runtime before task registration..."
& $python $verifier --activation-only
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.2 activation/runtime verification failed. Scheduler was not installed."
}

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(3)
if ($nextRun -le $now) {
    $nextRun = $nextRun.AddHours(1)
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "VowSig AI-v1.2 parallel expansion shadow inference for EURUSD/XAGUSD/USOIL. Hourly near minute 03. AI-v1.1 remains active. Broker execution disabled."

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
    ParallelTaskName = $ParallelTaskName
    ParallelTaskState = [string]$parallel.State
    ParallelTaskLastResult = [int64]$parallelInfo.LastTaskResult
    ScheduledMinute = 3
    PublicExposureEnabled = $false
    BrokerExecutionEnabled = $false
    Note = "Interactive logon required: keep this Windows user logged in and MT5 available."
} | Format-List
