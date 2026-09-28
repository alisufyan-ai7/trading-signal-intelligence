from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.local_env import load_local_env


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://api.openai.com/v1"

# Ordered for diagnostics only. This list does not change the frozen AI-v1
# provider/model selection. Any fallback selection requires a recorded
# pre-activation governance change before use.
CANDIDATES = [
    "gpt-5.4-2026-03-05",
    "gpt-5.5-2026-04-23",
    "gpt-5.4-mini-2026-03-17",
    "gpt-5.2-2025-12-11",
]


def _request_json(url: str, api_key: str) -> tuple[int, dict[str, Any] | None, str]:
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
    except urllib.error.URLError as exc:
        return 0, None, f"transport_error: {exc.reason}"

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return status, None, raw[:500]
    if isinstance(decoded, dict):
        return status, decoded, ""
    return status, None, raw[:500]


def _error_message(payload: dict[str, Any] | None, fallback: str) -> str:
    if not payload:
        return fallback
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        code = error.get("code")
        if message:
            return f"{message}" + (f" [code={code}]" if code else "")
    return fallback


def main() -> None:
    load_local_env(ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not configured in local .env/environment.")

    configured = json.loads(
        (ROOT / "config" / "ai_v1_provider.json").read_text(encoding="utf-8")
    )
    configured_model = str(configured["model_id"])

    list_status, list_payload, list_fallback = _request_json(
        f"{API_BASE}/models",
        api_key,
    )
    listed_ids: set[str] = set()
    if list_status == 200 and list_payload is not None:
        rows = list_payload.get("data")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and isinstance(row.get("id"), str):
                    listed_ids.add(row["id"])

    probe_ids: list[str] = []
    for model_id in [configured_model, *CANDIDATES]:
        if model_id not in probe_ids:
            probe_ids.append(model_id)

    probes: list[dict[str, Any]] = []
    for model_id in probe_ids:
        encoded = urllib.parse.quote(model_id, safe="")
        status, payload, fallback = _request_json(
            f"{API_BASE}/models/{encoded}",
            api_key,
        )
        accessible = status == 200
        probes.append(
            {
                "model_id": model_id,
                "accessible_via_retrieve": accessible,
                "http_status": status,
                "present_in_models_list": (
                    model_id in listed_ids if list_status == 200 else None
                ),
                "owned_by": (
                    payload.get("owned_by")
                    if accessible and isinstance(payload, dict)
                    else None
                ),
                "shutdown_date": (
                    payload.get("shutdown_date")
                    if accessible and isinstance(payload, dict)
                    else None
                ),
                "error": (
                    None
                    if accessible
                    else _error_message(payload, fallback)
                ),
            }
        )

    accessible_pinned = [
        row["model_id"]
        for row in probes
        if row["accessible_via_retrieve"]
        and row["model_id"] in CANDIDATES
    ]

    print(
        json.dumps(
            {
                "mode": "MODEL_ACCESS_DIAGNOSTIC_ONLY",
                "provider_call_made": False,
                "performance_ledger_write": False,
                "broker_execution_enabled": False,
                "configured_model": configured_model,
                "models_list_http_status": list_status,
                "models_list_count": (
                    len(listed_ids) if list_status == 200 else None
                ),
                "models_list_error": (
                    None
                    if list_status == 200
                    else _error_message(list_payload, list_fallback)
                ),
                "candidate_probes": probes,
                "accessible_pinned_candidates": accessible_pinned,
                "note": (
                    "Do not change config/ai_v1_provider.json from this output alone. "
                    "A fallback model requires an explicit pre-activation governance update."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
