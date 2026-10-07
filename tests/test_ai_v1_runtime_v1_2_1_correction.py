from __future__ import annotations

import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.engine_v1_2_1 import (
    RUNTIME_VERSION,
)
from trading_signal_intelligence.ai_v1.expansion_v1_2_1 import (
    DATABASE_PATHS,
    MARKETS,
    preactivation_report_v1_2_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_2_1 import (
    cycle_entity_id_v1_2_1,
)


ROOT = Path(__file__).resolve().parents[1]


def _canonicalize_successor_source(text: str) -> str:
    return (
        text.replace("AI-v1.2.1", "AI-v1.2")
        .replace("v1_2_1", "v1_2")
        .replace("V121", "V12")
        .replace("ai_v1_2_1_", "ai_v1_2_")
    )


def test_v1_2_1_identity_and_fresh_ledgers() -> None:
    assert RUNTIME_VERSION == "AI-v1.2.1"
    assert MARKETS == ("EURUSD", "XAGUSD", "USOIL")
    assert DATABASE_PATHS == {
        "EURUSD": "data/ai_v1_2_1_eurusd.sqlite",
        "XAGUSD": "data/ai_v1_2_1_xagusd.sqlite",
        "USOIL": "data/ai_v1_2_1_usoil.sqlite",
    }


def test_v1_2_1_entity_ids_are_isolated() -> None:
    from datetime import datetime, timezone

    value = cycle_entity_id_v1_2_1(
        "EURUSD",
        datetime(2026, 10, 7, 1, 0, tzinfo=timezone.utc),
    )
    assert value == "AI-v1.2.1:EURUSD:2026-10-07T01:00:00Z"


def test_successor_engine_changes_identity_only() -> None:
    predecessor = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "engine_v1_2.py"
    ).read_text(encoding="utf-8")
    successor = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "engine_v1_2_1.py"
    ).read_text(encoding="utf-8")

    assert _canonicalize_successor_source(successor) == predecessor


def test_successor_shadow_runtime_has_one_allowed_logic_correction() -> None:
    predecessor = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "shadow_runtime_v1_2.py"
    ).read_text(encoding="utf-8")
    successor = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "shadow_runtime_v1_2_1.py"
    ).read_text(encoding="utf-8")

    normalized = _canonicalize_successor_source(successor)
    normalized = normalized.replace(
        'activation_payload["expansion_guardrails_sha256"]',
        'activation_payload["guardrails_sha256"]',
    )
    assert normalized == predecessor

    assert (
        'activation_payload["expansion_guardrails_sha256"]'
        in successor
    )
    assert 'activation_payload["guardrails_sha256"]' not in successor


def test_v1_2_1_configs_preserve_decision_semantics() -> None:
    old_guard = json.loads(
        (ROOT / "config" / "ai_v1_2_guardrails.json").read_text(
            encoding="utf-8"
        )
    )
    new_guard = json.loads(
        (ROOT / "config" / "ai_v1_2_1_guardrails.json").read_text(
            encoding="utf-8"
        )
    )
    old_guard["status"] = "<status>"
    new_guard["status"] = "<status>"
    assert new_guard == old_guard

    old_gates = json.loads(
        (ROOT / "config" / "ai_v1_2_review_gates.json").read_text(
            encoding="utf-8"
        )
    )
    new_gates = json.loads(
        (ROOT / "config" / "ai_v1_2_1_review_gates.json").read_text(
            encoding="utf-8"
        )
    )
    assert new_gates["gates"] == old_gates["gates"]
    assert new_gates["markets"] == old_gates["markets"]


def test_v1_2_1_preactivation_is_side_effect_free_and_valid() -> None:
    before = {
        symbol: (ROOT / relative).exists()
        for symbol, relative in DATABASE_PATHS.items()
    }
    report = preactivation_report_v1_2_1(ROOT)
    after = {
        symbol: (ROOT / relative).exists()
        for symbol, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert report["preactivation_check"] == "PASS"
    assert report["runtime_version"] == "AI-v1.2.1"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["predecessor_runtime_version"] == "AI-v1.2"
    assert report["predecessor_failure"]["valid"] is True
    assert report["predecessor_failure"]["predecessor_valid_inferences"] == 0
    assert report["predecessor_failure"]["predecessor_missed_inferences"] == 1
    assert report["feature_formula_change"] is False
    assert report["decision_contract_change"] is False
    assert report["policy_change"] is False
    assert report["guard_numeric_semantics_change"] is False
    assert report["market_set_change_from_ai_v1_2"] is False
    assert report["gate_counts_carry_forward"] is False
    assert report["calendar_carry_forward"] is False
    assert report["backfill_prior_missed"] is False
    assert not any(report["successor_ledger_paths_exist"].values())
    assert report["successor_activation_anchors"] == []
    assert report["provider_call_made"] is False
    assert report["mt5_call_made"] is False
    assert report["ledger_write_performed"] is False
    assert report["activation_performed"] is False
    assert report["scheduler_changed"] is False
    assert report["public_exposure_changed"] is False
    assert report["broker_execution_enabled"] is False


def test_p2_failure_metadata_is_frozen_and_requires_successor() -> None:
    payload = json.loads(
        (
            ROOT
            / "research"
            / "forward"
            / "AI-v1.2-P2-fail-closed-2026-10-06T220043Z.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["classification"] == "FAIL_CLOSED_RUNTIME_WIRING_DEFECT"
    assert payload["aggregate_after"]["valid_inferences"] == 0
    assert payload["aggregate_after"]["missed_inferences"] == 1
    assert payload["root_cause"]["runtime_lookup"] == "guardrails_sha256"
    assert (
        payload["root_cause"]["frozen_activation_payload_field"]
        == "expansion_guardrails_sha256"
    )
    assert payload["governance"]["retry_ai_v1_2_forbidden"] is True
    assert payload["governance"]["successor_required"] is True
