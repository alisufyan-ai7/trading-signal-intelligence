from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    build_activation_anchor_preview_v1_1,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Preview the exact prospective AI-v1.1 activation material. "
            "Creates no ledgers, anchor, provider call, MT5 call, or scheduler change."
        )
    )
    parser.add_argument(
        "--activated-at-utc",
        default=None,
        help=(
            "Optional ISO-8601 activation timestamp for preview only. "
            "Default: current UTC time."
        ),
    )
    args = parser.parse_args()

    activated = (
        datetime.fromisoformat(args.activated_at_utc.replace("Z", "+00:00"))
        if args.activated_at_utc
        else datetime.now(timezone.utc)
    )
    if activated.tzinfo is None:
        raise SystemExit("--activated-at-utc must be timezone-aware")

    payload = build_activation_anchor_preview_v1_1(
        repo_root=ROOT,
        activated_at_utc=activated,
    )
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
