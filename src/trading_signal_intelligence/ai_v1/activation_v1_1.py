from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation import (
    cost_policy_fingerprint,
    load_json,
    provider_parameter_fingerprint,
)
from trading_signal_intelligence.ai_v1.features import canonical_json
from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    SYNC_MAX_WAIT_SECONDS,
    SYNC_POLL_INTERVAL_SECONDS,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS,
    MARKETS,
)


RUNTIME_VERSION = "AI-v1.1"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
SUPERSEDES_RUNTIME_VERSION = "AI-v1.0"

UPSTREAM_ACTIVATION_ANCHOR = (
    "research/forward/AI-v1-activation-2026-09-28T155616Z.json"
)

FROZEN_DECISION_ARTIFACT_PATHS = {
    "policy": "config/ai_v1_policy.txt",
    "feature_definitions": "docs/ai-v1-feature-definitions.md",
    "feature_schema": "config/ai_v1_feature_schema.json",
    "decision_schema": "config/ai_v1_decision_schema.json",
    "guardrails": "config/ai_v1_guardrails.json",
    "provider_config": "config/ai_v1_provider.json",
    "provider_response_schema": "config/ai_v1_openai_response_schema.json",
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
    "lifecycle_evaluator_source": (
        "src/trading_signal_intelligence/ai_v1/signals.py"
    ),
}

