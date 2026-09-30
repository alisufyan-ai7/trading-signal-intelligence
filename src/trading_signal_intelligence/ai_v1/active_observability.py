from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS as V10_DATABASE_PATHS,
    MARKETS,
    ObservabilityError,
    build_report as build_report_v1_0,
)
from trading_signal_intelligence.ai_v1.observability_v1_1 import (
    build_report_v1_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS as V11_DATABASE_PATHS,
)


def v1_1_state(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    anchors = sorted(
        (root / "research" / "forward").glob("AI-v1.1-activation-*.json")
    )
    ledgers = {
        symbol: (root / V11_DATABASE_PATHS[symbol]).exists()
        for symbol in MARKETS
    }
    return {
        "anchors": [str(path.relative_to(root)) for path in anchors],
        "ledgers": ledgers,
        "any_state": bool(anchors) or any(ledgers.values()),
        "complete_shape": len(anchors) == 1 and all(ledgers.values()),
    }


def detect_active_runtime(repo_root: Path) -> str:
    state = v1_1_state(repo_root)
    if not state["any_state"]:
        return "AI-v1.0"
    if not state["complete_shape"]:
        raise ObservabilityError(
            "partial AI-v1.1 state detected; refuse fallback to AI-v1.0"
        )

    # A complete-looking v1.1 state must actually verify. Never silently
    # fall back to v1.0 after any v1.1 activation evidence exists.
    build_report_v1_1(
        repo_root,
        include_scheduler=False,
        verify_upstream=False,
    )
    return "AI-v1.1"


def active_database_paths(repo_root: Path) -> dict[str, str]:
    runtime = detect_active_runtime(repo_root)
    return (
        dict(V11_DATABASE_PATHS)
        if runtime == "AI-v1.1"
        else dict(V10_DATABASE_PATHS)
    )


def build_active_report(
    repo_root: Path,
    *,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    runtime = detect_active_runtime(repo_root)
    if runtime == "AI-v1.1":
        return build_report_v1_1(
            repo_root,
            include_scheduler=include_scheduler,
            verify_upstream=verify_upstream,
        )

    report = build_report_v1_0(
        repo_root,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )
    return {
        **report,
        "runtime_version": "AI-v1.0",
        "decision_protocol_version": report["protocol_version"],
    }


def build_legacy_v1_0_summary(
    repo_root: Path,
) -> dict[str, Any]:
    report = build_report_v1_0(
        repo_root,
        include_scheduler=False,
        verify_upstream=False,
    )
    totals = report["totals"]
    return {
        "runtime_version": "AI-v1.0",
        "decision_protocol_version": report["protocol_version"],
        "activation_utc": report["activation"]["activated_at_utc"],
        "valid_inferences": totals["valid_inferences"],
        "signals": totals["signals"],
        "completed_shadow_trades": totals["completed_shadow_trades"],
        "missed_inferences": totals["missed_inferences"],
        "errors": totals["errors"],
        "performance_observational_only": totals[
            "performance_observational_only"
        ],
        "gate_counts_carried_into_active_runtime": False,
    }
