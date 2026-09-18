from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

import trading_signal_intelligence.backtesting.s02 as s02_module
from trading_signal_intelligence.backtesting.s02 import (
    S02Config,
    _candles_to_frame,
    _prepare_features,
)
from trading_signal_intelligence.connectors.mt5 import MT5Connector
from trading_signal_intelligence.forward import ForwardLedger, sha256_file, sha256_json, utc_now


STRATEGY = "S02-structure-breakout-v0.1"
DEFAULT_ENTITY = "S02-v0.1:XAUUSD:PRIMARY"


def _point_size(canonical: str, source: str, registry: str) -> float:
    payload = json.loads(Path(registry).read_text(encoding="utf-8"))
    for instrument in payload["instruments"]:
        if instrument["canonical"] != canonical:
            continue
        cfg = instrument.get("sources", {}).get(source)
        if cfg and cfg.get("digits") is not None:
            return 10.0 ** (-int(cfg["digits"]))
    raise ValueError(f"No point-size registry entry for {canonical} on {source}")


def _finite(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Expected finite numeric value, got {value!r}")
    return result


def _active_signal(ledger: ForwardLedger) -> dict[str, Any] | None:
    unresolved = ledger.unresolved_signal_entities()
    if not unresolved:
        return None
    if len(unresolved) > 1:
        raise RuntimeError(f"More than one unresolved forward signal: {unresolved}")
    rows = ledger.records(record_type="SIGNAL", entity_id=unresolved[0])
    return rows[-1] if rows else None


def _resolve_active_signal(
    *,
    ledger: ForwardLedger,
    signal_record: dict[str, Any],
    closed_h1,
    now: datetime,
) -> dict[str, Any] | None:
    payload = signal_record["payload"]
    entry_ts = pd.Timestamp(payload["entry_timestamp_utc"])
    direction = 1 if payload["direction"] == "long" else -1
    entry = float(payload["entry"])
    stop = float(payload["stop"])
    target = float(payload["target"])
    risk = float(payload["risk_price"])
    cost_price = float(payload["cost_price"])
    max_hold = int(payload["max_hold_bars"])

    eligible = [
        candle
        for candle in closed_h1
        if pd.Timestamp(candle.timestamp_utc) >= entry_ts
    ]
    eligible.sort(key=lambda c: c.timestamp_utc)

    exit_price = None
    exit_reason = None
    exit_bar = None
    bars_held = None

    for index, candle in enumerate(eligible[:max_hold], start=1):
        bar_open = float(candle.open)
        bar_high = float(candle.high)
        bar_low = float(candle.low)

        if direction > 0:
            if bar_open <= stop:
                exit_price, exit_reason = bar_open, "gap_stop"
            elif bar_open >= target:
                exit_price, exit_reason = target, "gap_target"
            else:
                stop_hit = bar_low <= stop
                target_hit = bar_high >= target
                if stop_hit and target_hit:
                    exit_price, exit_reason = stop, "same_bar_stop_first"
                elif stop_hit:
                    exit_price, exit_reason = stop, "stop"
                elif target_hit:
                    exit_price, exit_reason = target, "target"
        else:
            if bar_open >= stop:
                exit_price, exit_reason = bar_open, "gap_stop"
            elif bar_open <= target:
                exit_price, exit_reason = target, "gap_target"
            else:
                stop_hit = bar_high >= stop
                target_hit = bar_low <= target
                if stop_hit and target_hit:
                    exit_price, exit_reason = stop, "same_bar_stop_first"
                elif stop_hit:
                    exit_price, exit_reason = stop, "stop"
                elif target_hit:
                    exit_price, exit_reason = target, "target"

        if exit_price is not None:
            exit_bar = candle
            bars_held = index
            break

        if index == max_hold:
            exit_price = float(candle.close)
            exit_reason = "time_stop"
            exit_bar = candle
            bars_held = index
            break

    if exit_price is None or exit_bar is None:
        return None

    gross_pnl = direction * (float(exit_price) - entry)
    gross_r = gross_pnl / risk
    net_r = (gross_pnl - cost_price) / risk
    exit_payload = {
        "strategy": STRATEGY,
        "test_entity": payload["test_entity"],
        "signal_entity": signal_record["entity_id"],
        "direction": payload["direction"],
        "entry": entry,
        "stop": stop,
        "target": target,
        "exit": float(exit_price),
        "exit_reason": exit_reason,
        "bars_held": int(bars_held),
        "gross_r": gross_r,
        "net_r": net_r,
        "cost_price": cost_price,
        "exit_bar_timestamp_utc": exit_bar.timestamp_utc.isoformat(),
        "evaluated_at_utc": now.isoformat(),
    }
    return ledger.append(
        record_type="EXIT",
        entity_id=signal_record["entity_id"],
        effective_at_utc=exit_bar.timestamp_utc,
        payload=exit_payload,
        recorded_at_utc=now,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan MT5 and append fresh S02/XAU forward records")
    parser.add_argument("--database", default="data/forward.sqlite")
    parser.add_argument("--registry", default="config/instruments.json")
    parser.add_argument("--entity", default=DEFAULT_ENTITY)
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument("--h1-bars", type=int, default=500)
    parser.add_argument("--h4-bars", type=int, default=150)
    args = parser.parse_args()

    ledger = ForwardLedger(args.database)
    activations = ledger.records(record_type="ACTIVATION", entity_id=args.entity)
    if len(activations) != 1:
        raise RuntimeError(
            f"Expected exactly one activation for {args.entity!r}; found {len(activations)}"
        )
    activation = activations[0]["payload"]

    config = S02Config()
    current_config_hash = sha256_json(asdict(config))
    strategy_path = Path(s02_module.__file__).resolve()
    current_code_hash = sha256_file(strategy_path)
    if current_config_hash != activation["config_sha256"]:
        raise RuntimeError("Frozen S02 config hash no longer matches forward activation")
    if current_code_hash != activation["strategy_code_sha256"]:
        raise RuntimeError("S02 strategy source hash no longer matches forward activation")

    source = activation["source"]
    source_symbol = activation["source_symbol"]
    canonical = activation["canonical_symbol"]
    max_age_minutes = int(activation["max_signal_age_minutes"])
    activated_at = pd.Timestamp(activation["activated_at_utc"])
    point_size = _point_size(canonical, source, args.registry)

    connector = MT5Connector(source_name=source)
    connector.connect(args.terminal_path)
    try:
        h1_all = connector.bars_from_pos(
            source_symbol, canonical, "H1", 0, args.h1_bars, current_bar_is_closed=False
        )
        h4_all = connector.bars_from_pos(
            source_symbol, canonical, "H4", 0, args.h4_bars, current_bar_is_closed=False
        )
        quote = connector.latest_quote(source_symbol, canonical)
    finally:
        connector.disconnect()

    now = utc_now()
    closed_h1 = [bar for bar in h1_all if bar.is_closed]
    closed_h4 = [bar for bar in h4_all if bar.is_closed]
    current_h1 = next((bar for bar in reversed(h1_all) if not bar.is_closed), None)
    if not closed_h1 or not closed_h4 or current_h1 is None:
        raise RuntimeError("Need closed H1/H4 history plus the current H1 bar")

    actions: list[dict[str, Any]] = []

    active = _active_signal(ledger)
    if active is not None:
        exit_record = _resolve_active_signal(
            ledger=ledger,
            signal_record=active,
            closed_h1=closed_h1,
            now=now,
        )
        if exit_record is not None:
            actions.append({"action": "EXIT", "record": exit_record})
            active = None

    frame = _prepare_features(
        _candles_to_frame(closed_h1),
        _candles_to_frame(closed_h4),
        config,
    )
    candidates = frame[
        (frame["long_signal"].astype(bool) | frame["short_signal"].astype(bool))
        & (pd.to_datetime(frame["signal_close_time"], utc=True) > activated_at)
        & (pd.to_datetime(frame["signal_close_time"], utc=True) <= pd.Timestamp(now))
    ].copy()

    for _, row in candidates.iterrows():
        signal_start = pd.Timestamp(row["timestamp_utc"])
        signal_close = pd.Timestamp(row["signal_close_time"])
        signal_id = f"{args.entity}:{signal_start.isoformat()}"

        if (
            ledger.has(record_type="SIGNAL", entity_id=signal_id)
            or ledger.has(record_type="MISSED_SIGNAL", entity_id=signal_id)
            or ledger.has(record_type="SKIPPED_SIGNAL", entity_id=signal_id)
        ):
            continue

        age_minutes = (pd.Timestamp(now) - signal_close).total_seconds() / 60.0
        direction = "long" if bool(row["long_signal"]) else "short"

        if age_minutes > max_age_minutes:
            missed = ledger.append(
                record_type="MISSED_SIGNAL",
                entity_id=signal_id,
                effective_at_utc=signal_close.to_pydatetime(),
                payload={
                    "strategy": STRATEGY,
                    "test_entity": args.entity,
                    "source_symbol": source_symbol,
                    "canonical_symbol": canonical,
                    "direction": direction,
                    "signal_bar_timestamp_utc": signal_start.isoformat(),
                    "signal_close_time_utc": signal_close.isoformat(),
                    "discovered_age_minutes": age_minutes,
                    "max_signal_age_minutes": max_age_minutes,
                    "reason": "stale_at_discovery_no_backfill",
                },
                recorded_at_utc=now,
            )
            actions.append({"action": "MISSED_SIGNAL", "record": missed})
            continue

        if active is not None:
            skipped = ledger.append(
                record_type="SKIPPED_SIGNAL",
                entity_id=signal_id,
                effective_at_utc=signal_close.to_pydatetime(),
                payload={
                    "strategy": STRATEGY,
                    "test_entity": args.entity,
                    "direction": direction,
                    "signal_bar_timestamp_utc": signal_start.isoformat(),
                    "signal_close_time_utc": signal_close.isoformat(),
                    "reason": "existing_forward_position_open",
                    "active_signal_entity": active["entity_id"],
                },
                recorded_at_utc=now,
            )
            actions.append({"action": "SKIPPED_SIGNAL", "record": skipped})
            continue

        entry_ts = pd.Timestamp(current_h1.timestamp_utc)
        if entry_ts != signal_close:
            missed = ledger.append(
                record_type="MISSED_SIGNAL",
                entity_id=signal_id,
                effective_at_utc=signal_close.to_pydatetime(),
                payload={
                    "strategy": STRATEGY,
                    "test_entity": args.entity,
                    "direction": direction,
                    "signal_bar_timestamp_utc": signal_start.isoformat(),
                    "signal_close_time_utc": signal_close.isoformat(),
                    "current_h1_timestamp_utc": entry_ts.isoformat(),
                    "reason": "next_h1_open_not_current_when_discovered",
                },
                recorded_at_utc=now,
            )
            actions.append({"action": "MISSED_SIGNAL", "record": missed})
            continue

        atr = _finite(row["atr14"])
        spread_points = _finite(row["known_spread_points"])
        entry = float(current_h1.open)
        risk = config.stop_atr * atr
        if direction == "long":
            stop = entry - risk
            target = entry + config.target_r * risk
            structure_level = _finite(row["upper_structure"])
            breakout_distance_atr = _finite(row["long_breakout_distance_atr"])
        else:
            stop = entry + risk
            target = entry - config.target_r * risk
            structure_level = _finite(row["lower_structure"])
            breakout_distance_atr = _finite(row["short_breakout_distance_atr"])

        cost_price = config.cost_multiplier * spread_points * point_size
        signal_payload = {
            "strategy": STRATEGY,
            "test_entity": args.entity,
            "source": source,
            "source_symbol": source_symbol,
            "canonical_symbol": canonical,
            "direction": direction,
            "signal_bar_timestamp_utc": signal_start.isoformat(),
            "signal_close_time_utc": signal_close.isoformat(),
            "recorded_lag_seconds": (pd.Timestamp(now) - signal_close).total_seconds(),
            "entry_timestamp_utc": entry_ts.isoformat(),
            "entry_observed_from_mt5_current_h1_open": True,
            "entry": entry,
            "stop": stop,
            "target": target,
            "atr14": atr,
            "risk_price": risk,
            "structure_level": structure_level,
            "breakout_distance_atr": breakout_distance_atr,
            "tr_expansion_ratio": _finite(row["tr_expansion_ratio"]),
            "volume_expansion_ratio": _finite(row["volume_expansion_ratio"]),
            "spread_points": spread_points,
            "point_size": point_size,
            "cost_multiplier": config.cost_multiplier,
            "cost_price": cost_price,
            "max_hold_bars": config.max_hold_bars,
            "config_sha256": current_config_hash,
            "strategy_code_sha256": current_code_hash,
            "quote_timestamp_utc": quote.timestamp_utc.isoformat(),
        }
        signal_record = ledger.append(
            record_type="SIGNAL",
            entity_id=signal_id,
            effective_at_utc=signal_close.to_pydatetime(),
            payload=signal_payload,
            recorded_at_utc=now,
        )
        actions.append({"action": "SIGNAL", "record": signal_record})
        active = signal_record

    output = {
        "scanned_at_utc": now.isoformat(),
        "test_entity": args.entity,
        "actions": actions,
        "counts_by_type": ledger.counts_by_type(),
        "verification": ledger.verify(),
        "ledger_head_hash": ledger.head_hash(),
    }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
