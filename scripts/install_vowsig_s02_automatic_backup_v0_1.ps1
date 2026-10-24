# Isolated daily S02 encrypted cloud backup installer. Run on Windows VPS only.
param(
 [Parameter(Mandatory=$true)][string]$Candidate,
 [Parameter(Mandatory=$true)][string]$ExpectedHead,
 [Parameter(Mandatory=$true)][string]$Live,
 [string]$TimeLocal = "04:15"
)
$ErrorActionPreference = "Stop"
$TaskName = "VowSig S02 Encrypted Dual Cloud Backup"
$Base = Join-Path $env:ProgramData "VowSig-S02-AutoBackup"
$Current = Join-Path $Base "current"
$State = Join-Path $Base "state"
$SeedPy = Join-Path $env:TEMP "vowsig-b3-env-26717b61f7\Scripts\python.exe"
$SeedSite = Join-Path $env:TEMP "vowsig-b3-env-26717b61f7\Lib\site-packages"
$SdkSite = Join-Path $env:TEMP "vowsig-exp042-sdk-d9ddba373d87\Lib\site-packages"
$Account = (whoami).Trim()
$Sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$Stage = Join-Path $Base ("staging-" + [guid]::NewGuid().ToString("N"))
$Published = $false
function Need([bool]$Condition,[string]$Message) { if (-not $Condition) { throw $Message } }
try {
 Need ($env:OS -eq "Windows_NT") "Windows VPS required"
 Need ($TimeLocal -match '^([01][0-9]|2[0-3]):[0-5][0-9]$') "Invalid local task time"
 Need (Test-Path -LiteralPath $SeedPy -PathType Leaf) "Existing B3 Python missing"
 Need (Test-Path -LiteralPath $SeedSite -PathType Container) "Existing B3 site-packages missing"
 Need (Test-Path -LiteralPath $SdkSite -PathType Container) "Existing pinned SDK missing"
 Need ((git -C $Candidate rev-parse HEAD).Trim() -ceq $ExpectedHead) "Candidate SHA mismatch"
 Need (@(git -C $Candidate status --porcelain).Count -eq 0) "Candidate dirty"
 Need ((git -C $Live branch --show-current).Trim() -ceq "main") "Production branch changed"
 Need (@(git -C $Live status --porcelain).Count -eq 0) "Production dirty"
 Need ((Split-Path -Path $Live -Leaf) -ieq "trading-signal-intelligence") "Wrong production checkout"
 Need (Test-Path -LiteralPath (Join-Path $Live "data\forward.sqlite") -PathType Leaf) "S02 source missing"
 Need ($null -eq (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)) "Backup task exists; refuse overwrite"
 Need (-not (Test-Path -LiteralPath $Current)) "Backup runtime exists; refuse overwrite"
 New-Item -Path $Base -ItemType Directory -Force | Out-Null
 & icacls.exe $Base /inheritance:r /grant:r "SYSTEM:(OI)(CI)F" ("*" + $Sid + ":(OI)(CI)F") | Out-Null
 Need ($LASTEXITCODE -eq 0) "Owner-only folder ACL failed"
 New-Item -ItemType Directory -Path $Stage -Force | Out-Null
 New-Item -ItemType Directory -Path $State -Force | Out-Null
 New-Item -ItemType Directory -Path (Join-Path $Stage "scripts") -Force | Out-Null
 Copy-Item -Path (Join-Path $Candidate "src") -Destination (Join-Path $Stage "src") -Recurse -Force
 foreach ($File in @("vowsig_s02_automatic_backup_v0_1.py", "run_vowsig_s02_automatic_backup_v0_1.ps1")) {
   Copy-Item -LiteralPath (Join-Path $Candidate ("scripts\" + $File)) -Destination (Join-Path $Stage ("scripts\" + $File)) -Force
 }
 & $SeedPy -m venv --copies (Join-Path $Stage ".venv")
 Need ($LASTEXITCODE -eq 0) "Stable isolated Python creation failed"
 $SiteDest = Join-Path $Stage ".venv\Lib\site-packages"
 Copy-Item -Path (Join-Path $SeedSite "*") -Destination $SiteDest -Recurse -Force
 Copy-Item -Path (Join-Path $SdkSite "*") -Destination $SiteDest -Recurse -Force
 $StagedPy = Join-Path $Stage ".venv\Scripts\python.exe"
 Need (Test-Path -LiteralPath $StagedPy -PathType Leaf) "Stable Python missing"
 $OldPath = $env:PYTHONPATH
 $OldNoUser = $env:PYTHONNOUSERSITE
 try {
  $env:PYTHONPATH = Join-Path $Stage "src"
  $env:PYTHONNOUSERSITE = "1"
  $Probe = @'
from importlib import metadata
from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1
from trading_signal_intelligence.recovery import windows_credential_manager_v0_1
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import boto3, sqlite3
pins={"boto3":"1.43.114","botocore":"1.43.114","s3transfer":"0.19.3","jmespath":"1.0.1"}
assert all(metadata.version(key) == version for key,version in pins.items())
print("STABLE_PYTHON_SDK=PASS")
'@
  $Probe | & $StagedPy -B -
  Need ($LASTEXITCODE -eq 0) "Stable Python SDK or source imports failed"
 }
 finally { $env:PYTHONPATH=$OldPath; $env:PYTHONNOUSERSITE=$OldNoUser }
 # Validate all 5 Windows vault entries BEFORE moving staging to current.
 $OldPath = $env:PYTHONPATH
 try {
  $env:PYTHONPATH = Join-Path $Stage "src"
  $Py = Join-Path $Stage ".venv\Scripts\python.exe"
  $App = Join-Path $Stage "scripts\vowsig_s02_automatic_backup_v0_1.py"
  $ResultText = (& $Py -B $App --readiness --repo-root $Live --state-dir $State | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0) "Scheduled vault and source readiness failed"
  $Result = $ResultText | ConvertFrom-Json
  Need ($Result.ready -eq $true) "Scheduled credential readiness is false"
 }
 finally { $env:PYTHONPATH=$OldPath }
 Write-Output "SCHEDULED_CREDENTIALS=READY"
 Move-Item -LiteralPath $Stage -Destination $Current
 $Published = $true
 # Verify relocated .venv operates from durable ProgramData, not TEMP.
 $OldPath = $env:PYTHONPATH
 try {
  $env:PYTHONPATH = Join-Path $Current "src"
  $ActivePy = Join-Path $Current ".venv\Scripts\python.exe"
  $ActiveApp = Join-Path $Current "scripts\vowsig_s02_automatic_backup_v0_1.py"
  $ActiveJson = (& $ActivePy -B $ActiveApp --readiness --repo-root $Live --state-dir $State | Out-String).Trim()
  Need ($LASTEXITCODE -eq 0) "Relocated stable runtime is not ready"
  Need (($ActiveJson | ConvertFrom-Json).ready -eq $true) "Relocated task vault unavailable"
 }
 finally { $env:PYTHONPATH=$OldPath }
 Write-Output "RELOCATED_STABLE_RUNTIME=PASS"
 $Runner = Join-Path $Current "scripts\run_vowsig_s02_automatic_backup_v0_1.ps1"
 $Action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME "powershell.exe") -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $Runner + '"')
 $Trigger = New-ScheduledTaskTrigger -Daily -At $TimeLocal
 $Principal = New-ScheduledTaskPrincipal -UserId $Account -LogonType Interactive -RunLevel Limited
 $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 25)
 Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Daily encrypted S02 AWS/B2 backup and independent restore; same logged-on user" -ErrorAction Stop | Out-Null
 $Task = Get-ScheduledTask -TaskName $TaskName
 $Info = Get-ScheduledTaskInfo -TaskName $TaskName
 Need ($Task.Principal.LogonType -eq "Interactive") "Scheduled task logon mode mismatch"
 Write-Output "AUTOMATIC_BACKUP_INSTALL=PASS"
 Write-Output ("TASK_NAME=" + $TaskName)
 Write-Output ("TASK_USER=" + $Account)
 Write-Output ("TASK_LOCAL_TIME=" + $TimeLocal)
 Write-Output ("TASK_NEXT_RUN=" + $Info.NextRunTime.ToString("o"))
 Write-Output "OLDER_AWS_AND_B2_BACKUPS=PRESERVED"
 Write-Output "RDP_DISCONNECT=SUPPORTED; WINDOWS_FULL_LOGOFF=NOT_SUPPORTED"

 # Run the actual new scheduled task once under its Interactive principal.
 # Confirm the new history record, not merely successful registration.
 $StartedAt = Get-Date
 Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
 Write-Output "FIRST_SCHEDULED_BACKUP=STARTED"
 $Completed = $false
 for ($i=0; $i -lt 60; $i++) {
   Start-Sleep -Seconds 3
   $TaskNow = Get-ScheduledTask -TaskName $TaskName
   $InfoNow = Get-ScheduledTaskInfo -TaskName $TaskName
   if ($InfoNow.LastRunTime -ge $StartedAt.AddSeconds(-5) -and
       $TaskNow.State -ne "Running") {
      $Completed = $true
      break
   }
 }
 if (-not $Completed) {
   Write-Output "FIRST_SCHEDULED_BACKUP=PENDING_CHECK_TASK_HISTORY"
 } else {
   $LogPath = Join-Path $State "history.jsonl"
   $Last = $null
   if (Test-Path -LiteralPath $LogPath -PathType Leaf) {
      $LogLine = Get-Content -LiteralPath $LogPath -Tail 1
      try { $Last = $LogLine | ConvertFrom-Json } catch { $Last = $null }
   }
   if ($InfoNow.LastTaskResult -eq 0 -and $null -ne $Last -and
       $Last.status -eq "BACKUP_AND_INDEPENDENT_DUAL_CLOUD_RECOVERY_VERIFIED") {
      Write-Output "FIRST_SCHEDULED_BACKUP=PASS"
      Write-Output ("NEW_BACKUP_ID=" + $Last.backup_id)
   } else {
      Write-Output "FIRST_SCHEDULED_BACKUP=HOLD_REVIEW_HISTORY_NO_AUTOMATIC_RETRY"
   }
 }
}
catch {
 Write-Output "AUTOMATIC_BACKUP_INSTALL=HOLD"
 Write-Output ("REASON=" + $_.Exception.Message)
 if (-not $Published -and (Test-Path -LiteralPath $Stage)) { Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue }
 throw
}
