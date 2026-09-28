from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_signal_intelligence.ai_v1.observability import (
    ObservabilityError,
    build_report,
    format_text_report,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only SignalProof AI-v1 health and gate-progress monitor"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human-readable summary.",
    )
    parser.add_argument(
        "--no-scheduler",
        action="store_true",
        help="Skip the Windows Task Scheduler status probe.",
    )
    parser.add_argument(
        "--no-upstream-check",
        action="store_true",
        help="Skip the read-only Git upstream activation-anchor byte check.",
    )
    args = parser.parse_args()

    try:
        report = build_report(
            ROOT,
            include_scheduler=not args.no_scheduler,
            verify_upstream=not args.no_upstream_check,
        )
    except ObservabilityError as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "report_version": "AI-v1-Observability-v0.1",
                        "mode": "READ_ONLY",
                        "healthy": False,
                        "error": type(exc).__name__,
                        "message": str(exc),
                    },
                    indent=2,
                )
            )
        else:
            print(f"AI-v1 observability failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        print(format_text_report(report))

    if not report["health"]["healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
