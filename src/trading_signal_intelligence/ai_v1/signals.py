from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.models import Candle


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _finite(name: str, value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def append_signal_from_approved_inference(
    *,
    ledger: AILedger,
    entity_id: str,
    entry_bar: Candle,
    guardrails: dict[str, Any],
    recorded_at_utc: datetime | None = None,
) -> dict[str, Any]:
    if ledger.has(record_type="SIGNAL", entity_id=entity_id):
        raise RuntimeError(f"signal already exists for {entity_id}")

    inference_rows = ledger.records(record_type="INFERENCE", entity_id=entity_id)
    if len(inference_rows) != 1:
        raise RuntimeError(
            f"expected exactly one INFERENCE for {entity_id}; found {len(inference_rows)}"
        )
    inference = inference_rows[0]
    payload = inference["payload"]
    if not bool(payload.get("guard_publishable")):
        raise RuntimeError("inference was not approved by the publication guard")

    decision = payload["normalized_decision"]
    if decision["decision"] not in {"BUY", "SELL"}:
        raise RuntimeError("only directional approved inference can become a SIGNAL")

    feature = payload["feature_snapshot"]
    expected_entry = datetime.fromisoformat(
        str(feature["source_bar_close_utc"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    actual_entry = _utc(entry_bar.timestamp_utc)
    if actual_entry != expected_entry:
        raise RuntimeError(
            f"entry bar timestamp {actual_entry.isoformat()} does not match "
            f"required next-H1 open {expected_entry.isoformat()}"
        )

    entry = _finite("entry", entry_bar.open)
    atr = _finite("atr_14", feature["atr_14"])
    spread_price = _finite("spread_price", feature["spread_price"])
    stop_atr = _finite("stop_atr", decision["stop_atr"])
    tp1_r = _finite("tp1_r", decision["tp1_r"])
    tp2_r = _finite("tp2_r", decision["tp2_r"])
    risk_price = stop_atr * atr
    if risk_price <= 0:
        raise RuntimeError("risk_price must be positive")

    direction = decision["decision"]
    if direction == "BUY":
        stop = entry - risk_price
        tp1 = entry + tp1_r * risk_price
        tp2 = entry + tp2_r * risk_price
    else:
        stop = entry + risk_price
        tp1 = entry - tp1_r * risk_price
        tp2 = entry - tp2_r * risk_price

    cost_price = float(guardrails["cost_multiplier"]) * spread_price

    signal_payload = {
        "protocol_version": "AI-v1.0",
        "source_symbol": feature["source_symbol"],
        "canonical_symbol": feature["canonical_symbol"],
        "direction": direction,
        "source_bar_close_utc": feature["source_bar_close_utc"],
        "entry_policy": guardrails["entry_policy"],
        "entry_timestamp_utc": actual_entry.isoformat(),
        "entry": entry,
        "atr_14": atr,
        "stop_atr": stop_atr,
        "risk_price": risk_price,
        "stop": stop,
        "tp1_r": tp1_r,
        "tp1": tp1,
        "tp2_r": tp2_r,
        "tp2": tp2,
        "max_hold_h1_bars": int(guardrails["max_hold_h1_bars"]),
        "tp1_position_fraction": float(guardrails["tp1_position_fraction"]),
        "tp2_position_fraction": float(guardrails["tp2_position_fraction"]),
        "move_stop_after_tp1": bool(guardrails["move_stop_after_tp1"]),
        "spread_price": spread_price,
        "cost_multiplier": float(guardrails["cost_multiplier"]),
        "total_cost_price": cost_price,
        "raw_confidence": decision["raw_confidence"],
        "regime": decision["regime"],
        "feature_snapshot_sha256": payload["feature_snapshot_sha256"],
        "originating_inference_record_hash": inference["record_hash"],
        "broker_execution_enabled": False,
    }
    return ledger.append(
        record_type="SIGNAL",
        entity_id=entity_id,
        effective_at_utc=actual_entry,
        recorded_at_utc=recorded_at_utc or datetime.now(timezone.utc),
        payload=signal_payload,
    )


def _exit_contribution(
    *,
    direction: str,
    entry: float,
    exit_price: float,
    risk_price: float,
    fraction: float,
    total_cost_price: float,
) -> tuple[float, float, float]:
    sign = 1.0 if direction == "BUY" else -1.0
    raw_r = sign * (exit_price - entry) / risk_price
    gross_contribution_r = fraction * raw_r
    cost_contribution_r = fraction * total_cost_price / risk_price
    net_contribution_r = gross_contribution_r - cost_contribution_r
    return gross_contribution_r, cost_contribution_r, net_contribution_r


def _append_partial(
    *,
    ledger: AILedger,
    signal: dict[str, Any],
    candle: Candle,
    recorded_at_utc: datetime,
) -> dict[str, Any]:
    p = signal["payload"]
    gross_r, cost_r, net_r = _exit_contribution(
        direction=p["direction"],
        entry=float(p["entry"]),
        exit_price=float(p["tp1"]),
        risk_price=float(p["risk_price"]),
        fraction=float(p["tp1_position_fraction"]),
        total_cost_price=float(p["total_cost_price"]),
    )
    return ledger.append(
        record_type="PARTIAL_EXIT",
        entity_id=signal["entity_id"],
        effective_at_utc=_utc(candle.timestamp_utc),
        recorded_at_utc=recorded_at_utc,
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": p["source_symbol"],
            "direction": p["direction"],
            "exit_bar_timestamp_utc": _utc(candle.timestamp_utc).isoformat(),
            "exit_price": float(p["tp1"]),
            "fraction": float(p["tp1_position_fraction"]),
            "trigger_reason": "TP1",
            "gross_contribution_r": gross_r,
            "cost_contribution_r": cost_r,
            "net_contribution_r": net_r,
            "signal_record_hash": signal["record_hash"],
        },
    )


def _append_exit(
    *,
    ledger: AILedger,
    signal: dict[str, Any],
    candle: Candle,
    exit_price: float,
    reason: str,
    fraction: float,
    partial: dict[str, Any] | None,
    bars_held: int,
    recorded_at_utc: datetime,
) -> dict[str, Any]:
    p = signal["payload"]
    gross_r, cost_r, net_r = _exit_contribution(
        direction=p["direction"],
        entry=float(p["entry"]),
        exit_price=exit_price,
        risk_price=float(p["risk_price"]),
        fraction=fraction,
        total_cost_price=float(p["total_cost_price"]),
    )
    partial_net = (
        float(partial["payload"]["net_contribution_r"]) if partial is not None else 0.0
    )
    combined = partial_net + net_r
    return ledger.append(
        record_type="EXIT",
        entity_id=signal["entity_id"],
        effective_at_utc=_utc(candle.timestamp_utc),
        recorded_at_utc=recorded_at_utc,
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": p["source_symbol"],
            "direction": p["direction"],
            "exit_bar_timestamp_utc": _utc(candle.timestamp_utc).isoformat(),
            "exit_price": exit_price,
            "remaining_fraction": fraction,
            "reason": reason,
            "bars_held": bars_held,
            "gross_contribution_r": gross_r,
            "cost_contribution_r": cost_r,
            "net_contribution_r": net_r,
            "total_combined_signal_net_r": combined,
            "partial_exit_record_hash": (
                partial["record_hash"] if partial is not None else None
            ),
            "signal_record_hash": signal["record_hash"],
        },
    )


def evaluate_signal(
    *,
    ledger: AILedger,
    entity_id: str,
    closed_h1: list[Candle],
    recorded_at_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    if ledger.has(record_type="EXIT", entity_id=entity_id):
        return []

    signal_rows = ledger.records(record_type="SIGNAL", entity_id=entity_id)
    if len(signal_rows) != 1:
        raise RuntimeError(
            f"expected exactly one SIGNAL for {entity_id}; found {len(signal_rows)}"
        )
    signal = signal_rows[0]
    p = signal["payload"]

    entry_ts = pd.Timestamp(p["entry_timestamp_utc"])
    eligible = sorted(
        [
            candle
            for candle in closed_h1
            if candle.is_closed and pd.Timestamp(candle.timestamp_utc) >= entry_ts
        ],
        key=lambda candle: candle.timestamp_utc,
    )
    max_hold = int(p["max_hold_h1_bars"])
    eligible = eligible[:max_hold]
    if not eligible:
        return []

    partial_rows = ledger.records(record_type="PARTIAL_EXIT", entity_id=entity_id)
    if len(partial_rows) > 1:
        raise RuntimeError("more than one PARTIAL_EXIT exists")
    partial = partial_rows[0] if partial_rows else None

    start_after: pd.Timestamp | None = None
    if partial is not None:
        start_after = pd.Timestamp(partial["effective_at_utc"])

    now = recorded_at_utc or datetime.now(timezone.utc)
    actions: list[dict[str, Any]] = []
    direction = str(p["direction"])
    entry = float(p["entry"])
    stop = float(p["stop"])
    tp1 = float(p["tp1"])
    tp2 = float(p["tp2"])

    for absolute_index, candle in enumerate(eligible, start=1):
        ts = pd.Timestamp(candle.timestamp_utc)
        if start_after is not None and ts <= start_after:
            continue

        bar_open = float(candle.open)
        bar_high = float(candle.high)
        bar_low = float(candle.low)
        has_partial = partial is not None

        if direction == "BUY":
            gap_stop = bar_open <= stop
            gap_tp2 = bar_open >= tp2
            gap_tp1 = bar_open >= tp1
            stop_hit = bar_low <= stop
            tp1_hit = bar_high >= tp1
            tp2_hit = bar_high >= tp2
        else:
            gap_stop = bar_open >= stop
            gap_tp2 = bar_open <= tp2
            gap_tp1 = bar_open <= tp1
            stop_hit = bar_high >= stop
            tp1_hit = bar_low <= tp1
            tp2_hit = bar_low <= tp2

        if has_partial:
            if gap_stop:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=bar_open,
                        reason="GAP_STOP",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if gap_tp2:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=tp2,
                        reason="TP2",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if stop_hit and tp2_hit:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=stop,
                        reason="SAME_BAR_STOP_FIRST",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if stop_hit:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=stop,
                        reason="STOP",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if tp2_hit:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=tp2,
                        reason="TP2",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
        else:
            if gap_stop:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=bar_open,
                        reason="GAP_STOP",
                        fraction=1.0,
                        partial=None,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break

            if gap_tp2:
                partial = _append_partial(
                    ledger=ledger,
                    signal=signal,
                    candle=candle,
                    recorded_at_utc=now,
                )
                actions.append(partial)
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=tp2,
                        reason="TP2",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break

            if gap_tp1:
                partial = _append_partial(
                    ledger=ledger,
                    signal=signal,
                    candle=candle,
                    recorded_at_utc=now,
                )
                actions.append(partial)
                if stop_hit and tp2_hit:
                    actions.append(
                        _append_exit(
                            ledger=ledger,
                            signal=signal,
                            candle=candle,
                            exit_price=stop,
                            reason="SAME_BAR_STOP_FIRST",
                            fraction=float(p["tp2_position_fraction"]),
                            partial=partial,
                            bars_held=absolute_index,
                            recorded_at_utc=now,
                        )
                    )
                    break
                if stop_hit:
                    actions.append(
                        _append_exit(
                            ledger=ledger,
                            signal=signal,
                            candle=candle,
                            exit_price=stop,
                            reason="STOP",
                            fraction=float(p["tp2_position_fraction"]),
                            partial=partial,
                            bars_held=absolute_index,
                            recorded_at_utc=now,
                        )
                    )
                    break
                if tp2_hit:
                    actions.append(
                        _append_exit(
                            ledger=ledger,
                            signal=signal,
                            candle=candle,
                            exit_price=tp2,
                            reason="TP2",
                            fraction=float(p["tp2_position_fraction"]),
                            partial=partial,
                            bars_held=absolute_index,
                            recorded_at_utc=now,
                        )
                    )
                    break
                if absolute_index == max_hold:
                    actions.append(
                        _append_exit(
                            ledger=ledger,
                            signal=signal,
                            candle=candle,
                            exit_price=float(candle.close),
                            reason="TIMEOUT",
                            fraction=float(p["tp2_position_fraction"]),
                            partial=partial,
                            bars_held=absolute_index,
                            recorded_at_utc=now,
                        )
                    )
                    break
                continue

            if stop_hit and (tp1_hit or tp2_hit):
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=stop,
                        reason="SAME_BAR_STOP_FIRST",
                        fraction=1.0,
                        partial=None,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if stop_hit:
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=stop,
                        reason="STOP",
                        fraction=1.0,
                        partial=None,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if tp2_hit:
                partial = _append_partial(
                    ledger=ledger,
                    signal=signal,
                    candle=candle,
                    recorded_at_utc=now,
                )
                actions.append(partial)
                actions.append(
                    _append_exit(
                        ledger=ledger,
                        signal=signal,
                        candle=candle,
                        exit_price=tp2,
                        reason="TP2",
                        fraction=float(p["tp2_position_fraction"]),
                        partial=partial,
                        bars_held=absolute_index,
                        recorded_at_utc=now,
                    )
                )
                break
            if tp1_hit:
                partial = _append_partial(
                    ledger=ledger,
                    signal=signal,
                    candle=candle,
                    recorded_at_utc=now,
                )
                actions.append(partial)
                if absolute_index == max_hold:
                    actions.append(
                        _append_exit(
                            ledger=ledger,
                            signal=signal,
                            candle=candle,
                            exit_price=float(candle.close),
                            reason="TIMEOUT",
                            fraction=float(p["tp2_position_fraction"]),
                            partial=partial,
                            bars_held=absolute_index,
                            recorded_at_utc=now,
                        )
                    )
                    break
                continue

        if absolute_index == max_hold:
            fraction = (
                float(p["tp2_position_fraction"]) if partial is not None else 1.0
            )
            actions.append(
                _append_exit(
                    ledger=ledger,
                    signal=signal,
                    candle=candle,
                    exit_price=float(candle.close),
                    reason="TIMEOUT",
                    fraction=fraction,
                    partial=partial,
                    bars_held=absolute_index,
                    recorded_at_utc=now,
                )
            )
            break

    return actions
