"""P2 synthetic, deterministic complete-population performance contracts."""
from __future__ import annotations

from copy import deepcopy

import pytest

from trading_signal_intelligence.product.accounts.performance import (
    MetricContractError, admin_snapshot_diagnostics, complete_performance,
)

META = {
    "program_id": "core-ai-shadow",
    "model_version": "AI-v1.1",
    "cohort": "forward-shadow",
    "window_start_utc": "2026-10-01T00:00:00Z",
    "window_end_utc": "2026-10-31T23:59:59Z",
    "as_of_utc": "2026-11-01T01:00:00Z",
    "source_snapshot_sha256": "a" * 64,
    "cost_model_version": "gross-to-net-costs-v1",
}


def fact(id, state, net=None, *, exit="2026-10-04T12:00:00Z"):
    return {
        "program_id": META["program_id"], "model_version": META["model_version"],
        "cohort": META["cohort"], "entity_id": id,
        "source_record_sha256": "b" * 64, "state": state,
        "combined_net_r": net, "exit_at_utc": exit if state == "closed" else None,
        "after_costs_verified": state == "closed",
        "cost_model_version": META["cost_model_version"] if state == "closed" else None,
        "partial_tp1_net_r": 0.3 if state == "closed" else None,
    }


def test_closed_denominator_not_open_or_no_trade_and_tp1_counted_once():
    rows = [
        fact("win", "closed", 2.0),
        fact("loss", "closed", -1.0, exit="2026-10-05T12:00:00Z"),
        fact("even", "closed", 0.0, exit="2026-10-06T12:00:00Z"),
        fact("open", "open"), fact("nt", "no_trade"),
        fact("reject", "rejected"), fact("err", "error"),
    ]
    m = complete_performance(rows, **META)
    assert m["completed_count"] == 3 and m["total_outcomes"] == 7
    assert m["win_count"] == m["loss_count"] == m["breakeven_count"] == 1
    assert m["win_rate"] == pytest.approx(1 / 3)
    assert m["expectancy_net_r"] == pytest.approx(1 / 3)
    assert m["profit_factor"] == pytest.approx(2.0)
    assert m["sum_completed_net_r"] == pytest.approx(1.0)  # NOT 1.9 with TP1 added
    assert m["max_normalized_r_drawdown"] == pytest.approx(1.0)
    assert m["open_count"] == m["no_trade_count"] == 1
    assert m["rejected_count"] == m["error_count"] == 1
    assert not m["real_execution_pnl_available"]
    assert "not actual cash equity" in m["drawdown_notice"]


def test_no_completed_outcomes_are_nullable_not_fabricated_zero():
    m = complete_performance([fact("open", "open"),fact("abstain", "no_trade")], **META)
    assert m["completed_count"] == 0
    for key in ("win_rate", "expectancy_net_r", "median_net_r",
                "sum_completed_net_r", "profit_factor", "max_normalized_r_drawdown"):
        assert m[key] is None


def test_all_wins_have_no_proven_profit_factor_not_infinity():
    m = complete_performance([fact("a", "closed", 1.0)], **META)
    assert m["profit_factor"] is None


def test_chronological_r_drawdown_not_input_record_order():
    rows = [
        fact("late", "closed", -2.0, exit="2026-10-07T12:00:00Z"),
        fact("early", "closed", 3.0, exit="2026-10-04T12:00:00Z"),
        fact("mid", "closed", -1.0, exit="2026-10-05T12:00:00Z"),
    ]
    m = complete_performance(rows, **META)
    assert m["max_normalized_r_drawdown"] == pytest.approx(3.0)
    assert m["longest_loss_streak"] == 2


@pytest.mark.parametrize("bad", [
    {"combined_net_r": None},
    {"combined_net_r": float("nan")},
    {"combined_net_r": float("inf")},
    {"combined_net_r": "1.0"},
    {"after_costs_verified": False},
    {"cost_model_version": "other"},
    {"source_record_sha256": "short"},
    {"exit_at_utc": None},
    {"exit_at_utc": "2026-12-01T12:00:00Z"},
    {"state": "live_real_money"},
    {"program_id": "crypto-expansion-1"},
    {"model_version": "AI-v1.3"},
])
def test_invalid_outcome_source_or_cost_fails_closed(bad):
    record = fact("test", "closed", 1.0)
    record.update(bad)
    with pytest.raises(MetricContractError):
        complete_performance([record], **META)


def test_duplicate_exit_entities_and_unverified_hash_fails_closed():
    item = fact("id", "closed", 1.0)
    with pytest.raises(MetricContractError, match="Duplicate"):
        complete_performance([item,deepcopy(item)], **META)
    with pytest.raises(MetricContractError):
        complete_performance([item], **{**META,"source_snapshot_sha256":"trimmed"})


def test_noncompleted_net_r_and_naive_timestamps_fails_closed():
    with pytest.raises(MetricContractError):
        complete_performance([fact("open","open",1.0)], **META)
    with pytest.raises(MetricContractError):
        complete_performance([fact("late","closed",1.0,exit="2026-10-05T01:00:00")], **META)


def test_admin_health_diagnostics_explicitly_not_full_history():
    record = {
        "generated_at_utc": "2026-11-04T00:00:00Z",
        "health": {"ok": False},
        "validation_programs": [
            {"program_id": "market-expansion-1", "mode": "SHADOW_ONLY",
             "public_signal_exposure": False, "health": {"healthy": False},
             "totals": {"valid_inferences": 9, "errors": 1,
                        "completed_shadow_trades": 2, "secret_key": "NEVER"}},
        ],
    }
    result = admin_snapshot_diagnostics(record)
    assert result["verified_full_history"] is False
    assert result["independent_vps_runtime_health_verified"] is False
    assert result["backup_restore_proven"] is False
    assert result["public_health_reported"] is False
    assert "NEVER" not in str(result)
    assert result["programs"][0]["errors"] == 1
    assert result["programs"][0]["public_signal_exposure"] is False


def test_missing_snapshot_diagnostics_no_fake_metrics():
    result = admin_snapshot_diagnostics(None)
    assert result["as_of_utc"] is None
    assert result["programs"] == []
    assert result["public_health_reported"] is None
    assert result["performance_metrics_available"] is False
