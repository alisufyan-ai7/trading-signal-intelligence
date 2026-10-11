"""Read-only, fail-closed AI-v1.3 crypto -> public validation-program adapter.

This module is a PRODUCT adapter, not part of the frozen K3 crypto runtime.
It emits aggregate validation evidence only, never individual crypto signals.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import ObservabilityError

CRYPTO_LABELS = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
}
CRYPTO_GATES = ("C1", "C2", "C3")
CRYPTO_ANCHOR_PATTERN = "AI-v1.3-crypto-expansion-activation-*.json"


def crypto_activation_state(repo_root: Path) -> dict[str, bool]:
    """Inspect shape only; do not read or create prospective crypto ledgers."""
    from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
        DATABASE_PATHS,
        MARKETS,
    )

    if set(MARKETS) != set(CRYPTO_LABELS):
        raise ObservabilityError("crypto cohort changed outside frozen market set")

    anchors = list((repo_root / "research" / "forward").glob(CRYPTO_ANCHOR_PATTERN))
    ledgers = [(repo_root / DATABASE_PATHS[symbol]).is_file() for symbol in MARKETS]
    return {
        "any_state": bool(anchors) or any(ledgers),
        "complete_shape": len(anchors) == 1 and all(ledgers),
    }


def _count(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ObservabilityError(f"invalid crypto validation count: {label}")
    return value


def normalize_crypto_validation_report(report: dict[str, Any]) -> dict[str, Any]:
    """Whitelisted view understood by the existing generic public renderer.

    Never pass the original crypto report to a public response: it contains
    paths, ledger hashes, activation metadata and private observability data.
    """
    if (
        report.get("runtime_version") != "AI-v1.3"
        or report.get("decision_protocol_version") != "AI-v1.0"
        or report.get("program_id") != "crypto-expansion-1"
        or report.get("mode") != "READ_ONLY"
    ):
        raise ObservabilityError("unexpected crypto report identity")

    health = report.get("health")
    activation = report.get("activation")
    if not isinstance(health, dict) or not isinstance(activation, dict):
        raise ObservabilityError("crypto health or activation proof missing")
    for key in (
        "healthy",
        "ledgers_valid",
        "activation_anchor_matches_ledgers",
        "crypto_artifacts_valid",
        "activation_anchor_upstream_valid",
        "scheduler_healthy",
        "public_signal_exposure_disabled",
        "broker_execution_disabled",
    ):
        if health.get(key) is not True:
            raise ObservabilityError(f"crypto public validation unsafe: {key}")

    if (
        activation.get("public_signal_exposure_enabled") is not False
        or activation.get("broker_execution_enabled") is not False
        or activation.get("backfill_prior_missed") is not False
    ):
        raise ObservabilityError("crypto activation exposure or backfill boundary failed")

    markets = report.get("markets")
    gates = report.get("gates")
    totals = report.get("totals")
    if not isinstance(markets, dict) or set(markets) != set(CRYPTO_LABELS):
        raise ObservabilityError("crypto validation requires all three frozen markets")
    if not isinstance(gates, dict) or set(gates) != set(CRYPTO_GATES):
        raise ObservabilityError("crypto validation requires frozen C1/C2/C3 gates")
    if not isinstance(totals, dict):
        raise ObservabilityError("crypto validation totals missing")

    safe_markets: dict[str, dict[str, Any]] = {}
    aggregate = {
        key: 0
        for key in (
            "valid_inferences",
            "completed_shadow_trades",
            "open_shadow_signals",
            "signals",
            "no_trade",
            "rejected_inferences",
            "missed_inferences",
            "errors",
        )
    }
    for symbol in CRYPTO_LABELS:
        raw = markets[symbol]
        if not isinstance(raw, dict) or raw.get("symbol") != symbol:
            raise ObservabilityError(f"invalid crypto market report: {symbol}")
        verification = raw.get("ledger_verification")
        if (
            not isinstance(verification, dict)
            or verification.get("valid") is not True
            or raw.get("activation_anchor_match") is not True
        ):
            raise ObservabilityError(f"crypto ledger or anchor invalid: {symbol}")

        counts = raw.get("counts_by_type")
        if not isinstance(counts, dict):
            raise ObservabilityError(f"crypto record counts missing: {symbol}")
        for kind, count in counts.items():
            _count(count, f"{symbol}:{kind}")
        current = {
            "valid_inferences": _count(raw.get("valid_inferences"), f"{symbol}:inferences"),
            "completed_shadow_trades": _count(
                raw.get("completed_shadow_trades"), f"{symbol}:completed"
            ),
            "open_shadow_signals": _count(raw.get("open_signals"), f"{symbol}:open"),
            "signals": counts.get("SIGNAL", 0),
            "no_trade": counts.get("NO_TRADE", 0),
            "rejected_inferences": counts.get("REJECTED_INFERENCE", 0),
            "missed_inferences": counts.get("MISSED_INFERENCE", 0),
            "errors": counts.get("ERROR", 0),
        }
        if current["valid_inferences"] != counts.get("INFERENCE", 0):
            raise ObservabilityError(f"crypto inference ledger mismatch: {symbol}")
        if current["completed_shadow_trades"] != counts.get("EXIT", 0):
            raise ObservabilityError(f"crypto exit ledger mismatch: {symbol}")
        if current["open_shadow_signals"] > current["signals"]:
            raise ObservabilityError(f"crypto open signals exceed records: {symbol}")

        for key, value in current.items():
            aggregate[key] += value
        safe_markets[symbol] = {
            "ledger_verification": {"valid": True},
            "activation_anchor_match": True,
            "valid_inferences": current["valid_inferences"],
            "performance_observational_only": {
                "completed_trades": current["completed_shadow_trades"],
            },
            "counts_by_type": {
                "SIGNAL": current["signals"],
                "NO_TRADE": current["no_trade"],
                "REJECTED_INFERENCE": current["rejected_inferences"],
            },
            "open_signals": current["open_shadow_signals"],
            "missed_inferences": current["missed_inferences"],
            "errors": current["errors"],
            "latest_recorded_at_utc": raw.get("latest_recorded_at_utc"),
        }

    for key in ("valid_inferences", "completed_shadow_trades", "open_shadow_signals"):
        if _count(totals.get(key), f"aggregate:{key}") != aggregate[key]:
            raise ObservabilityError(f"crypto aggregate mismatch: {key}")

    # All gates come from the frozen crypto observability report. Generic
    # builder keeps ONLY eligibility and count/calendar requirements.
    for gate_id in CRYPTO_GATES:
        gate = gates[gate_id]
        if not isinstance(gate, dict) or gate.get("gate") != gate_id:
            raise ObservabilityError(f"invalid frozen crypto gate: {gate_id}")
        for metric in ("valid_inferences", "completed_shadow_trades"):
            evidence = gate.get(metric)
            if not isinstance(evidence, dict):
                raise ObservabilityError(f"crypto gate metric missing: {gate_id}/{metric}")
            if _count(evidence.get("current"), f"{gate_id}:{metric}") != aggregate[metric]:
                raise ObservabilityError(f"crypto gate count mismatch: {gate_id}/{metric}")

    return {
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "health": {
            "healthy": True,
            "ledgers_valid": True,
            "scheduler_healthy": True,
            "public_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "totals": aggregate,
        "gates": gates,
        "markets": safe_markets,
    }


def build_crypto_public_validation_program(
    repo_root: Path,
    *,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    if not include_scheduler or not verify_upstream:
        raise ObservabilityError("public crypto validation requires full verification")

    # Lazy imports avoid changing the private runtime and its frozen hashes.
    from trading_signal_intelligence.ai_v1.crypto_observability_v1_3 import (
        build_report_v1_3,
    )
    from trading_signal_intelligence.product.ai_insights import (
        build_public_validation_program,
    )

    report = build_report_v1_3(
        repo_root,
        include_scheduler=True,
        verify_upstream=True,
    )
    return build_public_validation_program(
        normalize_crypto_validation_report(report),
        program_id="crypto-expansion-1",
        title="Crypto AI Shadow Validation",
        market_labels=CRYPTO_LABELS,
        public_signal_exposure=False,
    )
