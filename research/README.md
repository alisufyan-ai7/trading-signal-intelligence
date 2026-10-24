# Research Evidence

## Latest verified S02 backup evidence — 2026-10-24

Read [current operational handoff](../docs/vowsig-operational-status-2026-10-24.md), then the immutable `research/recovery/EXP-2026-053` through `EXP-2026-059` files. Owner-run S02-only encrypted AWS+B2 manual + first scheduled backup and both-provider cold restores passed; 2 backup IDs and 4 exact encrypted data/manifest versions per provider passed read-only inventory. The GFS 30-daily/8-weekly/12-monthly policy is staged in draft PR #85; **automatic physical cloud deletion is not enabled**. A future daily run must be independently observed. No secrets, decrypted data or version IDs belong in Git.

This directory stores experiment definitions and results that support or reject project hypotheses.

## Convention

Each experiment should have a stable ID, for example:

`EXP-2026-001-mt5-symbol-discovery`

and should record:

- date
- objective
- code/config commit SHA
- data source and source-server identity (without account secrets/IDs)
- instruments and date ranges
- assumptions
- exact commands/config
- output summary
- anomalies
- conclusion
- resulting decision/next action

Do not replace old results when logic changes. Create a new experiment/version so strategy evolution remains auditable.
