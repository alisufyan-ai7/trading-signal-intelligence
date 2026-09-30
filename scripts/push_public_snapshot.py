from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


def _validated_endpoint(base_url: str) -> str:
    endpoint = base_url.strip().rstrip("/")
    if "TRADINGTOP_" in endpoint:
        raise SystemExit(
            "TRADINGTOP_INGEST_URL is malformed: it contains an environment "
            "variable name. Re-run scripts/configure_cloud_ingest.ps1."
        )

    if not endpoint.endswith("/api/internal/snapshot"):
        endpoint += "/api/internal/snapshot"

    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit(
            "TRADINGTOP_INGEST_URL must be a valid HTTPS URL."
        )
    if "=" in parsed.path:
        raise SystemExit(
            "TRADINGTOP_INGEST_URL appears malformed. "
            "Re-run scripts/configure_cloud_ingest.ps1."
        )
    return endpoint


def _validate_snapshot_for_push(payload: dict) -> None:
    _validate_snapshot_for_push(payload)

    ai = payload.get("ai_v1")
    if isinstance(ai, dict) and ai.get("publish_allowed") is False:
        raise SystemExit(
            "Refusing to overwrite the last good cloud snapshot during an "
            "incomplete/invalid AI-v1.1 transition."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push the derived public snapshot to the cloud beta app"
    )
    parser.add_argument("--snapshot", default="data/public_snapshot.json")
    parser.add_argument("--url", default=None)
    parser.add_argument("--optional", action="store_true")
    args = parser.parse_args()

    base_url = args.url or os.getenv("TRADINGTOP_INGEST_URL")
    token = os.getenv("TRADINGTOP_INGEST_TOKEN")
    if not base_url or not token:
        if args.optional:
            print(
                json.dumps(
                    {
                        "push_enabled": False,
                        "reason": (
                            "TRADINGTOP_INGEST_URL / INGEST_TOKEN "
                            "not configured"
                        ),
                    },
                    indent=2,
                )
            )
            return
        raise SystemExit(
            "Set TRADINGTOP_INGEST_URL and TRADINGTOP_INGEST_TOKEN in .env "
            "or pass --url."
        )

    endpoint = _validated_endpoint(base_url)

    payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    if payload.get("raw_market_data_included") is not False:
        raise SystemExit("Refusing to upload a snapshot containing raw market data")

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Cloud snapshot push failed: HTTP {exc.code}. "
            f"Response: {detail[:500]}"
        ) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cloud snapshot push failed: {exc.reason}") from None

    print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
