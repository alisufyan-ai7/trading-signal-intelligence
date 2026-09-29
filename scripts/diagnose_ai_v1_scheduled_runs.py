from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.scheduled_run_forensic import (
    build_forensic_report,
    format_report,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only forensic analysis of AI-v1 scheduled-run log vs missed index cycles"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_forensic_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(format_report(report))


if __name__ == "__main__":
    main()
