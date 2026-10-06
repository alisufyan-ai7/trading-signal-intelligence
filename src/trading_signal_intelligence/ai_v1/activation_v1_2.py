from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation import (
    cost_policy_fingerprint,
    load_json,
    provider_parameter_fingerprint,
)
from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    FROZEN_DECISION_ARTIFACT_PATHS,
    artifact_hashes,
    file_sha256,
    git_commit_sha,
    require_clean_tracked_worktree,
    verify_frozen_decision_lineage,
)
from trading_signal_intelligence.ai_v1.expansion_v1_2 import (
    BASE_FEATURE_SCHEMA,
    BASE_GUARDRAILS,
    EXPANSION_CONFIG,
    EXPANSION_FEATURE_SCHEMA,
    EXPANSION_GUARDRAILS,
    MARKETS,
    REVIEW_GATES,
    feature_schema_equivalence_report,
    guardrails_equivalence_report,
    load_expansion_config,
    review_gates_report,
)
from trading_signal_intelligence.ai_v1.features import canonical_json
from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    SYNC_MAX_WAIT_SECONDS,
    SYNC_POLL_INTERVAL_SECONDS,
)


RUNTIME_VERSION = "AI-v1.2"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
PARALLEL_TO_RUNTIME_VERSION = "AI-v1.1"
PARALLEL_RUNTIME_ANCHOR = (
    "research/forward/AI-v1.1-activation-2026-09-30T114412Z.json"
)
READINESS_EVIDENCE = (
    "research/forward/AI-v1.2-expansion-readiness-2026-10-06T190314Z.json"
)

EXPANSION_ARTIFACT_PATHS = {
    "readiness_evidence": READINESS_EVIDENCE,
    "preregistration_exp_2026_015": (
        "research/experiments/EXP-2026-015-ai-v1.2-market-expansion-preregistration.md"
    ),
    "compatibility_plan_v0_1": (
        "docs/ai-v1.2-market-expansion-compatibility-v0.1.md"
    ),
    "activation_plan_v0_1": (
        "docs/ai-v1.2-expansion-activation-plan-v0.1.md"
    ),
    "instrument_registry": "config/instruments.json",
    "activation_schema_v1_2": "config/ai_v1_2_activation_schema.json",
    "activation_anchor_schema_v1_2": "config/ai_v1_2_anchor_schema.json",
    "expansion_config": EXPANSION_CONFIG,
    "expansion_feature_schema": EXPANSION_FEATURE_SCHEMA,
    "expansion_guardrails": EXPANSION_GUARDRAILS,
    "review_gates": REVIEW_GATES,
    "expansion_compatibility_source": (
        "src/trading_signal_intelligence/ai_v1/expansion_v1_2.py"
    ),
    "readiness_source": (
        "src/trading_signal_intelligence/ai_v1/readiness_v1_2.py"
    ),
    "engine_source_v1_2": (
        "src/trading_signal_intelligence/ai_v1/engine_v1_2.py"
    ),
    "shadow_runtime_source_v1_2": (
        "src/trading_signal_intelligence/ai_v1/shadow_runtime_v1_2.py"
    ),
    "activation_builder_source_v1_2": (
        "src/trading_signal_intelligence/ai_v1/activation_v1_2.py"
    ),
    "observability_source_v1_2": (
        "src/trading_signal_intelligence/ai_v1/observability_v1_2.py"
    ),
    "runtime_verifier_source_v1_2": (
        "src/trading_signal_intelligence/ai_v1/runtime_verifier_v1_2.py"
    ),
    "preactivation_verifier_script_v1_2": (
        "scripts/verify_ai_v1_2_expansion_pre_activation.py"
    ),
    "activation_readiness_verifier_script_v1_2": (
        "scripts/verify_ai_v1_2_activation_readiness.py"
    ),
    "progress_report_script_v1_2": (
        "scripts/report_ai_v1_2_progress.py"
    ),
    "readiness_probe_script_v1_2": (
        "scripts/probe_ai_v1_2_market_readiness.py"
    ),
    "activation_preview_script_v1_2": (
        "scripts/preview_ai_v1_2_activation.py"
    ),
    "activation_execution_script_v1_2": (
        "scripts/activate_ai_v1_2.py"
    ),
    "live_runner_script_v1_2": "scripts/run_ai_v1_2_live.py",
    "runtime_verifier_script_v1_2": (
        "scripts/verify_ai_v1_2_runtime.py"
    ),
    "task_runner_script_v1_2": (
        "scripts/run_ai_v1_2_shadow_task.cmd"
    ),
    "task_installer_script_v1_2": (
        "scripts/install_ai_v1_2_shadow_task.ps1"
    ),
    "rates_sync_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/rates_sync_v1_1.py"
    ),
    "mt5_rates_adapter_source_v1_1": (
        "src/trading_signal_intelligence/ai_v1/mt5_rates_adapter_v1_1.py"
    ),
    "mt5_connector_source": (
        "src/trading_signal_intelligence/connectors/mt5.py"
    ),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class ActivationV12Error(RuntimeError):
    pass


