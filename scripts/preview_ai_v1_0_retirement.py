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
    parser.add_argument(
        "--output",
        default=None,
        help="Optional UTF-8 JSON file path for the exact pre-disable preview.",
    )
    args = parser.parse_args()

    payload = build_v1_0_retirement_preview(
        ROOT,
        include_scheduler=not args.no_scheduler,
        verify_upstream=not args.skip_upstream,
    )
    encoded = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
