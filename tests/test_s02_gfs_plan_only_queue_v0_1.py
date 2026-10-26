"""Synthetic-only unattended S02 GFS eligibility, private capsule and owner queue.

No provider credentials, actual cloud endpoints, signing key or delete identity.
"""
from __future__ import annotations

import ast
import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.recovery import s02_gfs_retention_policy_v0_1 as gfs
from trading_signal_intelligence.recovery import s02_gfs_plan_only_queue_v0_1 as q
from trading_signal_intelligence.recovery import s02_gfs_plan_only_vault_v0_1 as vault
from trading_signal_intelligence.recovery import s02_gfs_cloud_inventory_v0_1 as cloud
from trading_signal_intelligence.recovery import s02_gfs_owner_signed_prune_plan_v0_1 as signed
from scripts import vowsig_s02_gfs_plan_only_v0_1 as cli

NOW = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
TIME = NOW.isoformat(timespec="seconds")
PLAN = "SYNTHETIC-ONLY-PLAN-ENCRYPTION-2026-ISOLATED"
RECOVERY = "SYNTHETIC-ONLY-SQLITE-RECOVERY-2026-SEPARATE"


def success(days: int, i: int) -> dict:
    return {
        "at_utc": (NOW - timedelta(days=days)).isoformat(timespec="seconds"),
        "status": gfs.PASS, "backup_id": "backup-" + format(i, "032x"),
        "record_count": 30, "aws_restored": True, "b2_restored": True,
        "scheduled": True,
    }


def fixtures(tmp_path, *, count=120):
    history = [success(i, i+1) for i in range(count)]
    policy = gfs.choose_gfs(history, as_of_utc=TIME)
    assert policy["eligible_ids"]
    assert set(policy["hold_reasons"]) == q.EXPECTED_HOLDS
    base = tmp_path / "ProgramData" / q.STATE_ROOT
    for part in ("pending", "state"):
        sub = base / part
        sub.mkdir(parents=True)
        sub.chmod(0o700)
    return history, policy, base


def versions(ids):
    return {
        role: {bid: cloud.ObjectVersion(
            "AWS_S3" if role.startswith("aws") else "BACKBLAZE_B2",
            "manifest" if role.endswith("manifest") else "data",
            bid,
            ("pilot/vowsig/backup-receipts/v1/" + bid + ".aesgcm"
             if role.endswith("manifest") else
             "pilot/vowsig/approved-s02/v1/" + bid + "/" + "a"*64 + ".aesgcm"),
            "synthetic-version-" + role + bid[-8:],
        ) for bid in ids}
        for role in signed.EXPECTED_OPERATIONS
    }


def mock_dependencies(monkeypatch, history, policy, *, fail=None, base=None):
    events = []
    def list_versions(**kw):
        events.append("inventory")
        if base is not None:
            assert (base / "state" / "prepare-running.lock").is_file()
        assert kw["expected_ids"] == (set(policy["keep_ids"]) |
                                      set(policy["eligible_ids"]) |
                                      set(policy["protected_ids"]))
        if fail == "inventory":
            raise OSError("SYNTHETIC CLOUD ERROR DO_NOT_LEAK")
        return versions(kw["expected_ids"])
    def cold_restore(**kw):
        events.append("cold_restore")
        if base is not None:
            assert (base / "state" / "prepare-running.lock").is_file()
        assert kw["backup_ids"] == sorted(set(policy["keep_ids"]) |
                                           set(policy["protected_ids"]))
        assert kw["recovery_passphrase"] == RECOVERY
        if fail == "restore":
            raise ValueError("SYNTHETIC RECOVERY SECRET DO_NOT_LEAK")
        return {"status": "ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED",
                "verified_backup_count": len(kw["backup_ids"]),
                "provider_deletions_performed": 0}
    monkeypatch.setattr(q.inventory, "read_exact_version_inventory", list_versions)
    return events, cold_restore


