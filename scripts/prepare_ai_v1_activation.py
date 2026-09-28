from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation import (
    MARKETS,
    artifact_hashes,
    build_activation_payload,
    git_commit_sha,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare and inspect AI-v1 activation fingerprints without activating"
    )
    parser.add_argument(
        "--market",
        action="append",
        choices=MARKETS,
        help="Market to preview; may be repeated. Defaults to all three.",
    )
    args = parser.parse_args()

    markets = tuple(args.market or MARKETS)
    preview_time = datetime.now(timezone.utc)
    payloads = {
        market: build_activation_payload(
            repo_root=ROOT,
            market=market,
            activated_at_utc=preview_time,
        )
        for market in markets
    }

    print(
        json.dumps(
            {
                "mode": "PREVIEW_ONLY",
                "provider_call_made": False,
                "ai_ledgers_created": False,
                "broker_execution_enabled": False,
                "repository_commit_sha": git_commit_sha(ROOT),
                "artifact_hashes": artifact_hashes(ROOT),
                "activation_payloads": payloads,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
