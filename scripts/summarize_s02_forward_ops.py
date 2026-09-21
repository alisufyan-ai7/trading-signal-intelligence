from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


SCAN_RE = re.compile(r'"scanned_at_utc"\s*:\s*"([^"]+)"')
ACTION_RE = re.compile(r'"action"\s*:\s*"([A-Z_]+)"')
VALID_FALSE_RE = re.compile(r'"valid"\s*:\s*false')
RECORDS_RE = re.compile(r'"records"\s*:\s*(\d+)')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize S02 forward-task operational logs without modifying the forward ledger"
    )
    parser.add_argument(
        "logs",
        nargs="*",
        default=["data/forward-task-logs/s02_xau_forward.log"],
        help="One or more task log paths",
    )
    args = parser.parse_args()

    scan_times: list[datetime] = []
    action_counts: Counter[str] = Counter()
    valid_false_mentions = 0
    records_seen: list[int] = []
    files: list[str] = []

    for raw_path in args.logs:
        path = Path(raw_path)
        if not path.exists():
            continue
        files.append(str(path))
        text = path.read_text(encoding="utf-8", errors="replace")
        scan_times.extend(datetime.fromisoformat(value) for value in SCAN_RE.findall(text))
        action_counts.update(ACTION_RE.findall(text))
        valid_false_mentions += len(VALID_FALSE_RE.findall(text))
        records_seen.extend(int(value) for value in RECORDS_RE.findall(text))

    scan_times.sort()
    gaps_hours = [
        (later - earlier).total_seconds() / 3600.0
        for earlier, later in zip(scan_times, scan_times[1:])
    ]

    payload = {
        "files": files,
        "scan_runs": len(scan_times),
        "first_scan_utc": scan_times[0].isoformat() if scan_times else None,
        "last_scan_utc": scan_times[-1].isoformat() if scan_times else None,
        "action_counts": dict(sorted(action_counts.items())),
        "scans_with_no_action": len(scan_times) - sum(action_counts.values()),
        "verification_false_mentions": valid_false_mentions,
        "max_gap_hours": max(gaps_hours) if gaps_hours else None,
        "gaps_over_1_5_hours": sum(gap > 1.5 for gap in gaps_hours),
        "record_count_min_seen": min(records_seen) if records_seen else None,
        "record_count_max_seen": max(records_seen) if records_seen else None,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
