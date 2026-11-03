"""Read-only independent cold-restore verification of retained GFS points.

Explicit owner opt-in only. Existing manual recovery implementation GETs
encrypted manifests and data, authenticates AEAD and SQLite content using
owner-held passphrase, and writes recovered files to disposable LOCAL scratch.
No S3/B2 deletion, object overwrites or automatic retries.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from . import manual_dual_cloud_backup_v0_1 as backup

MAX_RESTORE_AUDIT = 80


class GfsRestoreAuditRejected(RuntimeError):
    """Fixed sanitized result; provider exception is deliberately suppressed."""


def audit_retained_recovery_points(
    *, backup_ids: list[str], read_credentials: tuple[tuple[str, str], ...],
    recovery_passphrase: str,
) -> dict[str, Any]:
    if (type(backup_ids) is not list or not 0 < len(backup_ids) <= MAX_RESTORE_AUDIT
            or len(set(backup_ids)) != len(backup_ids)
            or any(type(x) is not str or not backup.RUN_RX.fullmatch(x)
                   for x in backup_ids)):
        raise GfsRestoreAuditRejected("invalid bounded protected backup ID set")
    if (type(recovery_passphrase) is not str
            or not 16 <= len(recovery_passphrase) <= 1024
            or type(read_credentials) is not tuple or len(read_credentials) != 2):
        raise GfsRestoreAuditRejected("scoped owner recovery inputs required")
    recovered = []
    try:
        with tempfile.TemporaryDirectory(prefix="vowsig-s02-gfs-audit-") as folder:
            temp = Path(folder)
            for index, bid in enumerate(backup_ids):
                response = backup.restore_once(
                    backup_id=bid,
                    output_path=temp / ("restored-" + str(index) + ".sqlite"),
                    credentials=read_credentials,
                    passphrase=recovery_passphrase,
                )
                if (type(response) is not dict
                        or response.get("status") != "BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED"
                        or response.get("backup_id") != bid
                        or response.get("aws_restored") is not True
                        or response.get("b2_restored") is not True
                        or type(response.get("record_count")) is not int
                        or response["record_count"] < 1):
                    raise GfsRestoreAuditRejected(
                        "retained dual-cloud cold restore failed"
                    )
                recovered.append(bid)
    except Exception:
        raise GfsRestoreAuditRejected(
            "one or more retained dual-cloud recoveries failed; pruning blocked"
        ) from None
    return {
        "status": "ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED",
        "verified_backup_count": len(recovered),
        "provider_deletions_performed": 0,
        "cloud_deletion_authorized": False,
    }
