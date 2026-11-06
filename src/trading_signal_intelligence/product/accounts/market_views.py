"""P3 bounded source-safe Signal Center projections.

These are the 12 recent decisions and 20 recent shadow signals from the public
snapshot, not comprehensive verified history. Never serve restricted-six events.
"""
from __future__ import annotations

from typing import Any

from trading_signal_intelligence.product.accounts.policy import (
    CORE, core_signal_available, permitted_core_recent_signals,
)

DECISION_FIELDS = (
    "entity_id", "source_symbol", "source_bar_close_utc", "recorded_at_utc",
    "decision", "raw_confidence", "confidence_label", "regime", "rationale",
    "supporting_factors", "risk_factors", "guard_publishable", "guard_reasons",
    "estimated_cost_r", "status", "record_hash",
)


def current_research_feed(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "research_only": True, "history_complete": False,
        "source": "bounded_public_snapshot", "commercial_customer_eligible": False,
        "snapshot_generated_at_utc": (
            snapshot.get("generated_at_utc") if isinstance(snapshot, dict) else None
        ),
        "signal_records": [], "decisions": [],
    }
    if not core_signal_available(snapshot):
        return {**base, "status": "unavailable"}
    assert isinstance(snapshot, dict)
    ai = snapshot["ai_v1"]
    for symbol in ("XAUUSD", "USTEC", "US30"):
        base["signal_records"].extend(permitted_core_recent_signals(snapshot, symbol)["signals"])
    recent = ai.get("recent_decisions")
    if isinstance(recent, list):
        for item in recent[:12]:
            if not isinstance(item, dict) or item.get("source_symbol") not in CORE:
                continue
            # The guard/NO_TRADE decision and signal lifecycle are distinct.
            decision = item.get("decision")
            if decision not in ("BUY", "SELL", "NO_TRADE"):
                continue
            base["decisions"].append({f: item.get(f) for f in DECISION_FIELDS})
    base["status"] = "shadow_only"
    return base


def research_signal_by_id(
    snapshot: dict[str, Any] | None, entity_id: str,
) -> dict[str, Any] | None:
    if not entity_id or len(entity_id) > 128:
        return None
    matches = [r for r in current_research_feed(snapshot)["signal_records"]
               if r.get("entity_id") == entity_id]
    if len(matches) != 1:
        return None
    return {**matches[0], "history_complete": False,
            "research_only": True, "commercial_customer_eligible": False}


def bounded_history(
    snapshot: dict[str, Any] | None, *, symbol: str | None = None,
    decision: str | None = None, lifecycle: str | None = None,
) -> dict[str, Any]:
    if symbol is not None and symbol not in CORE:
        raise PermissionError("Research detail is not available for this market")
    if decision is not None and decision not in ("BUY", "SELL", "NO_TRADE"):
        raise ValueError("Invalid decision filter")
    if lifecycle is not None and lifecycle not in ("active", "closed", "NO_TRADE"):
        raise ValueError("Invalid lifecycle filter")
    feed = current_research_feed(snapshot)
    signals = [
        x for x in feed["signal_records"]
        if (symbol is None or x["source_symbol"] == symbol)
        and (decision is None or x.get("direction") == decision)
        and (lifecycle is None or x.get("status") == lifecycle)
    ]
    decisions = [
        x for x in feed["decisions"]
        if (symbol is None or x["source_symbol"] == symbol)
        and (decision is None or x.get("decision") == decision)
        and (lifecycle is None or (
            lifecycle == "NO_TRADE" and x.get("decision") == "NO_TRADE"))
    ]
    return {
        **{k: feed[k] for k in (
            "research_only", "history_complete", "source", "status",
            "snapshot_generated_at_utc", "commercial_customer_eligible"
        )},
        "signals": signals, "decisions": decisions,
        "record_window_notice": (
            "Only the current sanitized public snapshot: at most 20 recent "
            "signals and 12 recent decisions. Not an entire historical track record."
        ),
    }
