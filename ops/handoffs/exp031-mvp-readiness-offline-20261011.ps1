# EXP-031 reduced-scope historic crypto-card MVP — OFFLINE READINESS ONLY.
# Owner-approved preparation. No merge, production source change, task change,
# new crypto capture, provider, cloud POST, notification, backup or trading.
& {
    $ErrorActionPreference = "Stop"

    $Repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
    $Review = "C:\Users\ADMINI~1\AppData\Local\Temp\2\vowsig-guarded-publisher-review-3f0de0cb6c94499789aae0eeaab22012"
    $Python = Join-Path $Repo ".venv\Scripts\python.exe"

    $Main = "47687d8d0e21523e417899a71dddc886ecf25d73"
    $ReviewHead = "620ee672f22b57fde8f512b4493dcd0f6f562e08"
    $Pr46 = "13f10339df1410bbbe075371b52b34901ebd121b"
    $Pr48 = "3cc0384ee21e66ce0e93bcc4d6a6e855ec21d34d"
    $Pr49 = "c3e2ae4276f58bb338b2d97a36908a2ae2b01689"
    $Pr51 = $ReviewHead
    $Pr55 = "99c49ecabcb696b6533fe4382eed1d9cd11a2fdb"
    $Pr50 = "e1fb7073100746848bce8ee1ee0b823f5528d14b"

    function Assert-Checkout($Folder, $Expected, $Branch) {
        $Actual = (& git -C $Folder rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $Actual -cne $Expected) {
            throw "Unexpected checkout HEAD: $Folder"
        }
        $Ref = (& git -C $Folder rev-parse --abbrev-ref HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $Ref -cne $Branch) {
            throw "Unexpected checkout branch: $Folder"
        }
        $Dirty = @(& git -C $Folder status --porcelain --untracked-files=all)
        if ($LASTEXITCODE -ne 0 -or $Dirty.Count -ne 0) {
            throw "Unexpected dirty Git checkout: $Folder"
        }
    }
    function Assert-Blob($Folder, $Relative, $Expected) {
        $Disk = (& git -C $Folder hash-object -- (Join-Path $Folder $Relative)).Trim()
        if ($LASTEXITCODE -ne 0 -or $Disk -cne $Expected) {
            throw "Unexpected file contents: $Relative"
        }
    }
    function Fetch-Exact($Branch, $Sha) {
        & git -C $Review fetch --no-tags origin "refs/heads/$Branch"
        if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
        $Actual = (& git -C $Review rev-parse FETCH_HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $Actual -cne $Sha) {
            throw "Fetched branch moved or unexpected SHA: $Branch"
        }
    }

    Assert-Checkout $Repo $Main "main"
    Assert-Checkout $Review $ReviewHead "HEAD"
    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Frozen production venv Python missing"
    }

    # Read ONLY the existing sanitized seal, not any SQLite ledger.
    $Seal = Join-Path $Repo "data\crypto-research-asof-v0.1.json"
    $SealInfo = Get-Item -LiteralPath $Seal -ErrorAction Stop
    $SealHash = (Get-FileHash -LiteralPath $Seal -Algorithm SHA256).Hash
    if ($SealInfo.Length -ne 3048 -or
        $SealHash.ToLowerInvariant() -cne
          "f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4") {
        throw "Existing historic seal no longer matches approved identity"
    }
    $SealMtime = $SealInfo.LastWriteTimeUtc
    Write-Host "HISTORICAL_SEAL_PIN_STILL_VALID=PASS"

    # GET-only metadata of the EXISTING, unchanged :05 publisher.
    $TaskName = "TradingTop Product Publish"
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $Info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
    $ExpectedRunner = Join-Path $Repo "scripts\run_product_publish_task.cmd"
    $ExpectedArgs = '/c "' + $ExpectedRunner + '"'
    $ActionOK = (
        $Task.Actions.Count -eq 1 -and
        $Task.Actions[0].Execute -ieq "cmd.exe" -and
        $Task.Actions[0].Arguments -ceq $ExpectedArgs
    )
    Assert-Blob $Repo "scripts\run_product_publish_task.cmd" "3c5d292338b65c65e0faa5ffe04c1fb2000efa84"
    $Snapshot = Join-Path $Repo "data\public_snapshot.json"
    $SnapshotPresent = Test-Path -LiteralPath $Snapshot -PathType Leaf
    $SnapshotSHA = "ABSENT"
    if ($SnapshotPresent) {
        $SnapshotSHA = (Get-FileHash -LiteralPath $Snapshot -Algorithm SHA256).Hash
    }
    Write-Host "LEGACY_PUBLISHER_STATE=$($Task.State)"
    Write-Host "LEGACY_PUBLISHER_LAST_RESULT=$($Info.LastTaskResult)"
    Write-Host "LEGACY_PUBLISHER_LAST_UTC=$($Info.LastRunTime.ToUniversalTime().ToString('o'))"
    Write-Host "LEGACY_PUBLISHER_NEXT_UTC=$($Info.NextRunTime.ToUniversalTime().ToString('o'))"
    Write-Host "LEGACY_PUBLISHER_ACTION_MATCH=$ActionOK"
    Write-Host "LEGACY_PUBLISHER_TRIGGER_COUNT=$($Task.Triggers.Count)"
    Write-Host "LEGACY_PUBLISHER_MULTIPLE_INSTANCES=$($Task.Settings.MultipleInstances)"
    Write-Host "PUBLIC_SNAPSHOT_PRESENT=$SnapshotPresent"
    Write-Host "PUBLIC_SNAPSHOT_SHA256=$SnapshotSHA"
    if (-not $ActionOK) {
        throw "Live publisher action differs from reviewed configuration; stop"
    }
    Write-Host "LEGACY_PUBLISHER_READONLY_INVENTORY=PASS"

    # Isolated review worktrees only; NEVER change production source or schedule.
    Fetch-Exact "research/exp031-crypto-asof-publication-preparation-20261011" $Pr55
    Fetch-Exact "governance/frozen-dependency-change-impact-gate-20261010" $Pr50
    $TempRoot = Join-Path $env:TEMP ("exp031-mvp-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $TempRoot -ErrorAction Stop | Out-Null
    $Candidate = Join-Path $TempRoot "p55"
    $GuardRoot = Join-Path $TempRoot "p50"
    & git -C $Review worktree add --detach $Candidate $Pr55
    if ($LASTEXITCODE -ne 0) { throw "Candidate worktree failed" }
    & git -C $Review worktree add --detach $GuardRoot $Pr50
    if ($LASTEXITCODE -ne 0) { throw "Guard worktree failed" }
    Assert-Checkout $Candidate $Pr55 "HEAD"
    Assert-Checkout $GuardRoot $Pr50 "HEAD"

    $Checker = Join-Path $GuardRoot "scripts\check_frozen_dependency_impact.py"
    Assert-Blob $GuardRoot "scripts\check_frozen_dependency_impact.py" "502d180a91ed5e9c76d967289c30f2637d58fffa"
    Write-Host "TRUSTED_MANUAL_GUARD_EXACT_SHA=PASS"

    # Dry-run each intended stacked merge. BLOCK for PR46 is EXPECTED:
    # prior prospectively approved correction #9 changes a frozen source
    # and adds a separately governed correction anchor. Never treat as PASS.
    $Pairs = @(
        @("PR46", $Main, $Pr46, "BLOCKED"),
        @("PR48", $Pr46, $Pr48, "PASS"),
        @("PR49", $Pr48, $Pr49, "PASS"),
        @("PR51", $Pr49, $Pr51, "PASS"),
        @("PR55", $Pr51, $Pr55, "PASS")
    )
    foreach ($Pair in $Pairs) {
        $Name, $Base, $Head, $Expected = $Pair
        $Output = @(& $Python -B $Checker --repo $Review --base $Base --head $Head)
        $Code = $LASTEXITCODE
        Write-Host "GUARD_REVIEW=$Name"
        $Output | ForEach-Object { Write-Host $_ }
        $ExpectedCode = if ($Expected -eq "BLOCKED") { 1 } else { 0 }
        if ($Code -ne $ExpectedCode -or
            -not ($Output -contains "FROZEN_DEPENDENCY_CHANGE_IMPACT=$Expected")) {
            throw "Unexpected frozen-dependency result: $Name, exit $Code"
        }
        if ($Name -eq "PR46") {
            $Found = @($Output | Where-Object { $_ -like "BLOCKED_PATH=*" })
            $Allowed = @(
                "BLOCKED_PATH=src/trading_signal_intelligence/product/ai_insights.py",
                "BLOCKED_PATH=research/forward/AI-v1.1-public-surface-correction-v0.3-2026-10-10T125803Z.json"
            )
            if ($Found.Count -ne $Allowed.Count -or
                @($Found | Where-Object { $_ -cnotin $Allowed }).Count -gt 0) {
                throw "PR46 blocked paths extend beyond audited prospective correction"
            }
        }
    }
    Write-Host "MANUAL_GUARD_REVIEW_COMPLETED=TRUE"
    Write-Host "PR46_PROSPECTIVE_CORRECTION_EXCEPTION_REQUIRED=TRUE"
    Write-Host "MERGE_APPROVAL_GRANTED=FALSE"

    # ONE consolidated, isolated Windows synthetic regression at current PR55.
    $Tests = @(
        "tests/test_guarded_snapshot_history_audit_v0_3.py",
        "tests/test_guarded_product_publish_v0_1.py",
        "tests/test_expansion_registry_compat_v0_1.py",
        "tests/test_expansion_registry_public_integration_v0_1.py",
        "tests/test_crypto_public_validation_v0_1.py",
        "tests/test_vowsig_multilineage_public_observability.py",
        "tests/test_public_snapshot_push_guard.py",
        "tests/test_cloud_ai_runtime_validation.py",
        "tests/test_crypto_asof_publication_v0_1.py",
        "tests/test_guarded_crypto_asof_capture_entry_v0_1.py"
    )
    $OriginalEnv = @{
        PYTHONPATH = $env:PYTHONPATH
        PYTEST_DISABLE_PLUGIN_AUTOLOAD = $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD
        PYTHONDONTWRITEBYTECODE = $env:PYTHONDONTWRITEBYTECODE
    }
    try {
        $env:PYTHONPATH = Join-Path $Candidate "src"
        $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
        $env:PYTHONDONTWRITEBYTECODE = "1"
        Push-Location $Candidate
        try {
            & $Python -B -m pytest -q -p no:cacheprovider @Tests
            $PytestCode = $LASTEXITCODE
        }
        finally { Pop-Location }
    }
    finally {
        foreach ($Key in $OriginalEnv.Keys) {
            [Environment]::SetEnvironmentVariable($Key, $OriginalEnv[$Key], "Process")
        }
    }
    Write-Host "PR55_COMBINED_OFFLINE_EXIT_CODE=$PytestCode"

    $SealInfoAfter = Get-Item -LiteralPath $Seal -ErrorAction Stop
    $SealHashAfter = (Get-FileHash -LiteralPath $Seal -Algorithm SHA256).Hash
    if ($SealHashAfter -cne $SealHash -or
        $SealInfoAfter.Length -ne $SealInfo.Length -or
        $SealInfoAfter.LastWriteTimeUtc -ne $SealMtime) {
        throw "Historical seal changed during offline checks"
    }
    Assert-Checkout $Repo $Main "main"
    Assert-Checkout $Review $ReviewHead "HEAD"
    Assert-Checkout $Candidate $Pr55 "HEAD"
    Assert-Checkout $GuardRoot $Pr50 "HEAD"
    Write-Host "SEAL_AND_ALL_GIT_CHECKOUTS_UNCHANGED=PASS"
    if ($PytestCode -ne 0) { throw "Focused PR55 regression failed" }
    Write-Host "EXP031_MVP_OFFLINE_READINESS=PASS_WITH_PR46_MANUAL_CORRECTION_DECISION_PENDING"
    Write-Host "PRODUCTION_SYNC_TASK_CHANGE_CLOUD_PUBLICATION=False"
}
