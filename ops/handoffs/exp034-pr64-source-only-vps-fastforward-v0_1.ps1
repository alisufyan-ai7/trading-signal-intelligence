# EXP034 PR64 — controlled VPS SOURCE-ONLY fast-forward; no task edits or runs.
# Owner-authorized mutation: git fetch + ONE git merge --ff-only old main -> PR64 merge.
# Source changes are 3 tested files; all tasks, ProgramData launchers and K5 ledgers remain untouched.
[CmdletBinding()]
param(
    [string]$Confirm = ""
)
$ErrorActionPreference = "Stop"

$VsgRepo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$VsgOld = "b900796dd7075a31dd01c89639c9461ef9ee3fb1"
$VsgNew = "bc1e7ff4f8afebee953f6c62c5eac70c563162ad"
$VsgExpectedTree = "12afcfe19ee7e1acf5f0b63140768b198a1d90f8"
$VsgPublisher = "TradingTop Product Publish"
$VsgNewRunner = "C:\ProgramData\VowSig-EXP031-HourlyPublisher\current-aggregate-task-runner.ps1"
$VsgOldRunner = "C:\ProgramData\VowSig-EXP031-HourlyPublisher\guarded-task-runner.ps1"
$VsgRollback = "C:\ProgramData\VowSig-EXP034-ActivationRollback-20261012"
$VsgHistoricalRollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$VsgSeal = Join-Path $VsgRepo "data\crypto-research-asof-v0.1.json"
$VsgMarker = Join-Path $VsgRepo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
$VsgSealSha = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"
$VsgTaskNames = @(
    "SignalProof AI-v1.1 Shadow Scan",
    "VowSig AI-v1.2.1 Expansion Shadow Scan",
    "VowSig AI-v1.3 Crypto Shadow Scan",
    "TradingTop Product Publish"
)
$VsgModifiedPins = [ordered]@{
    "scripts/guarded_product_publish_v0_1.py" = "98363fb8a0122f560a468063fed1329987ebb130"
    "tests/test_guarded_crypto_current_aggregate_v0_1.py" = "4590ded706da1776e01b151fbc8359fb21a074ec"
    "tests/test_guarded_product_publish_v0_1.py" = "435e296d1cf512ada0f715ae0f4c5b386ebae418"
}
$VsgFrozenPins = [ordered]@{
    "src/trading_signal_intelligence/ai_v1/observability.py" = "b4ba334e6c7c2e54c301251268f5bfe2746c75cd"
    "src/trading_signal_intelligence/ai_v1/crypto_observability_v1_3.py" = "c974d65354ccc17060e0e1c6a85d1e7d9237281e"
    "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py" = "afba5b93cfeb1f849f70f242f137bd16bd24fd6d"
    "config/ai_v1_3_crypto_review_gates.json" = "e74e4102ec71fdea362a460130bcadee61e1777e"
    "src/trading_signal_intelligence/product/crypto_epoch_source_producer_v0_1.py" = "dc0e6637e0cdcd16fbac554e76842c79d254cdeb"
    "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py" = "0f7c6a3af73ee3c5669e114b8903121cc1161397"
    "scripts/run_product_publish_guarded_v0_1.cmd" = "7fb2dea42cd0ac2bbe3239d9bd364c35106a8231"
    "ops/handoffs/exp034-current-crypto-aggregate-hourly-runner-v0_1.ps1" = "3992bb46df25d97678f30023324a9dfc4bf41038"
}

