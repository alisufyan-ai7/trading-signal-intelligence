from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.observability import DATABASE_PATHS, MARKETS
from trading_signal_intelligence.product.ai_insights import build_public_ai_insights


ACTIVATED = datetime(2026, 9, 28, 15, 56, 16, tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed(repo_root: Path) -> None:
    anchor_markets: dict[str, dict] = {}
    for symbol in MARKETS:
        ledger = AILedger(repo_root / DATABASE_PATHS[symbol])
        activation = ledger.append(
            record_type="ACTIVATION",
            entity_id=f"AI-v1.0:{symbol}:ACTIVATION",
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload={
                "protocol_version": "AI-v1.0",
                "market": symbol,
                "activated_at_utc": ACTIVATED.isoformat(),
                "broker_execution_enabled": False,
            },
        )
        anchor_markets[symbol] = {
            "record_hash": activation["record_hash"],
            "payload": activation["payload"],
        }

    forward = repo_root / "research" / "forward"
    forward.mkdir(parents=True, exist_ok=True)
    (forward / "AI-v1-activation-2026-09-28T155616Z.json").write_text(
        json.dumps(
            {
                "protocol_version": "AI-v1.0",
                "status": "TEST",
                "activated_at_utc": ACTIVATED.isoformat(),
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "artifact_hashes": {},
                "markets": anchor_markets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    xau = AILedger(repo_root / DATABASE_PATHS["XAUUSD"])
    entity = "AI-v1.0:XAUUSD:2026-09-28T17:00:00Z"
    inference = xau.append(
        record_type="INFERENCE",
        entity_id=entity,
        effective_at_utc=ACTIVATED + timedelta(hours=1),
        recorded_at_utc=ACTIVATED + timedelta(hours=1, minutes=2),
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": "XAUUSD",
            "source_bar_close_utc": "2026-09-28T17:00:00Z",
            "feature_snapshot": {
                "secret_derived_feature": 123.45,
                "source_bar_close_utc": "2026-09-28T17:00:00Z",
            },
            "feature_snapshot_sha256": "feature-secret-hash",
            "raw_structured_response": {"private": "provider-response"},
            "provider_request_id": "req_private",
            "metadata": {"internal": "metadata"},
            "normalized_decision": {
                "protocol_version": "AI-v1.0",
                "decision": "BUY",
                "raw_confidence": 73,
                "regime": "TREND_UP",
                "stop_atr": 1.5,
                "tp1_r": 1.0,
                "tp2_r": 2.5,
                "rationale": "Trend structure supports a shadow long setup.",
                "supporting_factors": ["positive trend", "controlled volatility"],
                "risk_factors": ["event risk"],
            },
            "guard_publishable": True,
            "guard_reasons": [],
            "estimated_cost_r": 0.04,
        },
    )
    xau.append(
        record_type="SIGNAL",
        entity_id=entity,
        effective_at_utc=ACTIVATED + timedelta(hours=2),
        recorded_at_utc=ACTIVATED + timedelta(hours=2),
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": "XAUUSD",
            "direction": "BUY",
            "entry_timestamp_utc": "2026-09-28T18:00:00+00:00",
            "entry": 3775.0,
            "stop": 3768.0,
            "tp1": 3782.0,
            "tp2": 3792.5,
            "max_hold_h1_bars": 24,
            "originating_inference_record_hash": inference["record_hash"],
            "broker_execution_enabled": False,
        },
    )

    ustec = AILedger(repo_root / DATABASE_PATHS["USTEC"])
    ustec_entity = "AI-v1.0:USTEC:2026-09-28T17:00:00Z"
    ustec.append(
        record_type="INFERENCE",
        entity_id=ustec_entity,
        effective_at_utc=ACTIVATED + timedelta(hours=1),
        recorded_at_utc=ACTIVATED + timedelta(hours=1, minutes=2),
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": "USTEC",
            "source_bar_close_utc": "2026-09-28T17:00:00Z",
            "normalized_decision": {
                "protocol_version": "AI-v1.0",
                "decision": "NO_TRADE",
                "raw_confidence": 31,
                "regime": "MIXED",
                "stop_atr": None,
                "tp1_r": None,
                "tp2_r": None,
                "rationale": "No sufficiently clear setup.",
                "supporting_factors": [],
                "risk_factors": ["mixed structure"],
            },
            "guard_publishable": False,
            "guard_reasons": [],
            "estimated_cost_r": 0.03,
        },
    )
    ustec.append(
        record_type="NO_TRADE",
        entity_id=ustec_entity,
        effective_at_utc=ACTIVATED + timedelta(hours=1),
        recorded_at_utc=ACTIVATED + timedelta(hours=1, minutes=2),
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": "USTEC",
        },
    )

    us30 = AILedger(repo_root / DATABASE_PATHS["US30"])
    us30.append(
        record_type="MISSED_INFERENCE",
        entity_id="AI-v1.0:US30:2026-09-28T17:00:00Z",
        effective_at_utc=ACTIVATED + timedelta(hours=1),
        recorded_at_utc=ACTIVATED + timedelta(hours=2),
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": "US30",
            "reason": "scheduler_gap_or_stale_at_discovery",
            "provider_call_made": False,
        },
    )


