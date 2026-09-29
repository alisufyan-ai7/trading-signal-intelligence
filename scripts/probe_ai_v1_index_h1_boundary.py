from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.mt5_boundary_probe import (
    capture_boundary,
    next_hour_boundary,
)


ROOT = Path(__file__).resolve().parents[1]


def _parse_boundary(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("boundary must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prospective read-only raw-MT5 H1 boundary probe for "
            "XAUUSD/USTEC/US30. No AI or ledger mutation."
        )
    )
    parser.add_argument(
        "--boundary-utc",
        type=_parse_boundary,
        default=None,
        help=(
            "UTC H1 boundary in ISO-8601 form. "
            "Default: next whole UTC hour."
        ),
    )
    parser.add_argument("--pre-seconds", type=int, default=60)
    parser.add_argument("--post-seconds", type=int, default=330)
    parser.add_argument("--interval-seconds", type=float, default=10.0)
    parser.add_argument(
        "--output-dir",
        default="data/diagnostics",
    )
    args = parser.parse_args()

    if args.pre_seconds < 0 or args.post_seconds < 1:
        raise SystemExit("pre/post seconds must be non-negative/positive")
    if not 2.0 <= args.interval_seconds <= 60.0:
        raise SystemExit("interval-seconds must be between 2 and 60")

    now = datetime.now(timezone.utc)
    boundary = args.boundary_utc or next_hour_boundary(now)
    if boundary <= now and now > boundary.replace(microsecond=0):
        raise SystemExit("boundary-utc must be in the future when starting the probe")

    stamp = boundary.strftime("%Y%m%dT%H%M%SZ")
    output_dir = ROOT / args.output_dir
    output_jsonl = output_dir / f"ai_v1_index_h1_boundary_probe_{stamp}.jsonl"
    summary_path = output_dir / f"ai_v1_index_h1_boundary_probe_{stamp}_summary.json"

    print(
        json.dumps(
            {
                "probe": "AI-v1-Index-H1-Boundary-Probe-v0.1",
                "mode": "READ_ONLY",
                "boundary_utc": boundary.isoformat(),
                "capture_start_utc": (
                    boundary.timestamp() - args.pre_seconds
                ),
                "pre_seconds": args.pre_seconds,
                "post_seconds": args.post_seconds,
                "interval_seconds": args.interval_seconds,
                "symbols": ["XAUUSD", "USTEC", "US30"],
                "output_jsonl": str(output_jsonl.relative_to(ROOT)),
                "summary_json": str(summary_path.relative_to(ROOT)),
                "provider_call_made": False,
                "ledger_write_made": False,
                "broker_order_made": False,
                "symbol_selection_made": False,
            },
            indent=2,
        )
    )

    report = capture_boundary(
        boundary_utc=boundary,
        pre_seconds=args.pre_seconds,
        post_seconds=args.post_seconds,
        interval_seconds=args.interval_seconds,
        output_jsonl=output_jsonl,
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
