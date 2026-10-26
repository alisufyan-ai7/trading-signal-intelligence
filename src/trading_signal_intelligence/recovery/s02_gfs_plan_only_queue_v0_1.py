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
    """Recognize exactly one valid private capsule + matching public receipt.

    A left-behind lock, orphan receipt, unknown entry or partial file HOLDs.
    """
    entries = list(pending.iterdir())
    journals = list(state.iterdir())
    if len(entries) > 1 or len(journals) > 2:
        raise PlanOnlyHold("too many or conflicting owner review artifacts")
    if any(path.is_symlink() or not path.is_file() for path in entries + journals):
        raise PlanOnlyHold("unsafe owner review artifact")
    if any(path.name == "prepare-running.lock" for path in journals):
        raise PlanOnlyHold("previous preparation incomplete; operator review required")
    if not entries and not journals:
        return False
    if len(entries) != 1 or len(journals) != 1:
        raise PlanOnlyHold("private plan and public receipt not paired")
    private, receipt = entries[0], journals[0]
    bid = private.name.removesuffix(".aesgcm")
    if (private.name != bid + ".aesgcm"
            or not gfs.BACKUP_ID.fullmatch(bid)
            or receipt.name != "review-" + bid + ".json"
            or not 80 < private.stat().st_size <= approval.MAX_SEALED_BYTES
            or receipt.stat().st_size > 4096):
        raise PlanOnlyHold("invalid or unexpected pending-plan files")
    try:
        metadata = json.loads(receipt.read_text(encoding="ascii"))
        blob = private.read_bytes()
        if (type(metadata) is not dict
                or metadata.get("status") != "PENDING_SEPARATE_OWNER_APPROVAL"
                or metadata.get("backup_id") != bid
                or metadata.get("sealed_sha256") != approval._sha(blob)
                or metadata.get("plan_signed") is not False
                or metadata.get("deletion_authorized") is not False
                or metadata.get("cloud_deletions_performed") != 0):
            raise ValueError
    except Exception:
        raise PlanOnlyHold("private pending-plan integrity HOLD") from None
    return True


def _acquire_preparation_lock(state: Path) -> Path:
    """Exclusive lock BEFORE provider calls. Abandoned lock needs review."""
    lock = state / "prepare-running.lock"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(lock, flags, 0o600)
        os.close(fd)
        return lock
    except Exception:
        raise PlanOnlyHold("private planner busy or interrupted") from None


def _write_private_pending(pending: Path, state: Path,
                           capsule: approval.SealedDeletePlan) -> None:
    """Write once under the exclusive lock already held by the caller."""
    lock = state / "prepare-running.lock"
    if not lock.is_file() or lock.is_symlink():
        raise PlanOnlyHold("exclusive planner lock missing")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        if any(pending.iterdir()) or any(p.name != lock.name for p in state.iterdir()):
            raise PlanOnlyHold("private pending artifact or unsafe state exists")
        path = pending / (capsule.backup_id + ".aesgcm")
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(capsule.blob)
            stream.flush()
            os.fsync(stream.fileno())
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
    except PlanOnlyHold:
        raise
    except Exception:
        raise PlanOnlyHold("private plan publication interrupted; operator review required") from None



def _existing_entries_while_locked(pending: Path, state: Path,
                                   lock: Path, capsule: approval.SealedDeletePlan) -> bool:
    """Check exact capsule/receipt bytes without bypassing the exclusive lock."""
    if not lock.is_file() or lock.is_symlink():
        raise PlanOnlyHold("planner lock missing while verifying publication")
    path = pending / (capsule.backup_id + ".aesgcm")
    receipt = state / ("review-" + capsule.backup_id + ".json")
    if (not path.is_file() or path.is_symlink()
            or not receipt.is_file() or receipt.is_symlink()
            or set(x.name for x in pending.iterdir()) != {path.name}
            or set(x.name for x in state.iterdir()) != {lock.name, receipt.name}):
        raise PlanOnlyHold("private candidate publication incomplete")
    try:
        metadata = json.loads(receipt.read_text(encoding="ascii"))
        return (path.read_bytes() == capsule.blob
                and metadata.get("sealed_sha256") == capsule.sha256
                and metadata.get("status") == "PENDING_SEPARATE_OWNER_APPROVAL"
                and metadata.get("deletion_authorized") is False)
    except Exception:
        raise PlanOnlyHold("private candidate file verification failed") from None


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
    # Exclusive lock is acquired BEFORE any cloud inventory, vault-backed
    # restore or encrypted capsule creation. Crash/failure leaves the lock.
    lock = _acquire_preparation_lock(state)
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
        # Only a complete matched encrypted capsule + receipt releases lock.
        if not _existing_entries_while_locked(pending, state, lock, capsule):
            raise PlanOnlyHold("private plan persistence proof failed")
        lock.unlink()
    except Exception:
        # Keep abandoned lock to require owner manual reconciliation, never
        # silently retry after an ambiguous provider or local disk failure.
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
