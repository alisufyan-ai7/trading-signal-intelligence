"""Separate one-ID-at-a-time, exact-VersionId GFS cloud deletion executor.

Default RELEASE FENCE is CLOSED. No scheduled task, credential targets, CLI
or delete IAM rights are installed. Synthetic tests may monkeypatch the
release fence but the checked production default never issues DeleteObject.

When separately released, each owner-approved execution must:
- re-list complete AWS/B2 versions, re-run GFS, check exact signed capsule;
- independently cold-restore ALL retained snapshots from BOTH providers;
- use two distinct purpose-bound delete identities, not backup writers;
- create a durable exclusive journal BEFORE any delete call;
- delete exactly 4 frozen VersionIds, in strictly named order, no retry;
- verify both clouds contain exactly the retained objects and restore again.
On any ambiguous failure, journal remains and blocks blind re-execution.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

from . import live_dual_provider_transport_v0_1 as providers
from . import manual_dual_cloud_backup_v0_1 as backup
from . import s02_gfs_retention_policy_v0_1 as gfs
from . import s02_gfs_owner_signed_prune_plan_v0_1 as approvals
from . import s02_gfs_exact_inventory_for_pruning_v0_1 as inventory
from . import s02_gfs_retained_restore_audit_v0_1 as cold

# Requires separate, explicit owner-approved code-review/release change to
# switch on. Never set this via CLI, env var, GitHub secret or config file.
PRODUCTION_CLOUD_DELETE_ENABLED = False
FINAL_STATUS = "FOUR_EXACT_CLOUD_VERSIONS_REMOVED_RETAINED_RESTORES_VERIFIED"


class GfsExecutionHold(RuntimeError):
    """Sanitized incident requiring human reconciliation, never retry."""


class _DurableOneShotJournal:
    def __init__(self, directory: Path, plan_sha256: str, backup_id: str) -> None:
        if (not isinstance(directory, Path)
                or directory.is_symlink()
                or not directory.is_dir()
                or directory.name != "state"
                or directory.parent.name != "VowSig-S02-RetentionOperator"
                or not directory.parent.is_dir()
                or directory.parent.is_symlink()):
            raise GfsExecutionHold("isolated owner-protected deletion journal required")
        self.path = directory / (backup_id + ".jsonl")
        if self.path.exists() or self.path.is_symlink():
            raise GfsExecutionHold("existing or suspicious deletion journal; manual review")
        if os.name != "nt":
            if directory.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise GfsExecutionHold("deletion journal must be owner-only")
        try:
            # Exclusive create without following symlinks. No retry after
            # creating the state record, even after a partial network write.
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(str(self.path), flags, 0o600)
            self._file = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
            self.record("BEGIN", backup_id)
        except Exception:
            raise GfsExecutionHold("cannot durably initialize deletion journal") from None

    def record(self, state: str, stage: str) -> None:
        if (type(state) is not str or state not in {
                "BEGIN", "ATTEMPT", "RECEIPT", "POSTCHECK_PASS", "COMPLETE", "HOLD"}
                or type(stage) is not str or len(stage) > 120):
            raise GfsExecutionHold("invalid private journal entry")
        try:
            self._file.write(json.dumps(
                {"state": state, "stage": stage},
                sort_keys=True, separators=(",", ":")) + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())
        except Exception:
            raise GfsExecutionHold("journal fsync failed; reconciliation required") from None

    def close(self) -> None:
        try:
            self._file.close()
        except Exception:
            pass


def _check_prior_operations(directory: Path) -> None:
    """Block all new pruning after ANY earlier incomplete/unknown operation.

    File names bind to BACKUP IDs, not randomized encrypted plan digests,
    preventing a second plan for the same candidate from bypassing history.
    """
    if (not isinstance(directory, Path)
            or directory.name != "state"
            or directory.parent.name != "VowSig-S02-RetentionOperator"
            or not directory.is_dir()
            or directory.is_symlink() or directory.parent.is_symlink()):
        raise GfsExecutionHold("protected retention-operator state not ready")
    entries = list(directory.iterdir())
    if len(entries) > 20000:
        raise GfsExecutionHold("deletion history bound exceeded")
    for path in entries:
        if path.is_symlink() or not path.is_file():
            raise GfsExecutionHold("unexpected deletion history entry")
        if path.name == "current-operation.lock":
            raise GfsExecutionHold("another or interrupted deletion operation pending")
        if (path.suffix != ".jsonl"
                or not gfs.BACKUP_ID.fullmatch(path.stem)
                or path.stat().st_size > 131072):
            raise GfsExecutionHold("unrecognized deletion history entry")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            last = json.loads(lines[-1])
            if (not lines or type(last) is not dict
                    or set(last) != {"state", "stage"}
                    or last["state"] != "COMPLETE"):
                raise ValueError
        except Exception:
            raise GfsExecutionHold(
                "prior incomplete deletion; block every future operation"
            ) from None


class _ExclusiveOperatorLock:
    """One process at a time, fail-closed on crash/abandoned lock."""
    def __init__(self, directory: Path) -> None:
        self.path = directory / "current-operation.lock"
        try:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(str(self.path), flags, 0o600)
            os.close(fd)
        except Exception:
            raise GfsExecutionHold("operator already running or lock unavailable") from None

    def release(self, completed: bool) -> None:
        # If a provider call or audit failed, retain the lock for manual
        # reconciliation rather than allowing any unrelated candidate prune.
        if completed:
            try:
                self.path.unlink()
            except Exception:
                raise GfsExecutionHold("cannot release completed operator lock") from None



def _check_prior_operations_after_lock(directory: Path) -> None:
    # Verify all other journals while preserving the one lock just acquired.
    lock = directory / "current-operation.lock"
    if not lock.is_file() or lock.is_symlink():
        raise GfsExecutionHold("exclusive lock unexpectedly missing")
    for item in directory.glob("*.jsonl"):
        if (item.is_symlink() or not gfs.BACKUP_ID.fullmatch(item.stem)
                or item.stat().st_size > 131072):
            raise GfsExecutionHold("invalid existing deletion journal")
        try:
            last = json.loads(item.read_text(encoding="utf-8").splitlines()[-1])
            if last.get("state") != "COMPLETE":
                raise ValueError
        except Exception:
            raise GfsExecutionHold("incomplete earlier prune blocks new run") from None

def _same_fresh_policy(
    *, history: list[dict], now: str, pins: tuple[str, ...],
    latch_present: bool,
) -> dict:
    return gfs.choose_gfs(
        history, as_of_utc=now, extra_pinned_ids=pins,
        review_latch_present=latch_present,
    )


def _restore_kept(
    *, policy: dict, reader_credentials: tuple[tuple[str, str], ...],
    passphrase: str,
) -> None:
    ids = sorted(set(policy["keep_ids"]) | set(policy["protected_ids"]))
    try:
        report = cold.audit_retained_recovery_points(
            backup_ids=ids, read_credentials=reader_credentials,
            recovery_passphrase=passphrase,
        )
        if (report.get("status") != "ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED"
                or report.get("verified_backup_count") != len(ids)
                or report.get("provider_deletions_performed") != 0):
            raise GfsExecutionHold("retained backup recovery verification incomplete")
    except Exception:
        raise GfsExecutionHold("both-provider retained cold restore gate failed") from None


def _delete_clients(
    *, reader_credentials: tuple[tuple[str, str], ...],
    delete_credentials: tuple[tuple[str, str], ...],
) -> tuple[Any, Any]:
    if (type(reader_credentials) is not tuple or len(reader_credentials) != 2
            or type(delete_credentials) is not tuple or len(delete_credentials) != 2
            or any(type(x) is not tuple or len(x) != 2 for x in
                   (*reader_credentials, *delete_credentials))
            or len({x[0] for x in (*reader_credentials, *delete_credentials)}) != 4):
        raise GfsExecutionHold("separate AWS/B2 reader and deletion identities required")
    try:
        return backup._configured_clients(
            delete_credentials, (providers.AWS, providers.B2)
        )
    except Exception:
        raise GfsExecutionHold("separate scoped delete clients unavailable") from None


def execute_single_owner_approved_prune(
    *, sealed_blob: bytes, signature: bytes, pinned_owner_public_key: bytes,
    private_phrase: str, current_utc: str,
    history: list[dict], extra_pinned_ids: tuple[str, ...],
    review_latch_present: bool,
    aws_reader: Any, b2_reader: Any,
    reader_credentials: tuple[tuple[str, str], ...],
    delete_credentials: tuple[tuple[str, str], ...],
    journal_directory: Path,
) -> dict:
    """One shot only; one backup ID; 4 exact VersionIds; no retry.

    Never use the owner recovery phrase as an Ed25519 signing key. The
    private approval key lives outside the VPS and outside this program.
    """
    if not PRODUCTION_CLOUD_DELETE_ENABLED:
        raise GfsExecutionHold("production cloud deletion release fence is closed")
    if type(review_latch_present) is not bool or review_latch_present:
        raise GfsExecutionHold("operator incident latch present")
    # Guard all candidate IDs, even if the owner seals a NEW capsule with
    # a fresh random nonce after an earlier partial provider failure.
    _check_prior_operations(Path(journal_directory))
    try:
        policy = _same_fresh_policy(
            history=history, now=current_utc, pins=extra_pinned_ids,
            latch_present=review_latch_present,
        )
        expected = (set(policy["keep_ids"]) | set(policy["eligible_ids"]) |
                    set(policy["protected_ids"]))
        exact = inventory.read_exact_version_inventory(
            aws_reader=aws_reader, b2_reader=b2_reader, expected_ids=expected
        )
        permit = approvals.verify_owner_signed_candidate(
            blob=sealed_blob, private_phrase=private_phrase,
            signature=signature, pinned_owner_public_key=pinned_owner_public_key,
            current_utc=current_utc, current_policy=policy,
            version_inventory=exact,
        )
        # Complete two-cloud authenticated SQLite restore before ANY write.
        _restore_kept(
            policy=policy, reader_credentials=reader_credentials,
            passphrase=private_phrase,
        )
        deleters = _delete_clients(
            reader_credentials=reader_credentials,
            delete_credentials=delete_credentials,
        )
    except Exception:
        raise GfsExecutionHold("owner signed plan, versions or predelete restore HOLD") from None

    journal: _DurableOneShotJournal | None = None
    operator_lock: _ExclusiveOperatorLock | None = None
    complete = False
    attempts = 0
    try:
        operator_lock = _ExclusiveOperatorLock(Path(journal_directory))
        _check_prior_operations_after_lock(Path(journal_directory))
        journal = _DurableOneShotJournal(
            Path(journal_directory), permit.sealed_sha256, permit.backup_id
        )
        by_role = {"aws_manifest": deleters[0], "aws_data": deleters[0],
                   "b2_manifest": deleters[1], "b2_data": deleters[1]}
        for role, bucket, key, version in permit.objects:
            if role not in approvals.EXPECTED_OPERATIONS or role not in by_role:
                raise GfsExecutionHold("unexpected exact provider deletion role")
            journal.record("ATTEMPT", role)
            attempts += 1
            try:
                # Important: NEVER call without VersionId; key-only DELETE
                # inserts a delete marker and does not free cloud storage.
                response = by_role[role].delete_object(
                    Bucket=bucket, Key=key, VersionId=version
                )
                if (type(response) is not dict
                        or response.get("VersionId") != version
                        or response.get("DeleteMarker") is True):
                    raise GfsExecutionHold("provider deletion receipt ambiguous")
                journal.record("RECEIPT", role)
            except Exception:
                raise GfsExecutionHold(
                    "provider delete incomplete/ambiguous; no automatic retry"
                ) from None
        if attempts != 4:
            raise GfsExecutionHold("four-operation cap not met")
        survivors = expected - {permit.backup_id}
        inventory.read_exact_version_inventory(
            aws_reader=aws_reader, b2_reader=b2_reader, expected_ids=survivors
        )
        # ALL protected/retained restore points still recover from BOTH clouds.
        _restore_kept(
            policy=policy, reader_credentials=reader_credentials,
            passphrase=private_phrase,
        )
        journal.record("POSTCHECK_PASS", permit.backup_id)
        journal.record("COMPLETE", permit.backup_id)
        complete = True
        return {
            "status": FINAL_STATUS,
            "backup_id": permit.backup_id,
            "provider_deletions_performed": 4,
            "remaining_recovery_points_verified": len(
                set(policy["keep_ids"]) | set(policy["protected_ids"])
            ),
            "automatic_retry_enabled": False,
            "new_scheduled_task_installed": False,
        }
    except Exception:
        if journal is not None:
            try:
                journal.record("HOLD", "MANUAL_RECONCILIATION_REQUIRED")
            except Exception:
                pass
        raise GfsExecutionHold(
            "partial or uncertain cloud expiration; durable hold, no retry"
        ) from None
    finally:
        if journal is not None:
            journal.close()
        if operator_lock is not None:
            operator_lock.release(completed=complete)
