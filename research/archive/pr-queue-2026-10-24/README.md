# Historical PR source archive — 2026-10-24

**Status: IMMUTABLE HISTORICAL SOURCE; NOT ACTIVE CODE, NOT AN INSTALLER, NOT A RECOMMENDATION TO REPLAY OLD CLOUD/IAM ACTIONS.**

This archive was created as part of the owner-requested thorough audit and reduction of **18 open GitHub PRs** in the private repository `alisufyan-ai7/trading-signal-intelligence`. It preserves **byte-for-byte Git file contents** of three unique, earlier prospective branches so their original work is accessible from `main` even when their PRs are closed or remote source branches later disappear. The original `PR-NN/<original path>` hierarchy is retained below this folder. The original individual commits and full PR discussions stay accessible at the linked GitHub PRs; none were force-pushed or branch-deleted during this preservation.

| Source | Exact reviewed tip | Archived contents | Status / caveat |
|---|---|---|---|
| [PR #68](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/68) | `0f8231f1dddbd1df43bd1e9d19de5bbdd72a840b` | 4 nonsecret AWS/B2 pilot IAM JSON/config/operator instructions under `PR-68/ops/backup/` | **Historical October 22 `$0` / no-real-transfer preparation**, explicitly superseded by later owner-verified real S02 backups and permission updates. No cloud changes happen merely because these files are in Git. |
| [PR #75](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/75) | `89611cb7b2ac5128e04eb4436ca30a457785727c` | 3 original EXP042 botocore fake-HTTP proof/script/tests/failed-and-corrected chronology under `PR-75/` | **No-network development-only SDK experiment**; do not treat earlier `131 PASS + 1 SKIP` as release PASS. Its unique source and regression evidence are preserved for future historical replay, not active test discovery. |
| [PR #76](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/76) | `293730690796de6b49b4a494c1108e35301b9ad7` | 4 original seven-wheel official PyPI SHA-256 lock / disposable SDK downloader / offline test / research doc under `PR-76/` | **Frozen Python package versions and hashes are historical**, not necessarily today's recommended PyPI versions. Do not execute archived downloader as current VPS backup setup. |

All **11 archive files** were fetched from their exact source commit, committed under this isolated inert `research/archive` path with unchanged UTF-8 file bytes, and are intended to enter `main` with a **documentation/evidence-only** consolidation PR. Original `.py` source and test files are preserved as `.py.txt` with **identical original UTF-8 content/Git blob SHA** to prevent pytest test discovery or accidental execution; original relative path is otherwise retained. `.json` and `.md` historical files remain in inert archive paths, outside active `scripts/`, `tests/`, `ops/` and importable `src/`; no code/scheduler imports them and no AWS/cloud/task action runs from this location.

**To recover exactly what was closed:** open the historical PR in GitHub (Conversation / Commits / Files changed); click the exact tip SHA above; recover any path using that SHA; or read its byte-preserved archived copy from this folder. GitHub PRs can be reopened if a prospective restoration is required. New work must be rebased and re-tested on current `main`; never resurrect dated credentials/billing/governance assumptions without fresh approval.

## Relationship to current operational evidence

The separately compiled [2026-10-24 VowSig operational handoff](../../../docs/vowsig-operational-status-2026-10-24.md) and [recovery evidence index](../../recovery/README.md) preserve the actual **manual+scheduled two-provider S02 backup PASS**, two-provider cold-restore PASS, and GFS exact-version inventory PASS. Those real successes supersede the historical preparation/hard-$0 holds only prospectively; original failed/halt evidence remains immutable.

See [PR audit and disposition register](../../../docs/pr-queue-review-2026-10-24.md) for all 18 initial PRs, including staged backup PR #85 and untouched frozen-dependency guard #50.
