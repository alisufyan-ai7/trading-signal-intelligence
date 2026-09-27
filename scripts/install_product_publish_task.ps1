param(
    [string]$TaskName = "TradingTop Product Publish"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_product_publish_task.cmd"
if (-not (Test-Path $runner)) { throw "Task runner not found: $runner" }

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(5)
if ($nextRun -le $now) { $nextRun = $nextRun.AddHours(1) }

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Exports derived TradingTop snapshot, sends optional Telegram alerts, and optionally pushes snapshot to cloud."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
$info = Get-ScheduledTaskInfo -TaskName $TaskName
$def = Get-ScheduledTask -TaskName $TaskName
[pscustomobject]@{
  TaskName = $TaskName
  State = $def.State
  NextRunTime = $info.NextRunTime
  LastRunTime = $info.LastRunTime
  LastTaskResult = $info.LastTaskResult
  Runner = $runner
} | Format-List
