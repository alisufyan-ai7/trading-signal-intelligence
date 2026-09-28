param(
    [string]$TaskName = "SignalProof AI-v1 Shadow Scan",
    [switch]$ConfirmActivatedRuntime
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmActivatedRuntime) {
    throw "Refusing task installation. Re-run with -ConfirmActivatedRuntime after the current AI-v1 activation anchor is committed and verified."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_ai_v1_shadow_task.cmd"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$verifier = Join-Path $repoRoot "scripts\verify_ai_v1_runtime.py"

if (-not (Test-Path $runner)) {
    throw "Task runner not found: $runner"
}
if (-not (Test-Path $python)) {
    throw "Python venv executable not found: $python"
}
if (-not (Test-Path $verifier)) {
    throw "Runtime verifier not found: $verifier"
}

Write-Host "Verifying activated AI-v1 runtime before task registration..."
& $python $verifier --activation-only
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1 activation/runtime verification failed. Scheduler was not installed."
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
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Activated SignalProof AI-v1.0 shadow inference. H1 cadence near minute 02. Broker execution disabled."

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
    BrokerExecutionEnabled = $false
    Note = "Interactive logon required: keep this Windows user logged in and MT5 available."
} | Format-List
