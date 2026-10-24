# TODO

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
