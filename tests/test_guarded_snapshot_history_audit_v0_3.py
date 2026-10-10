"""Offline tests of read-only prospective snapshot retention audit."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "archive_audit_review", ROOT / "scripts/audit_guarded_snapshot_history_v0_3.py",
)
assert spec and spec.loader
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

CREATED = "2026-10-10T13:05:09+00:00"
ACCEPTED = "2026-10-10T13:05:10+00:00"


def _sample() -> dict:
    return {
        "schema_version": 1, "generated_at_utc": CREATED,
        "raw_market_data_included": False, "validation_programs": [],
        "markets": [],
    }


def _archive(root: Path, *, accepted: bool = True):
    folder = root / "data" / audit.HISTORY_NAME
    folder.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(_sample(), sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    p = folder / ("snapshot-20261010T130509Z-" + digest + ".json")
    p.write_bytes(raw)
    receipt = folder / (p.name + ".accepted")
    if accepted:
        receipt.write_text(json.dumps({
            "schema": 1, "snapshot_sha256": digest,
            "accepted_at_utc": ACCEPTED,
        }), encoding="utf-8")
    return p, receipt


def test_empty_history_is_not_an_external_backup(tmp_path):
    summary = audit.audit_local_history(tmp_path)
    assert summary["status"] == "NO_LOCAL_HISTORY"
    assert summary["accepted_snapshots"] == 0
    assert summary["external_backup_verified"] is False
    assert summary["hosted_snapshot_durability_verified"] is False
    assert not (tmp_path / "data").exists()


def test_accepted_and_pending_are_distinguished_without_writes(tmp_path):
    archive, receipt = _archive(tmp_path, accepted=True)
    original = archive.read_bytes()
    result = audit.audit_local_history(tmp_path)
    assert result["status"] == "LOCAL_HASHES_PASS"
    assert result["accepted_snapshots"] == 1
    assert result["pending_candidates"] == 0
    assert result["oldest_accepted_generated_at_utc"] == CREATED
    assert result["external_backup_verified"] is False
    assert receipt.is_file()
    assert archive.read_bytes() == original
    newroot = tmp_path / "another"
    _archive(newroot, accepted=False)
    pending = audit.audit_local_history(newroot)
    assert pending["accepted_snapshots"] == 0
    assert pending["pending_candidates"] == 1
    assert pending["external_backup_verified"] is False


def test_modified_candidate_fails_even_if_receipt_is_old(tmp_path):
    p, _ = _archive(tmp_path)
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(audit.HistoryAuditRejected, match="SHA-addressed"):
        audit.audit_local_history(tmp_path)


def test_orphan_accepted_receipt_rejected(tmp_path):
    p, receipt = _archive(tmp_path)
    p.unlink()
    with pytest.raises(audit.HistoryAuditRejected, match="without immutable snapshot"):
        audit.audit_local_history(tmp_path)


def test_invalid_receipt_hash_rejected(tmp_path):
    p, receipt = _archive(tmp_path)
    evidence = json.loads(receipt.read_text(encoding="utf-8"))
    evidence["snapshot_sha256"] = "0" * 64
    receipt.write_text(json.dumps(evidence), encoding="utf-8")
    with pytest.raises(audit.HistoryAuditRejected, match="acceptance receipt invalid"):
        audit.audit_local_history(tmp_path)


def test_receipt_is_not_accepted_before_creation(tmp_path):
    _, receipt = _archive(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["accepted_at_utc"] = "2026-10-10T13:05:08+00:00"
    receipt.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(audit.HistoryAuditRejected, match="acceptance receipt invalid"):
        audit.audit_local_history(tmp_path)


def test_unknown_file_in_archive_directory_fails_closed(tmp_path):
    p, _ = _archive(tmp_path)
    (p.parent / "temporary-unverified.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(audit.HistoryAuditRejected, match="unknown archive"):
        audit.audit_local_history(tmp_path)


def test_nested_directory_in_archive_directory_fails_closed(tmp_path):
    p, _ = _archive(tmp_path)
    (p.parent / "surprise").mkdir()
    with pytest.raises(audit.HistoryAuditRejected, match="non-regular"):
        audit.audit_local_history(tmp_path)


def test_no_raw_candle_or_private_market_payload_is_admissible(tmp_path):
    p, receipt = _archive(tmp_path)
    data = json.loads(p.read_text())
    data["raw_market_data_included"] = True
    raw = json.dumps(data, sort_keys=True).encode()
    old_name = p.name
    p.unlink()
    receipt.unlink()
    dig = hashlib.sha256(raw).hexdigest()
    filename = "snapshot-20261010T130509Z-" + dig + ".json"
    replacement = p.parent / filename
    replacement.write_bytes(raw)
    with pytest.raises(audit.HistoryAuditRejected, match="contract incomplete"):
        audit.audit_local_history(tmp_path)


@pytest.mark.parametrize("invalid", ["incorrect_timestamp", "oversized", "invalid_json"])
def test_malformed_candidate_fails_closed(tmp_path, invalid):
    p, receipt = _archive(tmp_path)
    receipt.unlink()
    if invalid == "incorrect_timestamp":
        raw = json.dumps({**_sample(), "generated_at_utc":
            "2026-10-10T13:05:11+00:00"}, sort_keys=True).encode()
    elif invalid == "oversized":
        raw = b"x" * (audit.MAX_SINGLE_SNAPSHOT_BYTES + 1)
    else:
        raw = b"invalid JSON"
    p.unlink()
    dig = hashlib.sha256(raw).hexdigest()
    replacement = p.parent / ("snapshot-20261010T130509Z-" + dig + ".json")
    replacement.write_bytes(raw)
    with pytest.raises(audit.HistoryAuditRejected):
        audit.audit_local_history(tmp_path)


def test_bounded_audit_rejects_excessive_items(monkeypatch, tmp_path):
    p, _ = _archive(tmp_path)
    monkeypatch.setattr(audit, "MAX_ARCHIVES_PER_AUDIT", 0)
    with pytest.raises(audit.HistoryAuditRejected, match="bounded audit"):
        audit.audit_local_history(tmp_path)


def test_archive_root_symlink_does_not_get_followed(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    external = tmp_path / "outside"
    external.mkdir()
    location = data / audit.HISTORY_NAME
    try:
        location.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Windows user lacks symlink privilege")
    with pytest.raises(audit.HistoryAuditRejected, match="archive root"):
        audit.audit_local_history(tmp_path)
