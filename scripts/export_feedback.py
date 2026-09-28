from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_BASE_URL = "https://tradingtop-early-access-production.up.railway.app"


def _get(url: str, token: str) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "SignalProof-Feedback-Owner/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30.0) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"Feedback owner request failed: HTTP {exc.code}: {detail[:500]}"
        ) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach feedback endpoint: {exc.reason}") from None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Owner-only SignalProof feedback summary/export helper"
    )
    parser.add_argument(
        "action",
        choices=("summary", "json", "csv"),
        help="Read aggregate summary or export submissions.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=True)

    token = os.getenv("SIGNALPROOF_FEEDBACK_OWNER_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "SIGNALPROOF_FEEDBACK_OWNER_TOKEN is not configured in local .env."
        )

    base = args.base_url.rstrip("/")
    if args.action == "summary":
        payload, _ = _get(f"{base}/api/internal/feedback/summary", token)
        parsed = json.loads(payload.decode("utf-8"))
        print(json.dumps(parsed, indent=2))
        return

    format_name = args.action
    payload, _ = _get(
        f"{base}/api/internal/feedback/export?format={format_name}",
        token,
    )
    suffix = ".json" if format_name == "json" else ".csv"
    output = (
        Path(args.output)
        if args.output
        else repo_root / "data" / f"feedback-export{suffix}"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    print(f"Feedback export written: {output}")
    print(f"bytes={len(payload)}")


if __name__ == "__main__":
    main()
