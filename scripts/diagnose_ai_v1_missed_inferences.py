from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_signal_intelligence.ai_v1.missed_inference_diagnostic import (
    build_missed_inference_diagnostic,
    format_diagnostic_text,
)
from trading_signal_intelligence.ai_v1.observability import ObservabilityError


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only diagnosis of AI-v1 USTEC/US30 missed inference timing. "
            "No provider, MT5, broker or ledger mutation occurs."
        )
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    args = parser.parse_args()

    try:
        report = build_missed_inference_diagnostic(ROOT)
    except ObservabilityError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "diagnostic_version": (
                            "AI-v1-Index-Missed-Inference-Diagnostic-v0.1"
                        ),
                        "mode": "READ_ONLY",
                        "ok": False,
                        "error": type(exc).__name__,
                        "message": str(exc),
                    },
                    indent=2,
                )
            )
        else:
            print(f"Diagnostic failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(format_diagnostic_text(report))


if __name__ == "__main__":
    main()
