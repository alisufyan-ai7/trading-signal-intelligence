from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "https://vowsig.com"


def _get_json(url: str, timeout: float = 20.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VowSig-Durability-Check/1.0"},
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
            "Read-only verification of the VowSig cloud snapshot contract. "
            "Run before and after a Railway redeploy to prove durability."
        )
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    health = _get_json(f"{base}/api/health")
    ai = _get_json(f"{base}/api/ai/insights")
    validation = _get_json(f"{base}/api/validation/programs")

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
    _require(
        ai.get("decision_protocol_version") == "AI-v1.0",
        "Wrong AI decision protocol version",
    )
    runtime_version = ai.get("runtime_version")
    _require(
        runtime_version in {"AI-v1.0", "AI-v1.1"},
        f"Unexpected active AI runtime: {runtime_version!r}",
    )
    if runtime_version == "AI-v1.1":
        legacy = ai.get("legacy_lineage")
        _require(
            isinstance(legacy, dict),
            "AI-v1.1 public contract missing legacy lineage",
        )
        _require(
            legacy.get("gate_counts_carried_into_active_runtime") is False,
            "AI-v1.1 legacy gate-count isolation failed",
        )
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

    _require(
        validation.get("schema_version") == 1,
        "Wrong validation-program schema",
    )
    programs = validation.get("programs")
    _require(
        isinstance(programs, list),
        "Validation programs endpoint must return a list",
    )
    by_id = {
        row.get("program_id"): row
        for row in programs
        if isinstance(row, dict)
    }
    _require(
        "core-ai-shadow" in by_id,
        "Core AI validation program missing",
    )
    _require(
        "market-expansion-1" in by_id,
        "Expansion validation program missing",
    )

    for program_id, program in by_id.items():
        _require(
            program.get("mode") == "SHADOW_ONLY",
            f"{program_id} is not shadow-only",
        )
        _require(
            program.get("public_research_observability") is True,
            f"{program_id} observability flag missing",
        )
        _require(
            program.get("signal_details_included") is False,
            f"{program_id} exposes signal details",
        )
        program_health = program.get("health") or {}
        _require(
            program_health.get("broker_execution_disabled") is True,
            f"{program_id} broker boundary failed",
        )

    core = by_id["core-ai-shadow"]
    _require(
        {row.get("gate_id") for row in core.get("gates", [])}
        == {"A1", "A2", "A3"},
        "Core A1/A2/A3 gate set mismatch",
    )

    expansion = by_id["market-expansion-1"]
    _require(
        expansion.get("public_signal_exposure") is False,
        "Expansion signal exposure must remain disabled",
    )
    _require(
        {row.get("gate_id") for row in expansion.get("gates", [])}
        == {"X1", "X2", "X3"},
        "Expansion X1/X2/X3 gate set mismatch",
    )
    _require(
        {row.get("source_symbol") for row in expansion.get("markets", [])}
        == {"EURUSD", "XAGUSD", "USOIL"},
        "Expansion market set mismatch",
    )

    totals = ai.get("totals") or {}
    result = {
        "cloud_snapshot_durability_check": "PASS",
        "base_url": base,
        "snapshot_generated_at_utc": health.get("snapshot_generated_at_utc"),
        "market_count": len(markets),
        "validation_program_count": len(programs),
        "validation_program_ids": sorted(by_id),
        "ai_runtime_version": runtime_version,
        "ai_protocol": ai.get("protocol_version"),
        "ai_decision_protocol": ai.get("decision_protocol_version"),
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
