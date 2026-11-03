"""Read-only S02 dual-cloud version inventory for future GFS cleanup.

This module may list AWS S3 and Backblaze B2 object versions with caller-owned
READ-ONLY scoped clients. It never decrypts, writes, deletes or prunes.
Inventory alone never authorizes deletion or proves cold recoverability.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from . import live_dual_provider_transport_v0_1 as cloud_target
from . import manual_dual_cloud_backup_v0_1 as backup

_DATA_KEY = re.compile(
    r"^pilot/vowsig/approved-s02/v1/(backup-[0-9a-f]{32})/([0-9a-f]{64})\.aesgcm$"
)
_RECEIPT_KEY = re.compile(
    r"^pilot/vowsig/backup-receipts/v1/(backup-[0-9a-f]{32})\.aesgcm$"
)
MAX_PAGES = 100
MAX_VERSIONS = 20000


class CloudInventoryRejected(RuntimeError):
    """Sanitized error; do not leak provider keys/versions/response bodies."""


@dataclass(frozen=True, repr=False)
class ObjectVersion:
    provider: str
    kind: str
    backup_id: str
    key: str
    version_id: str

    def __repr__(self) -> str:
        return "<ScopedVersion PRIVATE>"


def _identifier(value: Any) -> bool:
    return (type(value) is str and 0 < len(value) <= 512
            and all(33 <= ord(c) <= 126 for c in value))


def _key_identity(key: Any, expected_kind: str) -> tuple[str, str]:
    match = (_DATA_KEY.fullmatch(key) if expected_kind == "data"
             else _RECEIPT_KEY.fullmatch(key)) if type(key) is str else None
    if match is None:
        raise CloudInventoryRejected("unexpected key in scoped cloud prefix")
    return (match.group(1), key)


def _list_scoped_versions(client: Any, target: cloud_target.Provider,
                          prefix: str, kind: str) -> dict[str, ObjectVersion]:
    """Fail closed on truncation/markers/deletes/duplicates/SDK permission errors."""
    records: dict[str, ObjectVersion] = {}
    key_marker: str | None = None
    version_marker: str | None = None
    markers: set[tuple[str, str]] = set()

    for _ in range(MAX_PAGES):
        params: dict[str, Any] = {
            "Bucket": target.bucket, "Prefix": prefix, "MaxKeys": 500,
        }
        if key_marker is not None:
            params["KeyMarker"] = key_marker
            if version_marker is not None:
                params["VersionIdMarker"] = version_marker
        try:
            result = client.list_object_versions(**params)
        except Exception:
            raise CloudInventoryRejected(
                "scoped provider version listing unavailable or denied"
            ) from None
        if (type(result) is not dict
                or result.get("IsTruncated") not in (True, False)
                or type(result.get("Versions", [])) is not list
                or type(result.get("DeleteMarkers", [])) is not list):
            raise CloudInventoryRejected("provider version listing malformed")
        if result.get("DeleteMarkers"):
            raise CloudInventoryRejected("scoped delete marker needs manual review")
        for item in result.get("Versions", []):
            if (type(item) is not dict
                    or not _identifier(item.get("VersionId"))
                    or type(item.get("IsLatest")) is not bool
                    or type(item.get("Size")) is not int
                    or not 0 < item["Size"] <= (
                        backup.DATA_MAX if kind == "data" else backup.MANIFEST_MAX
                    )):
                raise CloudInventoryRejected("provider version entry invalid")
            bid, key = _key_identity(item.get("Key"), kind)
            if not key.startswith(prefix) or not item["IsLatest"]:
                raise CloudInventoryRejected(
                    "nonlatest or escaped backup version requires manual review"
                )
            if bid in records:
                raise CloudInventoryRejected(
                    "duplicate backup or multiple versions require manual review"
                )
            records[bid] = ObjectVersion(
                provider=target.name, kind=kind, backup_id=bid,
                key=key, version_id=item["VersionId"],
            )
            if len(records) > MAX_VERSIONS:
                raise CloudInventoryRejected("cloud inventory limit exceeded")
        if result["IsTruncated"] is False:
            return records
        new_key = result.get("NextKeyMarker")
        new_version = result.get("NextVersionIdMarker")
        if not _identifier(new_key) or (new_version is not None
                                        and not _identifier(new_version)):
            raise CloudInventoryRejected("cloud inventory pagination malformed")
        marker = (new_key, new_version or "")
        if marker in markers:
            raise CloudInventoryRejected("repeating version page marker")
        markers.add(marker)
        key_marker, version_marker = new_key, new_version
    raise CloudInventoryRejected("cloud version inventory exceeds page limit")


def audit_provider_pair(
    *, aws_reader: Any, b2_reader: Any, expected_backup_ids: set[str],
) -> dict[str, Any]:
    """Compare exact latest-key/version topology, never provider mutation.

    Caller separately proves encrypted receipts, data digest and independent
    cold restores BEFORE any external deletion approval.
    """
    if (type(expected_backup_ids) is not set
            or not expected_backup_ids
            or len(expected_backup_ids) > MAX_VERSIONS
            or any(type(x) is not str or not backup.RUN_RX.fullmatch(x)
                   for x in expected_backup_ids)):
        raise CloudInventoryRejected("expected complete backup ID set missing")
    results = {}
    for provider, reader in ((cloud_target.AWS, aws_reader),
                             (cloud_target.B2, b2_reader)):
        data = _list_scoped_versions(
            reader, provider, backup.OBJECT_PREFIX, "data"
        )
        manifest = _list_scoped_versions(
            reader, provider, backup.MANIFEST_PREFIX, "manifest"
        )
        if set(data) != expected_backup_ids or set(manifest) != expected_backup_ids:
            raise CloudInventoryRejected(
                "provider backup history incomplete or unknown; no pruning"
            )
        results[provider.name] = (data, manifest)
    aws_data, aws_receipts = results[cloud_target.AWS.name]
    b2_data, b2_receipts = results[cloud_target.B2.name]
    for bid in expected_backup_ids:
        if (aws_data[bid].key != b2_data[bid].key
                or aws_receipts[bid].key != b2_receipts[bid].key
                or aws_receipts[bid].key != backup._manifest_key(bid)):
            raise CloudInventoryRejected("cloud data/manifest pairing mismatch")
    # Hash of nonsecret backup IDs only. Never log opaque cloud VersionIds.
    joined = "\n".join(sorted(expected_backup_ids)).encode("ascii")
    return {
        "status": "READ_ONLY_DUAL_PROVIDER_VERSION_INVENTORY_MATCH",
        "backup_ids_seen": len(expected_backup_ids),
        "aws_object_versions_seen": len(aws_data) + len(aws_receipts),
        "b2_object_versions_seen": len(b2_data) + len(b2_receipts),
        "backup_id_set_sha256": hashlib.sha256(joined).hexdigest(),
        "exact_versions_enumerated_in_memory": True,
        "cloud_deletion_authorized": False,
        "provider_deletions_performed": 0,
        "cold_restore_verification_separate": True,
    }