def test_public_ai_insights_are_sanitized_and_read_only(tmp_path) -> None:
    _seed(tmp_path)

    before = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }

    payload = build_public_ai_insights(
        tmp_path,
        include_scheduler=False,
        verify_upstream=False,
    )

    after = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }

    assert before == after
    assert payload["mode"] == "SHADOW_ONLY"
    assert payload["runtime_version"] == "AI-v1.0"
    assert payload["decision_protocol_version"] == "AI-v1.0"
    assert payload["legacy_lineage"] is None
    assert payload["health"]["healthy"] is True
    assert payload["health"]["broker_execution_disabled"] is True
    assert payload["totals"]["valid_inferences"] == 2
    assert payload["totals"]["signals"] == 1
    assert payload["totals"]["open_shadow_signals"] == 1
    assert payload["totals"]["missed_inferences"] == 1
    assert payload["totals"]["missed_reason_counts"] == {}
    assert payload["totals"]["no_current_h1_tick_count"] == 0
    assert payload["totals"]["processing_miss_count"] == 1
    assert payload["totals"]["processing_miss_denominator"] == 3
    assert payload["totals"]["processing_miss_rate"] == 1 / 3
    assert "not missed trades" in payload["operational_miss_notice"].lower()
    us30_public = next(
        row for row in payload["markets"]
        if row["source_symbol"] == "US30"
    )
    assert us30_public["missed_inferences"] == 1
    assert us30_public["no_current_h1_tick_count"] == 0
    assert us30_public["processing_miss_count"] == 1
    assert us30_public["processing_miss_denominator"] == 1
    assert us30_public["processing_miss_rate"] == 1.0
    assert payload["recent_decisions"][0]["decision"] == "BUY"
    assert payload["recent_decisions"][0]["raw_confidence"] == 73
    assert payload["recent_decisions"][0]["status"] == "SHADOW_SIGNAL"
    assert payload["shadow_signals"][0]["status"] == "active"
    assert payload["shadow_signals"][0]["entry"] == 3775.0

    public_keys: set[str] = set()

    def collect_keys(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                public_keys.add(str(key))
                collect_keys(item)
        elif isinstance(value, list):
            for item in value:
                collect_keys(item)

    collect_keys(payload)

    forbidden_keys = {
        "feature_snapshot",
        "feature_snapshot_sha256",
        "raw_structured_response",
        "provider_request_id",
        "metadata",
    }
    assert public_keys.isdisjoint(forbidden_keys), public_keys & forbidden_keys

    # Safety declaration keys are intentionally public and must not trigger the
    # exact-key leakage checks above.
    assert "raw_feature_snapshots_included" in public_keys
    assert "provider_request_metadata_included" in public_keys

    serialized = json.dumps(payload, sort_keys=True)
    for private_seed_value in (
        "req_private",
        "secret_derived_feature",
        "provider-response",
        "feature-secret-hash",
    ):
        assert private_seed_value not in serialized

    assert payload["raw_market_data_included"] is False
    assert payload["raw_feature_snapshots_included"] is False
    assert payload["provider_request_metadata_included"] is False
    assert payload["hidden_reasoning_included"] is False


def test_public_confidence_is_explicitly_uncalibrated(tmp_path) -> None:
    _seed(tmp_path)
    payload = build_public_ai_insights(
        tmp_path,
        include_scheduler=False,
        verify_upstream=False,
    )

    buy = next(
        row for row in payload["recent_decisions"]
        if row["decision"] == "BUY"
    )
    assert buy["confidence_label"] == "uncalibrated_model_score"
    assert "not a probability" in payload["confidence_notice"].lower()
