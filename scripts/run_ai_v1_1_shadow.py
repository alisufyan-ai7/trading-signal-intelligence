from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    preactivation_report_v1_1,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "AI-v1.1 shadow runner entry point. "
            "Pre-activation builds are intentionally fail-closed."
        )
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "Verify frozen lineage/version isolation only. "
            "Makes no MT5/OpenAI call and creates no ledger/anchor."
        ),
    )
    args = parser.parse_args()

    if not args.preflight_only:
        raise SystemExit(
            "AI-v1.1 live execution is not activated or authorized. "
            "Only --preflight-only is available at this stage."
        )

    report = preactivation_report_v1_1(ROOT)
    output = {
        **report,
        "runner_mode": "PRE_ACTIVATION_ONLY",
        "live_execution_available": False,
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_created": False,
        "activation_anchor_created": False,
        "scheduler_changed": False,
    }
    print(json.dumps(output, indent=2, allow_nan=False))
    if report["preactivation_check"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
