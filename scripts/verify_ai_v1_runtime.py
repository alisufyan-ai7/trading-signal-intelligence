from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.shadow_runtime import verify_active_runtime


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify active AI-v1 activation anchor, frozen artifacts and ledgers"
    )
    parser.add_argument(
        "--activation-only",
        action="store_true",
        help="Require each AI-v1 ledger to contain only its ACTIVATION record.",
    )
    args = parser.parse_args()

    result = verify_active_runtime(
        ROOT,
        require_activation_only=args.activation_only,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
