param(
    [string]$TaskName = "TradingTop S02 XAU Forward Scan"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_s02_forward_task.cmd"

if (-not (Test-Path $runner)) {
    throw "Task runner not found: $runner"
}

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(2)
if ($nextRun -le $now) {
    $nextRun = $nextRun.AddHours(1)
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Frozen S02 v0.1 XAUUSD forward scanner. Runs hourly near minute 02."

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
    Note = "Interactive logon: keep this Windows user logged in and MT5 available."
} | Format-List
