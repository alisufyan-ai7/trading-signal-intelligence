from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import trading_signal_intelligence.backtesting.s02 as s02_module
import trading_signal_intelligence.forward.ledger as ledger_module
from trading_signal_intelligence.backtesting.s02 import S02Config
from trading_signal_intelligence.forward import ForwardLedger, sha256_file, sha256_json, utc_now


STRATEGY = "S02-structure-breakout-v0.1"
DEFAULT_ENTITY = "S02-v0.1:XAUUSD:PRIMARY"


def main() -> None:
    parser = argparse.ArgumentParser(description="Activate the primary immutable S02/XAU forward test")
    parser.add_argument("--database", default="data/forward.sqlite")
    parser.add_argument("--source", default="exness_mt5_demo")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--canonical", default="XAU/USD")
    parser.add_argument("--entity", default=DEFAULT_ENTITY)
    parser.add_argument("--max-signal-age-minutes", type=int, default=5)
    args = parser.parse_args()

    ledger = ForwardLedger(args.database)
    if ledger.has(record_type="ACTIVATION", entity_id=args.entity):
        raise RuntimeError(
            f"Forward test {args.entity!r} is already activated in {args.database}. "
            "Do not overwrite or reactivate an existing forward ledger."
        )

    config = S02Config()
    config_payload = asdict(config)
    strategy_path = Path(s02_module.__file__).resolve()
    scanner_path = Path(__file__).resolve().with_name("scan_s02_forward.py")
    ledger_path = Path(ledger_module.__file__).resolve()
    activated_at = utc_now()

    config_hash = sha256_json(config_payload)
    strategy_hash = sha256_file(strategy_path)
    scanner_hash = sha256_file(scanner_path)
    ledger_hash = sha256_file(ledger_path)
    protocol_bundle_hash = sha256_json(
        {
            "config_sha256": config_hash,
            "strategy_code_sha256": strategy_hash,
            "scanner_code_sha256": scanner_hash,
            "ledger_code_sha256": ledger_hash,
            "max_signal_age_minutes": args.max_signal_age_minutes,
        }
    )

    payload = {
        "strategy": STRATEGY,
        "test_entity": args.entity,
        "source": args.source,
        "source_symbol": args.symbol,
        "canonical_symbol": args.canonical,
        "activated_at_utc": activated_at.isoformat(),
        "config": config_payload,
        "config_sha256": config_hash,
        "strategy_code_sha256": strategy_hash,
        "scanner_code_sha256": scanner_hash,
        "ledger_code_sha256": ledger_hash,
        "protocol_bundle_sha256": protocol_bundle_hash,
        "max_signal_age_minutes": args.max_signal_age_minutes,
        "anti_backfill_rule": (
            "candidate signals older than max_signal_age_minutes at discovery are logged "
            "as MISSED_SIGNAL, never SIGNAL"
        ),
    }

    record = ledger.append(
        record_type="ACTIVATION",
        entity_id=args.entity,
        effective_at_utc=activated_at,
        payload=payload,
        recorded_at_utc=activated_at,
    )

    output = {
        "database": str(Path(args.database)),
        "activation": record,
        "ledger_head_hash": ledger.head_hash(),
        "verification": ledger.verify(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
