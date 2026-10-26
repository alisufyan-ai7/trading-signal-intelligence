"""Synthetic-only GFS owner-approved exact-VersionId deletion tests.

Never uses real cloud keys, real SDK clients, production VPS history or IAM.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trading_signal_intelligence.recovery import s02_gfs_retention_policy_v0_1 as gfs
from trading_signal_intelligence.recovery import s02_gfs_cloud_inventory_v0_1 as inv
from trading_signal_intelligence.recovery import s02_gfs_owner_signed_prune_plan_v0_1 as approval
from trading_signal_intelligence.recovery import s02_gfs_exact_inventory_for_pruning_v0_1 as exact
from trading_signal_intelligence.recovery import s02_gfs_single_version_delete_executor_v0_1 as actor

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
PHRASE = "SYNTHETIC-NEVER-REAL-RECOVERY-PHRASE-2026"


def row(day: int):
    return {
        "at_utc": (NOW - timedelta(days=day)).isoformat(timespec="seconds"),
        "status": gfs.PASS,
        "backup_id": "backup-" + format(day + 1, "032x"),
        "record_count": 30,
        "aws_restored": True, "b2_restored": True, "scheduled": True,
    }


def fixtures(count=120):
    records = [row(i) for i in range(count)]
    now = NOW.isoformat(timespec="seconds")
    initial = gfs.choose_gfs(records, as_of_utc=now)
    future = gfs.choose_gfs(
        records, as_of_utc=(NOW + timedelta(days=8)).isoformat(timespec="seconds")
    )
    candidates = [x for x in initial["eligible_ids"] if x in future["eligible_ids"]]
    assert candidates
    return records, initial, future, candidates[0]


def _fake_object(bid: str, slot: str):
    provider = "AWS_S3" if slot.startswith("aws") else "BACKBLAZE_B2"
    kind = "manifest" if slot.endswith("manifest") else "data"
    key = ("pilot/vowsig/backup-receipts/v1/" + bid + ".aesgcm"
           if kind == "manifest" else
           "pilot/vowsig/approved-s02/v1/" + bid + "/" + "a"*64 + ".aesgcm")
    return inv.ObjectVersion(provider, kind, bid, key, provider + "-version-" + slot + "-" + bid[-8:])


def inventory_for(records, policy):
    ids = set(policy["keep_ids"]) | set(policy["eligible_ids"]) | set(policy["protected_ids"])
    return {
        role: {bid: _fake_object(bid, role) for bid in ids}
        for role in approval.EXPECTED_OPERATIONS
    }


def keys():
    secret = Ed25519PrivateKey.generate()
    public = secret.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return secret, public


def sealed_case():
    records, before, after, candidate = fixtures()
    sealed = approval.freeze_one_candidate(
        policy=before, candidate=candidate,
        version_inventory=inventory_for(records, before),
        prepared_utc=NOW.isoformat(timespec="seconds"),
        private_phrase=PHRASE,
    )
    private, public = keys()
    sig = private.sign(approval.approval_message(sealed.sha256))
    return records, before, after, candidate, sealed, sig, public


def verify(case, *, days=8, signature=None, inventory=None, policy=None):
    records, before, after, candidate, sealed, sig, public = case
    return approval.verify_owner_signed_candidate(
        blob=sealed.blob, private_phrase=PHRASE,
        signature=sig if signature is None else signature,
        pinned_owner_public_key=public,
        current_utc=(NOW + timedelta(days=days)).isoformat(timespec="seconds"),
        current_policy=after if policy is None else policy,
        version_inventory=(inventory_for(records, after)
                           if inventory is None else inventory),
    )


def test_policy_selects_actual_aged_candidate_and_never_baseline():
    rec, doc, _, candidate = fixtures()
    assert candidate in doc["eligible_ids"]
    assert gfs.FIRST_MANUAL_ID in doc["protected_ids"]
    assert gfs.FIRST_MANUAL_ID not in doc["eligible_ids"]
    assert len(doc["keep_ids"]) >= 2
    assert not doc["cloud_deletion_authorized"]


def test_encrypted_capsule_contains_no_plain_backup_id_or_version_id():
    *_, candidate, plan, _, _ = sealed_case()
    assert candidate.encode() not in plan.blob
    assert b"aws-version" not in plan.blob
    assert len(plan.sha256) == 64
    assert plan.earliest_review_utc.endswith("+00:00")
    assert "PRIVATE" in repr(plan)
    assert "VersionId" not in repr(plan)


def test_explicit_owner_signature_and_seven_day_grace():
    case = sealed_case()
    approved = verify(case, days=8)
    assert approved.backup_id == case[3]
    assert len(approved.objects) == 4
    assert tuple(v[0] for v in approved.objects) == approval.EXPECTED_OPERATIONS
    with pytest.raises(approval.GfsDeleteHold, match="review grace"):
        verify(case, days=6)
    with pytest.raises(approval.GfsDeleteHold, match="expired"):
        verify(case, days=15)


def test_no_signed_approval_or_invalid_signature_denied():
    case = sealed_case()
    with pytest.raises(approval.GfsDeleteHold, match="owner approval"):
        verify(case, signature=b"0"*64)
    with pytest.raises(approval.GfsDeleteHold, match="signature missing"):
        verify(case, signature=b"")


def test_approved_exact_cloud_version_must_remain_identical():
    case = sealed_case()
    rec, _, after, candidate, *_ = case
    data = inventory_for(rec, after)
    old = data["aws_data"][candidate]
    data["aws_data"][candidate] = inv.ObjectVersion(
        old.provider, old.kind, candidate, old.key, old.version_id + "-unexpected")
    with pytest.raises(approval.GfsDeleteHold, match="versions changed"):
        verify(case, inventory=data)


def test_missing_provider_or_unrelated_extra_backup_forces_hold():
    record, original, _, candidate = fixtures()
    data = inventory_for(record, original)
    data["aws_manifest"].pop(candidate)
    with pytest.raises(approval.GfsDeleteHold, match="coverage mismatch"):
        approval.freeze_one_candidate(
            policy=original, candidate=candidate,
            version_inventory=data, prepared_utc=NOW.isoformat(),
            private_phrase=PHRASE
        )


def test_old_manual_and_latest_two_always_rejected():
    rec, before, _, _ = fixtures()
    ids = inventory_for(rec, before)
    for protected in before["protected_ids"]:
        with pytest.raises(approval.GfsDeleteHold):
            approval.freeze_one_candidate(
                policy=before, candidate=protected,
                version_inventory=ids, prepared_utc=NOW.isoformat(),
                private_phrase=PHRASE
            )


def test_stale_or_failed_scheduled_history_blocks_owner_plan():
    rec, before, _, candidate = fixtures()
    blocked = gfs.choose_gfs(
        rec + [{"status":"REVIEW_REQUIRED_PARTIAL_PROVIDER_WRITE"}],
        as_of_utc=NOW.isoformat(timespec="seconds"))
    with pytest.raises(approval.GfsDeleteHold, match="unresolved"):
        approval.freeze_one_candidate(
            policy=blocked, candidate=candidate,
            version_inventory=inventory_for(rec, before),
            prepared_utc=NOW.isoformat(timespec="seconds"), private_phrase=PHRASE)


def test_no_delete_call_when_production_release_fence_closed(tmp_path):
    with pytest.raises(actor.GfsExecutionHold, match="fence is closed"):
        actor.execute_single_owner_approved_prune(
            sealed_blob=b"x", signature=b"x", pinned_owner_public_key=b"x",
            private_phrase=PHRASE, current_utc=NOW.isoformat(),
            history=[], extra_pinned_ids=(), review_latch_present=False,
            aws_reader=None, b2_reader=None,
            reader_credentials=(), delete_credentials=(),
            journal_directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_owner_plan_never_accepts_null_cloud_version():
    records, doc, _, candidate = fixtures()
    data = inventory_for(records, doc)
    old = data["aws_manifest"][candidate]
    data["aws_manifest"][candidate] = inv.ObjectVersion(
        old.provider, old.kind, old.backup_id, old.key, "null")
    with pytest.raises(approval.GfsDeleteHold, match="inconsistent"):
        approval.freeze_one_candidate(
            policy=doc, candidate=candidate, version_inventory=data,
            prepared_utc=NOW.isoformat(), private_phrase=PHRASE)


class FakeCloud:
    def __init__(self, provider):
        self.provider = provider
        self.deleted = []
        self.fail_at = None

    def delete_object(self, **kwargs):
        if self.fail_at == len(self.deleted):
            raise OSError("synthetic broken provider response DO_NOT_LEAK")
        assert set(kwargs) == {"Bucket", "Key", "VersionId"}
        assert kwargs["VersionId"] and kwargs["VersionId"] != "null"
        self.deleted.append(kwargs)
        return {"VersionId": kwargs["VersionId"], "DeleteMarker": False}


def _fake_executor(monkeypatch, case, tmp_path, *, fail_at=None):
    records, _, after, candidate, sealed, signature, public = case
    aws, b2 = FakeCloud("aws"), FakeCloud("b2")
    aws.fail_at = fail_at
    cwd = tmp_path / "VowSig-S02-RetentionOperator" / "state"
    cwd.mkdir(parents=True)
    cwd.chmod(0o700)
    fake = inventory_for(records, after)
    order = []

    def list_versions(**kw):
        order.append("inventory")
        remaining = set(fake["aws_data"])
        expected = kw["expected_ids"]
        # Before deletion: all IDs; after: selected removed from all 4 slots.
        assert expected == remaining
        return fake

    def mock_restore(**kw):
        order.append("cold_restore")
        return {"status": "ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED",
                "verified_backup_count": len(kw["backup_ids"]),
                "provider_deletions_performed": 0}

    def mock_clients(**kw):
        order.append("separate_deleter_ids")
        return aws, b2

    def delete_with_inventory(client):
        original = client.delete_object
        def impl(**kw):
            ans = original(**kw)
            for entries in fake.values():
                obj = entries.get(candidate)
                if obj and obj.key == kw["Key"] and obj.version_id == kw["VersionId"]:
                    entries.pop(candidate)
                    break
            return ans
        client.delete_object = impl
    delete_with_inventory(aws)
    delete_with_inventory(b2)

    monkeypatch.setattr(actor, "PRODUCTION_CLOUD_DELETE_ENABLED", True)
    monkeypatch.setattr(actor.inventory, "read_exact_version_inventory", list_versions)
    monkeypatch.setattr(actor.cold, "audit_retained_recovery_points", mock_restore)
    monkeypatch.setattr(actor, "_delete_clients", mock_clients)

    kwargs = dict(
        sealed_blob=sealed.blob, signature=signature, pinned_owner_public_key=public,
        private_phrase=PHRASE,
        current_utc=(NOW + timedelta(days=8)).isoformat(timespec="seconds"),
        history=records, extra_pinned_ids=(), review_latch_present=False,
        aws_reader=object(), b2_reader=object(),
        reader_credentials=(("reader-aws", "test"), ("reader-b2", "test")),
        delete_credentials=(("delete-aws", "test"), ("delete-b2", "test")),
        journal_directory=cwd,
    )
    return aws, b2, cwd, order, kwargs


def test_synthetic_four_exact_deletions_and_pre_post_restore(monkeypatch, tmp_path):
    case = sealed_case()
    aws, b2, directory, calls, args = _fake_executor(monkeypatch, case, tmp_path)
    result = actor.execute_single_owner_approved_prune(**args)
    assert result["status"] == actor.FINAL_STATUS
    assert result["provider_deletions_performed"] == 4
    assert not result["automatic_retry_enabled"]
    assert len(aws.deleted) == len(b2.deleted) == 2
    assert calls.count("inventory") == 2
    assert calls.count("cold_restore") == 2
    files = list(directory.glob("*.jsonl"))
    assert len(files) == 1
    events = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert [x["state"] for x in events].count("ATTEMPT") == 4
    assert events[-1]["state"] == "COMPLETE"
    assert all("VersionId" not in line for line in files[0].read_text().splitlines())


def test_synthetic_second_delete_try_is_blocked_by_journal(monkeypatch, tmp_path):
    case = sealed_case()
    aws, b2, directory, calls, args = _fake_executor(monkeypatch, case, tmp_path)
    actor.execute_single_owner_approved_prune(**args)
    with pytest.raises(actor.GfsExecutionHold, match="prior deletion attempt"):
        actor.execute_single_owner_approved_prune(**args)
    assert len(aws.deleted) + len(b2.deleted) == 4


def test_synthetic_failed_first_provider_denies_retry_and_redacts_exception(monkeypatch, tmp_path):
    case = sealed_case()
    aws, b2, directory, calls, args = _fake_executor(
        monkeypatch, case, tmp_path, fail_at=0
    )
    with pytest.raises(actor.GfsExecutionHold) as err:
        actor.execute_single_owner_approved_prune(**args)
    assert "DO_NOT_LEAK" not in str(err.value)
    assert len(aws.deleted) == len(b2.deleted) == 0
    j = next(directory.glob("*.jsonl"))
    assert '"state":"HOLD"' in j.read_text()
    with pytest.raises(actor.GfsExecutionHold, match="prior deletion attempt"):
        actor.execute_single_owner_approved_prune(**args)


def test_deleter_identity_must_be_distinct_from_reader():
    with pytest.raises(actor.GfsExecutionHold, match="separate"):
        actor._delete_clients(
            reader_credentials=(("AWS-SAME","private"),("b2-reader","private")),
            delete_credentials=(("AWS-SAME","private"),("b2-delete","private")),
        )
