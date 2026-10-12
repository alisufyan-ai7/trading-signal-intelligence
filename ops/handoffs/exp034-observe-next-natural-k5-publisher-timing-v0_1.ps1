# EXP034 ONE NATURAL H1 K5 -> guarded publisher observation, READ ONLY.
# No private K5 data, Task Scheduler modification, task trigger, secret, or HTTP POST.
# Run in existing VPS PowerShell before next hourly K5 :04 cycle.
[CmdletBinding()]
param([int]$MaxWaitMinutes = 80)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$Head = "b900796dd7075a31dd01c89639c9461ef9ee3fb1"
$K5 = "VowSig AI-v1.3 Crypto Shadow Scan"
$Publisher = "TradingTop Product Publish"
$Log = Join-Path $Repo "data\forward-task-logs\product_publish_guarded_v0_1.log"
$PollSeconds = 2
$Utc = [datetime]::UtcNow

function Hold([string]$Reason) { throw ("EXP034_TIMING_OBSERVATION_HELD: " + $Reason) }
function Read-Task([string]$TaskName) {
    $Job = Get-ScheduledTask -TaskName $TaskName -TaskPath "\" -ErrorAction Stop
    $Info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath "\" -ErrorAction Stop
    return [pscustomobject]@{
        State = [string]$Job.State
        LastResult = [int64]$Info.LastTaskResult
        LastUtc = [datetime]$Info.LastRunTime.ToUniversalTime()
        NextUtc = [datetime]$Info.NextRunTime.ToUniversalTime()
        ActionArguments = [string]$Job.Actions[0].Arguments
    }
}
function Format-Utc([datetime]$Value) {
    return $Value.ToString("yyyy-MM-ddTHH:mm:ss.fffZ",[Globalization.CultureInfo]::InvariantCulture)
}

if ($MaxWaitMinutes -lt 10 -or $MaxWaitMinutes -gt 80) {
    Hold "bounded 10 to 80 minute watch required"
}
$Actual = @(& git -C $Repo rev-parse HEAD)
if ($LASTEXITCODE -ne 0 -or $Actual.Count -ne 1 -or ([string]$Actual[0]).Trim() -cne $Head) {
    Hold "live source does not match approved release"
}
$JobK5 = Read-Task $K5
$JobPub = Read-Task $Publisher
if ($JobK5.State -cne "Ready" -or $JobPub.State -cne "Ready" -or
    $JobK5.LastResult -ne 0 -or $JobPub.LastResult -ne 0 -or
    $JobPub.ActionArguments -notlike "*current-aggregate-task-runner.ps1*") {
    Hold "existing tasks are not Ready/successful/current aggregate launcher"
}
$K5Target = $JobK5.NextUtc
$PubTarget = $JobPub.NextUtc
if ($K5Target -le $Utc -or $PubTarget -le $K5Target -or
    ($PubTarget - $K5Target).TotalSeconds -ne 61 -or
    ($K5Target - $Utc).TotalMinutes -gt $MaxWaitMinutes -or
    $K5Target.Minute -ne 4 -or $PubTarget.Minute -ne 5) {
    Hold "not before the same expected natural :04/:05 cycle"
}
$Deadline = $PubTarget.AddMinutes(8)
$PriorK5Last = $JobK5.LastUtc
$PriorPubLast = $JobPub.LastUtc

Write-Output "EXP034_NATURAL_K5_TARGET_UTC=$(Format-Utc $K5Target)"
Write-Output "EXP034_NATURAL_PUBLISH_TARGET_UTC=$(Format-Utc $PubTarget)"
Write-Output "EXP034_TIMING_OBSERVER_READ_ONLY=TRUE"
Write-Output "EXP034_NO_TASK_START_OR_SCHEDULE_EDIT=TRUE"

$FirstK5Running = $null
$FirstK5Ready = $null
$FirstPubRunning = $null
$FirstPubReady = $null
$K5RunningAfterPub = $false
$K5ReadyBeforePub = $false
$K5Result = $null
$PubResult = $null
$Samples = 0

