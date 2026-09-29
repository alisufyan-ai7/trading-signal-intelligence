from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.rates_cache_correlation import (
    build_rates_cache_access_correlation,
    format_report,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only correlation of AI-v1 index valid/missed cycles with "
            "known pre-AI MT5 rates accesses."
        )
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_rates_cache_access_correlation(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(format_report(report))


if __name__ == "__main__":
    main()
