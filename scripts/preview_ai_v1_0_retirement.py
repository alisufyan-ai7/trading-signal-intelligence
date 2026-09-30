from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.retirement_v1_0 import (
    build_v1_0_retirement_preview,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview AI-v1.0 retirement metadata without mutating ledgers, "
            "scheduler state, or repository files."
        )
    )
    parser.add_argument("--no-scheduler", action="store_true")
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    payload = build_v1_0_retirement_preview(
        ROOT,
        include_scheduler=not args.no_scheduler,
        verify_upstream=not args.skip_upstream,
    )
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
