# VowSig public-staleness incident: READ ONLY / NO NETWORK / NO SECRETS.
# Four existing Windows tasks, safe numeric log markers, and local public snapshot.
$ErrorActionPreference = "Stop"
& {
  $Root=(Get-Location).Path
  if ((Split-Path $Root -Leaf) -ne "trading-signal-intelligence") { throw "BAD_REPO_ROOT" }
  $Now=[DateTime]::UtcNow
  $Names=[ordered]@{
    core="SignalProof AI-v1.1 Shadow Scan"
    expansion="VowSig AI-v1.2.1 Expansion Shadow Scan"
    crypto="VowSig AI-v1.3 Crypto Shadow Scan"
    publisher="TradingTop Product Publish"
  }
  $Logs=@{
    core="ai_v1_1_shadow.log"
    expansion="ai_v1_2_1_expansion_shadow.log"
    crypto="ai_v1_3_crypto_shadow.log"
    publisher="product_publish_guarded_v0_1.log"
  }
  $Report=[ordered]@{}
  $Issues=@()
  foreach($Role in $Names.Keys) {
    $Entry=[ordered]@{
      state="NOT_FOUND";last_task_result=$null;last_run_utc=$null;
      last_run_age_minutes=$null;next_run_utc=$null;log_present=$false;
      log_last_write_utc=$null;safe_run_exit=$null;safe_verify_exit=$null;
      safe_guarded_exit=$null
    }
    try {
      $Task=Get-ScheduledTask -TaskName $Names[$Role] -ErrorAction Stop
      $Info=Get-ScheduledTaskInfo -TaskName $Names[$Role] -ErrorAction Stop
      $Entry.state=[string]$Task.State
      $Entry.last_task_result=[long]$Info.LastTaskResult
      if($Info.LastRunTime.Year -ge 2025) {
        $UTC=$Info.LastRunTime.ToUniversalTime()
        $Entry.last_run_utc=$UTC.ToString("o")
        $Entry.last_run_age_minutes=[math]::Round(($Now-$UTC).TotalMinutes,1)
      }
      if($Info.NextRunTime.Year -ge 2025) {
        $Entry.next_run_utc=$Info.NextRunTime.ToUniversalTime().ToString("o")
      }
    } catch {
      $Entry.state="TASK_READ_UNAVAILABLE"
    }
    $Log=Join-Path (Join-Path $Root "data\forward-task-logs") $Logs[$Role]
    if(Test-Path -LiteralPath $Log -PathType Leaf) {
      $Entry.log_present=$true
      $Entry.log_last_write_utc=(Get-Item -LiteralPath $Log).LastWriteTimeUtc.ToString("o")
      # Log contents are private. Only numeric wrapper exit markers leave this process.
      $Tail=@(Get-Content -LiteralPath $Log -Tail 160 -ErrorAction Stop)
      foreach($Line in $Tail) {
        if($Line -match '(?i)\brun_exit=(\d+)\s+verify_exit=(\d+|SKIPPED)') {
          $Entry.safe_run_exit=[int]$Matches[1]
          $Entry.safe_verify_exit=[string]$Matches[2]
        }
        if($Line -match '(?i)\bguarded_exit=(\d+)') {
          $Entry.safe_guarded_exit=[int]$Matches[1]
        }
        if($Line -match '(?i)\bexport_exit=(\d+)\s+alert_exit=(\d+)\s+push_exit=(\d+)') {
          $Entry.safe_run_exit=[int]$Matches[1]
          $Entry.safe_verify_exit="LEGACY_PUSH_"+$Matches[3]
        }
      }
    }
    if($Entry.state -notin @("Ready","Running")) { $Issues+=($Role+":TASK_UNAVAILABLE_OR_DISABLED") }
    if($null -ne $Entry.last_task_result -and $Entry.last_task_result -ne 0) { $Issues+=($Role+":TASK_NONZERO_EXIT") }
    if($null -ne $Entry.safe_run_exit -and $Entry.safe_run_exit -ne 0) { $Issues+=($Role+":RUN_NONZERO_EXIT") }
    if($null -ne $Entry.safe_guarded_exit -and $Entry.safe_guarded_exit -ne 0) { $Issues+=($Role+":PUBLISH_HELD") }
    if($null -ne $Entry.last_run_age_minutes -and $Entry.last_run_age_minutes -gt 180) { $Issues+=($Role+":LAST_RUN_OLDER_THAN_3H") }
    $Report[$Role]=$Entry
  }
  $Local=[ordered]@{present=$false;generated_at_utc=$null;age_minutes=$null;core_inferences=$null;core_exits=$null;state="MISSING"}
  $Snap=Join-Path $Root "data\public_snapshot.json"
  if(Test-Path -LiteralPath $Snap -PathType Leaf) {
    $Local.present=$true
    try {
      $Body=Get-Content -LiteralPath $Snap -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
      $Time=[DateTimeOffset]::Parse([string]$Body.generated_at_utc).UtcDateTime
      $Local.generated_at_utc=$Time.ToString("o")
      $Local.age_minutes=[math]::Round(($Now-$Time).TotalMinutes,1)
      $Local.core_inferences=$Body.ai_v1.totals.valid_inferences
      $Local.core_exits=$Body.ai_v1.totals.completed_shadow_trades
      $Local.state="READ_OK"
      if($Local.age_minutes -ge 150) { $Issues+="LOCAL_SNAPSHOT_STALE_150MIN" }
    } catch {
      $Local.state="MALFORMED_OR_UNAVAILABLE"
      $Issues+="LOCAL_SNAPSHOT_UNREADABLE"
    }
  }
  # Existing private frozen copies, never the mutable AI writer databases.
  $Frozen=Join-Path $env:LOCALAPPDATA "VowSig\OriginalLedgerEvidence-20261105T031248Z-9bc9e41817b3\freeze-20261105T031251Z-de2b076d5d36"
  $CoreErrorEvidence=[ordered]@{status="NOT_CHECKED";rows=@()}
  $Python=Join-Path $Root ".venv\Scripts\python.exe"
  if((Test-Path -LiteralPath $Frozen -PathType Container) -and
     (Test-Path -LiteralPath $Python -PathType Leaf)) {
    $Probe=@'
import json,sqlite3,sys,re
from contextlib import closing
from pathlib import Path
frozen=Path(sys.argv[1])
sources=(("XAUUSD","ai_v1_1_xauusd.sqlite"),
         ("USTEC","ai_v1_1_ustec.sqlite"),
         ("US30","ai_v1_1_us30.sqlite"))
allowed={"OpenAIHTTPError","TimeoutError","ConnectionError","HTTPError"}
safe=[]
try:
    if frozen.is_symlink() or not frozen.is_dir():
        raise ValueError()
    for market,name in sources:
        file=frozen/name
        if file.is_symlink() or not file.is_file() or file.resolve().parent!=frozen.resolve():
            raise ValueError()
        with closing(sqlite3.connect(file.resolve().as_uri()+"?mode=ro&immutable=1",
                                     uri=True,timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            row=db.execute(
                "SELECT recorded_at_utc,payload_json FROM ai_records "
                "WHERE record_type='ERROR' ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        if not row:
            safe.append({"market":market,"category":"NO_FROZEN_ERROR"})
            continue
        data=json.loads(row[1])
        klass=data.get("error_class")
        raw=str(data.get("sanitized_message") or "")
        stage=data.get("stage")
        if klass not in allowed: klass="OTHER"
        if stage not in ("provider_inference","crypto_execution_cost_context"):
            stage="OTHER"
        if klass=="OpenAIHTTPError" and ("API_KEY_INVALID" in raw.upper() or
            re.search(r"\b401\b",raw)):
            category="OPENAI_AUTH_401"
        elif klass=="OpenAIHTTPError" and re.search(r"\b429\b",raw):
            category="OPENAI_RATE_429"
        elif klass=="OpenAIHTTPError":
            category="OPENAI_OTHER_HTTP"
        elif klass=="TimeoutError":
            category="TIMEOUT"
        else:
            category="OTHER"
        safe.append({"market":market,"latest_frozen_error_utc":row[0],
                     "stage":stage,"error_class":klass,"category":category})
    print(json.dumps({"status":"FROZEN_CORE_LAST_ERROR_CATEGORIES_ONLY",
                      "rows":safe,"raw_error_messages_exported":False},sort_keys=True))
except Exception:
    print(json.dumps({"status":"FROZEN_ERROR_PROBE_HELD",
                      "rows":[],"raw_error_messages_exported":False}))
'@
    $Raw=$Probe | & $Python -B - $Frozen
    if($LASTEXITCODE -eq 0) {
      try { $CoreErrorEvidence=$Raw | ConvertFrom-Json -ErrorAction Stop }
      catch { $CoreErrorEvidence=[ordered]@{status="BAD_PROBE_OUTPUT";rows=@()} }
    }
  }
  [ordered]@{
    schema="vowsig-staleness-triage-v0.1";observed_at_utc=$Now.ToString("o");
    read_only=$true;network_calls=0;task_changes=0;raw_logs_or_secrets_exported=$false;
    website_hosted_health_not_checked=$true;root_cause_verified=$false;
    tasks=$Report;local_snapshot=$Local;frozen_core_errors=$CoreErrorEvidence;issue_codes=@($Issues)
  } | ConvertTo-Json -Depth 8 -Compress
  Write-Host "VOWSIG_PUBLIC_STALENESS_TRIAGE=COMPLETED_READ_ONLY"
}