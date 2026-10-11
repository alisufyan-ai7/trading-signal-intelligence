"""Synthetic-only contract tests; no Binance, OpenAI, VPS, or SQLite calls."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_crypto_research_quality_v0_1 import assess, QualityEvidenceRejected  # noqa: E402


def perf(n=0, net=0.0):
    return {
        "completed_trades": n,
        "cumulative_net_r": net,
        "average_net_r": net/n if n else None,
        "profit_factor": 2.0 if n else None,
        "max_drawdown_r": -1.0 if n else 0.0,
        "average_hold_h1_bars": 4.0 if n else None,
    }


def fixture():
    markets = {}
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        n, exits = (100, 20) if symbol == "BTCUSDT" else (0, 0)
        markets[symbol] = {
            "symbol": symbol,
            "ledger_path": "PRIVATE_DO_NOT_EMIT",
            "current_head_hash": "PRIVATE_DO_NOT_EMIT",
            "valid_inferences": n,
            "completed_shadow_trades": exits,
            "open_signals": 1 if n else 0,
            "counts_by_type": {"INFERENCE": n, "EXIT": exits},
            "weekday_weekend": {
                "weekday_valid_inferences": n - (30 if n else 0),
                "weekend_valid_inferences": 30 if n else 0,
                "weekday_completed_shadow_trades": exits - (5 if exits else 0),
                "weekend_completed_shadow_trades": 5 if exits else 0,
            },
            "ledger_verification": {"valid": True},
            "activation_anchor_match": True,
            "performance_observational_only": perf(exits, 2.0 if exits else 0.0),
        }
    report = {
        "runtime_version": "AI-v1.3",
        "program_id": "crypto-expansion-1",
        "mode": "READ_ONLY",
        "performance_metrics_are_observational_only": True,
        "generated_at_utc": "2026-10-11T18:05:00+00:00",
        "health": {
            "healthy": True, "ledgers_valid": True,
            "activation_anchor_matches_ledgers": True, "crypto_artifacts_valid": True,
            "activation_anchor_upstream_valid": True, "scheduler_healthy": True,
            "public_signal_exposure_disabled": True, "broker_execution_disabled": True,
        },
        "markets": markets,
        "totals": {
            "valid_inferences": 100,
            "completed_shadow_trades": 20,
            "open_shadow_signals": 1,
            "weekday_weekend": {
                "weekday_valid_inferences": 70,
                "weekend_valid_inferences": 30,
                "weekday_completed_shadow_trades": 15,
                "weekend_completed_shadow_trades": 5,
            },
            "performance_observational_only": perf(20, 2.0),
        },
        "gates": {
            "C1": {"eligible": True, "minimum_calendar_days": 0,
                   "calendar_requirement_met": True},
            "C2": {"eligible": False, "minimum_calendar_days": 60,
                   "calendar_requirement_met": False},
            "C3": {"eligible": False, "minimum_calendar_days": 120,
                   "calendar_requirement_met": False},
        },
    }
    gate_cfg = {
        "markets": ["BTCUSDT","ETHUSDT","SOLUSDT"],
        "gates": {
            "C1": {"valid_inferences":100,"completed_shadow_trades":20,
                   "minimum_calendar_days":0},
            "C2": {"valid_inferences":500,"completed_shadow_trades":50,
                   "minimum_calendar_days":60},
            "C3": {"valid_inferences":1000,"completed_shadow_trades":100,
                   "minimum_calendar_days":120},
        },
        "gate_results_do_not_authorize_public_signal_exposure": True,
        "gate_results_do_not_authorize_broker_execution": True,
    }
    cost_cfg = {
        "markets": ["BTCUSDT","ETHUSDT","SOLUSDT"],
        "broker_execution_authority": False,
        "fee_policy": {"fee_rate_per_side_fraction":0.001},
        "guard_policy": {"max_round_trip_cost_r":0.15},
    }
    return report, gate_cfg, cost_cfg


class TestReadOnlyCryptoQuality(unittest.TestCase):
    def test_whitelisted_observational_summary_and_frozen_gate(self):
        report, gates, costs = fixture()
        out = assess(report, gates, costs)
        self.assertEqual(out["valid_inferences"], 100)
        self.assertEqual(out["completed_shadow_trades"], 20)
        self.assertTrue(out["frozen_gate_progress"]["C1"]["eligible"])
        self.assertFalse(out["frozen_gate_progress"]["C2"]["eligible"])
        self.assertFalse(out["current_public_actionable_crypto_eligible"])
        self.assertFalse(out["live_exchange_execution_eligible"])
        self.assertFalse(out["writes_or_network_calls"])
        serialized = json.dumps(out)
        self.assertNotIn("PRIVATE_DO_NOT_EMIT", serialized)
        self.assertNotIn("current_head_hash", serialized)
        self.assertNotIn("ledger_path", serialized)

    def test_reject_malformed_weekend_denominators(self):
        report, gates, costs = fixture()
        report["markets"]["BTCUSDT"]["weekday_weekend"]["weekend_valid_inferences"] = 29
        with self.assertRaises(QualityEvidenceRejected):
            assess(report, gates, costs)

    def test_reject_incorrect_gate_eligibility(self):
        report, gates, costs = fixture()
        report["gates"]["C1"]["eligible"] = False
        with self.assertRaises(QualityEvidenceRejected):
            assess(report, gates, costs)

    def test_reject_public_and_broker_exposure(self):
        for key in ("broker_execution_disabled","public_signal_exposure_disabled"):
            report, gates, costs = fixture()
            report["health"][key] = False
            with self.subTest(key=key), self.assertRaises(QualityEvidenceRejected):
                assess(report, gates, costs)

    def test_reject_changed_frozen_gate_and_cost(self):
        report, gates, costs = fixture()
        gates["gates"]["C3"]["minimum_calendar_days"] = 30
        with self.assertRaises(QualityEvidenceRejected):
            assess(report, gates, costs)
        report, gates, costs = fixture()
        costs["fee_policy"]["fee_rate_per_side_fraction"] = 0.0005
        with self.assertRaises(QualityEvidenceRejected):
            assess(report, gates, costs)

    def test_reject_nonfinite_performance(self):
        report, gates, costs = fixture()
        report["totals"]["performance_observational_only"]["average_net_r"] = float("nan")
        with self.assertRaises(QualityEvidenceRejected):
            assess(report, gates, costs)

    def test_unhealthy_runtime_is_not_assumed_healthy(self):
        report, gates, costs = fixture()
        report["health"]["scheduler_healthy"] = False
        out = assess(report, gates, costs)
        self.assertFalse(out["runtime_healthy_at_observation"])
        self.assertFalse(out["live_exchange_execution_eligible"])


if __name__ == "__main__":
    unittest.main()
