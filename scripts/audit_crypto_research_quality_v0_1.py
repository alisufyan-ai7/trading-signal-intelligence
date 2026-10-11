"""Read-only, non-actionable AI-v1.3 research quality summary.

Input: existing PRIVATE build_report_v1_3 JSON, supplied via stdin or an
explicit local file. This script NEVER opens live SQLite, invokes providers,
changes records, or publishes anything. Only whitelisted aggregate metrics
are printed; raw input, ledger paths/hashes and individual signals are not.
This is NOT a strategy optimization / eligibility approval process.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
GATE_THRESHOLDS = {
    "C1": (100, 20, 0),
    "C2": (500, 50, 60),
    "C3": (1000, 100, 120),
}
HEALTH_KEYS = (
    "healthy", "ledgers_valid", "activation_anchor_matches_ledgers",
    "crypto_artifacts_valid", "activation_anchor_upstream_valid",
    "scheduler_healthy", "public_signal_exposure_disabled",
    "broker_execution_disabled",
)


class QualityEvidenceRejected(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise QualityEvidenceRejected(message)


def whole(value: Any, label: str) -> int:
    require(type(value) is int and value >= 0, "invalid nonnegative count: " + label)
    return value


def number(value: Any, label: str) -> float | None:
    if value is None:
        return None
    require(type(value) in (float, int) and math.isfinite(value),
            "invalid finite metric: " + label)
    return float(value)


def utc(value: Any) -> datetime:
    require(isinstance(value, str), "missing UTC observation time")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityEvidenceRejected("invalid UTC observation time") from exc
    require(result.tzinfo is not None and result.utcoffset() is not None,
            "observation time has no UTC offset")
    return result.astimezone(timezone.utc)


def performance(raw: Any, label: str) -> dict[str, Any]:
    require(isinstance(raw, dict), "missing observational performance: " + label)
    n = whole(raw.get("completed_trades"), label + ".completed_trades")
    net = number(raw.get("cumulative_net_r"), label + ".cumulative_net_r")
    avg = number(raw.get("average_net_r"), label + ".average_net_r")
    pf = number(raw.get("profit_factor"), label + ".profit_factor")
    dd = number(raw.get("max_drawdown_r"), label + ".max_drawdown_r")
    hold = number(raw.get("average_hold_h1_bars"), label + ".average_hold_h1_bars")
    require(net is not None and dd is not None and dd <= 0,
            "missing/invalid cumulative return or drawdown")
    require(n > 0 or (avg is None and pf is None), "empty sample has defined metric")
    require(n == 0 or (avg is not None and abs(avg * n - net) <= 1e-6),
            "sample average/net inconsistency")
    require(pf is None or pf >= 0, "negative profit factor")
    require(hold is None or hold >= 0, "negative hold period")
    return {
        "completed_trades": n,
        "cumulative_net_r": net,
        "average_net_r": avg,
        "profit_factor": pf,
        "max_drawdown_r": dd,
        "average_hold_h1_bars": hold,
    }


def assess(report: dict[str, Any], gates_config: dict[str, Any],
           cost_config: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(report, dict), "crypto report is not an object")
    require(report.get("runtime_version") == "AI-v1.3"
            and report.get("program_id") == "crypto-expansion-1"
            and report.get("mode") == "READ_ONLY"
            and report.get("performance_metrics_are_observational_only") is True,
            "not the registered read-only crypto research report")
    observed = utc(report.get("generated_at_utc"))
    require(gates_config.get("markets") == list(SYMBOLS),
            "frozen crypto cohort changed")
    spec = gates_config.get("gates")
    require(isinstance(spec, dict) and set(spec) == set(GATE_THRESHOLDS),
            "frozen gate set changed")
    for gate_id, (inferences, exits, days) in GATE_THRESHOLDS.items():
        gate = spec[gate_id]
        require((gate.get("valid_inferences"), gate.get("completed_shadow_trades"),
                 gate.get("minimum_calendar_days")) == (inferences, exits, days),
                "frozen gate criteria mismatch: " + gate_id)
    require(gates_config.get("gate_results_do_not_authorize_public_signal_exposure") is True
            and gates_config.get("gate_results_do_not_authorize_broker_execution") is True,
            "frozen public/trading boundary changed")
    require(cost_config.get("markets") == list(SYMBOLS)
            and cost_config.get("broker_execution_authority") is False
            and cost_config.get("fee_policy", {}).get("fee_rate_per_side_fraction") == 0.001
            and cost_config.get("guard_policy", {}).get("max_round_trip_cost_r") == 0.15,
            "frozen crypto cost research assumptions changed")

    health = report.get("health")
    require(isinstance(health, dict), "missing health attestation")
    health_ok = all(health.get(key) is True for key in HEALTH_KEYS)
    safety_ok = health.get("public_signal_exposure_disabled") is True and (
        health.get("broker_execution_disabled") is True
    )
    require(safety_ok, "crypto research safety boundary failed or unavailable")

    market_data = report.get("markets")
    require(isinstance(market_data, dict) and set(market_data) == set(SYMBOLS),
            "not the exact three preregistered markets")
    markets = {}
    total_inferences = total_exits = total_weekday = total_weekend = 0
    total_weekday_exits = total_weekend_exits = 0
    for symbol in SYMBOLS:
        market = market_data[symbol]
        require(isinstance(market, dict) and market.get("symbol") == symbol,
                "incorrect market identity: " + symbol)
        infer = whole(market.get("valid_inferences"), symbol + ".inferences")
        exits = whole(market.get("completed_shadow_trades"), symbol + ".exits")
        open_signals = whole(market.get("open_signals"), symbol + ".open")
        counts = market.get("counts_by_type")
        require(isinstance(counts, dict), "missing counts_by_type: " + symbol)
        require(infer == whole(counts.get("INFERENCE", 0), symbol + ".INFERENCE")
                and exits == whole(counts.get("EXIT", 0), symbol + ".EXIT"),
                "inconsistent crypto ledger record counts: " + symbol)
        week = market.get("weekday_weekend")
        require(isinstance(week, dict), "missing weekend split: " + symbol)
        wi = whole(week.get("weekday_valid_inferences"), symbol + ".weekday_inf")
        we = whole(week.get("weekend_valid_inferences"), symbol + ".weekend_inf")
        wx = whole(week.get("weekday_completed_shadow_trades"), symbol + ".weekday_exits")
        ex = whole(week.get("weekend_completed_shadow_trades"), symbol + ".weekend_exits")
        require(wi + we == infer and wx + ex == exits,
                "weekday/weekend denominators inconsistent: " + symbol)
        perf = performance(market.get("performance_observational_only"), symbol)
        require(perf["completed_trades"] == exits,
                "performance denominator does not match EXIT count: " + symbol)
        market_valid = (
            market.get("ledger_verification", {}).get("valid") is True
            and market.get("activation_anchor_match") is True
        )
        markets[symbol] = {
            "inferences": infer, "completed_shadow_trades": exits,
            "open_shadow_signals": open_signals,
            "missed_inferences": whole(counts.get("MISSED_INFERENCE", 0), symbol + ".missed"),
            "errors": whole(counts.get("ERROR", 0), symbol + ".errors"),
            "rejected_inferences": whole(counts.get("REJECTED_INFERENCE", 0), symbol + ".rejected"),
            "weekday_inferences": wi, "weekend_inferences": we,
            "weekday_completed_shadow_trades": wx,
            "weekend_completed_shadow_trades": ex,
            "source_and_anchor_valid": market_valid,
            "observational_performance": perf,
        }
        total_inferences += infer
        total_exits += exits
        total_weekday += wi
        total_weekend += we
        total_weekday_exits += wx
        total_weekend_exits += ex

    totals = report.get("totals", {})
    require(isinstance(totals, dict)
            and totals.get("valid_inferences") == total_inferences
            and totals.get("completed_shadow_trades") == total_exits
            and totals.get("open_shadow_signals") ==
              sum(m["open_shadow_signals"] for m in markets.values()),
            "reported aggregate totals inconsistent with cohort")
    total_week = totals.get("weekday_weekend", {})
    require(isinstance(total_week, dict) and (
        total_week.get("weekday_valid_inferences"),
        total_week.get("weekend_valid_inferences"),
        total_week.get("weekday_completed_shadow_trades"),
        total_week.get("weekend_completed_shadow_trades")
    ) == (total_weekday, total_weekend, total_weekday_exits, total_weekend_exits),
        "aggregate weekday/weekend totals inconsistent")
    agg = performance(totals.get("performance_observational_only"), "cohort")
    require(agg["completed_trades"] == total_exits,
            "cohort performance trade denominator mismatch")

    gates = report.get("gates")
    require(isinstance(gates, dict) and set(gates) == set(GATE_THRESHOLDS),
            "report missing C1/C2/C3")
    eligibility = {}
    for gate_id, (required_i, required_x, required_days) in GATE_THRESHOLDS.items():
        gate = gates[gate_id]
        require(isinstance(gate, dict), "malformed gate: " + gate_id)
        calendar = gate.get("calendar_requirement_met")
        require(type(calendar) is bool, "unqualified gate calendar")
        require(gate.get("minimum_calendar_days") == required_days,
                "gate calendar requirement changed")
        expected = total_inferences >= required_i and total_exits >= required_x and calendar
        require(gate.get("eligible") is expected,
                "reported gate eligibility inconsistent: " + gate_id)
        eligibility[gate_id] = {
            "eligible": expected,
            "remaining_inferences": max(required_i - total_inferences, 0),
            "remaining_completed_shadow_trades": max(required_x - total_exits, 0),
            "calendar_requirement_met": calendar,
        }

    return {
        "audit_schema_version": 1,
        "source": "AI-v1.3 private read-only observability report; NOT public fixed as-of card",
        "observed_at_utc": observed.isoformat(),
        "program_id": "crypto-expansion-1",
        "market_cohort": list(SYMBOLS),
        "runtime_healthy_at_observation": health_ok and all(
            market["source_and_anchor_valid"] for market in markets.values()
        ),
        "valid_inferences": total_inferences,
        "completed_shadow_trades": total_exits,
        "markets": markets,
        "weekday_weekend_counts": total_week,
        "cohort_observational_performance": agg,
        "frozen_gate_progress": eligibility,
        "research_findings": [
            "Observational shadow statistics, not proof of future profitable live execution",
            "Small-sample/no-trade patterns require retention, not post-hoc tuning or market removal",
            "Weekday/weekend economic attribution and confidence calibration are not available from this summary alone",
            "Fee/spread/slippage remain a frozen research proxy, not an executable venue cost model",
        ],
        "current_public_actionable_crypto_eligible": False,
        "live_exchange_execution_eligible": False,
        "graduation": "NO_AUTOMATIC_PROMOTION_EVEN_IF_C3_MET",
        "writes_or_network_calls": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", default="-",
                        help="existing private AI-v1.3 JSON report; '-' reads stdin")
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[1],
                        help="repo root for FROZEN config files only")
    args = parser.parse_args(argv)
    try:
        content = sys.stdin.read() if args.report_json == "-" else Path(args.report_json).read_text(encoding="utf-8")
        report = json.loads(content)
        config = json.loads((args.root / "config/ai_v1_3_crypto_review_gates.json").read_text(encoding="utf-8"))
        costs = json.loads((args.root / "config/ai_v1_3_crypto_cost_policy.json").read_text(encoding="utf-8"))
        output = assess(report, config, costs)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("CRYPTO_QUALITY_AUDIT=HOLD", file=sys.stderr)
        print("REASON_CLASS=" + type(exc).__name__, file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
