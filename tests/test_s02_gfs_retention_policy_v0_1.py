"""Offline GFS retention tests — no credentials, provider calls or cloud deletes."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.recovery import s02_gfs_retention_policy_v0_1 as gfs
from scripts import vowsig_s02_gfs_retention_preview_v0_1 as cli

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def ok(days: int, index: int, *, now: datetime = NOW) -> dict:
    return {
        "at_utc": (now - timedelta(days=days)).isoformat(timespec="seconds"),
        "status": gfs.PASS,
        "backup_id": "backup-" + format(index, "032x"),
        "record_count": 30,
        "aws_restored": True,
        "b2_restored": True,
        "scheduled": True,
    }


def planned(data, *, now=NOW, **kw):
    return gfs.choose_gfs(data, as_of_utc=now.isoformat(), **kw)


def test_full_history_retains_daily_weekly_monthly_and_protects_baseline():
    rows = [ok(days, days + 1) for days in range(500)]
    result = planned(rows)
    assert result["policy"] == gfs.POLICY
    assert result["counts"]["history_verified"] == 500
    assert result["counts"]["daily"] == 31
    assert 7 <= result["counts"]["weekly"] <= 8
    assert 1 <= result["counts"]["monthly"] <= 12
    assert result["counts"]["eligible_in_history"] > 100
    assert len(result["keep_ids"]) == len(set(result["keep_ids"]))
    assert set(result["keep_ids"]).isdisjoint(result["eligible_ids"])
    assert len(result["keep_ids"]) + len(result["eligible_ids"]) == 500
    assert gfs.FIRST_MANUAL_ID in result["protected_ids"]
    assert ok(0, 1)["backup_id"] in result["protected_ids"]
    assert ok(1, 2)["backup_id"] in result["protected_ids"]
    assert not result["cloud_deletion_authorized"]
    assert result["provider_deletions_performed"] == 0
    assert "DUAL_CLOUD_VERSION_AND_RESTORE_INVENTORY_REQUIRED" in result["hold_reasons"]


def test_recent_history_is_never_expired():
    data = [ok(i, i + 1) for i in range(25)]
    result = planned(data)
    assert result["counts"]["keep_in_history"] == 25
    assert result["eligible_ids"] == []
    assert result["hold_reasons"] == []
    assert result["minimum_approval_grace_days"] == 7


def test_weekly_keeps_one_successful_backup_per_iso_week():
    rows = [ok(i, i + 1) for i in range(1, 88)]
    result = planned(rows)
    kept = set(result["keep_ids"])
    assert ok(1, 2)["backup_id"] in kept
    assert result["counts"]["weekly"] <= 8
    # An old daily backup must never be misclassified as another recent day.
    assert any(x not in kept for x in (ok(35, 36)["backup_id"], ok(36, 37)["backup_id"]))


def test_utc_year_boundary_keeps_weekly_bucket_from_iso_year():
    end = datetime(2027, 2, 4, 12, tzinfo=timezone.utc)
    result = planned([ok(i, i + 200, now=end) for i in range(0, 110)],
                     now=end)
    assert result["counts"]["weekly"] <= 8
    assert result["counts"]["monthly"] <= 12
    assert not result["cloud_deletion_authorized"]


def test_original_manual_backup_is_immovable_even_if_history_contains_id():
    rows = [ok(i, i + 1) for i in range(90)]
    special = ok(400, 999)
    special["backup_id"] = gfs.FIRST_MANUAL_ID
    rows.append(special)
    result = planned(rows)
    assert gfs.FIRST_MANUAL_ID in result["keep_ids"]
    assert gfs.FIRST_MANUAL_ID not in result["eligible_ids"]


def test_protect_owner_pins_and_latest_two():
    rows = [ok(i, i + 1) for i in range(300)]
    pin = ok(299, 300)["backup_id"]
    result = planned(rows, extra_pinned_ids=(pin,))
    assert pin in result["protected_ids"]
    assert pin in result["keep_ids"]
    assert set(result["keep_ids"]).isdisjoint(result["eligible_ids"])


@pytest.mark.parametrize("bad", [
    [{"status":gfs.PASS,"at_utc":NOW.isoformat(),"backup_id":"bad"}],
    [dict(ok(0, 1),aws_restored=False)],
    [dict(ok(0, 1),record_count=0)],
    [dict(ok(0, 1),at_utc="2026-10-24T12:00:00+05:00")],
    [dict(ok(0, 1),at_utc="not-a-time")],
    [ok(0, 1), ok(1, 1)],
    [dict(ok(-1, 1),at_utc=(NOW + timedelta(hours=1)).isoformat())],
])
def test_malformed_success_or_duplicate_fails_closed(bad):
    with pytest.raises(gfs.RetentionPlanRejected):
        planned(bad)


def test_unknown_hold_and_review_latch_prevent_pruning():
    rows = [ok(i, i + 1) for i in range(100)]
    rows.append({"at_utc":NOW.isoformat(),"status":"REVIEW_REQUIRED_PARTIAL_CLOUD_STATE_POSSIBLE"})
    result = planned(rows, review_latch_present=True)
    assert "UNACKNOWLEDGED_HOLD_PRESENT_IN_HISTORY" in result["hold_reasons"]
    assert "OPERATOR_REVIEW_LATCH_PRESENT" in result["hold_reasons"]
    assert result["cloud_deletion_authorized"] is False


def test_stale_history_requires_review_even_if_retention_candidates_exist():
    rows = [ok(i, i + 1) for i in range(40, 130)]
    result = planned(rows)
    assert "NO_RECENT_VERIFIED_BACKUP" in result["hold_reasons"]
    assert result["eligible_ids"]


def test_plan_is_deterministic_regardless_history_input_order():
    rows = [ok(i, i + 1) for i in range(100)]
    one = planned(rows)
    two = planned(list(reversed(rows)))
    assert one == two
    assert len(one["plan_sha256"]) == 64


def test_history_preview_is_read_only_and_reports_no_delete(tmp_path, capsys):
    base = tmp_path / "VowSig-S02-AutoBackup" / "state"
    base.mkdir(parents=True)
    source = base / "history.jsonl"
    source.write_text("\n".join(json.dumps(ok(i, i + 1))
                                   for i in range(60)) + "\n")
    result = cli.main(["--history", str(source), "--as-of-utc", NOW.isoformat()])
    stdout = capsys.readouterr().out
    data = json.loads(stdout)
    assert result == 0
    assert not data["cloud_deletion_authorized"]
    assert data["provider_deletions_performed"] == 0
    assert data["counts"]["history_verified"] == 60
    assert not (base / "operator-review-required.json").exists()
    assert source.exists()


def test_preview_refuses_bad_path_and_latched_state(tmp_path, capsys):
    base = tmp_path / "VowSig-S02-AutoBackup" / "state"
    base.mkdir(parents=True)
    source = base / "history.jsonl"
    source.write_text(json.dumps(ok(0, 1)) + "\n")
    (base / "operator-review-required.json").write_text("{}")
    result = cli.main(["--history", str(source), "--as-of-utc", NOW.isoformat()])
    payload = json.loads(capsys.readouterr().out)
    assert result == 0
    assert "OPERATOR_REVIEW_LATCH_PRESENT" in payload["hold_reasons"]
    assert cli.main(["--history", str(tmp_path / "history.jsonl")]) == 2


def test_no_provider_delete_calls_in_policy_or_preview_modules():
    import ast
    import inspect
    for module in (gfs, cli):
        tree = ast.parse(inspect.getsource(module))
        assert not any(
            isinstance(node, ast.Attribute) and node.attr in {
                "delete_object", "delete_objects", "put_bucket_lifecycle_configuration",
                "list_object_versions", "put_object",
            } for node in ast.walk(tree)
        )
