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


def test_v1_2_1_preactivation_is_side_effect_free_and_fails_closed_after_activation() -> None:
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
    assert report["preactivation_check"] == "FAIL"
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
    assert [
        Path(value).as_posix()
        for value in report["successor_activation_anchors"]
    ] == [
        "research/forward/AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
    ]
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


def _candle(
    *,
    symbol: str,
    canonical: str,
    timeframe: str,
    timestamp,
    index: int,
    closed: bool,
):
    from decimal import Decimal
    from trading_signal_intelligence.models import Candle

    base = Decimal("100") + Decimal(index) / Decimal("100")
    return Candle(
        source="exness_mt5_demo",
        source_symbol=symbol,
        symbol=canonical,
        timeframe=timeframe,
        timestamp_utc=timestamp,
        open=base,
        high=base + Decimal("0.30"),
        low=base - Decimal("0.30"),
        close=base + Decimal("0.05"),
        volume=Decimal(100 + (index % 17)),
        volume_kind="tick_volume",
        spread=Decimal("6"),
        is_closed=closed,
    )


class NoTradeAdapterV121:
    provider = "test"
    model_id = "test-model"
    parameters = {"temperature": 0}

    def __init__(self) -> None:
        self.calls = 0

    def infer(self, **kwargs):
        self.calls += 1
        return (
            {
                "protocol_version": "AI-v1.0",
                "decision": "NO_TRADE",
                "raw_confidence": 50,
                "regime": "UNCLEAR",
                "stop_atr": None,
                "tp1_r": None,
                "tp2_r": None,
                "rationale": "correction plumbing test",
                "supporting_factors": [],
                "risk_factors": ["test"],
            },
            {"request_id": "test-v121"},
        )


def test_corrected_activation_guard_hash_reaches_inference_record(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timedelta, timezone

    from trading_signal_intelligence.ai_v1.ledger import AILedger
    from trading_signal_intelligence.ai_v1.shadow_runtime_v1_2_1 import (
        MarketSpecV121,
        run_market_cycle_v1_2_1,
    )

    utc = timezone.utc
    activated = datetime(2026, 10, 7, 0, 0, tzinfo=utc)
    now = datetime(2026, 10, 7, 1, 0, 30, tzinfo=utc)
    current_h1 = datetime(2026, 10, 7, 1, 0, tzinfo=utc)
    current_h4 = datetime(2026, 10, 7, 0, 0, tzinfo=utc)

    h1 = [
        _candle(
            symbol="EURUSD",
            canonical="EUR/USD",
            timeframe="H1",
            timestamp=current_h1 - timedelta(hours=499 - index),
            index=index,
            closed=index != 499,
        )
        for index in range(500)
    ]
    h4 = [
        _candle(
            symbol="EURUSD",
            canonical="EUR/USD",
            timeframe="H4",
            timestamp=current_h4 - timedelta(hours=4 * (199 - index)),
            index=index,
            closed=index != 199,
        )
        for index in range(200)
    ]

    ledger = AILedger(tmp_path / "ai_v1_2_1_eurusd.sqlite")
    ledger.append(
        record_type="ACTIVATION",
        entity_id="AI-v1.2.1:EURUSD:ACTIVATION",
        effective_at_utc=activated,
        recorded_at_utc=activated,
        payload={
            "runtime_version": "AI-v1.2.1",
            "decision_protocol_version": "AI-v1.0",
            "parallel_to_runtime_version": "AI-v1.1",
            "activated_at_utc": activated.isoformat(),
            "policy_sha256": "a" * 64,
            "expansion_guardrails_sha256": "b" * 64,
            "public_exposure_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    guardrails = json.loads(
        (ROOT / "config" / "ai_v1_2_1_guardrails.json").read_text(
            encoding="utf-8"
        )
    )
    decision_schema = json.loads(
        (ROOT / "config" / "ai_v1_decision_schema.json").read_text(
            encoding="utf-8"
        )
    )
    adapter = NoTradeAdapterV121()
    market = MarketSpecV121(
        source_symbol="EURUSD",
        canonical_symbol="EUR/USD",
        point_size=0.00001,
        database_path=tmp_path / "ai_v1_2_1_eurusd.sqlite",
    )

    result = run_market_cycle_v1_2_1(
        ledger=ledger,
        market=market,
        h1_all=h1,
        h4_all=h4,
        adapter=adapter,
        policy_text="frozen policy",
        decision_schema=decision_schema,
        guardrails=guardrails,
        now_utc=now,
    )

    assert result["provider_error_seen"] is False
    assert adapter.calls == 1
    counts = ledger.counts_by_type()
    assert counts["ACTIVATION"] == 1
    assert counts["INFERENCE"] == 1
    assert counts["NO_TRADE"] == 1

    inference = ledger.records(record_type="INFERENCE")[0]
    assert inference["payload"]["runtime_version"] == "AI-v1.2.1"
    assert inference["payload"]["guardrails_sha256"] == "b" * 64


def test_successor_probe_is_read_only_and_has_no_activation_path() -> None:
    text = (
        ROOT / "scripts" / "probe_ai_v1_2_1_market_readiness.py"
    ).read_text(encoding="utf-8")

    assert "symbol_select(" not in text
    assert "OpenAIResponsesAdapter" not in text
    assert "AILedger" not in text
    assert "Register-ScheduledTask" not in text
    assert "activate_ai" not in text


def test_frozen_predecessor_file_hashes_match_p2_evidence() -> None:
    payload = json.loads(
        (
            ROOT
            / "research"
            / "forward"
            / "AI-v1.2-P2-fail-closed-2026-10-06T220043Z.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["markets"]["EURUSD"]["ledger_file_sha256_after"] == (
        "f2fef91f7b2b5b77853d1618a0c8fa8de03133a392c4fa620450ea3cea211322"
    )
    assert payload["markets"]["XAGUSD"]["ledger_file_sha256_after"] == (
        "5813067c4d19f53aa98ca992b75798b3a447083ed0fc0c97131adece2c0b24e4"
    )
    assert payload["markets"]["USOIL"]["ledger_file_sha256_after"] == (
        "a5cfa5bc29b30b5607673c8da336d28f357b2cb7ffeb09933af3a21a00a0e8ca"
    )
