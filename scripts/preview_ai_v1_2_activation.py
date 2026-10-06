from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_2 import (
    build_activation_anchor_preview_v1_2,
    preactivation_report_v1_2,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = preactivation_report_v1_2(ROOT)
    if report["preactivation_check"] != "PASS":
        print(json.dumps({"preactivation": report}, indent=2, allow_nan=False))
        raise SystemExit(2)

    preview = build_activation_anchor_preview_v1_2(
        repo_root=ROOT,
        activated_at_utc=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "preactivation": report,
                "activation_preview": preview,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
