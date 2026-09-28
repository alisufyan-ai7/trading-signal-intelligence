from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.features import canonical_json
from trading_signal_intelligence.ai_v1.inference import parameter_fingerprint
from trading_signal_intelligence.ai_v1.openai_responses import OpenAIResponsesAdapter


PROTOCOL_VERSION = "AI-v1.0"
MARKETS = ("XAUUSD", "USTEC", "US30")

ARTIFACT_PATHS = {
    "provider_selection": "docs/ai-v1-provider-selection.md",
    "architecture": "docs/ai-v1-architecture.md",
    "ledger_spec": "docs/ai-v1-ledger-spec.md",
    "runtime_spec": "docs/ai-v1-shadow-runtime.md",
    "policy": "config/ai_v1_policy.txt",
    "feature_definitions": "docs/ai-v1-feature-definitions.md",
    "feature_schema": "config/ai_v1_feature_schema.json",
    "decision_schema": "config/ai_v1_decision_schema.json",
    "guardrails": "config/ai_v1_guardrails.json",
    "provider_config": "config/ai_v1_provider.json",
    "provider_response_schema": "config/ai_v1_openai_response_schema.json",
    "activation_schema": "config/ai_v1_activation_schema.json",
    "feature_builder_source": "src/trading_signal_intelligence/ai_v1/features.py",
    "inference_adapter_source": (
        "src/trading_signal_intelligence/ai_v1/openai_responses.py"
    ),
    "provider_neutral_inference_source": (
        "src/trading_signal_intelligence/ai_v1/inference.py"
    ),
    "contract_source": "src/trading_signal_intelligence/ai_v1/contract.py",
    "guard_source": "src/trading_signal_intelligence/ai_v1/guardrails.py",
    "ai_ledger_source": "src/trading_signal_intelligence/ai_v1/ledger.py",
    "engine_source": "src/trading_signal_intelligence/ai_v1/engine.py",
    "lifecycle_evaluator_source": "src/trading_signal_intelligence/ai_v1/signals.py",
    "activation_builder_source": "src/trading_signal_intelligence/ai_v1/activation.py",
    "shadow_runtime_source": "src/trading_signal_intelligence/ai_v1/shadow_runtime.py",
    "shadow_runner_script": "scripts/run_ai_v1_shadow.py",
    "shadow_task_runner_script": "scripts/run_ai_v1_shadow_task.cmd",
    "shadow_task_installer_script": "scripts/install_ai_v1_shadow_task.ps1",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ActivationError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    if not path.is_file():
        raise ActivationError(f"required activation artifact missing: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit_sha(repo_root: Path) -> str:
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ActivationError("unable to resolve repository HEAD") from exc
    if not _COMMIT_RE.fullmatch(value):
        raise ActivationError(f"unexpected repository HEAD: {value!r}")
    return value


def require_clean_tracked_worktree(repo_root: Path) -> None:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ActivationError("unable to inspect repository worktree") from exc
    if output.strip():
        raise ActivationError(
            "tracked worktree is dirty; commit/revert changes before activation"
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationError(f"unable to load JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ActivationError(f"JSON root must be object: {path}")
    return value


def artifact_hashes(repo_root: Path) -> dict[str, str]:
    return {
        name: file_sha256(repo_root / relative)
        for name, relative in ARTIFACT_PATHS.items()
    }


def cost_policy_fingerprint(guardrails: dict[str, Any]) -> str:
    cost_policy = {
        "cost_multiplier": guardrails["cost_multiplier"],
        "max_round_trip_cost_r": guardrails["max_round_trip_cost_r"],
        "ambiguous_same_bar_policy": guardrails["ambiguous_same_bar_policy"],
        "tp1_position_fraction": guardrails["tp1_position_fraction"],
        "tp2_position_fraction": guardrails["tp2_position_fraction"],
        "move_stop_after_tp1": guardrails["move_stop_after_tp1"],
        "max_hold_h1_bars": guardrails["max_hold_h1_bars"],
    }
    return hashlib.sha256(
        canonical_json(cost_policy).encode("utf-8")
    ).hexdigest()


def provider_parameter_fingerprint(
    provider_config: dict[str, Any],
    provider_schema: dict[str, Any],
) -> str:
    adapter = OpenAIResponsesAdapter(
        config=provider_config,
        provider_response_schema=provider_schema,
        api_key="<fingerprint-only-not-a-secret>",
    )
    return parameter_fingerprint(
        provider=adapter.provider,
        model_id=adapter.model_id,
        parameters=adapter.parameters,
    )


def build_activation_payload(
    *,
    repo_root: Path,
    market: str,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    if market not in MARKETS:
        raise ActivationError(f"unsupported AI-v1 market: {market}")
    if activated_at_utc.tzinfo is None:
        raise ActivationError("activation timestamp must be timezone-aware")

    require_clean_tracked_worktree(repo_root)
    hashes = artifact_hashes(repo_root)
    provider_config = load_json(repo_root / ARTIFACT_PATHS["provider_config"])
    provider_schema = load_json(
        repo_root / ARTIFACT_PATHS["provider_response_schema"]
    )
    guardrails = load_json(repo_root / ARTIFACT_PATHS["guardrails"])

    if provider_config.get("protocol_version") != PROTOCOL_VERSION:
        raise ActivationError("provider config protocol version mismatch")
    if provider_config.get("model_id") != "gpt-5.4-2026-03-05":
        raise ActivationError("unexpected frozen AI-v1 model_id")
    if guardrails.get("broker_execution_enabled") is not False:
        raise ActivationError("broker execution must remain disabled")

    payload: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "market": market,
        "activated_at_utc": activated_at_utc.astimezone(timezone.utc).isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "activation_bundle_sha256": "",
        "provider": str(provider_config["provider"]),
        "model_id": str(provider_config["model_id"]),
        "model_parameter_fingerprint": provider_parameter_fingerprint(
            provider_config,
            provider_schema,
        ),
        "policy_sha256": hashes["policy"],
        "feature_definitions_sha256": hashes["feature_definitions"],
        "feature_schema_sha256": hashes["feature_schema"],
        "decision_schema_sha256": hashes["decision_schema"],
        "guardrails_sha256": hashes["guardrails"],
        "feature_builder_source_sha256": hashes["feature_builder_source"],
        "inference_adapter_source_sha256": hashes["inference_adapter_source"],
        "ai_ledger_source_sha256": hashes["ai_ledger_source"],
        "lifecycle_evaluator_source_sha256": hashes["lifecycle_evaluator_source"],
        "cost_policy_fingerprint": cost_policy_fingerprint(guardrails),
        "broker_execution_enabled": False,
    }

    hash_material = {
        **payload,
        "activation_bundle_sha256": None,
        "all_artifact_hashes": hashes,
    }
    payload["activation_bundle_sha256"] = hashlib.sha256(
        canonical_json(hash_material).encode("utf-8")
    ).hexdigest()
    validate_activation_payload(payload)
    return payload


def validate_activation_payload(payload: dict[str, Any]) -> None:
    required = {
        "protocol_version",
        "market",
        "activated_at_utc",
        "repository_commit_sha",
        "activation_bundle_sha256",
        "provider",
        "model_id",
        "model_parameter_fingerprint",
        "policy_sha256",
        "feature_definitions_sha256",
        "feature_schema_sha256",
        "decision_schema_sha256",
        "guardrails_sha256",
        "feature_builder_source_sha256",
        "inference_adapter_source_sha256",
        "ai_ledger_source_sha256",
        "lifecycle_evaluator_source_sha256",
        "cost_policy_fingerprint",
        "broker_execution_enabled",
    }
    if set(payload) != required:
        raise ActivationError(
            f"activation payload keys mismatch; missing={sorted(required-set(payload))}, "
            f"extra={sorted(set(payload)-required)}"
        )
    if payload["protocol_version"] != PROTOCOL_VERSION:
        raise ActivationError("activation protocol mismatch")
    if payload["market"] not in MARKETS:
        raise ActivationError("activation market mismatch")
    if not _COMMIT_RE.fullmatch(str(payload["repository_commit_sha"])):
        raise ActivationError("invalid repository commit SHA")
    for key in (
        "activation_bundle_sha256",
        "model_parameter_fingerprint",
        "policy_sha256",
        "feature_definitions_sha256",
        "feature_schema_sha256",
        "decision_schema_sha256",
        "guardrails_sha256",
        "feature_builder_source_sha256",
        "inference_adapter_source_sha256",
        "ai_ledger_source_sha256",
        "lifecycle_evaluator_source_sha256",
        "cost_policy_fingerprint",
    ):
        if not _SHA256_RE.fullmatch(str(payload[key])):
            raise ActivationError(f"{key} must be SHA-256 hex")
    if payload["provider"] != "openai":
        raise ActivationError("unexpected AI-v1 provider")
    if payload["model_id"] != "gpt-5.4-2026-03-05":
        raise ActivationError("unexpected AI-v1 model")
    if payload["broker_execution_enabled"] is not False:
        raise ActivationError("broker execution must be false")


def require_provider_key(provider_config: dict[str, Any]) -> None:
    env_name = str(provider_config["api_key_env"])
    if not os.getenv(env_name, "").strip():
        raise ActivationError(
            f"{env_name} is not configured; refuse AI-v1 activation"
        )
