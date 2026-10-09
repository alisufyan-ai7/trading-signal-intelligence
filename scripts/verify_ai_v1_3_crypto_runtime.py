from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.crypto_runtime_verifier_v1_3 import (
    verify_active_runtime_v1_3,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify activated AI-v1.3 BTC/ETH/SOL parallel crypto runtime."
        )
    )
    parser.add_argument("--activation-only", action="store_true")
    parser.add_argument("--include-scheduler", action="store_true")
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    result = verify_active_runtime_v1_3(
        ROOT,
        require_activation_only=args.activation_only,
        include_scheduler=args.include_scheduler,
        verify_upstream=not args.skip_upstream,
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
