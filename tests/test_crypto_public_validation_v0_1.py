"""Offline-only prospective BTC/ETH/SOL website observability tests.

No Binance/OpenAI calls, broker action, ledger writes, scheduler changes, or
hosted snapshot publication are permitted by this suite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.observability import ObservabilityError
from trading_signal_intelligence.product import ai_insights, crypto_validation
from trading_signal_intelligence.product.cloud_app import _validate_validation_programs


def _report() -> dict:
    markets = {}
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        markets[symbol] = {
            "symbol": symbol,
            "ledger_path": f"private/{symbol}.sqlite",
            "current_head_hash": "PRIVATE_LEDGER_HEAD",
            "ledger_verification": {"valid": True, "record_hashes": ["PRIVATE_HASH"]},
            "activation_anchor_match": True,
            "valid_inferences": 2,
            "completed_shadow_trades": 1,
            "open_signals": 1,
            "counts_by_type": {
                "ACTIVATION": 1,
                "INFERENCE": 2,
                "SIGNAL": 2,
                "EXIT": 1,
                "NO_TRADE": 1,
                "REJECTED_INFERENCE": 1,
                "MISSED_INFERENCE": 1,
                "ERROR": 0,
            },
            "latest_recorded_at_utc": "2026-10-10T12:04:04+00:00",
            "private_provider_payload": "PRIVATE_PROVIDER_PAYLOAD",
        }

    gates = {}
    for name, inf_req, exits_req, days in (
        ("C1", 100, 20, 0),
        ("C2", 500, 50, 60),
        ("C3", 1000, 100, 120),
    ):
        gates[name] = {
            "gate": name,
            "eligible": False,
            "valid_inferences": {
                "current": 6, "required": inf_req, "met": False
            },
            "completed_shadow_trades": {
                "current": 3, "required": exits_req, "met": False
            },
            "minimum_calendar_days": days,
            "calendar_days_remaining": days,
            "calendar_requirement_met": days == 0,
            "calendar_eligible_at_utc": "2027-02-06T00:00:00+00:00",
            "private_review_notes": "PRIVATE_REVIEW_NOTES",
        }

    return {
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "program_id": "crypto-expansion-1",
        "mode": "READ_ONLY",
        "health": {
            "healthy": True,
            "ledgers_valid": True,
            "activation_anchor_matches_ledgers": True,
            "crypto_artifacts_valid": True,
            "activation_anchor_upstream_valid": True,
            "scheduler_healthy": True,
            "public_signal_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "activation": {
            "public_signal_exposure_enabled": False,
            "broker_execution_enabled": False,
            "backfill_prior_missed": False,
            "provider_parameters": "PRIVATE_PROVIDER_PARAMS",
        },
        "totals": {
            "valid_inferences": 6,
            "completed_shadow_trades": 3,
            "open_shadow_signals": 3,
            "private_performance": "PRIVATE_PROFIT_METRICS",
        },
        "markets": markets,
        "gates": gates,
        "private_reasoning": "PRIVATE_REASONING",
    }


def _public(report: dict) -> dict:
    return ai_insights.build_public_validation_program(
        crypto_validation.normalize_crypto_validation_report(report),
        program_id="crypto-expansion-1",
        title="Crypto AI Shadow Validation",
        market_labels=crypto_validation.CRYPTO_LABELS,
        public_signal_exposure=False,
    )


def test_crypto_public_payload_has_three_markets_three_frozen_gates_and_no_private_data():
    program = _public(_report())
    assert program["program_id"] == "crypto-expansion-1"
    assert program["runtime_version"] == "AI-v1.3"
    assert program["mode"] == "SHADOW_ONLY"
    assert program["public_research_observability"] is True
    assert program["public_signal_exposure"] is False
    assert program["signal_details_included"] is False
    assert program["health"]["healthy"] is True
    assert program["health"]["broker_execution_disabled"] is True
    assert program["totals"]["valid_inferences"] == 6
    assert program["totals"]["completed_shadow_trades"] == 3
    assert program["totals"]["open_shadow_signals"] == 3
    assert program["totals"]["missed_inferences"] == 3
    assert program["totals"]["rejected_inferences"] == 3
    assert program["totals"]["no_trade"] == 3
    assert [g["gate_id"] for g in program["gates"]] == ["C1", "C2", "C3"]
    c2 = program["gates"][1]
    requirements = {r["metric"]: r for r in c2["requirements"]}
    assert requirements["valid_inferences"]["required"] == 500
    assert requirements["completed_shadow_trades"]["required"] == 50
    assert requirements["calendar_days"]["required"] == 60
    assert [m["canonical_symbol"] for m in program["markets"]] == [
        "BTC/USDT", "ETH/USDT", "SOL/USDT"
    ]
    assert all(m["ledger_valid"] for m in program["markets"])

    serialized = json.dumps(program, sort_keys=True)
    for private in (
        "PRIVATE_", "ledger_path", "current_head_hash", "entry_price",
        "take_profit", "stop_loss", "confidence", "provider_parameters",
        "reasoning", "weekend_private", "activation_record_hash",
    ):
        assert private not in serialized
    for key in ("raw_market_data_included", "raw_feature_snapshots_included",
                "provider_request_metadata_included", "hidden_reasoning_included"):
        assert program[key] is False
    assert "shadow_signals" not in program
    assert "recent_decisions" not in program
    assert "alerts" not in program
    _validate_validation_programs({
        "validation_programs_schema_version": 1,
        "validation_programs": [program],
    })


@pytest.mark.parametrize("field", [
    "healthy", "ledgers_valid", "activation_anchor_matches_ledgers",
    "crypto_artifacts_valid", "activation_anchor_upstream_valid",
    "scheduler_healthy", "public_signal_exposure_disabled",
    "broker_execution_disabled",
])
def test_crypto_public_program_fails_closed_on_invalid_health(field):
    report = _report()
    report["health"][field] = False
    with pytest.raises(ObservabilityError, match="unsafe"):
        _public(report)


@pytest.mark.parametrize("field", [
    "public_signal_exposure_enabled", "broker_execution_enabled",
    "backfill_prior_missed",
])
def test_crypto_public_program_refuses_unsafe_activation_boundary(field):
    report = _report()
    report["activation"][field] = True
    with pytest.raises(ObservabilityError, match="boundary"):
        _public(report)


@pytest.mark.parametrize("defect", [
    "missing_market", "extra_market", "missing_gate", "negative_count",
    "inference_mismatch", "exit_mismatch", "totals_mismatch",
    "open_exceeds_signals", "invalid_ledger", "wrong_protocol",
])
def test_crypto_public_program_refuses_bad_or_partial_report(defect):
    report = _report()
    btc = report["markets"]["BTCUSDT"]
    if defect == "missing_market":
        del report["markets"]["SOLUSDT"]
    elif defect == "extra_market":
        report["markets"]["DOGEUSDT"] = {}
    elif defect == "missing_gate":
        del report["gates"]["C3"]
    elif defect == "negative_count":
        btc["counts_by_type"]["NO_TRADE"] = -1
    elif defect == "inference_mismatch":
        btc["counts_by_type"]["INFERENCE"] = 3
    elif defect == "exit_mismatch":
        btc["completed_shadow_trades"] = 2
    elif defect == "totals_mismatch":
        report["totals"]["valid_inferences"] = 20
    elif defect == "open_exceeds_signals":
        btc["open_signals"] = 3
    elif defect == "invalid_ledger":
        btc["ledger_verification"]["valid"] = False
    elif defect == "wrong_protocol":
        report["decision_protocol_version"] = "AI-v2.0"
    with pytest.raises(ObservabilityError):
        _public(report)


def test_crypto_activation_state_is_shape_only_and_refuses_partial(tmp_path):
    state = crypto_validation.crypto_activation_state(tmp_path)
    assert state == {"any_state": False, "complete_shape": False}

    from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import DATABASE_PATHS
    first = tmp_path / DATABASE_PATHS["BTCUSDT"]
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_bytes(b"opaque; not a valid sqlite ledger")
    state = crypto_validation.crypto_activation_state(tmp_path)
    assert state == {"any_state": True, "complete_shape": False}

    for symbol in ("ETHUSDT", "SOLUSDT"):
        path = tmp_path / DATABASE_PATHS[symbol]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"opaque; not a valid sqlite ledger")
    anchor = tmp_path / "research/forward/AI-v1.3-crypto-expansion-activation-2026-10-10T000000Z.json"
    anchor.parent.mkdir(parents=True, exist_ok=True)
    anchor.write_text("opaque, validation done separately", encoding="utf-8")
    state = crypto_validation.crypto_activation_state(tmp_path)
    assert state == {"any_state": True, "complete_shape": True}


def test_public_program_builder_registers_crypto_only_with_complete_state(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(ai_insights, "build_active_report", lambda *args, **kwargs: {
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "health": {"healthy": True, "broker_execution_disabled": True},
        "totals": {},
        "gates": {},
        "markets": {},
    })
    monkeypatch.setattr(ai_insights, "_v1_2_1_state", lambda root: {
        "any_state": False, "complete_shape": False
    })

    # No crypto state: preserve existing core lineage only.
    monkeypatch.setattr(crypto_validation, "crypto_activation_state", lambda root: {
        "any_state": False, "complete_shape": False
    })
    assert [
        p["program_id"] for p in ai_insights.build_public_validation_programs(tmp_path)
    ] == ["core-ai-shadow"]

    # Partial crypto state: fail closed rather than quietly omit a market.
    monkeypatch.setattr(crypto_validation, "crypto_activation_state", lambda root: {
        "any_state": True, "complete_shape": False
    })
    with pytest.raises(ObservabilityError, match="partial AI-v1.3"):
        ai_insights.build_public_validation_programs(tmp_path)

    # Complete crypto state: exactly one sanitized additional program.
    monkeypatch.setattr(crypto_validation, "crypto_activation_state", lambda root: {
        "any_state": True, "complete_shape": True
    })
    monkeypatch.setattr(
        crypto_validation, "build_crypto_public_validation_program",
        lambda *args, **kwargs: _public(_report()),
    )
    programs = ai_insights.build_public_validation_programs(tmp_path)
    assert [p["program_id"] for p in programs] == [
        "core-ai-shadow", "crypto-expansion-1"
    ]
    assert programs[1]["public_signal_exposure"] is False


def test_crypto_builder_forbids_skipped_scheduler_and_upstream(monkeypatch, tmp_path):
    with pytest.raises(ObservabilityError, match="full verification"):
        crypto_validation.build_crypto_public_validation_program(
            tmp_path, include_scheduler=False
        )
    with pytest.raises(ObservabilityError, match="full verification"):
        crypto_validation.build_crypto_public_validation_program(
            tmp_path, verify_upstream=False
        )


def test_public_crypto_research_does_not_change_k3_runtime_sources():
    root = Path(__file__).resolve().parents[1]
    adapter = (root / "src/trading_signal_intelligence/product/crypto_validation.py").read_text()
    builder = (root / "src/trading_signal_intelligence/product/ai_insights.py").read_text()
    assert "build_report_v1_3" in adapter
    assert "public_signal_exposure=False" in adapter
    assert "crypto_activation_state(root)" in builder
    assert "build_crypto_public_validation_program" in builder
