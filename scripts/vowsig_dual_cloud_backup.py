"""Manual one-shot dual-cloud encrypted S02 backup / disaster restore.

VPS interactive console only. No automatic scheduling, unattended credentials,
dotenv, environment/command-line secrets, silent charges or secret logging.
Running 'backup' intentionally uses real AWS S3 and B2 provider APIs.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as backup
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as targets

EXPECTED_REPO = "trading-signal-intelligence"


def _prompt(label: str) -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise backup.BackupOperationError("interactive VPS console required")
    try:
        value = getpass.getpass(label + ": ")
    except (EOFError, KeyboardInterrupt):
        raise backup.BackupOperationError("masked input cancelled") from None
    if type(value) is not str or not value:
        raise backup.BackupOperationError("required masked input absent")
    return value


def _credentials(mode: str) -> tuple[tuple[str, str], ...]:
    labels = (
        ("AWS S3 backup writer", "AWS S3 restore reader",
         "Backblaze B2 backup writer", "Backblaze B2 restore reader")
        if mode == "backup" else
        ("AWS S3 restore reader", "Backblaze B2 restore reader")
    )
    values = []
    for label in labels:
        ident = _prompt(label + " access key ID (masked)")
        secret = _prompt(label + " secret key (masked)")
        values.append((ident, secret))
    return tuple(values)


def _passphrase(mode: str) -> str:
    password = _prompt("Private off-VPS recovery passphrase (16+ characters)")
    if mode == "backup":
        confirm = _prompt("Confirm private recovery passphrase")
        if password != confirm:
            raise backup.BackupOperationError("recovery passphrase confirmation mismatch")
    if len(password) < 16:
        raise backup.BackupOperationError("recovery passphrase too short")
    return password


def _emit(result: dict) -> None:
    # Only dictionaries composed by the sanitized backup/restore library.
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, allow_abbrev=False,
        description="Manually back up or restore one encrypted S02 SQLite database")
    group = parser.add_subparsers(dest="operation", required=True)

    verify = group.add_parser("status", allow_abbrev=False)
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

    if args.operation == "backup":
        repo = Path(args.repo_root)
        if (repo.name.lower() != EXPECTED_REPO
                or not repo.is_dir()
                or not (repo / ".git").exists()):
            raise backup.BackupOperationError("expected scoped repository missing")
        # All prompts are masked; do not print any access ID or secret. An
        # authorized backup necessarily reads the selected real S02 source.
        print("MODE=MANUAL_REAL_S02_CLOUD_BACKUP; NO_AUTOMATIC_RETRY", flush=True)
        key = _passphrase("backup")
        creds = _credentials("backup")
        result = backup.backup_once(
            repo_root=repo, receipt_dir=Path(args.receipt_dir),
            credentials=creds, passphrase=key,
        )
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
