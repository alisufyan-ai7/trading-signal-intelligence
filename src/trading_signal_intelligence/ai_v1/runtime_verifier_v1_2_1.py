from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
    build_report_v1_2_1,
)
from trading_signal_intelligence.ai_v1.runtime_verifier_v1_1 import (
    verify_active_runtime_v1_1,
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


class RuntimeVerificationV121Error(RuntimeError):
    pass


def verify_active_runtime_v1_2_1(
    repo_root: Path,
    *,
    require_activation_only: bool = False,
    include_scheduler: bool = False,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    parallel = verify_active_runtime_v1_1(
        repo_root,
        require_activation_only=False,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )
    report = build_report_v1_2_1(
        repo_root,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )

    if report["runtime_version"] != "AI-v1.2.1":
        raise RuntimeVerificationV121Error("unexpected runtime version")
    if report["decision_protocol_version"] != "AI-v1.0":
        raise RuntimeVerificationV121Error("unexpected decision protocol")
    if report["activation"]["predecessor_runtime_version"] != "AI-v1.2":
        raise RuntimeVerificationV121Error("predecessor runtime binding mismatch")
    if report["activation"]["predecessor_evidence_carry_forward"] is not False:
        raise RuntimeVerificationV121Error("predecessor evidence carry-forward detected")
    if report["activation"]["calendar_carry_forward"] is not False:
        raise RuntimeVerificationV121Error("predecessor calendar carry-forward detected")
    if report["activation"]["parallel_to_runtime_version"] != "AI-v1.1":
        raise RuntimeVerificationV121Error("parallel runtime binding mismatch")
    if not report["health"]["ledgers_valid"]:
        raise RuntimeVerificationV121Error("AI-v1.2.1 ledger verification failed")
    if not report["health"]["expansion_artifacts_valid"]:
        raise RuntimeVerificationV121Error(
            "AI-v1.2.1 expansion artifact verification failed"
        )
    if report["health"]["public_exposure_disabled"] is not True:
        raise RuntimeVerificationV121Error("public exposure boundary failed")
    if report["health"]["broker_execution_disabled"] is not True:
        raise RuntimeVerificationV121Error("broker execution boundary failed")

    if verify_upstream and report["health"][
        "activation_anchor_upstream_valid"
    ] is not True:
        raise RuntimeVerificationV121Error(
            "AI-v1.2.1 activation anchor does not match upstream"
        )

    if parallel["runtime_verification"] != "PASS":
        raise RuntimeVerificationV121Error(
            "parallel AI-v1.1 runtime verification failed"
        )
    if parallel["broker_execution_disabled"] is not True:
        raise RuntimeVerificationV121Error(
            "parallel AI-v1.1 broker boundary failed"
        )

    if require_activation_only:
        for symbol, market in report["markets"].items():
            counts = market["counts_by_type"]
            if counts.get("ACTIVATION", 0) != 1:
                raise RuntimeVerificationV121Error(
                    f"{symbol} activation-only ledger must have one ACTIVATION"
                )
            present = {
                record_type: counts.get(record_type, 0)
                for record_type in PERFORMANCE_TYPES
                if counts.get(record_type, 0)
            }
            if present:
                raise RuntimeVerificationV121Error(
                    f"{symbol} already contains performance-bearing records: "
                    f"{present}"
                )
            if market["records"] != 1:
                raise RuntimeVerificationV121Error(
                    f"{symbol} activation-only ledger has "
                    f"{market['records']} records"
                )

    return {
        "runtime_verification": "PASS",
        "runtime_version": report["runtime_version"],
        "decision_protocol_version": report["decision_protocol_version"],
        "parallel_runtime_verification": parallel,
        "anchor_file": report["activation"]["anchor_file"],
        "activated_at_utc": report["activation"]["activated_at_utc"],
        "activation_only_required": require_activation_only,
        "ledgers_valid": report["health"]["ledgers_valid"],
        "expansion_artifacts_valid": report["health"][
            "expansion_artifacts_valid"
        ],
        "activation_anchor_upstream_valid": report["health"][
            "activation_anchor_upstream_valid"
        ],
        "public_exposure_disabled": report["health"][
            "public_exposure_disabled"
        ],
        "broker_execution_disabled": report["health"][
            "broker_execution_disabled"
        ],
        "scheduler_healthy": report["health"]["scheduler_healthy"],
        "markets": {
            symbol: {
                "records": market["records"],
                "head_hash": market["current_head_hash"],
                "counts_by_type": market["counts_by_type"],
                "open_signals": market["open_signals"],
            }
            for symbol, market in report["markets"].items()
        },
    }
