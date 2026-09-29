from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.historical_tick_boundary import (
    build_historical_tick_boundary_report,
    format_report,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only MT5 historical tick timing diagnostic for "
            "AI-v1 index valid/missed H1 boundaries."
        )
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_historical_tick_boundary_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(format_report(report))


if __name__ == "__main__":
    main()