def prepare(history, base, cold_restore, **kwargs):
    return q.prepare_one_unsigned_plan(
        history=history, now_utc=TIME, review_latch_present=False,
        base_directory=base, aws_reader=object(), b2_reader=object(),
        reader_credentials=(("fake-reader-aws", "fake-secret"),
                            ("fake-reader-b2", "fake-secret")),
        plan_passphrase=PLAN, recovery_passphrase=RECOVERY,
        retained_restore=cold_restore, **kwargs,
    )


def test_default_local_check_no_eligibility_no_network_no_disk(tmp_path):
    history = [success(i, i+1) for i in range(12)]
    result = q.check_eligibility(
        history=history, now_utc=TIME, review_latch_present=False)
    assert result["status"] == "NO_ELIGIBLE_BACKUP"
    assert result["network_requests"] == 0
    assert result["provider_deletions_performed"] == 0
    assert list(tmp_path.iterdir()) == []


def test_healthy_old_histories_require_exact_owner_review_holds(tmp_path):
    history, policy, base = fixtures(tmp_path)
    check = q.check_eligibility(
        history=history, now_utc=TIME, review_latch_present=False)
    assert check["status"] == "ELIGIBLE_FOR_PRIVATE_PREPARATION"
    assert set(check["hold_reasons"]) == q.EXPECTED_HOLDS
    assert check["eligible_count"] > 0
    assert check["cloud_deletion_authorized"] is False


@pytest.mark.parametrize("outage", ["latch", "stale", "unknown_history"])
def test_live_backup_safety_holds_prevent_preparation(tmp_path, outage):
    history, policy, base = fixtures(tmp_path)
    if outage == "stale":
        history = [success(i+40, i+1) for i in range(120)]
    if outage == "unknown_history":
        history = [*history, {"status": "REVIEW_REQUIRED_PARTIAL_CLOUD_STATE_POSSIBLE"}]
    checked = q.check_eligibility(
        history=history, now_utc=TIME,
        review_latch_present=(outage == "latch"))
    assert checked["status"] == "GFS_SAFETY_HOLD"
    assert checked["network_requests"] == 0
    with pytest.raises(q.PlanOnlyHold):
        q.prepare_one_unsigned_plan(
                    history=history, now_utc=TIME,
                    review_latch_present=(outage == "latch"),
                    base_directory=base, aws_reader=None, b2_reader=None,
                    reader_credentials=(), plan_passphrase=PLAN,
                    recovery_passphrase=RECOVERY,
                )
    assert not list((base / "pending").iterdir())


