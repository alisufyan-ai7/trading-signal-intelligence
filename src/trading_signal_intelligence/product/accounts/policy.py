"""Fixed P0 market permissions, independent of account role, access tier or UI filtering.

This module must never infer permission from a market being cataloged, a user's
watchlist, a model's confidence, or an observed internal inference.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CORE = frozenset({"XAUUSD", "USTEC", "US30"})
CATALOG = (
    ("XAUUSD", "Gold (XAU/USD)", "Gold & indices", "core-ai-shadow"),
    ("USTEC", "NASDAQ 100 (USTEC)", "Gold & indices", "core-ai-shadow"),
    ("US30", "Dow 30 (US30)", "Gold & indices", "core-ai-shadow"),
    ("EURUSD", "EUR/USD", "Forex & commodities", "market-expansion-1"),
    ("XAGUSD", "Silver (XAG/USD)", "Forex & commodities", "market-expansion-1"),
    ("USOIL", "WTI Oil (USOIL)", "Forex & commodities", "market-expansion-1"),
    ("BTCUSDT", "Bitcoin (BTC/USDT)", "Crypto", "crypto-expansion-1"),
    ("ETHUSDT", "Ethereum (ETH/USDT)", "Crypto", "crypto-expansion-1"),
    ("SOLUSDT", "Solana (SOL/USDT)", "Crypto", "crypto-expansion-1"),
)
MARKETS = frozenset(row[0] for row in CATALOG)
FORBIDDEN_FIELDS = frozenset({
    "recent_decisions", "shadow_signals", "signal_records", "signals",
    "entry", "stop", "tp1", "tp2", "direction", "rationale", "record_hash",
    "alerts", "provider_request_metadata", "hidden_reasoning",
})
FRESH_SECONDS = 90 * 60  # A stricter "fresh" threshold than public delayed at >=90m.


def snapshot_is_fresh(snapshot: dict[str, Any] | None, *, now: datetime | None = None) -> bool:
    if not isinstance(snapshot, dict):
        return False
    raw = snapshot.get("generated_at_utc")
    if not isinstance(raw, str):
        return False
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return False
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        age = (current - stamp.astimezone(timezone.utc)).total_seconds()
    except (ValueError, TypeError, OverflowError):
        return False
    return 0 <= age < FRESH_SECONDS


def _program(snapshot: dict[str, Any] | None, program_id: str) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {}
    programs = snapshot.get("validation_programs")
    if not isinstance(programs, list):
        return {}
    matching = [
        p for p in programs if isinstance(p, dict) and p.get("program_id") == program_id
    ]
    if len(matching) != 1:
        return {}
    return matching[0]


def _program_allowed(snapshot: dict[str, Any] | None, program_id: str) -> bool:
    p = _program(snapshot, program_id)
    health = p.get("health")
    return (
        p.get("mode") == "SHADOW_ONLY"
        and p.get("public_research_observability") is True
        and p.get("public_signal_exposure") is True
        and p.get("signal_details_included") is False
        and isinstance(health, dict)
        and health.get("broker_execution_disabled") is True
    )


def core_signal_available(
    snapshot: dict[str, Any] | None, *, now: datetime | None = None
) -> bool:
    if not snapshot_is_fresh(snapshot, now=now):
        return False
    assert isinstance(snapshot, dict)
    ai = snapshot.get("ai_v1")
    if not isinstance(ai, dict):
        return False
    health = ai.get("health")
    return (
        _program_allowed(snapshot, "core-ai-shadow")
        and ai.get("runtime_version") == "AI-v1.1"
        and ai.get("mode") == "SHADOW_ONLY"
        and ai.get("publish_allowed") is True
        and isinstance(health, dict)
        and health.get("healthy") is True
        and health.get("broker_execution_disabled") is True
    )


def market_directory(
    snapshot: dict[str, Any] | None, *, now: datetime | None = None
) -> dict[str, Any]:
    fresh = snapshot_is_fresh(snapshot, now=now)
    core_ready = core_signal_available(snapshot, now=now)
    rows = []
    for symbol, label, group, program in CATALOG:
        p = _program(snapshot, program)
        observed = (
            p.get("mode") == "SHADOW_ONLY"
            and p.get("public_research_observability") is True
            and (symbol in CORE or p.get("public_signal_exposure") is False)
        )
        # Status/availability cannot grant detail rights to restricted markets.
        detailed = symbol in CORE and core_ready
        rows.append({
            "symbol": symbol,
            "name": label,
            "group": group,
            "cataloged": True,
            "research_status": (
                "core_shadow_research" if detailed else
                "updates_delayed" if observed and not fresh else
                "research_validation" if observed and symbol not in CORE else
                "status_unavailable"
            ),
            "snapshot_fresh": fresh,
            "research_signal_detail_available": detailed,
            "current_signal_present": (
                any(s.get("current_signal_eligible") is True
                    for s in permitted_core_recent_signals(
                        snapshot, symbol, now=now,
                    )["signals"]) if detailed else False
            ),
            "commercial_customer_eligible": False,
            "research_only": True,
        })
    return {
        "schema_version": 1,
        "markets": rows,
        "snapshot_generated_at_utc": (
            snapshot.get("generated_at_utc") if isinstance(snapshot, dict) else None
        ),
        "commercial_customer_eligible": False,
    }


def permitted_core_recent_signals(
    snapshot: dict[str, Any] | None,
    symbol: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return only allowlisted already-public core fields; no reconstructed history."""
    if symbol not in CORE:
        raise PermissionError("Detailed research signals are not released for this market")
    if not core_signal_available(snapshot, now=now):
        return {"symbol": symbol, "research_only": True, "status": "unavailable", "signals": []}
    assert isinstance(snapshot, dict)
    ai = snapshot["ai_v1"]
    signals = ai.get("shadow_signals")
    if not isinstance(signals, list):
        return {"symbol": symbol, "research_only": True, "status": "unavailable", "signals": []}
    allowed = (
        "entity_id", "source_symbol", "status", "direction", "issued_at_utc",
        "entry_at_utc", "entry", "stop", "tp1", "tp2", "max_hold_h1_bars",
        "rationale", "supporting_factors", "risk_factors", "tp1_partial",
        "tp1_partial_net_r", "exit_at_utc", "exit_price", "exit_reason",
        "net_r", "record_hash", "exit_record_hash",
    )
    rows = []
    for signal in signals[:20]:
        if not isinstance(signal, dict) or signal.get("source_symbol") != symbol:
            continue
        if signal.get("status") not in ("active", "closed"):
            continue
        public = {key: signal.get(key) for key in allowed}
        # An "active" ledger row alone cannot prove a current/eligible setup.
        # Verify issuance time and declared H1 maximum hold; do not reinterpret
        # a stale/unknown lifetime as a current customer signal.
        public["current_signal_eligible"] = False
        if signal["status"] == "active":
            try:
                issued_raw = signal.get("issued_at_utc")
                hold = signal.get("max_hold_h1_bars")
                if not isinstance(issued_raw, str) or type(hold) is not int or not 1 <= hold <= 720:
                    raise ValueError("Missing bounded hold or issued time")
                issued = datetime.fromisoformat(issued_raw.replace("Z", "+00:00"))
                if issued.tzinfo is None:
                    raise ValueError("Naive signal issuance time")
                current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
                seconds = (current - issued.astimezone(timezone.utc)).total_seconds()
                if not 0 <= seconds < hold * 3600:
                    raise ValueError("Signal lifetime expired or future")
                public["current_signal_eligible"] = True
            except (TypeError, ValueError, OverflowError):
                public["status"] = "activity_unverified"
        rows.append(public)
    return {
        "symbol": symbol, "research_only": True, "status": "shadow_only",
        "snapshot_generated_at_utc": snapshot.get("generated_at_utc"),
        "signals": rows,
        "history_complete": False,
    }
