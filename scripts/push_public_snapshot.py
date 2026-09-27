from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push the derived public snapshot to the cloud beta app"
    )
    parser.add_argument("--snapshot", default="data/public_snapshot.json")
    parser.add_argument("--url", default=None)
    args = parser.parse_args()

    base_url = args.url or os.getenv("TRADINGTOP_INGEST_URL")
    token = os.getenv("TRADINGTOP_INGEST_TOKEN")
    if not base_url or not token:
        if args.optional:
            print(json.dumps({
                "push_enabled": False,
                "reason": "TRADINGTOP_INGEST_URL / INGEST_TOKEN not configured",
            }, indent=2))
            return
        raise SystemExit(
            "Set TRADINGTOP_INGEST_URL and TRADINGTOP_INGEST_TOKEN in .env "
            "or pass --url."
        )

    payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    if payload.get("raw_market_data_included") is not False:
        raise SystemExit("Refusing to upload a snapshot containing raw market data")

    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/api/internal/snapshot"):
        endpoint += "/api/internal/snapshot"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
