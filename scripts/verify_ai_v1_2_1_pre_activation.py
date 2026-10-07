from __future__ import annotations

import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.expansion_v1_2_1 import (
    preactivation_report_v1_2_1,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    report = preactivation_report_v1_2_1(ROOT)
    print(json.dumps(report, indent=2, allow_nan=False))
    if report["preactivation_check"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
