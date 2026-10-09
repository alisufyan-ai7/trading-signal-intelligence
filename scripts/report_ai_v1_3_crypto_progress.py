from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.crypto_observability_v1_3 import (
    build_report_v1_3,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only AI-v1.3 crypto C1/C2/C3 observability report."
    )
    parser.add_argument("--skip-scheduler", action="store_true")
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    report = build_report_v1_3(
        ROOT,
        include_scheduler=not args.skip_scheduler,
        verify_upstream=not args.skip_upstream,
    )
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