def _parallel_anchor(repo_root: Path) -> dict[str, Any]:
    path = repo_root / PARALLEL_RUNTIME_ANCHOR
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationV12Error(
            f"unable to load parallel AI-v1.1 anchor: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActivationV12Error("parallel AI-v1.1 anchor root must be object")
    if payload.get("runtime_version") != PARALLEL_TO_RUNTIME_VERSION:
        raise ActivationV12Error("parallel runtime version mismatch")
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ActivationV12Error("parallel decision protocol mismatch")
    if payload.get("status") != "ACTIVE":
        raise ActivationV12Error("parallel AI-v1.1 anchor is not ACTIVE")
    if payload.get("broker_execution_enabled") is not False:
        raise ActivationV12Error("parallel broker execution must be disabled")
    return payload



def _validate_readiness_evidence(repo_root: Path) -> dict[str, Any]:
    path = repo_root / READINESS_EVIDENCE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationV12Error(
            f"unable to load AI-v1.2 readiness evidence: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ActivationV12Error("AI-v1.2 readiness evidence root must be object")
    if payload.get("status") != "PASS":
        raise ActivationV12Error("AI-v1.2 live readiness is not PASS")
    if payload.get("runtime_version") != RUNTIME_VERSION:
        raise ActivationV12Error("readiness runtime version mismatch")
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ActivationV12Error("readiness decision protocol mismatch")
    markets = payload.get("markets")
    if not isinstance(markets, dict) or set(markets) != set(MARKETS):
        raise ActivationV12Error("readiness market set mismatch")
    for market in MARKETS:
        item = markets[market]
        if not isinstance(item, dict):
            raise ActivationV12Error(f"{market} readiness item invalid")
        if item.get("readiness") != "READY":
            raise ActivationV12Error(f"{market} readiness is not READY")
        if item.get("feature_snapshot_built") is not True:
            raise ActivationV12Error(
                f"{market} readiness feature snapshot was not built"
            )
        age = float(item.get("data_age_seconds"))
        if age < 0 or age > 300:
            raise ActivationV12Error(
                f"{market} readiness was outside frozen freshness"
            )
    required_false = (
        "provider_call_made",
        "ledger_write_performed",
        "scheduler_changed",
        "public_exposure_changed",
        "broker_execution_enabled",
    )
    for key in required_false:
        if payload.get(key) is not False:
            raise ActivationV12Error(
                f"readiness evidence {key} must be false"
            )
    if payload.get("active_ai_v1_1_ledger_byte_identity") is not True:
        raise ActivationV12Error(
            "readiness did not prove AI-v1.1 ledger byte identity"
        )
    before = payload.get("expansion_ledger_presence_before")
    after = payload.get("expansion_ledger_presence_after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ActivationV12Error("readiness expansion-ledger proof missing")
    if any(bool(before.get(market)) for market in MARKETS):
        raise ActivationV12Error("expansion ledger existed before readiness")
    if any(bool(after.get(market)) for market in MARKETS):
        raise ActivationV12Error("expansion ledger appeared during readiness")
    return payload


def _validate_expansion_profiles(repo_root: Path) -> None:
    load_expansion_config(repo_root)
    schema = feature_schema_equivalence_report(repo_root)
    if not schema[
        "equivalent_except_schema_metadata_and_source_symbol_allowlist"
    ]:
        raise ActivationV12Error("expansion feature schema compatibility failed")
    if schema["feature_schema_version_preserved"] is not True:
        raise ActivationV12Error("feature schema version changed")
    if schema["expansion_source_symbol_enum"] != list(MARKETS):
        raise ActivationV12Error("expansion feature market allowlist mismatch")

    guards = guardrails_equivalence_report(repo_root)
    if not guards[
        "equivalent_except_status_and_shadow_market_allowlist"
    ]:
        raise ActivationV12Error("expansion guard semantics changed")
    if guards["expansion_shadow_markets"] != list(MARKETS):
        raise ActivationV12Error("expansion guard market allowlist mismatch")
    if guards["broker_execution_disabled"] is not True:
        raise ActivationV12Error("broker execution must remain disabled")
    if guards["protocol_version_preserved"] is not True:
        raise ActivationV12Error("guard decision protocol changed")

    gates = review_gates_report(repo_root)
    if gates["valid"] is not True:
        raise ActivationV12Error("AI-v1.2 review gates are not frozen/valid")


def _shared_payload_fields(
    *,
    repo_root: Path,
    market: str,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    if market not in MARKETS:
        raise ActivationV12Error(f"unsupported AI-v1.2 market: {market}")
    if activated_at_utc.tzinfo is None:
        raise ActivationV12Error("activation timestamp must be timezone-aware")

    lineage = verify_frozen_decision_lineage(repo_root)
    if not lineage["match"]:
        raise ActivationV12Error(
            f"frozen AI-v1.0 decision lineage mismatch: {lineage['mismatches']}"
        )
    _validate_expansion_profiles(repo_root)
    _validate_readiness_evidence(repo_root)
    _parallel_anchor(repo_root)

    provider_config = load_json(
        repo_root / FROZEN_DECISION_ARTIFACT_PATHS["provider_config"]
    )
    provider_schema = load_json(
        repo_root / FROZEN_DECISION_ARTIFACT_PATHS["provider_response_schema"]
    )
    expansion_guardrails = load_json(repo_root / EXPANSION_GUARDRAILS)

    if provider_config.get("protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ActivationV12Error("provider decision protocol changed")
    if provider_config.get("model_id") != "gpt-5.4-2026-03-05":
        raise ActivationV12Error("frozen model_id changed")
    if expansion_guardrails.get("broker_execution_enabled") is not False:
        raise ActivationV12Error("broker execution must remain disabled")

    frozen = lineage["observed"]
    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "market": market,
        "activated_at_utc": activated_at_utc.astimezone(timezone.utc).isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "activation_bundle_sha256": "",
        "parallel_to_runtime_version": PARALLEL_TO_RUNTIME_VERSION,
        "parallel_runtime_anchor": PARALLEL_RUNTIME_ANCHOR,
        "parallel_runtime_anchor_sha256": file_sha256(
            repo_root / PARALLEL_RUNTIME_ANCHOR
        ),
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
        "base_feature_schema_sha256": file_sha256(
            repo_root / BASE_FEATURE_SCHEMA
        ),
        "expansion_feature_schema_sha256": file_sha256(
            repo_root / EXPANSION_FEATURE_SCHEMA
        ),
        "decision_schema_sha256": frozen["decision_schema"],
        "base_guardrails_sha256": file_sha256(
            repo_root / BASE_GUARDRAILS
        ),
        "expansion_guardrails_sha256": file_sha256(
            repo_root / EXPANSION_GUARDRAILS
        ),
        "review_gates_sha256": file_sha256(repo_root / REVIEW_GATES),
        "expansion_config_sha256": file_sha256(repo_root / EXPANSION_CONFIG),
        "readiness_evidence_sha256": file_sha256(
            repo_root / READINESS_EVIDENCE
        ),
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
        "cost_policy_fingerprint": cost_policy_fingerprint(
            expansion_guardrails
        ),
        "sync_max_wait_seconds": float(SYNC_MAX_WAIT_SECONDS),
        "sync_poll_interval_seconds": float(SYNC_POLL_INTERVAL_SECONDS),
        "public_exposure_enabled": False,
        "broker_execution_enabled": False,
    }


def build_activation_payload_v1_2(
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
        "expansion_artifacts": artifact_hashes(
            repo_root,
            EXPANSION_ARTIFACT_PATHS,
        ),
    }
    material = {
        **payload,
        "activation_bundle_sha256": None,
        "all_artifact_hashes": all_hashes,
    }
    payload["activation_bundle_sha256"] = hashlib.sha256(
        canonical_json(material).encode("utf-8")
    ).hexdigest()
    validate_activation_payload_v1_2(payload)
    return payload


def validate_activation_payload_v1_2(payload: dict[str, Any]) -> None:
    required = {
        "runtime_version",
        "decision_protocol_version",
        "market",
        "activated_at_utc",
        "repository_commit_sha",
        "activation_bundle_sha256",
        "parallel_to_runtime_version",
        "parallel_runtime_anchor",
        "parallel_runtime_anchor_sha256",
        "gate_counts_carry_forward",
        "backfill_prior_missed",
        "provider",
        "model_id",
        "model_parameter_fingerprint",
        "policy_sha256",
        "feature_definitions_sha256",
        "base_feature_schema_sha256",
        "expansion_feature_schema_sha256",
        "decision_schema_sha256",
        "base_guardrails_sha256",
        "expansion_guardrails_sha256",
        "review_gates_sha256",
        "expansion_config_sha256",
        "readiness_evidence_sha256",
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
        "public_exposure_enabled",
        "broker_execution_enabled",
    }
    if set(payload) != required:
        raise ActivationV12Error("AI-v1.2 activation payload keys mismatch")
    if payload["runtime_version"] != RUNTIME_VERSION:
        raise ActivationV12Error("runtime_version mismatch")
    if payload["decision_protocol_version"] != DECISION_PROTOCOL_VERSION:
        raise ActivationV12Error("decision_protocol_version mismatch")
    if payload["market"] not in MARKETS:
        raise ActivationV12Error("market mismatch")
    if payload["parallel_to_runtime_version"] != PARALLEL_TO_RUNTIME_VERSION:
        raise ActivationV12Error("parallel runtime mismatch")
    if payload["parallel_runtime_anchor"] != PARALLEL_RUNTIME_ANCHOR:
        raise ActivationV12Error("parallel anchor path mismatch")
    if payload["gate_counts_carry_forward"] is not False:
        raise ActivationV12Error("gate count carry-forward forbidden")
    if payload["backfill_prior_missed"] is not False:
        raise ActivationV12Error("backfill forbidden")
    if payload["provider"] != "openai":
        raise ActivationV12Error("provider mismatch")
    if payload["model_id"] != "gpt-5.4-2026-03-05":
        raise ActivationV12Error("model mismatch")
    if payload["sync_max_wait_seconds"] != 30.0:
        raise ActivationV12Error("sync max wait mismatch")
    if payload["sync_poll_interval_seconds"] != 1.0:
        raise ActivationV12Error("sync poll interval mismatch")
    if payload["public_exposure_enabled"] is not False:
        raise ActivationV12Error("public exposure must remain disabled")
    if payload["broker_execution_enabled"] is not False:
        raise ActivationV12Error("broker execution must remain disabled")
    if not _COMMIT_RE.fullmatch(str(payload["repository_commit_sha"])):
        raise ActivationV12Error("invalid repository commit SHA")

    sha_fields = (
        "activation_bundle_sha256",
        "parallel_runtime_anchor_sha256",
        "model_parameter_fingerprint",
        "policy_sha256",
        "feature_definitions_sha256",
        "base_feature_schema_sha256",
        "expansion_feature_schema_sha256",
        "decision_schema_sha256",
        "base_guardrails_sha256",
        "expansion_guardrails_sha256",
        "review_gates_sha256",
        "expansion_config_sha256",
        "readiness_evidence_sha256",
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
            raise ActivationV12Error(f"{key} must be SHA-256 hex")


def preactivation_report_v1_2(repo_root: Path) -> dict[str, Any]:
    require_clean_tracked_worktree(repo_root)
    config = load_expansion_config(repo_root)
    lineage = verify_frozen_decision_lineage(repo_root)
    schema = feature_schema_equivalence_report(repo_root)
    guards = guardrails_equivalence_report(repo_root)
    gates = review_gates_report(repo_root)
    readiness = _validate_readiness_evidence(repo_root)
    parallel = _parallel_anchor(repo_root)

    from trading_signal_intelligence.ai_v1.shadow_runtime_v1_2 import (
        DATABASE_PATHS,
    )

    ledgers = {
        market: (repo_root / DATABASE_PATHS[market]).exists()
        for market in MARKETS
    }
    anchors = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "research" / "forward").glob(
            "AI-v1.2-expansion-activation-*.json"
        )
    )

    artifacts = artifact_hashes(repo_root, EXPANSION_ARTIFACT_PATHS)
    ready = (
        config["status"] == "pre_activation"
        and lineage["match"]
        and schema[
            "equivalent_except_schema_metadata_and_source_symbol_allowlist"
        ]
        and schema["feature_schema_version_preserved"]
        and guards[
            "equivalent_except_status_and_shadow_market_allowlist"
        ]
        and guards["broker_execution_disabled"]
        and gates["valid"]
        and parallel.get("broker_execution_enabled") is False
        and not any(ledgers.values())
        and not anchors
    )
    return {
        "preactivation_check": "PASS" if ready else "FAIL",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "repository_commit_sha": git_commit_sha(repo_root),
        "parallel_to_runtime_version": PARALLEL_TO_RUNTIME_VERSION,
        "parallel_runtime_anchor": PARALLEL_RUNTIME_ANCHOR,
        "parallel_runtime_anchor_sha256": file_sha256(
            repo_root / PARALLEL_RUNTIME_ANCHOR
        ),
        "frozen_decision_artifacts_match_upstream": lineage["match"],
        "feature_schema_compatibility": schema,
        "guardrails_compatibility": guards,
        "review_gates": gates,
        "readiness_evidence": {
            "path": READINESS_EVIDENCE,
            "sha256": file_sha256(repo_root / READINESS_EVIDENCE),
            "status": readiness["status"],
            "observed_at_utc": readiness["observed_at_utc"],
        },
        "expansion_artifact_hashes": artifacts,
        "expansion_ledger_paths_exist": ledgers,
        "expansion_activation_anchors": anchors,
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_write_performed": False,
        "activation_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
    }


def build_activation_anchor_preview_v1_2(
    *,
    repo_root: Path,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    require_clean_tracked_worktree(repo_root)
    payloads = {
        market: build_activation_payload_v1_2(
            repo_root=repo_root,
            market=market,
            activated_at_utc=activated_at_utc,
        )
        for market in MARKETS
    }
    activated = activated_at_utc.astimezone(timezone.utc)
    return {
        "anchor_preview_only": True,
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "activated_at_utc": activated.isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "parallel_to_runtime_version": PARALLEL_TO_RUNTIME_VERSION,
        "parallel_runtime_anchor": PARALLEL_RUNTIME_ANCHOR,
        "parallel_runtime_anchor_sha256": file_sha256(
            repo_root / PARALLEL_RUNTIME_ANCHOR
        ),
        "gate_counts_carry_forward": False,
        "backfill_prior_missed": False,
        "provider_call_made": False,
        "public_exposure_enabled": False,
        "broker_execution_enabled": False,
        "artifact_hashes": artifact_hashes(
            repo_root,
            EXPANSION_ARTIFACT_PATHS,
        ),
        "market_payloads": payloads,
        "ledger_records_created": 0,
        "activation_anchor_written": False,
        "scheduler_changed": False,
    }


def build_activation_anchor_document_v1_2(
    *,
    repo_root: Path,
    activated_at_utc: datetime,
    activation_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    require_clean_tracked_worktree(repo_root)
    expected_payloads = {
        market: build_activation_payload_v1_2(
            repo_root=repo_root,
            market=market,
            activated_at_utc=activated_at_utc,
        )
        for market in MARKETS
    }

    markets: dict[str, dict[str, Any]] = {}
    for market in MARKETS:
        record = activation_records.get(market)
        if not isinstance(record, dict):
            raise ActivationV12Error(f"missing activation record for {market}")
        if record.get("record_type") != "ACTIVATION":
            raise ActivationV12Error(f"{market} record is not ACTIVATION")
        if record.get("payload") != expected_payloads[market]:
            raise ActivationV12Error(
                f"{market} activation payload does not match preview"
            )
        record_hash = str(record.get("record_hash") or "")
        if not _SHA256_RE.fullmatch(record_hash):
            raise ActivationV12Error(
                f"{market} activation record hash invalid"
            )
        markets[market] = {
            "record_hash": record_hash,
            "payload": record["payload"],
        }

    activated = activated_at_utc.astimezone(timezone.utc)
    anchor = {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "status": "ACTIVE_PARALLEL_SHADOW",
        "activated_at_utc": activated.isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "parallel_to_runtime_version": PARALLEL_TO_RUNTIME_VERSION,
        "parallel_runtime_anchor": PARALLEL_RUNTIME_ANCHOR,
        "parallel_runtime_anchor_sha256": file_sha256(
            repo_root / PARALLEL_RUNTIME_ANCHOR
        ),
        "gate_counts_carry_forward": False,
        "backfill_prior_missed": False,
        "provider_call_made": False,
        "public_exposure_enabled": False,
        "broker_execution_enabled": False,
        "artifact_hashes": artifact_hashes(
            repo_root,
            EXPANSION_ARTIFACT_PATHS,
        ),
        "markets": markets,
    }
    validate_activation_anchor_document_v1_2(anchor)
    return anchor


def validate_activation_anchor_document_v1_2(
    anchor: dict[str, Any],
) -> None:
    required = {
        "runtime_version",
        "decision_protocol_version",
        "status",
        "activated_at_utc",
        "repository_commit_sha",
        "parallel_to_runtime_version",
        "parallel_runtime_anchor",
        "parallel_runtime_anchor_sha256",
        "gate_counts_carry_forward",
        "backfill_prior_missed",
        "provider_call_made",
        "public_exposure_enabled",
        "broker_execution_enabled",
        "artifact_hashes",
        "markets",
    }
    if set(anchor) != required:
        raise ActivationV12Error("AI-v1.2 aggregate anchor keys mismatch")
    if anchor["runtime_version"] != RUNTIME_VERSION:
        raise ActivationV12Error("aggregate runtime mismatch")
    if anchor["decision_protocol_version"] != DECISION_PROTOCOL_VERSION:
        raise ActivationV12Error("aggregate decision protocol mismatch")
    if anchor["status"] != "ACTIVE_PARALLEL_SHADOW":
        raise ActivationV12Error("aggregate anchor status mismatch")
    if anchor["parallel_to_runtime_version"] != PARALLEL_TO_RUNTIME_VERSION:
        raise ActivationV12Error("aggregate parallel runtime mismatch")
    if anchor["parallel_runtime_anchor"] != PARALLEL_RUNTIME_ANCHOR:
        raise ActivationV12Error("aggregate parallel anchor mismatch")
    if anchor["gate_counts_carry_forward"] is not False:
        raise ActivationV12Error("aggregate gate carry-forward forbidden")
    if anchor["backfill_prior_missed"] is not False:
        raise ActivationV12Error("aggregate backfill forbidden")
    if anchor["provider_call_made"] is not False:
        raise ActivationV12Error("provider call at activation forbidden")
    if anchor["public_exposure_enabled"] is not False:
        raise ActivationV12Error("public exposure must remain disabled")
    if anchor["broker_execution_enabled"] is not False:
        raise ActivationV12Error("broker execution must remain disabled")
    if not _COMMIT_RE.fullmatch(str(anchor["repository_commit_sha"])):
        raise ActivationV12Error("aggregate repository SHA invalid")
    if not _SHA256_RE.fullmatch(
        str(anchor["parallel_runtime_anchor_sha256"])
    ):
        raise ActivationV12Error("parallel anchor SHA invalid")

    markets = anchor.get("markets")
    if not isinstance(markets, dict) or set(markets) != set(MARKETS):
        raise ActivationV12Error("aggregate markets mismatch")
    for market in MARKETS:
        item = markets[market]
        if not isinstance(item, dict):
            raise ActivationV12Error(f"{market} anchor item invalid")
        if set(item) != {"record_hash", "payload"}:
            raise ActivationV12Error(f"{market} anchor item keys mismatch")
        if not _SHA256_RE.fullmatch(str(item["record_hash"])):
            raise ActivationV12Error(f"{market} anchor record hash invalid")
        payload = item["payload"]
        if not isinstance(payload, dict):
            raise ActivationV12Error(f"{market} payload invalid")
        validate_activation_payload_v1_2(payload)
        if payload["market"] != market:
            raise ActivationV12Error(f"{market} payload market mismatch")
