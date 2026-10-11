& {
    $ErrorActionPreference = "Stop"

    $repo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
    $review = "C:\Users\ADMINI~1\AppData\Local\Temp\2\vowsig-guarded-publisher-review-3f0de0cb6c94499789aae0eeaab22012"
    $python = Join-Path $repo ".venv\Scripts\python.exe"
    $seal = Join-Path $repo "data\crypto-research-asof-v0.1.json"

    $mainSHA = "47687d8d0e21523e417899a71dddc886ecf25d73"
    $pr51SHA = "620ee672f22b57fde8f512b4493dcd0f6f562e08"
    $pr55SHA = "99c49ecabcb696b6533fe4382eed1d9cd11a2fdb"

    $branch = "research/exp031-crypto-asof-publication-preparation-20261011"

    $databases = @(
        "data\ai_v1_1_xauusd.sqlite",
        "data\ai_v1_1_ustec.sqlite",
        "data\ai_v1_1_us30.sqlite",
        "data\ai_v1_2_1_eurusd.sqlite",
        "data\ai_v1_2_1_xagusd.sqlite",
        "data\ai_v1_2_1_usoil.sqlite",
        "data\ai_v1_3_btcusdt.sqlite",
        "data\ai_v1_3_ethusdt.sqlite",
        "data\ai_v1_3_solusdt.sqlite"
    )

    function Check-Git($path, $sha, $ref) {
        $head = (& git -C $path rev-parse HEAD).Trim()
        $actual = (& git -C $path rev-parse --abbrev-ref HEAD).Trim()
        $dirty = @(& git -C $path status --porcelain --untracked-files=all)

        if ($LASTEXITCODE -ne 0 -or
            $head -cne $sha -or
            $actual -cne $ref -or
            $dirty.Count -ne 0) {
            throw "Git identity or cleanliness failed: $path"
        }
    }

    function Get-LedgerState($relative) {
        $path = Join-Path $repo $relative
        $item = Get-Item -LiteralPath $path -ErrorAction Stop

        if ($item.PSIsContainer -or
            ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            $item.Length -le 0 -or $item.Length -gt 32MB) {
            throw "Unsafe source ledger: $relative"
        }

        foreach ($suffix in @("-wal", "-shm", "-journal")) {
            if (Test-Path -LiteralPath ($path + $suffix)) {
                throw "SQLite sidecar detected: $relative"
            }
        }

        return @{
            Size = $item.Length
            Modified = $item.LastWriteTimeUtc
            SHA = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        }
    }

    function Check-Scheduler {
        $active = @(
            Get-ScheduledTask -ErrorAction Stop |
                Where-Object {
                    $_.State -eq "Running" -and
                    $_.TaskName -match "(?i)(VowSig|SignalProof).*Shadow Scan"
                }
        )

        if ($active.Count -ne 0) {
            throw "Shadow scan running; capture held"
        }

        $task = Get-ScheduledTask `
            -TaskName "VowSig AI-v1.3 Crypto Shadow Scan" `
            -ErrorAction Stop

        $info = Get-ScheduledTaskInfo `
            -TaskName "VowSig AI-v1.3 Crypto Shadow Scan" `
            -ErrorAction Stop

        if ($task.State -ne "Ready" -or
            $info.LastTaskResult -ne 0) {
            throw "K5 is not in a successful ready state"
        }

        $age = ([datetime]::UtcNow -
            $info.LastRunTime.ToUniversalTime()).TotalSeconds

        if ($age -lt 0 -or $age -gt 900) {
            throw "Natural K5 completion outside 15-minute window"
        }

        if ($info.NextRunTime -le [datetime]::Now) {
            throw "K5 next execution time is invalid"
        }
    }

    $envNames = @(
        "PYTHONPATH", "PYTEST_ADDOPTS",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        "PYTHONDONTWRITEBYTECODE",
        "TEMP", "TMP", "TMPDIR",
        "VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED",
        "VOWSIG_CRYPTO_ASOF_ENABLED",
        "VOWSIG_CRYPTO_ASOF_SHA256",
        "VOWSIG_GUARDED_PUBLISH_ENABLED"
    )

    $saved = @{}
    foreach ($name in $envNames) {
        $saved[$name] = [Environment]::GetEnvironmentVariable(
            $name, "Process"
        )
    }

    $checkout = $null
    $before = @{}
    $captureStarted = $false
    $passed = $false

    try {
        Check-Git $repo $mainSHA "main"
        Check-Git $review $pr51SHA "HEAD"

        $prodGit = (& git -C $repo rev-parse --path-format=absolute --git-common-dir).Trim()
        $reviewGit = (& git -C $review rev-parse --path-format=absolute --git-common-dir).Trim()

        if ($prodGit -ieq $reviewGit) {
            throw "Production and review repositories not isolated"
        }

        if (Test-Path -LiteralPath $seal) {
            throw "Existing crypto seal; no overwrite allowed"
        }

        $dataDir = Get-Item -LiteralPath (Join-Path $repo "data")
        if (-not $dataDir.PSIsContainer -or
            ($dataDir.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Unsafe output directory"
        }

        Write-Host "GIT_PREFLIGHT=PASS"
        Write-Host "NONOVERWRITE_PREFLIGHT=PASS"

        # Git fetch affects only the independent review repository.
        & git -C $review fetch --no-tags origin "refs/heads/$branch"
        if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }

        $remoteHead = (& git -C $review rev-parse FETCH_HEAD).Trim()

        if ($remoteHead -cne $pr55SHA) {
            throw "Approved PR55 SHA no longer matches remote"
        }

        $root = Join-Path $env:TEMP (
            "p55-second-" + [guid]::NewGuid().ToString("N").Substring(0,8)
        )

        $checkout = Join-Path $root "c"
        $testScratch = Join-Path $root "pt"

        New-Item -ItemType Directory $root -ErrorAction Stop | Out-Null

        & git -C $review worktree add --detach $checkout $pr55SHA
        if ($LASTEXITCODE -ne 0) {
            throw "Isolated checkout creation failed"
        }

        Check-Git $checkout $pr55SHA "HEAD"

        $testGit = (& git -C $checkout rev-parse --path-format=absolute --git-common-dir).Trim()

        if ($testGit -ine $reviewGit) {
            throw "Review Git isolation failed"
        }

        $blobs = @{
            "scripts/guarded_crypto_asof_capture_entry_v0_1.py" = "eb96c2d8b614dadd92e4a18ade1001fb39b73bde"
            "tests/test_guarded_crypto_asof_capture_entry_v0_1.py" = "7d206d7f2817c488f1462a73238c8f6c28e646f9"
            "scripts/capture_crypto_research_asof_v0_1.py" = "630ef7dda423de5038143ca6c0fe1729410f106b"
            "src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py" = "cab8b03ca1eaa0b6cfa47d2f84958514b617cfc7"
            "scripts/guarded_product_publish_v0_1.py" = "26e6b8976536f57830347e48eba42a85d59f2848"
            "src/trading_signal_intelligence/product/crypto_validation.py" = "65e4d992784e7c4156dde703047c331eda51c2cf"
            "scripts/export_guarded_core_expansion_v0_2.py" = "bfb0fbe12c46afcb029abf7d42861d0a4128b4b7"
        }

        foreach ($file in $blobs.Keys) {
            $committed = (& git -C $checkout rev-parse "${pr55SHA}:$file").Trim()
            $disk = (& git -C $checkout hash-object -- (Join-Path $checkout $file)).Trim()

            if ($LASTEXITCODE -ne 0 -or
                $committed -cne $blobs[$file] -or
                $disk -cne $blobs[$file]) {
                throw "Exact source blob mismatch: $file"
            }
        }

        Write-Host "PR55_EXACT_SHA_AND_BLOBS=PASS"

        $version = (& $python --version 2>&1)
        if ($LASTEXITCODE -ne 0 -or
            $version -notmatch '^Python 3\.12\.\d+$') {
            throw "Native Python 3.12 required"
        }

        Write-Host "NATIVE_PYTHON=$version"

        # --------------------------------------------------
        # Stage 1: Synthetic guard verification only
        # --------------------------------------------------

        $env:PYTHONPATH = Join-Path $checkout "src"
        $env:PYTHONDONTWRITEBYTECODE = "1"
        $env:PYTEST_ADDOPTS = ""
        $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
        $env:TEMP = $root
        $env:TMP = $root
        $env:TMPDIR = $root

        $env:VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED = "0"
        $env:VOWSIG_CRYPTO_ASOF_ENABLED = "0"
        $env:VOWSIG_GUARDED_PUBLISH_ENABLED = "0"
        Remove-Item Env:VOWSIG_CRYPTO_ASOF_SHA256 -ErrorAction SilentlyContinue

        $entry = Join-Path $checkout "scripts\guarded_crypto_asof_capture_entry_v0_1.py"

        Write-Host "SYNTHETIC_PREFLIGHT_STARTED=TRUE"

        & $python -I -B $entry `
            --mode import-smoke `
            --live-root $repo

        if ($LASTEXITCODE -ne 0) {
            throw "Native Windows guarded import smoke failed"
        }

        Push-Location $checkout
        try {
            $testOutput = @(
                & $python -B -m pytest `
                    -q -ra --color=no `
                    -p no:cacheprovider --noconftest `
                    --basetemp $testScratch `
                    tests/test_guarded_crypto_asof_capture_entry_v0_1.py 2>&1
            )
            $testExit = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }

        $testOutput | ForEach-Object { Write-Host $_ }
        Write-Host "SYNTHETIC_TEST_EXIT_CODE=$testExit"

        $testPassed = @(
            $testOutput | Where-Object {
                $_ -match '^\s*17 passed in [0-9.]+s\s*$'
            }
        )

        if ($testExit -ne 0 -or $testPassed.Count -ne 1) {
            throw "New exact-SHA synthetic gate failed; NO real capture"
        }

        Write-Host "NEW_GUARDED_SYNTHETIC_GATE=PASS"

        # --------------------------------------------------
        # Stage 2: One explicitly approved real attempt
        # --------------------------------------------------

        Check-Git $repo $mainSHA "main"
        Check-Git $review $pr51SHA "HEAD"
        Check-Git $checkout $pr55SHA "HEAD"

        if (Test-Path -LiteralPath $seal) {
            throw "Seal appeared before capture; stop"
        }

        Check-Scheduler

        foreach ($relative in $databases) {
            $before[$relative] = Get-LedgerState $relative
        }

        if ($before.Count -ne 9) {
            throw "Nine-ledger preflight incomplete"
        }

        Write-Host "NINE_LEDGER_PREFLIGHT=PASS"
        Write-Host "K5_NATURAL_COMPLETION_PREFLIGHT=PASS"

        $env:PYTHONPATH = ""
        $env:VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED = "1"

        # Exactly ONE process invocation.
        $captureStarted = $true
        Write-Host "SECOND_REAL_CAPTURE_ATTEMPT_STARTED=TRUE"

        & $python -I -B $entry `
            --mode capture `
            --live-root $repo `
            --confirm CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL

        $captureExit = $LASTEXITCODE
        Write-Host "CAPTURE_EXIT_CODE=$captureExit"

        if ($captureExit -ne 0) {
            throw "Second capture attempt failed; DO NOT RETRY"
        }

        if (-not (Test-Path -LiteralPath $seal)) {
            throw "Capture returned success without seal file"
        }

        $sealItem = Get-Item -LiteralPath $seal -ErrorAction Stop

        if ($sealItem.PSIsContainer -or
            ($sealItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -or
            $sealItem.Length -le 0 -or $sealItem.Length -gt 65536) {
            throw "Created seal has unsafe file properties"
        }

        Write-Host "LOCAL_SEAL_SHA256_INDEPENDENT=$((Get-FileHash -LiteralPath $seal -Algorithm SHA256).Hash)"
        Write-Host "LOCAL_SEAL_BYTES_INDEPENDENT=$($sealItem.Length)"

        $passed = $true
    }
    finally {
        try {
            foreach ($relative in $before.Keys) {
                $after = Get-LedgerState $relative
                $old = $before[$relative]

                if ($after.Size -ne $old.Size -or
                    $after.Modified -ne $old.Modified -or
                    $after.SHA -cne $old.SHA) {
                    throw "AI ledger source changed: $relative"
                }
            }

            if ($before.Count -eq 9) {
                Write-Host "NINE_LEDGER_SOURCE_PRESERVATION=PASS"
            }

            Check-Git $repo $mainSHA "main"
            Check-Git $review $pr51SHA "HEAD"

            if ($checkout -and (Test-Path -LiteralPath $checkout)) {
                Check-Git $checkout $pr55SHA "HEAD"
            }

            Write-Host "ALL_GIT_CHECKOUTS_UNCHANGED=PASS"
        }
        finally {
            foreach ($name in $envNames) {
                [Environment]::SetEnvironmentVariable(
                    $name, $saved[$name], "Process"
                )
            }

            Write-Host "SECOND_REAL_CAPTURE_PROCESS_INVOKED=$captureStarted"
            Write-Host "LOCAL_SEAL_FILE_PRESENT=$([bool](Test-Path -LiteralPath $seal))"
        }
    }

    if ($passed) {
        Write-Host "SECOND_LOCAL_SANITIZED_CRYPTO_ASOF_CAPTURE=PASS"
        Write-Host "WEBSITE_PUBLICATION=False"
    }
}
