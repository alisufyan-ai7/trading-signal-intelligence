"""Manual one-shot dual-cloud encrypted S02 backup / disaster restore.

VPS graphical masked window for recovery passphrase (Ctrl+V capable). Cloud credentials loaded only
from four fixed Windows Credential Manager Generic entries in same Windows user
account. No automatic scheduling, dotenv, environment/command-line secrets,
silent charges or secret logging.
Running 'backup' intentionally uses real AWS S3 and B2 provider APIs.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as backup
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as targets
from trading_signal_intelligence.recovery import windows_credential_manager_v0_1 as vault
from trading_signal_intelligence.recovery import windows_passphrase_dialog_v0_1 as password_dialog

EXPECTED_REPO = "trading-signal-intelligence"


class _NoSecretEchoParser(argparse.ArgumentParser):
    """Reject malformed CLI input without printing possibly pasted credentials."""
    def error(self, message: str) -> None:
        raise backup.BackupOperationError(
            "invalid operator command arguments; never supply secrets on CLI"
        )


def _credentials(mode: str) -> tuple[tuple[str, str], ...]:
    """Credentials come only from fixed Windows Generic credential entries."""
    try:
        return vault.load_credentials(mode)
    except vault.WindowsVaultRejected:
        raise backup.BackupOperationError(
            "Windows Credential Manager roles missing/invalid; use "
            "'credential-status' and Windows Credentials GUI"
        ) from None


def _passphrase(mode: str) -> str:
    """Masked native Windows window; clipboard paste is supported in the GUI.

    A short or mismatched passphrase is rejected BEFORE cloud/source access.
    No key/secret is passed through PowerShell, environment or the clipboard
    APIs by this Python program.
    """
    try:
        return password_dialog.prompt(mode)
    except password_dialog.PrivatePassphraseRejected:
        raise backup.BackupOperationError(
            "Windows recovery passphrase dialog cancelled/unavailable"
        ) from None


def _emit(result: dict) -> None:
    # Only dictionaries composed by the sanitized backup/restore library.
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = _NoSecretEchoParser(add_help=True, allow_abbrev=False,
        description="Manually back up or restore one encrypted S02 SQLite database")
    group = parser.add_subparsers(dest="operation", required=True)

    verify = group.add_parser("status", allow_abbrev=False)
    credential_check = group.add_parser("credential-status", allow_abbrev=False)
    run = group.add_parser("backup", allow_abbrev=False)
    run.add_argument("--repo-root", required=True)
    run.add_argument("--receipt-dir", required=True)
    run.add_argument("--acknowledge-real-cloud-cost", required=True,
                     choices=["I_ACCEPT_MINIMAL_CLOUD_COSTS"])
    run.add_argument("--acknowledge-s02-only", required=True,
                     choices=["APPROVED_S02_DATABASE_ONLY"])
    recover = group.add_parser("restore", allow_abbrev=False)
    recover.add_argument("--backup-id", required=True)
    recover.add_argument("--output", required=True)
    recover.add_argument("--local-receipt", default=None)
    recover.add_argument("--acknowledge-real-cloud-cost", required=True,
                         choices=["I_ACCEPT_MINIMAL_CLOUD_COSTS"])

    args = parser.parse_args(argv)
    if args.operation == "status":
        _emit({
            "status": "MANUAL_OPERATOR_AVAILABLE_NOT_SCHEDULED",
            "real_cloud_action_on_status": False,
            "source": "data/forward.sqlite",
            "max_source_bytes": backup.s02.MAX_SOURCE_BYTES,
            "targets": [
                {"provider":"AWS_S3","region":targets.AWS.region},
                {"provider":"BACKBLAZE_B2","region":targets.B2.region},
            ],
            "billing_guarantee": "MINIMAL_COST_INTENT_NOT_ZERO_COST_GUARANTEE",
        })
        return 0

    if args.operation == "credential-status":
        _emit(vault.credential_status())
        return 0

    if args.operation == "backup":
        repo = Path(args.repo_root)
        if (repo.name.lower() != EXPECTED_REPO
                or not repo.is_dir()
                or not (repo / ".git").exists()):
            raise backup.BackupOperationError("expected scoped repository missing")
        # Only the passphrase is prompted; access IDs and secrets come from
        # the current Windows account Credential Manager, never PowerShell.
        # An authorized backup necessarily reads the selected real S02 source.
        print("MODE=MANUAL_REAL_S02_CLOUD_BACKUP; NO_AUTOMATIC_RETRY", flush=True)
        key = _passphrase("backup")
        creds = _credentials("backup")
        result = backup.backup_once(
            repo_root=repo, receipt_dir=Path(args.receipt_dir),
            credentials=creds, passphrase=key,
        )
        # Print the immutable nonsecret backup ID immediately, even when the
        # subsequent independent cold-recovery drill cannot be completed.
        _emit(result)
        with tempfile.TemporaryDirectory(prefix="vowsig-s02-cold-proof-") as temp:
            recovered = backup.restore_once(
                backup_id=result["backup_id"],
                output_path=Path(temp) / "restored-s02.sqlite",
                credentials=(creds[1], creds[3]), passphrase=key,
            )
            if recovered["status"] != "BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED":
                raise backup.BackupOperationError(
                    "dual-cloud cold recovery incomplete; inspect backup ID " +
                    result["backup_id"]
                )
        _emit({
            "status": "BACKUP_AND_INDEPENDENT_DUAL_CLOUD_RECOVERY_VERIFIED",
            "backup_id": result["backup_id"],
            "aws_restored": True,
            "b2_restored": True,
            "production_modified": False,
            "scheduler_installed": False,
        })
        return 0
    else:
        print("MODE=MANUAL_EXACT_VERSION_CLOUD_RECOVERY; NO_OVERWRITE", flush=True)
        key = _passphrase("restore")
        creds = _credentials("restore")
        result = backup.restore_once(
            backup_id=args.backup_id, output_path=Path(args.output),
            credentials=creds, passphrase=key,
            local_receipt=(Path(args.local_receipt)
                           if args.local_receipt is not None else None),
        )
    _emit(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except backup.BackupOperationError as exc:
        # Fixed internal categories only; no caught SDK exception may escape.
        print("BACKUP_OPERATOR=HOLD; REASON=" + str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    except Exception:
        print("BACKUP_OPERATOR=HOLD; REASON=unknown; do not retry blindly",
              file=sys.stderr)
        raise SystemExit(3) from None
