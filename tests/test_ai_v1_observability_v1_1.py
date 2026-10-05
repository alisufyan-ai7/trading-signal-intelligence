from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.observability_v1_1 import (
    build_report_v1_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS,
    MARKETS,
)


ACTIVATED = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)


def _seed(repo_root: Path) -> None:
    markets: dict[str, dict] = {}
    for symbol in MARKETS:
        ledger = AILedger(repo_root / DATABASE_PATHS[symbol])
        payload = {
            "runtime_version": "AI-v1.1",
            "decision_protocol_version": "AI-v1.0",
            "market": symbol,
            "activated_at_utc": ACTIVATED.isoformat(),
            "repository_commit_sha": "0" * 40,
            "activation_bundle_sha256": "a" * 64,
            "supersedes_runtime_version": "AI-v1.0",
            "upstream_activation_anchor": (
                "research/forward/AI-v1-activation-2026-09-28T155616Z.json"
            ),
            "upstream_activation_anchor_sha256": "b" * 64,
            "gate_counts_carry_forward": False,
            "backfill_prior_missed": False,
            "provider": "openai",
            "model_id": "gpt-5.4-2026-03-05",
            "model_parameter_fingerprint": "c" * 64,
            "policy_sha256": "d" * 64,
            "feature_definitions_sha256": "e" * 64,
            "feature_schema_sha256": "f" * 64,
            "decision_schema_sha256": "1" * 64,
            "guardrails_sha256": "2" * 64,
            "feature_builder_source_sha256": "3" * 64,
            "inference_adapter_source_sha256": "4" * 64,
            "provider_neutral_inference_source_sha256": "5" * 64,
            "contract_source_sha256": "6" * 64,
            "guard_source_sha256": "7" * 64,
            "ai_ledger_source_sha256": "8" * 64,
            "lifecycle_evaluator_source_sha256": "9" * 64,
            "cost_policy_fingerprint": "a" * 64,
            "sync_max_wait_seconds": 30.0,
            "sync_poll_interval_seconds": 1.0,
            "broker_execution_enabled": False,
        }
        activation = ledger.append(
            record_type="ACTIVATION",
            entity_id=f"AI-v1.1:{symbol}:ACTIVATION",
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload=payload,
        )
        markets[symbol] = {
            "record_hash": activation["record_hash"],
            "payload": payload,
        }

    forward = repo_root / "research" / "forward"
    forward.mkdir(parents=True, exist_ok=True)
    (forward / "AI-v1.1-activation-2026-09-30T120000Z.json").write_text(
        json.dumps(
            {
                "runtime_version": "AI-v1.1",
                "decision_protocol_version": "AI-v1.0",
                "activated_at_utc": ACTIVATED.isoformat(),
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "gate_counts_carry_forward": False,
                "backfill_prior_missed": False,
                "artifact_hashes": {},
                "markets": markets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_v1_1_observability_starts_gate_counts_at_zero(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed(tmp_path)
    monkeypatch.setattr(
        "trading_signal_intelligence.ai_v1.observability_v1_1.verify_v1_1_artifacts",
        lambda repo_root, anchor: {
            "valid": True,
            "checked": 0,
            "mismatches": {},
        },
    )
    monkeypatch.setattr(
        "trading_signal_intelligence.ai_v1.observability_v1_1.verify_frozen_decision_artifacts_v1_1",
        lambda repo_root, anchor: {
            "valid": True,
            "checked": 0,
            "mismatches": {},
        },
    )

    report = build_report_v1_1(
        tmp_path,
        now_utc=ACTIVATED + timedelta(hours=1),
        include_scheduler=False,
        verify_upstream=False,
    )

    assert report["runtime_version"] == "AI-v1.1"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["protocol_version"] == "AI-v1.0"
    assert report["health"]["healthy"] is True
    assert report["totals"]["valid_inferences"] == 0
    assert report["totals"]["completed_shadow_trades"] == 0
    assert report["totals"]["open_shadow_signals"] == 0
    assert report["gates"]["A1"]["valid_inferences"]["current"] == 0
    assert report["gates"]["A1"]["completed_shadow_trades"]["current"] == 0
    assert report["gates"]["A1"]["eligible"] is False
    assert report["gates"]["A2"]["eligible"] is False
    assert report["gates"]["A3"]["eligible"] is False
    for symbol in MARKETS:
        assert report["markets"][symbol]["ledger_path"] == DATABASE_PATHS[symbol]
        assert report["markets"][symbol]["counts_by_type"] == {"ACTIVATION": 1}


def test_v1_1_observability_separates_no_tick_from_processing_misses(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed(tmp_path)
    monkeypatch.setattr(
        "trading_signal_intelligence.ai_v1.observability_v1_1.verify_v1_1_artifacts",
        lambda repo_root, anchor: {
            "valid": True,
            "checked": 0,
            "mismatches": {},
        },
    )
    monkeypatch.setattr(
        "trading_signal_intelligence.ai_v1.observability_v1_1.verify_frozen_decision_artifacts_v1_1",
        lambda repo_root, anchor: {
            "valid": True,
            "checked": 0,
            "mismatches": {},
        },
    )

    def append_missed(
        symbol: str,
        hour: int,
        reason: str,
    ) -> None:
        at = ACTIVATED + timedelta(hours=hour)
        AILedger(tmp_path / DATABASE_PATHS[symbol]).append(
            record_type="MISSED_INFERENCE",
            entity_id=f"AI-v1.1:{symbol}:2026-09-30T{12 + hour:02d}:00:00Z",
            effective_at_utc=at,
            recorded_at_utc=at + timedelta(minutes=2),
            payload={
                "reason": reason,
                "provider_call_made": False,
            },
        )

    append_missed("XAUUSD", 1, "no_current_h1_tick")
    append_missed("XAUUSD", 2, "no_current_h1_tick")
    append_missed("XAUUSD", 3, "scheduler_gap_or_stale_at_discovery")
    append_missed("USTEC", 1, "no_current_h1_tick")
    append_missed("USTEC", 2, "rates_not_synchronized")
    append_missed("US30", 1, "next_h1_open_unavailable")

    inference_at = ACTIVATED + timedelta(hours=4)
    AILedger(tmp_path / DATABASE_PATHS["US30"]).append(
        record_type="INFERENCE",
        entity_id="AI-v1.1:US30:2026-09-30T16:00:00Z",
        effective_at_utc=inference_at,
        recorded_at_utc=inference_at + timedelta(minutes=2),
        payload={"normalized_decision": {"decision": "NO_TRADE"}},
    )

    report = build_report_v1_1(
        tmp_path,
        now_utc=ACTIVATED + timedelta(hours=5),
        include_scheduler=False,
        verify_upstream=False,
    )

    xau = report["markets"]["XAUUSD"]
    assert xau["missed_inferences"] == 3
    assert xau["missed_reason_counts"] == {
        "no_current_h1_tick": 2,
        "scheduler_gap_or_stale_at_discovery": 1,
    }
    assert xau["no_current_h1_tick_count"] == 2
    assert xau["processing_miss_count"] == 1
    assert xau["processing_miss_denominator"] == 1
    assert xau["processing_miss_rate_excluding_no_current_h1_tick"] == 1.0

    totals = report["totals"]
    assert totals["missed_inferences"] == 6
    assert totals["missed_reason_counts"] == {
        "next_h1_open_unavailable": 1,
        "no_current_h1_tick": 3,
        "rates_not_synchronized": 1,
        "scheduler_gap_or_stale_at_discovery": 1,
    }
    assert totals["no_current_h1_tick_count"] == 3
    assert totals["processing_miss_count"] == 3
    assert totals["processing_miss_denominator"] == 4
    assert totals["processing_miss_rate_excluding_no_current_h1_tick"] == 0.75

    # Raw immutable accounting remains available for evidence/backward compatibility.
    assert totals["missed_rate_of_processed_opportunities"] == 6 / 7
