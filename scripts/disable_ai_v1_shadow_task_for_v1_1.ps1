param(
    [string]$TaskName = "SignalProof AI-v1 Shadow Scan",
    [switch]$ConfirmCutover
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmCutover) {
    throw "Refusing AI-v1.0 task disable. Re-run with -ConfirmCutover only after the owner-approved cutover preconditions pass."
}

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName $TaskName

if ([string]$task.State -eq "Running") {
    throw "AI-v1.0 task is Running. Wait for it to finish and re-run the pre-cutover verification."
}
if ([string]$task.State -eq "Disabled") {
    throw "AI-v1.0 task is already Disabled. Stop for review rather than assuming cutover state."
}
if ([string]$task.State -ne "Ready") {
    throw "AI-v1.0 task must be Ready before disable. Current state: $($task.State)"
}

$before = [pscustomobject]@{
    TaskName = $task.TaskName
    State = [string]$task.State
    Description = $task.Description
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    NextRunTime = $info.NextRunTime
    Actions = @($task.Actions | ForEach-Object {
        [pscustomobject]@{
            Execute = $_.Execute
            Arguments = $_.Arguments
            WorkingDirectory = $_.WorkingDirectory
        }
    })
}

Disable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null

$afterTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$afterInfo = Get-ScheduledTaskInfo -TaskName $TaskName
if ([string]$afterTask.State -ne "Disabled") {
    throw "AI-v1.0 task disable verification failed. Current state: $($afterTask.State)"
}

[pscustomobject]@{
    cutover_action = "DISABLE_AI_V1_0_SCHEDULER"
    mutation_performed = $true
    task_name = $TaskName
    before_state = [string]$before.State
    after_state = [string]$afterTask.State
    before = $before
    after = [pscustomobject]@{
        TaskName = $afterTask.TaskName
        State = [string]$afterTask.State
        LastRunTime = $afterInfo.LastRunTime
        LastTaskResult = $afterInfo.LastTaskResult
        NextRunTime = $afterInfo.NextRunTime
    }
    broker_execution_enabled = $false
    next_required_step = "Finalize and commit AI-v1.0 retirement metadata before any AI-v1.1 activation."
} | ConvertTo-Json -Depth 8