def test_healthy_one_pending_plan_is_private_encrypted_unsigned(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    out = prepare(history, base, verify)
    assert out["status"] == "PENDING_SEPARATE_OWNER_APPROVAL"
    assert out["plan_signed"] is False
    assert out["provider_deletions_performed"] == 0
    assert out["cloud_deletion_authorized"] is False
    assert out["backup_id"] in policy["eligible_ids"]
    assert out["backup_id"] not in policy["protected_ids"]
    assert events == ["inventory", "cold_restore"]
    private = base / "pending" / (out["backup_id"] + ".aesgcm")
    public = base / "state" / ("review-" + out["backup_id"] + ".json")
    assert private.is_file() and public.is_file()
    assert not (base / "state" / "prepare-running.lock").exists()
    ciphertext = private.read_bytes()
    assert ciphertext.startswith(signed.MAGIC)
    assert PLAN.encode() not in ciphertext
    assert RECOVERY.encode() not in ciphertext
    assert out["backup_id"].encode() not in ciphertext
    assert b"synthetic-version" not in ciphertext
    meta = json.loads(public.read_text())
    assert meta["sealed_sha256"] == out["sealed_sha256"]
    assert meta["plan_signed"] is False
    assert meta["deletion_authorized"] is False
    assert "objects" not in meta and "VersionId" not in public.read_text()
    plan = signed._decrypt(ciphertext, PLAN)
    assert plan["candidate"] == out["backup_id"]
    assert len(plan["objects"]) == 4


def test_second_unattended_run_preserves_original_capsule_no_cloud_cost(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    out = prepare(history, base, verify)
    before = (base / "pending" / (out["backup_id"] + ".aesgcm")).read_bytes()
    result = prepare(history, base, verify)
    after = (base / "pending" / (out["backup_id"] + ".aesgcm")).read_bytes()
    assert result["status"] == "PENDING_OWNER_REVIEW"
    assert result["network_requests"] == 0
    assert events == ["inventory", "cold_restore"]
    assert before == after



def test_exclusive_lock_is_held_before_any_provider_inventory_or_restore(
    monkeypatch, tmp_path
):
    history, policy, base = fixtures(tmp_path)
    events, restore = mock_dependencies(
        monkeypatch, history, policy, base=base)
    prepared = prepare(history, base, restore)
    assert prepared["status"] == "PENDING_SEPARATE_OWNER_APPROVAL"
    assert events == ["inventory", "cold_restore"]
    assert not (base / "state" / "prepare-running.lock").exists()


def test_active_or_abandoned_preparation_lock_blocks_provider_requests(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    (base / "state" / "prepare-running.lock").write_text("abandoned")
    with pytest.raises(q.PlanOnlyHold, match="review"):
        prepare(history, base, verify)
    assert events == []


@pytest.mark.parametrize("bad", [None, "", PLAN])
def test_missing_or_aliased_backup_secret_blocks_before_cloud(monkeypatch, tmp_path, bad):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    with pytest.raises(q.PlanOnlyHold, match="independent"):
        q.prepare_one_unsigned_plan(
            history=history, now_utc=TIME, review_latch_present=False,
            base_directory=base, aws_reader=object(), b2_reader=object(),
            reader_credentials=(), plan_passphrase=PLAN,
            recovery_passphrase=bad,
        )
    assert events == [] and not list((base / "state").iterdir())


@pytest.mark.parametrize("broken", ["inventory", "restore"])
def test_failed_provider_audit_leaves_fail_closed_operator_lock(monkeypatch, tmp_path, broken):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy, fail=broken)
    with pytest.raises(q.PlanOnlyHold) as exc:
        prepare(history, base, verify)
    assert "DO_NOT_LEAK" not in str(exc.value)
    assert (base / "state" / "prepare-running.lock").is_file()
    assert not list((base / "pending").iterdir())
    with pytest.raises(q.PlanOnlyHold):
        prepare(history, base, verify)


def test_unrecognized_private_file_or_orphan_receipt_holds(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    (base / "pending" / "unknown.aesgcm").write_bytes(b"not owner signed")
    with pytest.raises(q.PlanOnlyHold):
        prepare(history, base, verify)
    assert events == []


def test_wrong_programdata_root_never_prepares(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    with pytest.raises(q.PlanOnlyHold):
        prepare(history, base.parent, verify)
    assert events == []


def test_plan_passphrase_windows_vault_is_separate_and_injectable():
    assert vault.PLAN_TARGET != "VowSig.S02.Recovery.Passphrase.v1"
    assert vault.PLAN_USERNAME == "VowSigGFSPlanner"
    assert vault.read_plan_passphrase(lookup=lambda: PLAN) == PLAN
    with pytest.raises(vault.GfsPlannerVaultHold):
        vault.read_plan_passphrase(lookup=lambda: "")
    with pytest.raises(vault.GfsPlannerVaultHold):
        vault.read_plan_passphrase(lookup=lambda: None)


def test_plan_only_modules_have_no_delete_and_no_owner_private_signature():
    for module in (q, vault, cli):
        tree = ast.parse(inspect.getsource(module))
        found = {node.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Attribute)}
        assert not found.intersection({
            "delete_object", "delete_objects", "DeleteObject",
            "put_object", "sign", "put_bucket_lifecycle_configuration",
        })
    assert q.PRODUCTION_CLOUD_DELETE_ENABLED is False



def freeze_cli_clock(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW
    monkeypatch.setattr(cli, "datetime", FrozenDateTime)


def test_cli_default_check_requires_no_plan_vault_or_provider(tmp_path, capsys, monkeypatch):
    freeze_cli_clock(monkeypatch)
    history = [success(i, i+1) for i in range(12)]
    source = tmp_path / "VowSig-S02-AutoBackup" / "state" / "history.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(json.dumps(x) for x in history)+"\n")
    ret = cli.main(["--history", str(source)])
    result = json.loads(capsys.readouterr().out)
    assert ret == 0
    assert result["network_requests"] == 0
    assert result["cloud_deletion_authorized"] is False
    assert not list(tmp_path.glob("**/*.aesgcm"))


def test_cli_refuses_prepare_without_provider_read_cost_ack(tmp_path, capsys):
    ret = cli.main(["--mode", "prepare", "--history",
                    str(tmp_path / "not-valid-history.jsonl")])
    assert ret == 2
    assert json.loads(capsys.readouterr().out)["status"] == "GFS_PLAN_ONLY_HOLD"


def test_cli_prepare_without_expired_backups_does_not_touch_vault(
    tmp_path, capsys, monkeypatch
):
    freeze_cli_clock(monkeypatch)
    history = [success(i, i+1) for i in range(12)]
    source = tmp_path / "VowSig-S02-AutoBackup" / "state" / "history.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(json.dumps(x) for x in history) + "\n")
    monkeypatch.setattr(vault, "read_plan_passphrase",
                        lambda: pytest.fail("vault should not be accessed"))
    result_code = cli.main([
        "--mode", "prepare", "--history", str(source),
        "--plan-root", str(tmp_path / "ProgramData" / q.STATE_ROOT),
        "--acknowledge-read-cost", "I_ACCEPT_READ_ONLY_CLOUD_RESTORE_COST",
    ])
    result = json.loads(capsys.readouterr().out)
    assert result_code == 0
    assert result["status"] == "NO_ELIGIBLE_BACKUP"
    assert result["network_requests"] == 0


def test_existing_pending_private_files_without_receipt_force_hold(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    (base / "pending" / (policy["eligible_ids"][0] + ".aesgcm")).write_bytes(b"partial")
    with pytest.raises(q.PlanOnlyHold, match="paired|invalid"):
        prepare(history, base, verify)
    assert events == []


def test_prepare_no_retained_cold_restore_proof_never_writes_plan(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    def invalid_restore(**kw):
        events.append("cold_restore")
        return {"status": "NOT_VERIFIED", "provider_deletions_performed": 0}
    with pytest.raises(q.PlanOnlyHold):
        prepare(history, base, invalid_restore)
    assert events == ["inventory", "cold_restore"]
    assert not list((base / "pending").iterdir())
    assert (base / "state" / "prepare-running.lock").exists()


def test_no_owner_approval_signature_or_real_delete_capability_in_queue(monkeypatch, tmp_path):
    history, policy, base = fixtures(tmp_path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    result = prepare(history, base, verify)
    receipt = json.loads(
        (base / "state" / ("review-" + result["backup_id"] + ".json")).read_text())
    assert set(receipt) == {
        "status", "backup_id", "sealed_sha256", "not_before_utc",
        "expires_utc", "plan_signed", "deletion_authorized",
        "cloud_deletions_performed",
    }
    assert receipt["plan_signed"] is False
    assert receipt["deletion_authorized"] is False


def test_owner_extra_pin_file_must_be_explicit_before_cloud_preparation(
    tmp_path, capsys, monkeypatch
):
    freeze_cli_clock(monkeypatch)
    history, policy, base = fixtures(tmp_path)
    monkeypatch.setattr(cli, "_validated_real_planner_root", lambda path: path)
    source = tmp_path / "VowSig-S02-AutoBackup" / "state" / "history.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(json.dumps(r) for r in history)+"\n")
    code = cli.main([
        "--mode", "prepare", "--history", str(source),
        "--plan-root", str(base),
        "--acknowledge-read-cost", "I_ACCEPT_READ_ONLY_CLOUD_RESTORE_COST",
    ])
    result = json.loads(capsys.readouterr().out)
    assert code == 2 and result["status"] == "GFS_PLAN_ONLY_HOLD"
    assert not list((base / "pending").iterdir())


def test_explicit_owner_pin_prevents_selected_retention_candidate(tmp_path):
    history, policy, base = fixtures(tmp_path)
    candidate = policy["eligible_ids"][0]
    pin_file = base / "owner-protected-ids.json"
    pin_file.write_text(json.dumps({
        "schema": cli.PINS_SCHEMA, "extra_pinned_ids": [candidate]}))
    pins = cli._load_owner_pins(base)
    assert pins == (candidate,)
    reselected = gfs.choose_gfs(
        history, as_of_utc=TIME, extra_pinned_ids=pins)
    assert candidate in reselected["protected_ids"]
    assert candidate in reselected["keep_ids"]
    assert candidate not in reselected["eligible_ids"]


@pytest.mark.parametrize("invalid", [
    {}, {"schema": "old", "extra_pinned_ids": []},
    {"schema": cli.PINS_SCHEMA, "extra_pinned_ids": ["bad"]},
    {"schema": cli.PINS_SCHEMA, "extra_pinned_ids": ["backup-"+"a"*32]*2},
])
def test_bad_owner_pin_config_never_defaults_to_empty(tmp_path, invalid):
    history, policy, base = fixtures(tmp_path)
    (base / "owner-protected-ids.json").write_text(json.dumps(invalid))
    with pytest.raises(q.PlanOnlyHold, match="pin"):
        cli._load_owner_pins(base)


def test_wellformed_explicit_empty_owner_pin_config_allowed(tmp_path):
    history, policy, base = fixtures(tmp_path)
    (base / "owner-protected-ids.json").write_text(json.dumps({
        "schema": cli.PINS_SCHEMA, "extra_pinned_ids": []}))
    assert cli._load_owner_pins(base) == ()


def test_unsigned_pending_status_cli_exposes_no_versions_or_secrets(
    monkeypatch, tmp_path, capsys
):
    history, policy, base = fixtures(tmp_path)
    monkeypatch.setattr(cli, "_validated_real_planner_root", lambda path: path)
    events, verify = mock_dependencies(monkeypatch, history, policy)
    sealed = prepare(history, base, verify)
    assert events == ["inventory", "cold_restore"]
    code = cli.main(["--mode", "status", "--plan-root", str(base)])
    raw = capsys.readouterr().out
    shown = json.loads(raw)
    assert code == 0
    assert shown["status"] == "PENDING_OWNER_APPROVAL"
    assert shown["backup_id"] == sealed["backup_id"]
    assert shown["sealed_sha256"] == sealed["sealed_sha256"]
    assert shown["trusted_7_day_approval_anchor_verified"] is False
    assert shown["independent_owner_signature_present"] is False
    assert shown["provider_deletions_performed"] == 0
    assert shown["network_requests"] == 0
    assert all(x not in raw for x in (
        PLAN, RECOVERY, "synthetic-version-", "VersionId", "DeleteObject"))
    assert events == ["inventory", "cold_restore"]


def test_status_no_pending_uses_no_vault_or_cloud(tmp_path, capsys, monkeypatch):
    history, policy, base = fixtures(tmp_path)
    monkeypatch.setattr(cli, "_validated_real_planner_root", lambda path: path)
    code = cli.main(["--mode", "status", "--plan-root", str(base)])
    shown = json.loads(capsys.readouterr().out)
    assert code == 0
    assert shown["status"] == "NO_PENDING_OWNER_PLAN"
    assert shown["network_requests"] == 0


def test_status_refuses_orphan_and_missing_root_without_cloud(tmp_path, capsys, monkeypatch):
    history, policy, base = fixtures(tmp_path)
    monkeypatch.setattr(cli, "_validated_real_planner_root", lambda path: path)
    (base / "state" / ("review-" + policy["eligible_ids"][0] + ".json")).write_text("{}")
    code = cli.main(["--mode", "status", "--plan-root", str(base)])
    status = json.loads(capsys.readouterr().out)
    assert code == 2
    assert status["status"] == "GFS_PLAN_ONLY_HOLD"
    assert status["provider_deletions_performed"] == 0
