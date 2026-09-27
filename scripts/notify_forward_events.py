from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from trading_signal_intelligence.forward import ForwardLedger
from trading_signal_intelligence.product.catalog import launch_catalog


load_dotenv()

DEFAULT_TYPES = {"SIGNAL", "EXIT"}


def _load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return set(payload.get("seen_record_hashes", []))


def _save_state(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps({"seen_record_hashes": sorted(seen)}, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def _events(types: set[str]) -> list[dict[str, Any]]:
    rows = []
    for market in launch_catalog()["live_signal_markets"]:
        ledger = ForwardLedger(market["forward_database"])
        for record in ledger.records():
            if record["record_type"] not in types:
                continue
            rows.append(
                {
                    "market": market,
                    "record": record,
                }
            )
    return sorted(rows, key=lambda row: row["record"]["recorded_at_utc"])


def _message(event: dict[str, Any]) -> str:
    market = event["market"]
    record = event["record"]
    payload = record["payload"]
    symbol = market["canonical_symbol"]
    kind = record["record_type"]

    if kind == "SIGNAL":
        return (
            f"TradingTop SIGNAL\n"
            f"{symbol} • {payload.get('direction', '').upper()}\n"
            f"Entry: {payload.get('entry')}\n"
            f"Stop: {payload.get('stop')}\n"
            f"Target: {payload.get('target')}\n"
            f"Issued: {payload.get('signal_close_time_utc')}\n"
            f"Strategy: {payload.get('strategy')}\n"
            f"Research beta — not personalized investment advice."
        )

    if kind == "EXIT":
        net_r = payload.get("net_r")
        net_text = f"{float(net_r):+.3f}R" if net_r is not None else "n/a"
        return (
            f"TradingTop EXIT\n"
            f"{symbol} • {payload.get('direction', '').upper()}\n"
            f"Reason: {payload.get('exit_reason')}\n"
            f"Result: {net_text}\n"
            f"Exit: {payload.get('exit')}\n"
            f"Exit bar: {payload.get('exit_bar_timestamp_utc')}"
        )

    return (
        f"TradingTop {kind}\n"
        f"{symbol}\n"
        f"Reason: {payload.get('reason') or 'n/a'}\n"
        f"Effective: {record.get('effective_at_utc')}"
    )


def _send_telegram(token: str, chat_id: str, message: str) -> None:
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(f"Telegram send failed: {body}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send new immutable forward lifecycle events to Telegram"
    )
    parser.add_argument("--state", default="data/telegram_alert_state.json")
    parser.add_argument("--types", default="SIGNAL,EXIT")
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    wanted = {
        item.strip().upper()
        for item in args.types.split(",")
        if item.strip()
    }
    state_path = Path(args.state)
    seen = _load_state(state_path)
    events = _events(wanted)

    if args.initialize:
        seen.update(event["record"]["record_hash"] for event in events)
        _save_state(state_path, seen)
        print(
            json.dumps(
                {
                    "initialized": True,
                    "marked_seen": len(events),
                    "state": str(state_path),
                },
                indent=2,
            )
        )
        return

    token = os.getenv("TRADINGTOP_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TRADINGTOP_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(
            json.dumps(
                {
                    "alerts_enabled": False,
                    "reason": "TRADINGTOP_TELEGRAM_BOT_TOKEN / CHAT_ID not configured",
                    "new_events_waiting": sum(
                        event["record"]["record_hash"] not in seen
                        for event in events
                    ),
                },
                indent=2,
            )
        )
        return

    sent = []
    for event in events:
        record_hash = event["record"]["record_hash"]
        if record_hash in seen:
            continue
        message = _message(event)
        if args.dry_run:
            print(message)
            print("---")
            continue
        _send_telegram(token, chat_id, message)
        seen.add(record_hash)
        _save_state(state_path, seen)
        sent.append(record_hash)

    print(
        json.dumps(
            {
                "alerts_enabled": True,
                "sent": len(sent),
                "dry_run": args.dry_run,
                "state": str(state_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
