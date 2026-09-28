from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://tradingtop-early-access-production.up.railway.app"


def _get_json(url: str, timeout: float = 20.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SignalProof-Durability-Check/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"HTTP {exc.code} from {url}: {detail[:500]}"
        ) from None
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach {url}: {exc.reason}") from None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON from {url}: {exc}") from None
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object from {url}")
    return payload


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only verification of the SignalProof cloud snapshot contract. "
            "Run before and after a Railway redeploy to prove durability."
        )
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    health = _get_json(f"{base}/api/health")
    ai = _get_json(f"{base}/api/ai/insights")

    markets_request = urllib.request.Request(
        f"{base}/api/markets",
        headers={"User-Agent": "SignalProof-Durability-Check/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(markets_request, timeout=20.0) as response:
            markets = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to validate market list: {exc}") from None

    _require(isinstance(markets, list), "Market endpoint must return a list")
    _require(health.get("ok") is True, "Cloud health is not OK")
    _require(health.get("launch_ready") is True, "Cloud snapshot is not launch-ready")
    _require(
        health.get("snapshot_pending") is False,
        "Cloud snapshot is pending/missing",
    )
    _require(ai.get("protocol_version") == "AI-v1.0", "Wrong AI protocol")
    _require(ai.get("mode") == "SHADOW_ONLY", "AI is not shadow-only")
    _require(
        ai.get("status") == "forward_validation_in_progress",
        "Unexpected AI status",
    )

    ai_health = ai.get("health") or {}
    _require(ai_health.get("healthy") is True, "AI health is not healthy")
    _require(
        ai_health.get("broker_execution_disabled") is True,
        "Broker execution boundary failed",
    )

    for key in (
        "raw_market_data_included",
        "raw_feature_snapshots_included",
        "provider_request_metadata_included",
        "hidden_reasoning_included",
    ):
        _require(ai.get(key) is False, f"Unsafe public AI flag: {key}")

    _require(len(markets) == 9, f"Expected 9 markets, got {len(markets)}")

    totals = ai.get("totals") or {}
    result = {
        "cloud_snapshot_durability_check": "PASS",
        "base_url": base,
        "snapshot_generated_at_utc": health.get("snapshot_generated_at_utc"),
        "market_count": len(markets),
        "ai_protocol": ai.get("protocol_version"),
        "ai_mode": ai.get("mode"),
        "ai_status": ai.get("status"),
        "ai_generated_at_utc": ai.get("generated_at_utc"),
        "valid_inferences": totals.get("valid_inferences"),
        "signals": totals.get("signals"),
        "open_shadow_signals": totals.get("open_shadow_signals"),
        "completed_shadow_trades": totals.get("completed_shadow_trades"),
        "missed_inferences": totals.get("missed_inferences"),
        "errors": totals.get("errors"),
        "broker_execution_disabled": ai_health.get("broker_execution_disabled"),
        "raw_market_data_included": ai.get("raw_market_data_included"),
        "raw_feature_snapshots_included": ai.get(
            "raw_feature_snapshots_included"
        ),
        "provider_request_metadata_included": ai.get(
            "provider_request_metadata_included"
        ),
        "hidden_reasoning_included": ai.get("hidden_reasoning_included"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
