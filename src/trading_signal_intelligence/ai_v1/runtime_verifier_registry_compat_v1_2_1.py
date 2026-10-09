from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
    build_report_v1_2_1,
)
from trading_signal_intelligence.ai_v1.registry_compat_v1_2_1 import (
    verify_expansion_artifacts_registry_compat_v1_2_1,
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


class RegistryCompatibleRuntimeVerificationV121Error(RuntimeError):
    pass


def _load_anchor(repo_root: Path, relative: str) -> dict[str, Any]:
    try:
        payload = json.loads((repo_root / relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            f"unable to load AI-v1.2.1 activation anchor: {relative}"
        ) from exc
    if not isinstance(payload, dict):
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "AI-v1.2.1 activation anchor root must be object"
        )
    return payload


def verify_active_runtime_registry_compat_v1_2_1(
    repo_root: Path,
    *,
    require_activation_only: bool = False,
    include_scheduler: bool = False,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
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

    anchor_file = str(report["activation"]["anchor_file"])
    anchor = _load_anchor(repo_root, anchor_file)
    artifacts = verify_expansion_artifacts_registry_compat_v1_2_1(
        repo_root,
        anchor,
    )

    if report["runtime_version"] != "AI-v1.2.1":
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "unexpected runtime version"
        )
    if report["decision_protocol_version"] != "AI-v1.0":
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "unexpected decision protocol"
        )
    if report["activation"]["predecessor_runtime_version"] != "AI-v1.2":
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "predecessor runtime binding mismatch"
        )
    if report["activation"]["predecessor_evidence_carry_forward"] is not False:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "predecessor evidence carry-forward detected"
        )
    if report["activation"]["calendar_carry_forward"] is not False:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "predecessor calendar carry-forward detected"
        )
    if report["activation"]["parallel_to_runtime_version"] != "AI-v1.1":
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "parallel runtime binding mismatch"
        )
    if report["health"]["ledgers_valid"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "AI-v1.2.1 ledger verification failed"
        )
    if artifacts["valid"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "AI-v1.2.1 expansion artifact verification failed"
        )
    if report["health"]["public_exposure_disabled"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "public exposure boundary failed"
        )
    if report["health"]["broker_execution_disabled"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "broker execution boundary failed"
        )

    if verify_upstream and report["health"][
        "activation_anchor_upstream_valid"
    ] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "AI-v1.2.1 activation anchor does not match upstream"
        )
    if include_scheduler and report["health"]["scheduler_healthy"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "AI-v1.2.1 scheduler unhealthy"
        )

    if parallel["runtime_verification"] != "PASS":
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "parallel AI-v1.1 runtime verification failed"
        )
    if parallel["broker_execution_disabled"] is not True:
        raise RegistryCompatibleRuntimeVerificationV121Error(
            "parallel AI-v1.1 broker boundary failed"
        )

    if require_activation_only:
        for symbol, market in report["markets"].items():
            counts = market["counts_by_type"]
            if counts.get("ACTIVATION", 0) != 1:
                raise RegistryCompatibleRuntimeVerificationV121Error(
                    f"{symbol} activation-only ledger must have one ACTIVATION"
                )
            present = {
                record_type: counts.get(record_type, 0)
                for record_type in PERFORMANCE_TYPES
                if counts.get(record_type, 0)
            }
            if present:
                raise RegistryCompatibleRuntimeVerificationV121Error(
                    f"{symbol} already contains performance-bearing records: "
                    f"{present}"
                )
            if market["records"] != 1:
                raise RegistryCompatibleRuntimeVerificationV121Error(
                    f"{symbol} activation-only ledger has "
                    f"{market['records']} records"
                )

    return {
        "runtime_verification": "PASS",
        "runtime_version": report["runtime_version"],
        "decision_protocol_version": report["decision_protocol_version"],
        "parallel_runtime_verification": parallel,
        "anchor_file": anchor_file,
        "activated_at_utc": report["activation"]["activated_at_utc"],
        "activation_only_required": require_activation_only,
        "ledgers_valid": report["health"]["ledgers_valid"],
        "expansion_artifacts_valid": True,
        "registry_compatibility": artifacts,
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
