"""CLI for scheduled NON-DESTRUCTIVE GFS check + private unsigned plan queue.

Default --mode check requires NO vault, no network and no filesystem writes.
--mode prepare requires preprovisioned owner-only state, two distinct vault
secrets and existing AWS/B2 READERS. Never accesses cloud deletion identities,
owner signing key or delete executor. No mock hooks are accepted by the CLI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.recovery import s02_gfs_plan_only_queue_v0_1 as queue
from trading_signal_intelligence.recovery import s02_gfs_retention_policy_v0_1 as policy
from scripts.vowsig_s02_gfs_retention_preview_v0_1 import _safe_history



PINS_SCHEMA = "vowsig-s02-gfs-owner-extra-pins-v1"


def _load_owner_pins(plan_root: Path) -> tuple[str, ...]:
    """Immutable-installed, owner ACL protected explicit list; never default to []."""
    root = Path(plan_root)
    source = root / "owner-protected-ids.json"
    if (root.is_symlink() or not source.is_file() or source.is_symlink()
            or source.stat().st_size > 8192):
        raise queue.PlanOnlyHold("owner-protected backup pin file required")
    try:
        obj = json.loads(source.read_text(encoding="utf-8"))
        if (type(obj) is not dict
                or set(obj) != {"schema", "extra_pinned_ids"}
                or obj["schema"] != PINS_SCHEMA
                or type(obj["extra_pinned_ids"]) is not list
                or len(obj["extra_pinned_ids"]) > 100
                or len(set(obj["extra_pinned_ids"])) != len(obj["extra_pinned_ids"])
                or any(type(x) is not str or not policy.BACKUP_ID.fullmatch(x)
                       for x in obj["extra_pinned_ids"])):
            raise ValueError
        return tuple(obj["extra_pinned_ids"])
    except Exception:
        raise queue.PlanOnlyHold("owner protected backup pins invalid") from None



def _validated_real_planner_root(path: Path) -> Path:
    """Native Windows never accepts user-supplied substitute ProgramData roots."""
    requested = Path(path)
    if sys.platform == "win32":
        installed = os.environ.get("ProgramData")
        if not installed:
            raise queue.PlanOnlyHold("Windows ProgramData root unavailable")
        canonical = Path(installed) / queue.STATE_ROOT
        if (requested.is_symlink()
                or requested.resolve(strict=False) != canonical.resolve(strict=False)):
            raise queue.PlanOnlyHold("planner root outside fixed Windows ProgramData")
    return requested


def _safe_print(payload: dict) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--mode", choices=["check", "prepare", "status"], default="check")
    parser.add_argument("--history", type=Path)
    parser.add_argument("--plan-root", type=Path)
    parser.add_argument("--acknowledge-read-cost",
                        choices=["I_ACCEPT_READ_ONLY_CLOUD_RESTORE_COST"])
    args = parser.parse_args(argv)
    try:
        if args.mode == "status":
            if (args.history is not None or args.plan_root is None
                    or args.acknowledge_read_cost is not None):
                raise queue.PlanOnlyHold("read-only review-status arguments invalid")
            state = queue.pending_owner_review_status(
                base_directory=_validated_real_planner_root(args.plan_root))
            _safe_print(state)
            return 0
        if args.history is None:
            raise queue.PlanOnlyHold("scheduled S02 history path required")
        if args.mode == "check":
            if args.plan_root is not None or args.acknowledge_read_cost is not None:
                raise queue.PlanOnlyHold("check-only mode does not use cloud options")
        else:
            if (args.plan_root is None
                    or args.acknowledge_read_cost !=
                       "I_ACCEPT_READ_ONLY_CLOUD_RESTORE_COST"):
                raise queue.PlanOnlyHold("read-only cloud expense consent missing")

        rows, latch = _safe_history(args.history)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        check = queue.check_eligibility(
            history=rows, now_utc=now, review_latch_present=latch,
        )
        if args.mode == "check" or check["status"] != "ELIGIBLE_FOR_PRIVATE_PREPARATION":
            _safe_print(check)
            return 0 if check["status"] in {
                "NO_ELIGIBLE_BACKUP", "ELIGIBLE_FOR_PRIVATE_PREPARATION"
            } else 2

        # No alternate user-selected destination for private capsules on VPS.
        # Resolve/check before owner pins, vault or cloud contact.
        root = _validated_real_planner_root(args.plan_root)
        # Before any credential/cloud use, fail closed if explicit owner pins
        # were not installed or changed. Re-evaluate eligibility with pins.
        pins = _load_owner_pins(root)
        check = queue.check_eligibility(
            history=rows, now_utc=now, review_latch_present=latch,
            extra_pinned_ids=pins,
        )
        if check["status"] != "ELIGIBLE_FOR_PRIVATE_PREPARATION":
            _safe_print(check)
            return 0 if check["status"] == "NO_ELIGIBLE_BACKUP" else 2

        # An unsigned plan already awaiting the owner must NOT be overwritten,
        # and should NOT cause repeated cloud reads, restore bills or vault use.
        pending, state = queue._state_directory(root)
        if queue._existing_entries(pending, state):
            _safe_print({
                "status": "PENDING_OWNER_REVIEW",
                "cloud_deletion_authorized": False,
                "provider_deletions_performed": 0,
                "network_requests": 0,
            })
            return 0

        from trading_signal_intelligence.recovery import (
            windows_credential_manager_v0_1 as vault,
            s02_gfs_plan_only_vault_v0_1 as private_vault,
            manual_dual_cloud_backup_v0_1 as backup,
        )
        # Three independently held READ-ONLY secrets, two reader pairs and
        # S02 disaster-recovery phrase. Never read backup writer/delete roles.
        readers = vault.load_credentials("restore")
        recovery_secret = vault.load_scheduled_recovery_passphrase()
        plan_secret = private_vault.read_plan_passphrase()
        if plan_secret == recovery_secret:
            raise queue.PlanOnlyHold("independent plan and recovery vault targets must differ")
        clients = backup._provider_readers(readers)
        result = queue.prepare_one_unsigned_plan(
            history=rows, now_utc=now, review_latch_present=latch,
            base_directory=root,
            aws_reader=clients[0], b2_reader=clients[1],
            reader_credentials=readers,
            plan_passphrase=plan_secret, recovery_passphrase=recovery_secret,
            extra_pinned_ids=pins,
        )
        _safe_print(result)
        return 0 if result["status"] in {
            "NO_ELIGIBLE_BACKUP", "PENDING_SEPARATE_OWNER_APPROVAL",
            "PENDING_OWNER_REVIEW"
        } else 2
    except (queue.PlanOnlyHold, policy.RetentionPlanRejected):
        _safe_print({
            "status": "GFS_PLAN_ONLY_HOLD",
            "reason": "local safety, cloud-read, credential or private queue blocked",
            "provider_deletions_performed": 0,
            "cloud_deletion_authorized": False,
        })
        return 2
    except Exception:
        _safe_print({
            "status": "GFS_PLAN_ONLY_HOLD",
            "reason": "unknown private planner failure",
            "provider_deletions_performed": 0,
            "cloud_deletion_authorized": False,
        })
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
