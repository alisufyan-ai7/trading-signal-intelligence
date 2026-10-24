"""Read-only review of 30 daily / 8 weekly / 12 monthly S02 backup IDs.

Reads only the owner ACL-protected scheduled history and review latch.
No cloud APIs, keys, manifests, deletion credentials, bucket mutations or
planned installs. A proposed eligible ID is NOT permission to delete.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.recovery import s02_gfs_retention_policy_v0_1 as policy


def _safe_history(path: Path) -> tuple[list[dict], bool]:
    path = Path(path)
    state = path.parent
    if (path.name != "history.jsonl"
            or state.name != "state"
            or state.parent.name != "VowSig-S02-AutoBackup"
            or not path.is_file() or path.is_symlink()
            or state.is_symlink() or state.parent.is_symlink()):
        raise policy.RetentionPlanRejected("expected protected scheduled history missing")
    if path.stat().st_size > 12_000_000:
        raise policy.RetentionPlanRejected("scheduled history exceeds safe bound")
    records = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip() or len(line) > 1800:
                    raise policy.RetentionPlanRejected("invalid scheduled history row")
                value = json.loads(line)
                if type(value) is not dict:
                    raise policy.RetentionPlanRejected("invalid scheduled history row")
                records.append(value)
                if len(records) > 20000:
                    raise policy.RetentionPlanRejected("too many scheduled history rows")
    except (ValueError, UnicodeError, OSError):
        raise policy.RetentionPlanRejected("scheduled history cannot be parsed") from None
    latch = state / "operator-review-required.json"
    if latch.is_symlink():
        raise policy.RetentionPlanRejected("review latch cannot be a link")
    return records, latch.exists()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--as-of-utc", default=None)
    parser.add_argument("--audit-provider-versions", action="store_true")
    parser.add_argument("--acknowledge-read-cost", default=None,
                        choices=["I_ACCEPT_READ_ONLY_CLOUD_LISTING_COST"])
    args = parser.parse_args(argv)
    try:
        records, latch = _safe_history(args.history)
        now = (args.as_of_utc if args.as_of_utc is not None
               else datetime.now(timezone.utc).isoformat(timespec="seconds"))
        result = policy.choose_gfs(
            records, as_of_utc=now, review_latch_present=latch,
        )
        if args.audit_provider_versions:
            if args.acknowledge_read_cost != "I_ACCEPT_READ_ONLY_CLOUD_LISTING_COST":
                raise policy.RetentionPlanRejected("read-only provider consent missing")
            # Import only in explicitly consented provider-audit mode.
            from trading_signal_intelligence.recovery import (
                windows_credential_manager_v0_1 as vault,
                manual_dual_cloud_backup_v0_1 as backups,
                s02_gfs_cloud_inventory_v0_1 as inventory,
            )
            ids = set(result["keep_ids"]) | set(result["eligible_ids"])
            ids.update(result["protected_ids"])
            readers = backups._provider_readers(vault.load_credentials("restore"))
            try:
                result["cloud_inventory"] = inventory.audit_provider_pair(
                    aws_reader=readers[0], b2_reader=readers[1],
                    expected_backup_ids=ids,
                )
            except inventory.CloudInventoryRejected:
                result["cloud_inventory"] = {
                    "status": "INVENTORY_HOLD_PROVIDER_READ_OR_COVERAGE_UNVERIFIED",
                    "provider_deletions_performed": 0,
                }
            # Even fully matching inventory is not a cold-restore or delete
            # authorization. Never expose opaque provider VersionIds.
            result["cloud_deletion_authorized"] = False
        elif args.acknowledge_read_cost is not None:
            raise policy.RetentionPlanRejected("unused provider consent option")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0  # non-destructive plan produced, even when HOLD is reported
    except policy.RetentionPlanRejected:
        print(json.dumps({
            "status": "GFS_READ_ONLY_PLAN_HOLD",
            "provider_deletions_performed": 0,
            "reason": "source history, audit or policy validation failed",
        }, sort_keys=True))
        return 2
    except Exception:
        print('{"status":"GFS_READ_ONLY_PLAN_HOLD","provider_deletions_performed":0,"reason":"unknown safe failure"}')
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
