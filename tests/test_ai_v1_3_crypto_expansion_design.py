from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONFIG = ROOT / "config" / "ai_v1_3_crypto_expansion.json"
GATES = ROOT / "config" / "ai_v1_3_crypto_review_gates.json"
REGISTRY = ROOT / "config" / "instruments.json"

MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_crypto_expansion_design_is_strictly_preactivation() -> None:
    payload = _load(CONFIG)

    assert payload["runtime_version"] == "AI-v1.3"
    assert payload["decision_protocol_version"] == "AI-v1.0"
    assert payload["program_id"] == "crypto-expansion-1"
    assert payload["status"] == "design_only_preactivation"
    assert payload["primary_source_name"] == "binance_spot"

    observed = tuple(
        row["source_symbol"] for row in payload["markets"]
    )
    assert observed == MARKETS

    assert payload["decision_cadence"] == "each_completed_h1_bar_24x7"
    assert payload["scheduler_target_minute"] == 4
    assert payload["snapshot_batch_freeze_before_provider_calls"] is True
    assert payload["max_data_age_seconds"] == 300

    assert payload["no_backfill"] is True
    assert payload["shares_gate_counts_with_ai_v1_1"] is False
    assert payload["shares_gate_counts_with_ai_v1_2_1"] is False
    assert payload["calendar_carry_forward"] is False
    assert payload["public_signal_exposure_enabled"] is False
    assert payload["public_research_observability_initially_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert payload["activation_authority"] is False


def test_crypto_feature_design_does_not_silently_reuse_mt5_spread_semantics() -> None:
    payload = _load(CONFIG)
    feature = payload["feature_profile"]
    cost = payload["execution_cost_profile"]

    assert feature["working_feature_schema_version"] == "AI-crypto-v1.0"
    assert (
        feature["volume_field_semantics"]
        == "binance_base_asset_volume"
    )
    assert feature["spread_semantics_change_required"] is True
    assert feature["spread_source"] == "prospective_binance_top_of_book"
    assert feature["zero_spread_substitution_forbidden"] is True
    assert feature["mt5_spread_substitution_forbidden"] is True

    assert cost["status"] == "calibration_required_before_activation"
    assert cost["top_of_book_spread_required"] is True
    assert cost["fee_rate_per_side"] is None
    assert cost["slippage_buffer_rule"] is None
    assert cost["all_in_round_trip_cost_rule"] is None
    assert cost["activation_blocked_until_numeric_cost_policy_frozen"] is True


def test_crypto_planned_ledgers_are_new_and_isolated() -> None:
    payload = _load(CONFIG)

    assert payload["planned_ledgers"] == {
        "BTCUSDT": "data/ai_v1_3_btcusdt.sqlite",
        "ETHUSDT": "data/ai_v1_3_ethusdt.sqlite",
        "SOLUSDT": "data/ai_v1_3_solusdt.sqlite",
    }
    assert payload["entity_id_prefix"] == "AI-v1.3:"

    forbidden_fragments = (
        "ai_v1_1_",
        "ai_v1_2_",
        "forward.sqlite",
        "forward_ustec.sqlite",
        "forward_us30.sqlite",
    )
    for path in payload["planned_ledgers"].values():
        assert not any(
            fragment in path for fragment in forbidden_fragments
        )


def test_crypto_review_gates_are_separate_and_calendar_guarded() -> None:
    payload = _load(GATES)

    assert payload["runtime_version"] == "AI-v1.3"
    assert payload["program_id"] == "crypto-expansion-1"
    assert payload["markets"] == list(MARKETS)

    assert payload["gates"] == {
        "C1": {
            "purpose": "operational_audit_only",
            "valid_inferences": 100,
            "completed_shadow_trades": 20,
            "minimum_calendar_days": 0,
        },
        "C2": {
            "purpose": "interim_crypto_economic_review",
            "valid_inferences": 500,
            "completed_shadow_trades": 50,
            "minimum_calendar_days": 60,
        },
        "C3": {
            "purpose": "first_crypto_publishability_graduation_decision",
            "valid_inferences": 1000,
            "completed_shadow_trades": 100,
            "minimum_calendar_days": 120,
        },
    }

    assert payload["per_market_reporting_required"] is True
    assert payload["weekday_weekend_reporting_required"] is True
    assert payload["no_post_activation_market_substitution"] is True
    assert payload["no_parameter_tuning_from_pre_gate_outcomes"] is True
    assert payload["gate_counts_may_not_pool_with_ai_v1_1"] is True
    assert payload["gate_counts_may_not_pool_with_ai_v1_2_1"] is True
    assert payload["gate_results_do_not_authorize_public_signal_exposure"] is True
    assert payload["gate_results_do_not_authorize_broker_execution"] is True


def test_crypto_registry_has_three_distinct_binance_spot_canonicals() -> None:
    registry = _load(REGISTRY)

    by_canonical = {
        row["canonical"]: row
        for row in registry["instruments"]
    }

    expected = {
        "BTC/USDT": "BTCUSDT",
        "ETH/USDT": "ETHUSDT",
        "SOL/USDT": "SOLUSDT",
    }

    for canonical, symbol in expected.items():
        row = by_canonical[canonical]
        assert row["asset_class"] == "crypto"
        source = row["sources"]["binance_spot"]
        assert source["symbol"] == symbol
        assert source["status"] == "primary"

    assert by_canonical["ETH/USD"]["sources"]["exness_mt5_demo"]["symbol"] == "ETHUSD"
    assert by_canonical["SOL/USD"]["sources"]["exness_mt5_demo"]["symbol"] == "SOLUSD"


def test_crypto_cost_checkpoint_matches_owner_vps_planning_evidence() -> None:
    payload = _load(CONFIG)
    cost = payload["api_cost_planning_checkpoint"]

    assert cost["usage_bearing_inferences"] == 456
    assert cost["observed_average_cost_per_inference_usd"] == 0.011578
    assert cost["assumed_24x7_h1_calls_per_crypto_market_30d"] == 720
    assert cost["estimated_increment_one_crypto_market_usd_30d"] == 8.34
    assert cost["estimated_increment_three_crypto_markets_usd_30d"] == 25.01
    assert cost["estimated_total_six_existing_plus_three_crypto_usd_30d"] == 61.69
    assert cost["planning_budget_six_existing_plus_three_crypto_usd_30d"] == 75.0
    assert cost["cost_estimate_is_not_a_research_gate"] is True
