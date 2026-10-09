from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.crypto_observability_v1_3 import (
    build_report_v1_3,
)
from trading_signal_intelligence.ai_v1.runtime_verifier_registry_compat_v1_2_1 import (
    verify_active_runtime_registry_compat_v1_2_1,
)

PERFORMANCE_TYPES = {
    "INFERENCE",
    "NO_TRADE",
    "REJECTED_INFERENCE",
    "SIGNAL",
    "PARTIAL_EXIT",
    "EXIT",
    "MISSED_INFERENCE",
    "ERROR",
}


class CryptoRuntimeVerificationV13Error(RuntimeError):
    pass


def verify_active_runtime_v1_3(
    repo_root: Path,
    *,
    require_activation_only: bool = False,
    include_scheduler: bool = False,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    parallel = verify_active_runtime_registry_compat_v1_2_1(
        repo_root,
        require_activation_only=False,
        include_scheduler=False,
        verify_upstream=verify_upstream,
    )
    report = build_report_v1_3(
        repo_root,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )

    if report["runtime_version"] != "AI-v1.3":
        raise CryptoRuntimeVerificationV13Error("unexpected runtime version")
    if report["decision_protocol_version"] != "AI-v1.0":
        raise CryptoRuntimeVerificationV13Error("unexpected decision protocol")
    if report["program_id"] != "crypto-expansion-1":
        raise CryptoRuntimeVerificationV13Error("unexpected program id")
    if report["health"]["ledgers_valid"] is not True:
        raise CryptoRuntimeVerificationV13Error("crypto ledger verification failed")
    if report["health"]["activation_anchor_matches_ledgers"] is not True:
        raise CryptoRuntimeVerificationV13Error("crypto activation anchor mismatch")
    if report["health"]["crypto_artifacts_valid"] is not True:
        raise CryptoRuntimeVerificationV13Error("crypto artifact verification failed")
    if report["health"]["public_signal_exposure_disabled"] is not True:
        raise CryptoRuntimeVerificationV13Error("public exposure boundary failed")
    if report["health"]["broker_execution_disabled"] is not True:
        raise CryptoRuntimeVerificationV13Error("broker execution boundary failed")

    if verify_upstream and report["health"][
        "activation_anchor_upstream_valid"
    ] is not True:
        raise CryptoRuntimeVerificationV13Error(
            "AI-v1.3 activation anchor does not match upstream"
        )
    if include_scheduler and report["health"]["scheduler_healthy"] is not True:
        raise CryptoRuntimeVerificationV13Error("AI-v1.3 scheduler unhealthy")

    if parallel["runtime_verification"] != "PASS":
        raise CryptoRuntimeVerificationV13Error(
            "parallel AI-v1.2.1 runtime verification failed"
        )
    if parallel["broker_execution_disabled"] is not True:
        raise CryptoRuntimeVerificationV13Error(
            "parallel AI-v1.2.1 broker boundary failed"
        )

    if require_activation_only:
        for symbol, market in report["markets"].items():
            counts = market["counts_by_type"]
            if counts.get("ACTIVATION", 0) != 1:
                raise CryptoRuntimeVerificationV13Error(
                    f"{symbol} activation-only ledger must have one ACTIVATION"
                )
            present = {
                record_type: counts.get(record_type, 0)
                for record_type in PERFORMANCE_TYPES
                if counts.get(record_type, 0)
            }
            if present:
                raise CryptoRuntimeVerificationV13Error(
                    f"{symbol} contains performance-bearing records before first run: "
                    f"{present}"
                )

    return {
        "runtime_verification": "PASS",
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "program_id": "crypto-expansion-1",
        "activation_only_required": require_activation_only,
        "broker_execution_disabled": True,
        "public_signal_exposure_disabled": True,
        "parallel_ai_v1_2_1_runtime": parallel,
        "crypto": report,
    }