V11_ARTIFACT_PATHS = {
    "activation_schema_v1_1": "config/ai_v1_1_activation_schema.json",
    "rates_sync_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/rates_sync_v1_1.py"
    ),
    "mt5_rates_adapter_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/mt5_rates_adapter_v1_1.py"
    ),
    "engine_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/engine_v1_1.py"
    ),
    "shadow_runtime_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/shadow_runtime_v1_1.py"
    ),
    "activation_builder_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/activation_v1_1.py"
    ),
    "shadow_runner_script_v1_1": "scripts/run_ai_v1_1_shadow.py",
    "preactivation_verifier_script_v1_1": (
        "scripts/verify_ai_v1_1_pre_activation.py"
    ),
    "mt5_connector_source": (
        "src/trading_signal_intelligence/connectors/mt5.py"
    ),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ActivationV11Error(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    if not path.is_file():
        raise ActivationV11Error(f"required artifact missing: {path}")
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
        raise ActivationV11Error("unable to resolve repository HEAD") from exc
    if not _COMMIT_RE.fullmatch(value):
        raise ActivationV11Error(f"unexpected repository HEAD: {value!r}")
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
        raise ActivationV11Error("unable to inspect repository worktree") from exc
    if output.strip():
        raise ActivationV11Error(
            "tracked worktree is dirty; commit/revert before v1.1 activation"
        )


def artifact_hashes(
    repo_root: Path,
    paths: dict[str, str],
) -> dict[str, str]:
    return {
        name: file_sha256(repo_root / relative)
        for name, relative in paths.items()
    }


def load_upstream_anchor(repo_root: Path) -> dict[str, Any]:
    path = repo_root / UPSTREAM_ACTIVATION_ANCHOR
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationV11Error(
            f"unable to load upstream activation anchor: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActivationV11Error("upstream activation anchor root must be object")
    if payload.get("protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ActivationV11Error("upstream activation protocol mismatch")
    if payload.get("broker_execution_enabled") is not False:
        raise ActivationV11Error("upstream broker execution must be disabled")
    return payload


def verify_frozen_decision_lineage(repo_root: Path) -> dict[str, Any]:
    anchor = load_upstream_anchor(repo_root)
    expected = anchor.get("artifact_hashes")
    if not isinstance(expected, dict):
        raise ActivationV11Error("upstream anchor artifact_hashes missing")

    observed = artifact_hashes(repo_root, FROZEN_DECISION_ARTIFACT_PATHS)
    mismatches = {
        name: {
            "expected": expected.get(name),
            "observed": observed[name],
        }
        for name in observed
        if expected.get(name) != observed[name]
    }
    return {
        "match": not mismatches,
        "mismatches": mismatches,
        "observed": observed,
    }


def _shared_payload_fields(
    *,
    repo_root: Path,
    market: str,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    if market not in MARKETS:
        raise ActivationV11Error(f"unsupported market: {market}")
    if activated_at_utc.tzinfo is None:
        raise ActivationV11Error("activation timestamp must be timezone-aware")

    lineage = verify_frozen_decision_lineage(repo_root)
    if not lineage["match"]:
        raise ActivationV11Error(
            f"frozen v1.0 decision lineage mismatch: {lineage['mismatches']}"
        )

    provider_config = load_json(
        repo_root / FROZEN_DECISION_ARTIFACT_PATHS["provider_config"]
    )
    provider_schema = load_json(
        repo_root / FROZEN_DECISION_ARTIFACT_PATHS["provider_response_schema"]
    )
    guardrails = load_json(
        repo_root / FROZEN_DECISION_ARTIFACT_PATHS["guardrails"]
    )
    if provider_config.get("protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ActivationV11Error("provider decision protocol changed")
    if provider_config.get("model_id") != "gpt-5.4-2026-03-05":
        raise ActivationV11Error("frozen model_id changed")
    if guardrails.get("broker_execution_enabled") is not False:
        raise ActivationV11Error("broker execution must remain disabled")
    if float(guardrails.get("max_data_age_seconds")) != 300.0:
        raise ActivationV11Error("frozen 300-second freshness rule changed")

    frozen = lineage["observed"]
    upstream_path = repo_root / UPSTREAM_ACTIVATION_ANCHOR
    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "market": market,
        "activated_at_utc": activated_at_utc.astimezone(timezone.utc).isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "activation_bundle_sha256": "",
        "supersedes_runtime_version": SUPERSEDES_RUNTIME_VERSION,
        "upstream_activation_anchor": UPSTREAM_ACTIVATION_ANCHOR,
        "upstream_activation_anchor_sha256": file_sha256(upstream_path),
        "gate_counts_carry_forward": False,
        "backfill_prior_missed": False,
        "provider": str(provider_config["provider"]),
        "model_id": str(provider_config["model_id"]),
        "model_parameter_fingerprint": provider_parameter_fingerprint(
            provider_config,
            provider_schema,
        ),
        "policy_sha256": frozen["policy"],
        "feature_definitions_sha256": frozen["feature_definitions"],
        "feature_schema_sha256": frozen["feature_schema"],
        "decision_schema_sha256": frozen["decision_schema"],
        "guardrails_sha256": frozen["guardrails"],
        "feature_builder_source_sha256": frozen["feature_builder_source"],
        "inference_adapter_source_sha256": frozen["inference_adapter_source"],
        "provider_neutral_inference_source_sha256": frozen[
            "provider_neutral_inference_source"
        ],
        "contract_source_sha256": frozen["contract_source"],
        "guard_source_sha256": frozen["guard_source"],
        "ai_ledger_source_sha256": frozen["ai_ledger_source"],
        "lifecycle_evaluator_source_sha256": frozen[
            "lifecycle_evaluator_source"
        ],
        "cost_policy_fingerprint": cost_policy_fingerprint(guardrails),
        "sync_max_wait_seconds": float(SYNC_MAX_WAIT_SECONDS),
        "sync_poll_interval_seconds": float(SYNC_POLL_INTERVAL_SECONDS),
        "broker_execution_enabled": False,
    }


def build_activation_payload_v1_1(
    *,
    repo_root: Path,
    market: str,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    require_clean_tracked_worktree(repo_root)
    payload = _shared_payload_fields(
        repo_root=repo_root,
        market=market,
        activated_at_utc=activated_at_utc,
    )
    all_hashes = {
        "frozen_decision_artifacts": artifact_hashes(
            repo_root,
            FROZEN_DECISION_ARTIFACT_PATHS,
        ),
        "v1_1_artifacts": artifact_hashes(repo_root, V11_ARTIFACT_PATHS),
    }
    material = {
        **payload,
        "activation_bundle_sha256": None,
        "all_artifact_hashes": all_hashes,
    }
    payload["activation_bundle_sha256"] = hashlib.sha256(
        canonical_json(material).encode("utf-8")
    ).hexdigest()
    validate_activation_payload_v1_1(payload)
    return payload


def validate_activation_payload_v1_1(payload: dict[str, Any]) -> None:
    required = {
        "runtime_version",
        "decision_protocol_version",
        "market",
        "activated_at_utc",
        "repository_commit_sha",
        "activation_bundle_sha256",
        "supersedes_runtime_version",
        "upstream_activation_anchor",
        "upstream_activation_anchor_sha256",
        "gate_counts_carry_forward",
        "backfill_prior_missed",
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
        "provider_neutral_inference_source_sha256",
        "contract_source_sha256",
        "guard_source_sha256",
        "ai_ledger_source_sha256",
        "lifecycle_evaluator_source_sha256",
        "cost_policy_fingerprint",
        "sync_max_wait_seconds",
        "sync_poll_interval_seconds",
        "broker_execution_enabled",
    }
    if set(payload) != required:
        raise ActivationV11Error(
            "v1.1 activation payload keys mismatch"
        )
    if payload["runtime_version"] != RUNTIME_VERSION:
        raise ActivationV11Error("runtime_version mismatch")
    if payload["decision_protocol_version"] != DECISION_PROTOCOL_VERSION:
        raise ActivationV11Error("decision_protocol_version mismatch")
    if payload["market"] not in MARKETS:
        raise ActivationV11Error("market mismatch")
    if payload["supersedes_runtime_version"] != SUPERSEDES_RUNTIME_VERSION:
        raise ActivationV11Error("supersession version mismatch")
    if payload["gate_counts_carry_forward"] is not False:
        raise ActivationV11Error("gate counts must restart for v1.1")
    if payload["backfill_prior_missed"] is not False:
        raise ActivationV11Error("prior missed cycles must not be backfilled")
    if payload["provider"] != "openai":
        raise ActivationV11Error("provider mismatch")
    if payload["model_id"] != "gpt-5.4-2026-03-05":
        raise ActivationV11Error("model mismatch")
    if payload["sync_max_wait_seconds"] != 30.0:
        raise ActivationV11Error("sync max wait mismatch")
    if payload["sync_poll_interval_seconds"] != 1.0:
        raise ActivationV11Error("sync poll interval mismatch")
    if payload["broker_execution_enabled"] is not False:
        raise ActivationV11Error("broker execution must remain disabled")
    if not _COMMIT_RE.fullmatch(str(payload["repository_commit_sha"])):
        raise ActivationV11Error("invalid repository commit SHA")

    sha_fields = (
        "activation_bundle_sha256",
        "upstream_activation_anchor_sha256",
        "model_parameter_fingerprint",
        "policy_sha256",
        "feature_definitions_sha256",
        "feature_schema_sha256",
        "decision_schema_sha256",
        "guardrails_sha256",
        "feature_builder_source_sha256",
        "inference_adapter_source_sha256",
        "provider_neutral_inference_source_sha256",
        "contract_source_sha256",
        "guard_source_sha256",
        "ai_ledger_source_sha256",
        "lifecycle_evaluator_source_sha256",
        "cost_policy_fingerprint",
    )
    for key in sha_fields:
        if not _SHA256_RE.fullmatch(str(payload[key])):
            raise ActivationV11Error(f"{key} must be SHA-256 hex")


def preactivation_report_v1_1(repo_root: Path) -> dict[str, Any]:
    require_clean_tracked_worktree(repo_root)
    lineage = verify_frozen_decision_lineage(repo_root)
    v11_hashes = artifact_hashes(repo_root, V11_ARTIFACT_PATHS)

    ledgers = {
        market: (repo_root / DATABASE_PATHS[market]).exists()
        for market in MARKETS
    }
    anchor_candidates = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "research" / "forward").glob(
            "AI-v1.1-activation-*.json"
        )
    )
    ready = (
        lineage["match"]
        and not any(ledgers.values())
        and not anchor_candidates
    )
    return {
        "preactivation_check": "PASS" if ready else "FAIL",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "repository_commit_sha": git_commit_sha(repo_root),
        "upstream_activation_anchor": UPSTREAM_ACTIVATION_ANCHOR,
        "upstream_activation_anchor_sha256": file_sha256(
            repo_root / UPSTREAM_ACTIVATION_ANCHOR
        ),
        "frozen_decision_artifacts_match_upstream": lineage["match"],
        "frozen_decision_artifact_mismatches": lineage["mismatches"],
        "v1_1_artifact_hashes": v11_hashes,
        "v1_1_ledger_paths_exist": ledgers,
        "v1_1_activation_anchors": anchor_candidates,
        "sync_max_wait_seconds": float(SYNC_MAX_WAIT_SECONDS),
        "sync_poll_interval_seconds": float(SYNC_POLL_INTERVAL_SECONDS),
        "provider_call_made": False,
        "mt5_call_made": False,
        "broker_execution_enabled": False,
        "activation_performed": False,
        "scheduler_changed": False,
    }
