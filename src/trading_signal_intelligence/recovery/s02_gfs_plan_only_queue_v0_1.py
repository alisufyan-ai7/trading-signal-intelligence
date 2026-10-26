"""Non-destructive S02 GFS candidate queue, separate from delete executor.

UNATTENDED: local eligibility first. If healthy/eligible, read-only scoped
four-prefix inventory + full retained two-cloud cold restores, then encrypt
ONE candidate as an UNSIGNED pending capsule. NO delete credentials/signing
key/real delete API. Lock or incomplete plan state blocks further runs.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Callable

from . import s02_gfs_retention_policy_v0_1 as gfs
from . import s02_gfs_exact_inventory_for_pruning_v0_1 as inventory
from . import s02_gfs_owner_signed_prune_plan_v0_1 as approval
from . import s02_gfs_retained_restore_audit_v0_1 as cold

STATE_ROOT = "VowSig-S02-GFS-PlanOnly"
PRODUCTION_CLOUD_DELETE_ENABLED = False
ALLOWED_PENDING = frozenset({"pending", "state"})
EXPECTED_HOLDS = {
    "DUAL_CLOUD_VERSION_AND_RESTORE_INVENTORY_REQUIRED",
    "SEPARATE_7_DAY_OWNER_APPROVAL_REQUIRED",
}


class PlanOnlyHold(RuntimeError):
    """Sanitized state, never a source of credential/version metadata."""


def check_eligibility(*, history: list[dict], now_utc: str,
                      review_latch_present: bool,
                      extra_pinned_ids: tuple[str, ...] = ()) -> dict:
    """No vault reads, providers, cloud costs, filesystem writes or deletions."""
    try:
        policy = gfs.choose_gfs(
            history, as_of_utc=now_utc,
            extra_pinned_ids=extra_pinned_ids,
            review_latch_present=review_latch_present,
        )
        holds = set(policy["hold_reasons"])
        if not holds and not policy["eligible_ids"]:
            status = "NO_ELIGIBLE_BACKUP"
        elif holds == EXPECTED_HOLDS and policy["eligible_ids"]:
            status = "ELIGIBLE_FOR_PRIVATE_PREPARATION"
        else:
            status = "GFS_SAFETY_HOLD"
        return {
            "status": status,
            "as_of_utc": policy["as_of_utc"],
            "policy": policy["policy"],
            "plan_sha256": policy["plan_sha256"],
            "eligible_count": len(policy["eligible_ids"]),
            "retained_count": len(set(policy["keep_ids"]) |
                                  set(policy["protected_ids"])),
            "hold_reasons": policy["hold_reasons"],
            "cloud_deletion_authorized": False,
            "provider_deletions_performed": 0,
            "network_requests": 0,
        }
    except Exception:
        return {"status": "GFS_SAFETY_HOLD",
                "reason": "history or retention state invalid",
                "cloud_deletion_authorized": False,
                "provider_deletions_performed": 0,
                "network_requests": 0}


def _state_directory(base: Path) -> tuple[Path, Path]:
    """Never create a writable root or assume correct Windows ACLs.

    Separate installer must establish a trusted owner-only ProgramData path,
    with an ACL verified outside this library before scheduling.
    """
    root = Path(base)
    if (root.name != STATE_ROOT or not root.is_dir() or root.is_symlink()
            or root.parent.name != "ProgramData"
            or (root / "pending").is_symlink()
            or (root / "state").is_symlink()
            or not (root / "pending").is_dir()
            or not (root / "state").is_dir()):
        raise PlanOnlyHold("isolated owner ACL retention planner directory missing")
    for name in ALLOWED_PENDING:
        child = root / name
        if os.name != "nt" and child.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise PlanOnlyHold("private planner state not owner-only")
    return root / "pending", root / "state"


def _existing_entries(pending: Path, state: Path) -> bool:
    """Any anomaly/lock fails closed; existing private capsules block next plan."""
    if any(state.iterdir()):
        raise PlanOnlyHold("review existing planner state before any new preparation")
    entries = list(pending.iterdir())
    if len(entries) > 20:
        raise PlanOnlyHold("too many pending private plans")
    for entry in entries:
        if (entry.is_symlink() or not entry.is_file()
                or not entry.name.startswith("backup-")
                or not entry.name.endswith(".aesgcm")
                or not gfs.BACKUP_ID.fullmatch(entry.name[:-7])
                or entry.stat().st_size > approval.MAX_SEALED_BYTES):
            raise PlanOnlyHold("unknown private planner artifact")
    return bool(entries)


def _write_private_pending(pending: Path, state: Path, capsule: approval.SealedDeletePlan) -> None:
    """Exclusive write-ahead lock; crash leaves HOLD, never auto retries."""
    lock = state / "prepare-running.lock"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
        os.close(fd)
    except Exception:
        raise PlanOnlyHold("private planner is busy or interrupted") from None
    complete = False
    try:
        if any(pending.iterdir()):
            raise PlanOnlyHold("private pending plan already exists")
        path = pending / (capsule.backup_id + ".aesgcm")
        if path.is_symlink() or path.exists():
            raise PlanOnlyHold("refuse to overwrite candidate capsule")
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(capsule.blob)
            stream.flush()
            os.fsync(stream.fileno())
        # The capsule is UNAPPROVED. The public receipt excludes all VersionIds.
        receipt = state / ("review-" + capsule.backup_id + ".json")
        record = {
            "status": "PENDING_SEPARATE_OWNER_APPROVAL",
            "backup_id": capsule.backup_id,
            "sealed_sha256": capsule.sha256,
            "not_before_utc": capsule.earliest_review_utc,
            "expires_utc": capsule.expires_utc,
            "plan_signed": False,
            "deletion_authorized": False,
            "cloud_deletions_performed": 0,
        }
        fd = os.open(receipt, flags, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":"))+"\n")
            stream.flush()
            os.fsync(stream.fileno())
        complete = True
    except PlanOnlyHold:
        raise
    except Exception:
        raise PlanOnlyHold("private plan publication interrupted; review required") from None
    finally:
        if complete:
            try:
                lock.unlink()
            except Exception:
                raise PlanOnlyHold("cannot clear successful owner planner lock") from None
        # On failure keep lock, capsule and any partial file for MANUAL review.


def prepare_one_unsigned_plan(
    *, history: list[dict], now_utc: str, review_latch_present: bool,
    base_directory: Path,
    aws_reader: Any, b2_reader: Any,
    reader_credentials: tuple[tuple[str, str], ...],
    plan_passphrase: str, recovery_passphrase: str,
    extra_pinned_ids: tuple[str, ...] = (),
    retained_restore: Callable[..., dict] | None = None,
) -> dict:
    """Never signs a plan, never deletes. Max one candidate per call."""
    checked = check_eligibility(
        history=history, now_utc=now_utc,
        review_latch_present=review_latch_present,
        extra_pinned_ids=extra_pinned_ids,
    )
    if checked["status"] == "NO_ELIGIBLE_BACKUP":
        return checked
    if checked["status"] != "ELIGIBLE_FOR_PRIVATE_PREPARATION":
        raise PlanOnlyHold("retention eligibility or fresh daily backup HOLD")
    if (type(plan_passphrase) is not str or not 16 <= len(plan_passphrase) <= 256
            or type(recovery_passphrase) is not str
            or not 16 <= len(recovery_passphrase) <= 1024
            or plan_passphrase == recovery_passphrase):
        raise PlanOnlyHold("independent owner plan/recovery secrets required")
    pending, state = _state_directory(base_directory)
    if _existing_entries(pending, state):
        return {
            "status": "PENDING_OWNER_REVIEW",
            "eligible_count": checked["eligible_count"],
            "cloud_deletion_authorized": False,
            "provider_deletions_performed": 0,
            "network_requests": 0,
        }
    try:
        policy = gfs.choose_gfs(
            history, as_of_utc=now_utc,
            extra_pinned_ids=extra_pinned_ids,
            review_latch_present=review_latch_present,
        )
        # The policy is calculated again immediately before provider reads.
        ids = set(policy["eligible_ids"]) | set(policy["keep_ids"]) | set(policy["protected_ids"])
        exact = inventory.read_exact_version_inventory(
            aws_reader=aws_reader, b2_reader=b2_reader, expected_ids=ids,
        )
        retained = sorted(set(policy["keep_ids"]) | set(policy["protected_ids"]))
        verify = cold.audit_retained_recovery_points if retained_restore is None else retained_restore
        recovered = verify(
            backup_ids=retained, read_credentials=reader_credentials,
            recovery_passphrase=recovery_passphrase,
        )
        if (type(recovered) is not dict
                or recovered.get("status") != "ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED"
                or recovered.get("verified_backup_count") != len(retained)
                or recovered.get("provider_deletions_performed") != 0):
            raise PlanOnlyHold("independent two-provider retained restores HOLD")
        # Bound to ONE eligible ID. The rest require individual future owner review.
        candidate = policy["eligible_ids"][0]
        capsule = approval.freeze_one_candidate(
            policy=policy, candidate=candidate,
            version_inventory=exact, prepared_utc=now_utc,
            plan_passphrase=plan_passphrase,
        )
        _write_private_pending(pending, state, capsule)
    except Exception:
        raise PlanOnlyHold("private GFS plan preparation/inventory/recovery HOLD") from None
    return {
        "status": "PENDING_SEPARATE_OWNER_APPROVAL",
        "backup_id": capsule.backup_id,
        "sealed_sha256": capsule.sha256,
        "not_before_utc": capsule.earliest_review_utc,
        "expires_utc": capsule.expires_utc,
        "other_eligible_count": len(policy["eligible_ids"]) - 1,
        "plan_signed": False,
        "cloud_deletion_authorized": False,
        "provider_deletions_performed": 0,
    }