function VsgDemand([bool]$Ok, [string]$Message) {
    if (-not $Ok) { throw ("EXP034_PR64_SOURCE_SYNC_HELD: " + $Message) }
}
function VsgGit([string[]]$Parts) {
    $Lines = @(& git -C $VsgRepo @Parts)
    VsgDemand ($LASTEXITCODE -eq 0 -and $Lines.Count -eq 1) "Git verification unavailable"
    return ([string]$Lines[0]).Trim()
}
function VsgCheckHead([string]$Sha) {
    VsgDemand ((VsgGit @("branch","--show-current")) -ceq "main") "live branch not main"
    VsgDemand ((VsgGit @("rev-parse","HEAD")) -ceq $Sha) "unexpected live commit"
    $Status = @(& git -C $VsgRepo status --porcelain --untracked-files=no)
    VsgDemand ($LASTEXITCODE -eq 0 -and $Status.Count -eq 0) "tracked working tree not clean"
}
function VsgCheckBlob([string]$Relative,[string]$Pin) {
    $Disk = Join-Path $VsgRepo ($Relative.Replace("/","\"))
    VsgDemand (Test-Path -LiteralPath $Disk -PathType Leaf) "source path missing"
    VsgDemand ((VsgGit @("rev-parse","HEAD:$Relative")) -ceq $Pin) "committed blob mismatch"
    VsgDemand ((VsgGit @("hash-object","--path=$Relative","--",$Disk)) -ceq $Pin) "on-disk blob mismatch"
}
function VsgCheckFrozen {
    foreach ($P in $VsgFrozenPins.Keys) {
        VsgCheckBlob $P ([string]$VsgFrozenPins[$P])
    }
    VsgDemand (([Environment]::GetEnvironmentVariable(
        "VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1","Process")) -cne "1") "global process opt-in enabled"
    foreach ($Scope in @("User","Machine")) {
        VsgDemand (([Environment]::GetEnvironmentVariable(
            "VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1",$Scope)) -cne "1") "global opt-in enabled"
    }
}
function VsgCheckPrivateRecovery {
    VsgDemand (Test-Path -LiteralPath $VsgNewRunner -PathType Leaf) "EXP034 successor launcher missing"
    VsgDemand (Test-Path -LiteralPath $VsgOldRunner -PathType Leaf) "EXP031 original launcher missing"
    VsgDemand (Test-Path -LiteralPath $VsgRollback -PathType Container) "EXP034 rollback absent"
    VsgDemand (Test-Path -LiteralPath $VsgHistoricalRollback -PathType Container) "EXP031 rollback absent"
    VsgDemand (Test-Path -LiteralPath $VsgMarker -PathType Leaf) "historic publication marker absent"
    $SealItem = Get-Item -LiteralPath $VsgSeal -ErrorAction Stop
    VsgDemand ($SealItem.Length -eq 3048 -and
        (Get-FileHash -LiteralPath $VsgSeal -Algorithm SHA256).Hash -ceq $VsgSealSha) "historic seal changed"
    $Manifest = Get-Content -LiteralPath (Join-Path $VsgRollback "manifest.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    VsgDemand ($Manifest.production_head -ceq $VsgOld) "rollback manifest production version changed"
    VsgDemand ((Get-FileHash -LiteralPath $VsgNewRunner -Algorithm SHA256).Hash -ceq
        $Manifest.new_runner_sha256) "installed current launcher hash drift"
    VsgDemand ((Get-FileHash -LiteralPath $VsgOldRunner -Algorithm SHA256).Hash -ceq
        $Manifest.old_runner_sha256) "original launcher hash drift"
    $Body = [IO.File]::ReadAllText($VsgNewRunner)
    VsgDemand ($Body.Contains("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1") -and
        $Body.Contains("guarded_product_publish_v0_1.py")) "successor launcher contract differs"
}
function VsgTasks([bool]$Quiet) {
    $Xml = @{}
    foreach ($Name in $VsgTaskNames) {
        $Jobs = @(Get-ScheduledTask -TaskName $Name -TaskPath "\" -ErrorAction Stop)
        VsgDemand ($Jobs.Count -eq 1 -and [string]$Jobs[0].State -ceq "Ready") "scheduled task not uniquely Ready"
        $Info = Get-ScheduledTaskInfo -TaskName $Name -TaskPath "\" -ErrorAction Stop
        VsgDemand ([int64]$Info.LastTaskResult -eq 0) "task last run not successful"
        if ($Quiet) {
            VsgDemand (($Info.NextRunTime - (Get-Date)).TotalMinutes -gt 12) "wait for quiet window (>12 minutes until next task)"
        }
        $Xml[$Name] = [string](Export-ScheduledTask -TaskName $Name -TaskPath "\" -ErrorAction Stop)
    }
    $Task = @(Get-ScheduledTask -TaskName $VsgPublisher -TaskPath "\" -ErrorAction Stop)[0]
    VsgDemand ($Task.Actions.Count -eq 1 -and $Task.Triggers.Count -eq 1) "publisher action/trigger count changed"
    VsgDemand ($Task.Actions[0].Execute -like "*powershell.exe" -and
        $Task.Actions[0].Arguments -like "*current-aggregate-task-runner.ps1*" -and
        $Task.Actions[0].Arguments -like "*VowSig-EXP031-HourlyPublisher*" -and
        $Task.Actions[0].WorkingDirectory -ieq $VsgRepo) "EXP034 installed action changed"
    VsgDemand ($Task.Triggers[0].StartBoundary -match 'T\d\d:05:00(?:\+00:00)?$' -and
        $Task.Triggers[0].Repetition.Interval -ceq "PT1H") "original :05 hourly trigger changed"
    return $Xml
}
function VsgCheckTaskSame($Before, $After) {
    foreach ($Name in $VsgTaskNames) {
        VsgDemand ($Before[$Name] -ceq $After[$Name]) "scheduled task XML definition changed"
    }
}

VsgDemand ($Confirm -ceq "APPROVE-EXP034-PR64-SOURCE-ONLY-FF") "missing owner-approved source-only token"
VsgDemand (Test-Path -LiteralPath $VsgRepo -PathType Container) "VPS repo absent"
$Remote = VsgGit @("remote","get-url","origin")
VsgDemand ($Remote -match '(?i)(^|[:/])alisufyan-ai7/trading-signal-intelligence(\.git)?$') "wrong GitHub remote"
VsgCheckHead $VsgOld
VsgCheckFrozen
VsgCheckBlob "scripts/guarded_product_publish_v0_1.py" "e3f153128d4c65c7c98cfba7427a6e892eca2e29"
VsgCheckPrivateRecovery
$Before = VsgTasks $true
$RunnerHash = (Get-FileHash -LiteralPath $VsgNewRunner -Algorithm SHA256).Hash

# Never execute arbitrary post-merge hooks from this owner handoff.
$Hook = VsgGit @("rev-parse","--git-path","hooks/post-merge")
if (-not [IO.Path]::IsPathRooted($Hook)) { $Hook = Join-Path $VsgRepo $Hook }
VsgDemand (-not (Test-Path -LiteralPath $Hook -PathType Leaf)) "active post-merge hook requires review"
$HookConfig = @(& git -C $VsgRepo config --get core.hooksPath)
VsgDemand ($HookConfig.Count -eq 0 -or
    [string]::IsNullOrWhiteSpace(([string]$HookConfig[0]))) "custom hooks require review"

$RemoteRow = VsgGit @("ls-remote","--heads","origin","refs/heads/main")
$RemoteParts = $RemoteRow -split "\s+"
VsgDemand ($RemoteParts.Count -eq 2 -and
    $RemoteParts[0] -ceq $VsgNew -and
    $RemoteParts[1] -ceq "refs/heads/main") "remote main changed"

Write-Output "EXP034_PR64_SOURCE_SYNC_PREFLIGHT=PASS"
# Exact approved remote acquisition; no working-tree mutation until fast-forward.
& git -C $VsgRepo fetch --no-tags origin refs/heads/main
VsgDemand ($LASTEXITCODE -eq 0) "fetch failed"
VsgDemand ((VsgGit @("rev-parse","FETCH_HEAD")) -ceq $VsgNew) "FETCH_HEAD mismatch"
& git -C $VsgRepo merge-base --is-ancestor $VsgOld $VsgNew
VsgDemand ($LASTEXITCODE -eq 0) "not a fast-forward from expected old main"
VsgDemand ((VsgGit @("rev-parse","$VsgNew^{tree}")) -ceq $VsgExpectedTree) "merged tree mismatch"
$Changed = @(& git -C $VsgRepo diff --no-renames --name-only $VsgOld $VsgNew)
VsgDemand ($LASTEXITCODE -eq 0 -and $Changed.Count -eq $VsgModifiedPins.Count) "unexpected changed-file count"
$Comparison = @(Compare-Object ($Changed | Sort-Object) (@($VsgModifiedPins.Keys) | Sort-Object))
VsgDemand ($Comparison.Count -eq 0) "PR64 source path scope not exact"
$Status = @(& git -C $VsgRepo diff --no-renames --name-status $VsgOld $VsgNew)
VsgDemand ($LASTEXITCODE -eq 0 -and $Status.Count -eq 3 -and
    @($Status | Where-Object {$_ -notmatch '^M\s+'}).Count -eq 0) "unexpected add/delete/rename"
foreach ($P in $VsgModifiedPins.Keys) {
    VsgDemand ((VsgGit @("rev-parse","$($VsgNew):$P")) -ceq
        [string]$VsgModifiedPins[$P]) "target tested blob mismatch"
}
VsgCheckHead $VsgOld
VsgCheckPrivateRecovery
$BeforeMutation = VsgTasks $true
VsgCheckTaskSame $Before $BeforeMutation

Write-Output "EXP034_PR64_THREE_FILE_SCOPE_AND_TASKS=PASS"
Write-Output "EXP034_PR64_SOURCE_FAST_FORWARD_START=TRUE"
& git -C $VsgRepo merge --ff-only $VsgNew
VsgDemand ($LASTEXITCODE -eq 0) "fast-forward failed; do not reset or retry automatically"
# Emit this marker immediately; if subsequent postflight fails the source HAS changed.
Write-Output "EXP034_PR64_GIT_FAST_FORWARD_COMPLETED=TRUE"

VsgCheckHead $VsgNew
VsgDemand ((VsgGit @("rev-parse","HEAD^{tree}")) -ceq $VsgExpectedTree) "new tree changed"
VsgCheckFrozen
foreach ($P in $VsgModifiedPins.Keys) {
    VsgCheckBlob $P ([string]$VsgModifiedPins[$P])
}
VsgCheckPrivateRecovery
VsgDemand ((Get-FileHash -LiteralPath $VsgNewRunner -Algorithm SHA256).Hash -ceq $RunnerHash) "installed launcher changed"
$After = VsgTasks $false
VsgCheckTaskSame $Before $After
Write-Output "EXP034_PR64_EXACT_NEW_MAIN_ON_VPS=PASS"
Write-Output "EXP034_PR64_EXISTING_FOUR_TASKS_AND_RUNNER_UNCHANGED=PASS"
Write-Output "EXP034_PR64_NO_MANUAL_K5_OR_PUBLISH=TRUE"
Write-Output "EXP034_PR64_SOURCE_ONLY_SYNC=PASS"
