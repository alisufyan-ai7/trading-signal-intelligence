# PR #93 — 2026-11-06 staging QA diagnostics and callback log hardening

## Scope and authority
- Only repository: `alisufyan-ai7/trading-signal-intelligence`, same DRAFT PR #93; no merge or production/VPS/trading/publisher changes authorized.
- Independent Railway staging inspection of project `vowsig-staging-20261105`; do not infer production environment status.
- The GitHub candidate and deployed staging image differ: prior tested branch HEAD `7847877b15157121cf313e0e994edd0286c1cdae`; staging deployment `d1b2aa0b-e372-4c27-a58c-49869b6dfceb`, SUCCESS, source SHA `e05808430a863841655e1fa62e22292eca311bca`. Subsequent PR code changes are **not** deployed or accepted merely by being committed.
- Production rollout and owner exact-SHA merge approval remain separately gated.

## Actual existing staging authentication evidence — not a new browser PASS
Railway staging proxy path/method/status-only receipts:
- 2026-11-05 19:32:38 UTC: `GET /auth/callback` **303**; immediately afterward `/app/` and `/api/v2/me` **200**.
- 19:36:50–19:37:01 UTC: watchlist `PUT` for three catalog symbols **200**, with subsequent watchlist GET **200**; responses are not independently inspected and therefore persistence/removal are not fully proved.
- 19:41:50 UTC: `POST /api/v2/me/logout` **200**; does not by itself prove revocation or old-cookie replay.
- 20:04:28 UTC: later `GET /auth/callback` **401**, followed by protected member route/API **401**.
- Independent browser reported credential handoff `origin_changed`. The identity claim or account-link rejection cause is **unconfirmed**; do not label invalid password, regression or unverified user as proven. Need a new verified sign-in through isolated secure browser profile, starting `/auth/start` and preserving all credentials outside logs/GitHub/chat.

Do NOT paste verbatim Railway runtime access lines from these windows: they contain OAuth callback query parameters. Record only method, pathname, timestamp and status.

## New security finding: OAuth callback parameters in Uvicorn logs
The deployed container's default Uvicorn access logs include request query strings, including OAuth one-time `code`, `state`, and `iss` fields. Although one-time/short-lived, such parameters do not belong in application log retention or incident artifacts.
- Draft fix in `Dockerfile` adds `--no-access-log` to Uvicorn's only launch command. Railway edge HTTP proxy logs remain available for method/path/status telemetry. Application errors and health checks remain enabled.
- Dedicated regression in `tests/test_vowsig_staging_http_acceptance_p5.py` checks the Docker `CMD` entrypoint includes the flag. This static check is **CI-only evidence**, not proof running deployment has changed.
- Before closing: exact-head CI success, check staged image deployed from exact SHA in an authorized staging window, then inspect post-deploy non-secret logs to confirm access-line suppression without disrupting error observability. Historical callback entries already in Railway logs are not removed by code changes; apply provider retention controls only through approved operational processes. Never paste raw historical callback URLs to tickets or GitHub.

## New live read-only staging snapshot diagnosis
2026-11-06 live unauthenticated GET results:
- `/api/health`: `snapshot_pending=true`, `snapshot_freshness=missing`, `snapshot_generated_at_utc=null`.
- `/api/v2/public/markets`: exactly nine catalog entries, all `status_unavailable` with `snapshot_fresh=false`, no current details, restricted-six exposure false.
- `/api/v2/public/history-summary`: zero recent decisions/signals, `history_complete=false`, `full_population_metrics=null`.

Infrastructure/source cross-check: staging app has **no attached persistent volume**, **no configured `TRADINGTOP_INGEST_TOKEN` variable** (only variable names were inspected), and a `TRADINGTOP_SNAPSHOT_PATH` variable whose value was NOT inspected. `cloud_app.py` reads a local JSON snapshot file via `_snapshot_path()`; absent file returns the above missing state. `POST /api/internal/snapshot` requires `TRADINGTOP_INGEST_TOKEN`, so authenticated snapshot ingestion is currently not configured for this staging service. These observations explain why no usable snapshot is available. Do not confuse nine *catalog entries* with nine live research feeds.

**Required safe completion:** establish a separate staging-only, authenticated, durable publication source for a genuinely generated, policy-approved sanitized snapshot (with approved storage, staging-scoped ingestion key held solely in secret manager, source proof, freshness tests, retention and rollback). Never copy confidential ledgers into GitHub, invent signals, replay expired timestamps, weaken market-detail release gates, force Windows publisher runs or alter production ingestion to make staging green. Until independently demonstrated, keep staging data acceptance **HOLD**; the current UI's unavailable status is truthful.

## Remaining release acceptance gates
- Real authenticated staging member dashboard, all nine market policies, XAUUSD add/refresh/remove/refresh and original watchlist restoration, preferences, logout, signed-out/old-session replay, re-login, responsive/accessibility observations.
- Owner offline two-person verified identity/TOTP enrollment and recovery drill with protected receipts.
- Independent original nine-market history/right-to-use/crypto-K5/after-cost net-R source certification; keep incomplete performance N/A.
- Real provider email branding/spam evaluation; avoid tenant-wide Auth0/Resend changes.
- Staging rollback rehearsal on the exact release SHA and signed owner approval for any final merge/deployment.
- Owner-approved exception: PostgreSQL encrypted offsite cold restore begins **immediately after launch**; status stays `DATABASE_RECOVERY_UNVERIFIED` until independently restored. It is NOT a renewed prelaunch blocker.

## Evidence taxonomy
- **Newly verified:** Railway staging deployment identity, proxy callback/status sequence, stage app storage/variable-name inventory, new live read-only snapshot outputs, runtime access-log privacy issue.
- **Previously verified:** real Auth0 verified account landing; scoped PG18 TLS and role boundaries; Resend delivery.
- **CI-only:** disposable Postgres lifecycle and Chromium synthetic-member tests; new Docker command regression until CI completes.
- **Blocked:** authenticated current-browser acceptance without isolated saved sign-in; real snapshot availability without staging delivery/persistence; owner MFA and original full-history certification.
- **Not performed:** production deployment, GitHub merge, account credential handling, stage migration, broker order, snapshot publication, private-ledger rerun or rollback.
