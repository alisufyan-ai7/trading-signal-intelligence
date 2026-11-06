# TODO

## CURRENT PRODUCTION LAUNCH ACTIONS — 2026-11-06

Read [current state](docs/VOWSIG_START_HERE_CURRENT_STATE.md) and [next-chat step](docs/vowsig-next-chat-execution-handoff.md), not the October backlog below, for current work. **ONE full authenticated release, no added features.**

- [x] Implement/test current Free member Signal Center and owner dashboards on draft PR #93; real staging member login/watchlist and founder solo TOTP/admin PASS.
- [x] Owner-approved policy: independent historic rights/cost/K5/full population certification **after** launch, **N/A** before real signature.
- [x] Production PG18 restricted SQL roles/schema 001–010 owner-operated atomic PASS; **DO NOT RERUN**.
- [x] Production Railway app 12 vars including OIDC/DB/CSRF/TOTP staged, both account flags **OFF**, **no production deployment**.
- [x] Resend sender domain verified and existing API key present; Auth0 issuer discovery/JWKS verified publicly.
- [x] Current exact-reviewed read-only app-role TLS acceptance script created/tested in PR.
- [ ] Owner returns one sanitized `PRODUCTION_APP_ROLE_TLS_PRIVILEGE` check receipt from existing production Postgres Console (no SQL schema changes).
- [ ] Verify production Auth0 allowed callback/logout/web origin and **real** email verification via Resend; check negative/replay cases.
- [ ] One coordinated production candidate: verified-full **app-container** DB connection, real owner production MFA/rotation/recovery, market rights, member UX/mobile/security, snapshot, app-only rollback evidence.
- [ ] Separate owner approval of **exact full release SHA** before PR merge/app live deployment.
- [ ] **FIRST immediate postlaunch:** independently encrypted recurring Railway PostgreSQL S3/B2 backups, alerts, retention and actual cold restore; `DATABASE_RECOVERY_UNVERIFIED` until PASS.
- [ ] Separately certify frozen nine-market historical source rights/costs/crypto K5/cohort before any return/win-rate/equity publication.

**No new staging publisher, no source freeze/VPS chain reruns, no payment/alerts/broker execution or unauthorized six-market details.** Historical S02/GFS work below retains its original date-specific scope.

---


Current priorities are tracked by the four validation gates. See `docs/next-actions.md` for execution details.

- [ ] G1 Data reliability
- [ ] G2 Commercial data rights
- [ ] G3 Strategy evidence
- [ ] G4 Customer value

## VowSig S02 cloud backup & GFS — 2026-10-24

- [x] Real AES-encrypted S02 AWS S3 + B2 manual backup and independent cold restores verified (EXP053).
- [x] Daily 04:15 VPS-local Interactive automatic S02 task installed and **first** task-run cold restore verified (EXP054–055).
- [x] GFS 30 daily / 8 weekly / 12 monthly selection and protected baseline implemented in draft PR #85; real paired exact cloud-version inventory PASS (EXP056–059).
- [ ] Observe **second natural daily** scheduled run, task result, new ID, two-provider recoveries and no incident latch.
- [ ] Run focused native Windows GFS synthetic tests against exact frozen source (separate from prior real cloud PASS).
- [ ] Engineer a separate, restricted version-aware cleanup executor with independently protected delete credentials, seven-day owner-approved signed plan, pre/post retained cold restore checks and immutable audit. **No physical cleanup or deletion is yet installed.**
- [ ] Deliver failure notifications, monitor AWS/B2 bills and review backup scope for other SQLite/IP classes.
- [ ] Keep owner-held recovery passphrase safely off VPS, with all historical backup evidence/receipts preserved.

See [canonical Oct 24 operations](docs/vowsig-operational-status-2026-10-24.md), [recovery index](research/recovery/README.md), Issue #67 and draft PR #85. Original G1–G4 checklist above remains a historical cross-cutting gate list, not a statement that S02 GFS is unfinished or active deletion is done.
