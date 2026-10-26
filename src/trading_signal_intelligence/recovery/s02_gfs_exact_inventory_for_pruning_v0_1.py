"""Exactly paired S02 AWS/B2 read-only inventory for gated deletion plans.

ALL version identifiers remain in process memory and never in logs.
No cloud writes or retries. No unrelated bucket/prefix access.
"""
from __future__ import annotations

from typing import Any

from . import live_dual_provider_transport_v0_1 as providers
from . import manual_dual_cloud_backup_v0_1 as backup
from . import s02_gfs_cloud_inventory_v0_1 as existing


class GfsFullInventoryHold(RuntimeError):
    """Safe categorized failure without leaking object/version credentials."""


def read_exact_version_inventory(
    *, aws_reader: Any, b2_reader: Any, expected_ids: set[str],
) -> dict[str, dict[str, existing.ObjectVersion]]:
    if (type(expected_ids) is not set or not 0 < len(expected_ids) <= existing.MAX_VERSIONS
            or any(type(i) is not str or not backup.RUN_RX.fullmatch(i)
                   for i in expected_ids)):
        raise GfsFullInventoryHold("complete audited history required")
    try:
        slots = {
            "aws_data": existing._list_scoped_versions(
                aws_reader, providers.AWS, backup.OBJECT_PREFIX, "data"),
            "aws_manifest": existing._list_scoped_versions(
                aws_reader, providers.AWS, backup.MANIFEST_PREFIX, "manifest"),
            "b2_data": existing._list_scoped_versions(
                b2_reader, providers.B2, backup.OBJECT_PREFIX, "data"),
            "b2_manifest": existing._list_scoped_versions(
                b2_reader, providers.B2, backup.MANIFEST_PREFIX, "manifest"),
        }
        if any(set(group) != expected_ids for group in slots.values()):
            raise GfsFullInventoryHold("unexpected missing or extra versions")
        for bid in expected_ids:
            aw, bw = slots["aws_data"][bid], slots["b2_data"][bid]
            am, bm = slots["aws_manifest"][bid], slots["b2_manifest"][bid]
            if (aw.key != bw.key or am.key != bm.key
                    or am.key != backup._manifest_key(bid)
                    or aw.version_id == "null" or bw.version_id == "null"
                    or am.version_id == "null" or bm.version_id == "null"):
                raise GfsFullInventoryHold("provider object/version pairing mismatch")
        return slots
    except GfsFullInventoryHold:
        raise
    except Exception:
        raise GfsFullInventoryHold(
            "read-only version inventory denied or inconsistent"
        ) from None


def sanitized_inventory_summary(slots: dict) -> dict:
    if type(slots) is not dict or set(slots) != {
        "aws_data", "aws_manifest", "b2_data", "b2_manifest"
    }:
        raise GfsFullInventoryHold("invalid inventory summary input")
    return {
        "status": "S02_GFS_READ_ONLY_4_OBJECT_INVENTORY",
        "aws_versions": len(slots["aws_data"]) + len(slots["aws_manifest"]),
        "b2_versions": len(slots["b2_data"]) + len(slots["b2_manifest"]),
        "provider_deletions_performed": 0,
        "cloud_deletion_authorized": False,
    }
