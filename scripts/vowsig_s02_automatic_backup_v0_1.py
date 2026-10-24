"""Daily unattended S02 AWS/B2 backup; no GUI, no .env, no deletes.

Windows Task Scheduler invokes this in the SAME still-logged-on Windows user
session whose Generic Credential vault contains four cloud credentials and the
recovery passphrase. Existing production tasks are never touched here.

On any ambiguous partial cloud outcome, latch REVIEW_REQUIRED and do not
schedule another attempt until a human reconciles the run. No auto retry,
automatic removal of historical versions, or unverified recovery successes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as cloud
from trading_signal_intelligence.recovery import windows_credential_manager_v0_1 as vault

TASK_NAME = "VowSig S02 Encrypted Dual Cloud Backup"
STATE_DIR_NAME = "VowSig-S02-AutoBackup"
REVIEW_FLAG = "operator-review-required.json"
HISTORY = "history.jsonl"
SUCCESS = "BACKUP_AND_INDEPENDENT_DUAL_CLOUD_RECOVERY_VERIFIED"


class AutomatedBackupRejected(RuntimeError):
    """A category only, without exception details or private content."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _state_paths(state_dir: Path) -> tuple[Path, Path, Path]:
    state_dir = Path(state_dir)
    if (not state_dir.is_dir() or state_dir.is_symlink()
            or state_dir.name != "state" or
            state_dir.parent.name != STATE_DIR_NAME):
        raise AutomatedBackupRejected("scheduled state directory invalid")
    return (state_dir / "running.lock", state_dir / REVIEW_FLAG,
            state_dir / HISTORY)


def _record(history: Path, value: dict) -> None:
    # Only author-created bounded nonsecret fields; file is owner ACL limited.
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if len(raw) > 1600 or "\n" in raw:
        raise AutomatedBackupRejected("scheduled audit record rejected")
    with history.open("a", encoding="utf-8", newline="\n") as f:
        f.write(raw + "\n")


@contextmanager
def _one_instance(lock: Path):
    if sys.platform != "win32":
        raise AutomatedBackupRejected("Windows Task Scheduler runtime required")
    import msvcrt
    with lock.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"1")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise AutomatedBackupRejected("scheduled backup already running") from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _repo_allowed(repo_root: Path) -> Path:
    repo_root = Path(repo_root)
    if (not repo_root.is_dir() or repo_root.is_symlink()
            or repo_root.name.lower() != "trading-signal-intelligence"
            or not (repo_root / ".git").exists()
            or not (repo_root / "data" / "forward.sqlite").is_file()):
        raise AutomatedBackupRejected("approved S02 source checkout missing")
    return repo_root


def readiness(*, repo_root: Path, state_dir: Path) -> dict:
    """Local check only. No S02 rows, cloud requests or credentials emitted."""
    _, latched, history = _state_paths(state_dir)
    _repo_allowed(repo_root)
    flags = vault.scheduled_credential_status()
    return {
        "status": "S02_AUTOMATIC_BACKUP_READINESS",
        "ready": flags["ready"] and not latched.exists(),
        "vault_ready": flags["ready"],
        "operator_review_required": latched.exists(),
        "history_present": history.is_file(),
        "network_requests": 0,
        "retention": "ALL_ENCRYPTED_CLOUD_VERSIONS_PRESERVED",
    }


def run_once(*, repo_root: Path, state_dir: Path) -> dict:
    """One unattended, isolated run and fresh exact-version restore from both."""
    lock, latch, history = _state_paths(state_dir)
    repo = _repo_allowed(repo_root)
    with _one_instance(lock):
        if latch.exists():
            raise AutomatedBackupRejected("operator review required; cloud calls skipped")
        try:
            credentials = vault.load_credentials("backup")
            passphrase = vault.load_scheduled_recovery_passphrase()
        except vault.WindowsVaultRejected:
            _record(history, {"at_utc":_now(), "status":"CREDENTIAL_READINESS_HOLD"})
            raise AutomatedBackupRejected("scheduled credential preparation failed") from None
        # All preflight inputs exist. From this point, provider writes may be
        # ambiguous after any failure; latch rather than blindly run next day.
        try:
            receipts = Path(state_dir) / "encrypted-receipts"
            receipts.mkdir(exist_ok=True)
            backed = cloud.backup_once(
                repo_root=repo, receipt_dir=receipts,
                credentials=credentials, passphrase=passphrase,
            )
            if backed.get("status") != "BACKUP_TWO_PROVIDER_VERIFIED":
                raise AutomatedBackupRejected("unverified dual-cloud backup result")
            with tempfile.TemporaryDirectory(prefix="vowsig-s02-scheduled-cold-") as temp:
                recover = cloud.restore_once(
                    backup_id=backed["backup_id"],
                    output_path=Path(temp) / "verified.sqlite",
                    credentials=(credentials[1], credentials[3]),
                    passphrase=passphrase,
                )
                if recover.get("status") != "BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED":
                    raise AutomatedBackupRejected("independent recovery not fully verified")
            result = {
                "at_utc": _now(),
                "status": SUCCESS,
                "backup_id": backed["backup_id"],
                "record_count": backed["record_count"],
                "aws_restored": True,
                "b2_restored": True,
                "scheduled": True,
                "older_cloud_versions_deleted": False,
            }
            _record(history, result)
            return result
        except Exception:
            # Conservative even if failure happened before upload: no repeated
            # unknown provider writes until the owner checks the account.
            flag = {
                "at_utc": _now(),
                "status": "REVIEW_REQUIRED_PARTIAL_CLOUD_STATE_POSSIBLE",
                "retry_allowed": False,
                "cloud_deletion_performed": False,
            }
            # Exclusive-create; if a prior latch exists preserve it.
            try:
                with latch.open("x", encoding="utf-8") as out:
                    json.dump(flag, out, sort_keys=True)
            except FileExistsError:
                pass
            _record(history, flag)
            raise AutomatedBackupRejected(
                "scheduled backup uncertain; review-required latch recorded"
            ) from None


def main(args: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--readiness", action="store_true")
    mode.add_argument("--run-once", action="store_true")
    parsed = p.parse_args(args)
    try:
        result = (readiness(repo_root=parsed.repo_root, state_dir=parsed.state_dir)
                  if parsed.readiness else
                  run_once(repo_root=parsed.repo_root, state_dir=parsed.state_dir))
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result.get("ready", True) else 2
    except AutomatedBackupRejected as exc:
        print(json.dumps({"status":"S02_AUTOMATIC_BACKUP_HOLD",
                          "reason":str(exc)}))
        return 2
    except Exception:
        print('{"status":"S02_AUTOMATIC_BACKUP_HOLD","reason":"unknown safe failure"}')
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
