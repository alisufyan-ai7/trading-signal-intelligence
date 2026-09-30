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
