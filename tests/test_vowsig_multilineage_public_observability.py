from __future__ import annotations

from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.observability import ObservabilityError
from trading_signal_intelligence.ai_v1.observability_v1_1 import (
    PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS,
    PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS,
)
from trading_signal_intelligence.product.ai_insights import (
    build_public_validation_program,
)


ROOT = Path(__file__).resolve().parents[1]


def _report() -> dict:
    return {
        "runtime_version": "AI-v1.2.1",
        "decision_protocol_version": "AI-v1.0",
        "health": {
            "healthy": True,
            "ledgers_valid": True,
            "scheduler_healthy": True,
            "public_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "totals": {
            "valid_inferences": 6,
            "completed_shadow_trades": 0,
            "open_shadow_signals": 2,
            "signals": 2,
            "no_trade": 2,
            "rejected_inferences": 2,
            "missed_inferences": 3,
            "errors": 0,
        },
        "gates": {
            "X1": {
                "eligible": False,
                "valid_inferences": {
                    "current": 6,
                    "required": 100,
                    "met": False,
                },
                "completed_shadow_trades": {
                    "current": 0,
                    "required": 20,
                    "met": False,
                },
                "minimum_calendar_days": 0,
                "calendar_requirement_met": True,
                "calendar_days_remaining": 0,
                "calendar_eligible_at_utc": "2026-10-07T09:35:43+00:00",
            },
            "X2": {
                "eligible": False,
                "valid_inferences": {
                    "current": 6,
                    "required": 500,
                    "met": False,
                },
                "completed_shadow_trades": {
                    "current": 0,
                    "required": 50,
                    "met": False,
                },
                "minimum_calendar_days": 60,
                "calendar_requirement_met": False,
                "calendar_days_remaining": 60,
                "calendar_eligible_at_utc": "2026-12-06T09:35:43+00:00",
            },
            "X3": {
                "eligible": False,
                "valid_inferences": {
                    "current": 6,
                    "required": 1000,
                    "met": False,
                },
                "completed_shadow_trades": {
                    "current": 0,
                    "required": 100,
                    "met": False,
                },
                "minimum_calendar_days": 120,
                "calendar_requirement_met": False,
                "calendar_days_remaining": 120,
                "calendar_eligible_at_utc": "2027-02-04T09:35:43+00:00",
            },
        },
        "markets": {
            symbol: {
                "ledger_verification": {"valid": True},
                "activation_anchor_match": True,
                "valid_inferences": 2,
                "performance_observational_only": {"completed_trades": 0},
                "counts_by_type": {
                    "SIGNAL": 1 if symbol != "USOIL" else 0,
                    "NO_TRADE": 1 if symbol == "USOIL" else 0,
                    "REJECTED_INFERENCE": 1 if symbol != "USOIL" else 0,
                },
                "open_signals": 1 if symbol != "USOIL" else 0,
                "missed_inferences": 1,
                "errors": 0,
                "latest_recorded_at_utc": "2026-10-07T12:03:31+00:00",
            }
            for symbol in ("EURUSD", "XAGUSD", "USOIL")
        },
    }


def test_generic_validation_program_exposes_progress_not_signal_details() -> None:
    payload = build_public_validation_program(
        _report(),
        program_id="market-expansion-1",
        title="Expansion Shadow Validation",
        market_labels={
            "EURUSD": "EUR/USD",
            "XAGUSD": "XAG/USD",
            "USOIL": "WTI",
        },
        public_signal_exposure=False,
    )

    assert payload["mode"] == "SHADOW_ONLY"
    assert payload["public_research_observability"] is True
    assert payload["public_signal_exposure"] is False
    assert payload["signal_details_included"] is False
    assert [gate["gate_id"] for gate in payload["gates"]] == ["X1", "X2", "X3"]

    x2 = next(gate for gate in payload["gates"] if gate["gate_id"] == "X2")
    metrics = {row["metric"]: row for row in x2["requirements"]}
    assert metrics["valid_inferences"]["current"] == 6
    assert metrics["valid_inferences"]["required"] == 500
    assert metrics["completed_shadow_trades"]["required"] == 50
    assert metrics["calendar_days"]["required"] == 60

    serialized = repr(payload)
    for forbidden in (
        "'entry'",
        "'stop'",
        "'tp1'",
        "'tp2'",
        "'rationale'",
        "'raw_confidence'",
    ):
        assert forbidden not in serialized


def test_research_only_program_requires_public_exposure_boundary_disabled() -> None:
    report = _report()
    report["health"]["public_exposure_disabled"] = False

    with pytest.raises(ObservabilityError, match="public exposure boundary"):
        build_public_validation_program(
            report,
            program_id="market-expansion-1",
            title="Expansion Shadow Validation",
            market_labels={},
            public_signal_exposure=False,
        )


def test_public_surface_v3_expands_only_product_observability_artifacts() -> None:
    assert PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS < (
        PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS
    )
    assert (
        PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS
        - PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS
    ) == {
        "ai_insights_source",
        "public_snapshot_export_script",
        "public_snapshot_push_script",
    }


def test_frontend_validation_programs_are_data_driven() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert 'fetch("/api/validation/programs")' in app
    assert "renderValidationPrograms" in app
    assert '["A1", "A2", "A3"]' not in app
    assert '["X1", "X2", "X3"]' not in app
    assert 'id="validation-programs"' in index
    assert "SHADOW VALIDATION PROGRAMS" in index
