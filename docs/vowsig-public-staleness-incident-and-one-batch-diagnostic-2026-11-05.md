# VowSig public AI stale-snapshot incident — 2026-11-05

Owner-provided screenshot shows **Public AI data stale**, public AI-v1.1 **1,356 inferences and 93 completed shadow trades**, displayed snapshot **04/11/2026 14:05:46** (browser-local timezone unspecified). This screenshot proves rendered app state but does not locate the publisher failure.

## Code trace and existing incident

- `web/app.js` shows the warning when `/api/health` reports `snapshot_freshness=stale`. `product/cloud_app.py` computes `delayed>=90min`, `stale>=150min` from accepted public snapshot `generated_at_utc`. It is correct to surface old data rather than silently update the time.
- The guarded hourly publication depends on the Windows `TradingTop Product Publish` task, its installed ProgramData launcher, verified fresh core/expansion exporter, accepted snapshot receipt and hosted POST. Production publisher/task must not be force-restarted or replaced without explicit cutover authority.
- GitHub Issue #92 records real Nov 3 core-provider HTTP 401 `API_KEY_INVALID` affecting all three AI-v1.1 markets and screenshot evidence of same-day recovery. It is an important historical possibility, not proof of the Nov 4/5 recurrence. The frozen Nov 5 source has 452 inferences per core market = 1,356 and 93 closed shadow trades, exactly matching screenshot counts; later ERROR events require safe classification.
- The legacy (not confirmed installed) `.cmd` publisher attempts optional push even after export failure, and missing ingestion credentials can make the optional push silently skip. This must be kept distinct from the previously owner-approved guarded production launcher.

## Safe single operator receipt, no repeated source rechecks

`ops/handoffs/vowsig_public_staleness_readonly_v0_1.ps1` reads the 4 known Windows tasks, numeric exit codes from bounded private log tails, and sanitized local public JSON snapshot count/time only. It prints issue codes, not raw log lines, secrets, task command arguments, full payloads or error bodies. It never touches original/frozen source ledgers, scheduler, broker, network, Git or hosted snapshots. Synthetic/static CI checks validate absence of known mutation commands; they do not establish native Windows runtime PASS.

## Resolution

Collect one operator receipt. Differentiate: scheduler absent/late; core scanner/provider held; publication guarded exit; valid locally newer accepted snapshot vs hosted lag; or unknown. Check one scoped sanitized root cause then plan exactly one minimally invasive, tested, approved correction. No synthetic snapshot timestamp bump, old snapshot POST, force trading task rerun or public broker enable.

All other single-release gates remain: Auth0 live signup/email, Railway `verify-full` restricted SQL, real owner MFA + signed provisioning, source rights/after-cost complete-history certification, full owner Performance Lab, rollback UAT, exact owner-approved deploy. PostgreSQL S3/B2 encrypted backup/cold restore is separately documented as first immediate postlaunch owner-accepted exception (`DATABASE_RECOVERY_UNVERIFIED`).
## UI historical-snapshot integrity adjustment (draft only)

The public AI detail panel formerly displayed archived `SHADOW RUNTIME HEALTHY` and `Scheduler healthy` flags even while the hero correctly said `Public AI data stale`. The draft update passes `/api/health` freshness into `renderAi`, marks the whole saved AI health panel `SAVED SHADOW STATUS • NOT CURRENT`, uses `Historical scheduler state only`, labels saved metrics as historical, and keeps broker status limited to the historical snapshot. Exact matching static frontend tests run in CI. This does not restore cloud publication; it prevents a stale public snapshot from misrepresenting current operational health. No production website redeployment authorized yet.
