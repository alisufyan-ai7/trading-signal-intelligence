from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_BASE_URL = "https://tradingtop-early-access-production.up.railway.app"

SYNTHETIC_FEEDBACK = {
    "comprehension_rating": 4,
    "lifecycle_clarity_rating": 4,
    "ai_reasoning_clarity_rating": 4,
    "immutable_record_trust": "yes",
    "missing_details": ["expiry_validity"],
    "alert_preference": "web",
    "willingness_to_pay": "maybe",
    "price_range": "10_25",
    "market_interests": ["XAUUSD", "USTEC", "US30"],
    "feedback_text": "Synthetic verification record for feedback persistence testing.",
}


def _request(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict | None = None,
) -> tuple[int, dict]:
    headers = {"User-Agent": "SignalProof-Feedback-Smoke/1.0"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, headers=headers, data=body, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30.0) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {detail[:500]}") from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach {url}: {exc.reason}") from None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Submit one synthetic feedback record and verify owner access."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=True)
    token = os.getenv("SIGNALPROOF_FEEDBACK_OWNER_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "SIGNALPROOF_FEEDBACK_OWNER_TOKEN is not configured in local .env."
        )

    base = args.base_url.rstrip("/")

    before_status, before = _request(
        f"{base}/api/internal/feedback/summary",
        token=token,
    )
    if before_status != 200:
        raise SystemExit("Owner summary did not return HTTP 200")

    submit_status, submitted = _request(
        f"{base}/api/feedback",
        method="POST",
        payload=SYNTHETIC_FEEDBACK,
    )
    if submit_status != 200 or submitted.get("accepted") is not True:
        raise SystemExit("Synthetic feedback submission failed")

    after_status, after = _request(
        f"{base}/api/internal/feedback/summary",
        token=token,
    )
    if after_status != 200:
        raise SystemExit("Owner summary after submission did not return HTTP 200")

    before_count = int(before.get("submission_count", 0))
    after_count = int(after.get("submission_count", 0))
    if after_count != before_count + 1:
        raise SystemExit(
            f"Feedback count mismatch: before={before_count} after={after_count}"
        )

    result = {
        "feedback_smoke": "PASS",
        "submission_id": submitted.get("submission_id"),
        "submitted_at_utc": submitted.get("submitted_at_utc"),
        "retention_months": submitted.get("retention_months"),
        "before_count": before_count,
        "after_count": after_count,
        "owner_summary_access": True,
        "public_submission_access": True,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