while ([datetime]::UtcNow -le $Deadline) {
    $Now = [datetime]::UtcNow
    # Sleeping until just before the natural K5 trigger is not a task mutation.
    $UntilStart = ($K5Target - $Now).TotalSeconds
    if ($UntilStart -gt 35) {
        Start-Sleep -Seconds ([int][Math]::Min(50, [Math]::Floor($UntilStart - 30)))
        continue
    }
    $K = Read-Task $K5
    $P = Read-Task $Publisher
    $ObservedAt = [datetime]::UtcNow
    $Samples++

    $KRan = $K.LastUtc -ge $K5Target.AddSeconds(-2) -and $K.LastUtc -gt $PriorK5Last
    $PRan = $P.LastUtc -ge $PubTarget.AddSeconds(-2) -and $P.LastUtc -gt $PriorPubLast

    if ($KRan -and $K.State -eq "Running" -and $null -eq $FirstK5Running) {
        $FirstK5Running = $ObservedAt
    }
    if ($KRan -and $K.State -eq "Running" -and $ObservedAt -ge $PubTarget) {
        $K5RunningAfterPub = $true
    }
    if ($KRan -and $K.State -eq "Ready" -and $K.LastResult -eq 0 -and
        $null -eq $FirstK5Ready) {
        $FirstK5Ready = $ObservedAt
        $K5Result = $K.LastResult
        if ($ObservedAt -lt $PubTarget) { $K5ReadyBeforePub = $true }
    }
    if ($PRan -and $P.State -eq "Running" -and $null -eq $FirstPubRunning) {
        $FirstPubRunning = $ObservedAt
    }
    if ($PRan -and $P.State -eq "Ready" -and $null -eq $FirstPubReady) {
        $FirstPubReady = $ObservedAt
        $PubResult = $P.LastResult
    }
    # The read-only observation is complete after both tasks return Ready.
    if ($null -ne $FirstK5Ready -and $null -ne $FirstPubReady) {
        break
    }
    Start-Sleep -Seconds $PollSeconds
}

$Fields = [ordered]@{
    EXP034_K5_RUNNING_FIRST_OBSERVED_UTC = $FirstK5Running
    EXP034_K5_READY_SUCCESS_FIRST_OBSERVED_UTC = $FirstK5Ready
    EXP034_PUBLISHER_RUNNING_FIRST_OBSERVED_UTC = $FirstPubRunning
    EXP034_PUBLISHER_READY_FIRST_OBSERVED_UTC = $FirstPubReady
}
foreach ($Field in $Fields.Keys) {
    $At = $Fields[$Field]
    if ($null -eq $At) { Write-Output "$Field=NOT_OBSERVED" }
    else { Write-Output "$Field=$(Format-Utc $At)" }
}
Write-Output "EXP034_K5_READY_BEFORE_PUBLISHER_TARGET=$($K5ReadyBeforePub.ToString().ToUpperInvariant())"
Write-Output "EXP034_K5_RUNNING_AFTER_PUBLISHER_TARGET=$($K5RunningAfterPub.ToString().ToUpperInvariant())"
Write-Output "EXP034_OBSERVATION_SAMPLES=$Samples"
if ($null -ne $FirstK5Ready) {
    Write-Output "EXP034_K5_COMPLETION_RESULT_OBSERVED=$K5Result"
}
if ($null -ne $FirstPubReady) {
    Write-Output "EXP034_PUBLISHER_COMPLETION_RESULT_OBSERVED=$PubResult"
}

# ONLY read the last publisher log segment; output allowlisted markers, never
# print raw logfile lines or private K5 report/ledger contents.
if ($null -ne $FirstPubReady -and (Test-Path -LiteralPath $Log -PathType Leaf)) {
    $Lines = @(Get-Content -LiteralPath $Log -Tail 240 -ErrorAction Stop)
    $LastHeader = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i] -match '^===== Guarded publisher start .{0,64} =====$') {
            $LastHeader = $i
        }
    }
    if ($LastHeader -ge 0) {
        $SafeSegment = @($Lines | Select-Object -Skip ($LastHeader + 1) |
            Where-Object { $_ -match '^(CRYPTO_CURRENT_AGGREGATE=HELD|guarded_exit=[0-9]+|alert_exit=[0-9]+)$' })
        Write-Output "EXP034_LAST_PUBLISHER_LOG_SEGMENT=FOUND"
        foreach ($Line in $SafeSegment) { Write-Output "EXP034_SAFE_LOG_MARKER=$Line" }
    } else {
        Write-Output "EXP034_LAST_PUBLISHER_LOG_SEGMENT=UNAVAILABLE"
    }
}

if ($null -eq $FirstPubReady -or $null -eq $FirstK5Ready) {
    Write-Output "EXP034_NATURAL_COMPLETION_EVIDENCE=INCOMPLETE"
} elseif ($K5RunningAfterPub) {
    Write-Output "EXP034_NATURAL_COMPLETION_EVIDENCE=K5_RUNNING_AFTER_PUBLISHER_START"
} elseif ($K5ReadyBeforePub) {
    Write-Output "EXP034_NATURAL_COMPLETION_EVIDENCE=K5_READY_BEFORE_PUBLISHER_START"
} else {
    Write-Output "EXP034_NATURAL_COMPLETION_EVIDENCE=INSUFFICIENT_TO_ORDER"
}
Write-Output "EXP034_READ_ONLY_TIMING_OBSERVATION_COMPLETE=TRUE"
