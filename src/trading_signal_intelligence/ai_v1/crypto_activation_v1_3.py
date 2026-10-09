from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    artifact_hashes,
    file_sha256,
    git_commit_sha,
    require_clean_tracked_worktree,
    verify_frozen_decision_lineage,
)
from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    canonical_policy_sha256,
    load_crypto_cost_policy,
)
from trading_signal_intelligence.ai_v1.features import canonical_json
from trading_signal_intelligence.ai_v1.inference import parameter_fingerprint

RUNTIME_VERSION = "AI-v1.3"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
PROGRAM_ID = "crypto-expansion-1"
SOURCE_NAME = "binance_spot"
MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DATABASE_PATHS = {
    "BTCUSDT": "data/ai_v1_3_btcusdt.sqlite",
    "ETHUSDT": "data/ai_v1_3_ethusdt.sqlite",
    "SOLUSDT": "data/ai_v1_3_solusdt.sqlite",
}
CANONICAL_SYMBOLS = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
}

EXPANSION_CONFIG = "config/ai_v1_3_crypto_expansion.json"
FEATURE_SCHEMA = "config/ai_v1_3_crypto_feature_schema.json"
GUARDRAILS = "config/ai_v1_3_crypto_guardrails.json"
COST_POLICY = "config/ai_v1_3_crypto_cost_policy.json"
REVIEW_GATES = "config/ai_v1_3_crypto_review_gates.json"
K1_EVIDENCE = (
    "research/forward/AI-v1.3-crypto-K1-readiness-2026-10-08T220416Z.json"
)
CORE_ANCHOR = "research/forward/AI-v1.1-activation-2026-09-30T114412Z.json"
EXPANSION_ANCHOR = (
    "research/forward/AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
)

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CryptoPackageV13Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CryptoMarketSpec:
    source_symbol: str
    canonical_symbol: str
    database_path: Path


ARTIFACT_PATHS = {
    "expansion_config": EXPANSION_CONFIG,
    "feature_schema": FEATURE_SCHEMA,
    "guardrails": GUARDRAILS,
    "cost_policy": COST_POLICY,
    "review_gates": REVIEW_GATES,
    "instrument_registry": "config/instruments.json",
    "provider_config": "config/ai_v1_provider.json",
    "provider_response_schema": "config/ai_v1_openai_response_schema.json",
    "decision_schema": "config/ai_v1_decision_schema.json",
    "policy": "config/ai_v1_policy.txt",
    "k1_readiness_evidence": K1_EVIDENCE,
    "parallel_core_anchor": CORE_ANCHOR,
    "parallel_expansion_anchor": EXPANSION_ANCHOR,
    "preregistration": (
        "research/experiments/"
        "EXP-2026-017-ai-v1.3-crypto-expansion-preregistration.md"
    ),
    "cost_policy_preregistration": (
        "research/experiments/"
        "EXP-2026-018-ai-v1.3-crypto-cost-policy.md"
    ),
    "compatibility_plan": "docs/ai-v1.3-crypto-expansion-compatibility-v0.1.md",
    "activation_plan": "docs/ai-v1.3-crypto-expansion-activation-plan-v0.1.md",
    "feature_source": (
        "src/trading_signal_intelligence/ai_v1/features.py"
    ),
    "decision_contract_source": (
        "src/trading_signal_intelligence/ai_v1/contract.py"
    ),
    "provider_neutral_inference_source": (
        "src/trading_signal_intelligence/ai_v1/inference.py"
    ),
    "openai_adapter_source": (
        "src/trading_signal_intelligence/ai_v1/openai_responses.py"
    ),
    "ai_ledger_source": (
        "src/trading_signal_intelligence/ai_v1/ledger.py"
    ),
    "lifecycle_evaluator_source": (
        "src/trading_signal_intelligence/ai_v1/signals.py"
    ),
    "binance_connector_source": (
        "src/trading_signal_intelligence/connectors/binance.py"
    ),
    "crypto_readiness_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_readiness_v1_3.py"
    ),
    "crypto_cost_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_cost_v1_3.py"
    ),
    "crypto_guard_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_guardrails_v1_3.py"
    ),
    "crypto_engine_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_engine_v1_3.py"
    ),
    "crypto_signal_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_signals_v1_3.py"
    ),
    "crypto_runtime_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_runtime_v1_3.py"
    ),
    "activation_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py"
    ),
    "observability_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_observability_v1_3.py"
    ),
    "runtime_verifier_source": (
        "src/trading_signal_intelligence/ai_v1/crypto_runtime_verifier_v1_3.py"
    ),
    "run_live_script": "scripts/run_ai_v1_3_crypto_live.py",
    "activation_preview_script": "scripts/preview_ai_v1_3_crypto_activation.py",
    "preactivation_verify_script": "scripts/verify_ai_v1_3_crypto_pre_activation.py",
    "activation_script": "scripts/activate_ai_v1_3_crypto.py",
    "runtime_verify_script": "scripts/verify_ai_v1_3_crypto_runtime.py",
    "progress_report_script": "scripts/report_ai_v1_3_crypto_progress.py",
    "task_runner": "scripts/run_ai_v1_3_crypto_shadow_task.cmd",
    "task_installer": "scripts/install_ai_v1_3_crypto_shadow_task.ps1",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CryptoPackageV13Error(f"unable to load JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise CryptoPackageV13Error(f"JSON root must be object: {path}")
    return payload


def provider_identity_v1_3(repo_root: Path) -> dict[str, str]:
    provider_config = _load_json(repo_root / "config" / "ai_v1_provider.json")
    provider_schema = _load_json(
        repo_root / "config" / "ai_v1_openai_response_schema.json"
    )
    provider = str(provider_config.get("provider") or "")
    model_id = str(provider_config.get("model_id") or "")
    if provider != "openai":
        raise CryptoPackageV13Error("provider must remain openai")
    if model_id != "gpt-5.4-2026-03-05":
        raise CryptoPackageV13Error("model_id mismatch")

    schema_sha256 = hashlib.sha256(
        canonical_json(provider_schema).encode("utf-8")
    ).hexdigest()
    parameters = {
        "api": provider_config["api"],
        "endpoint": provider_config["endpoint"],
        "reasoning_effort": provider_config["reasoning_effort"],
        "service_tier": provider_config["service_tier"],
        "store": provider_config["store"],
        "truncation": provider_config["truncation"],
        "max_output_tokens": provider_config["max_output_tokens"],
        "tools": provider_config["tools"],
        "temperature": provider_config["temperature"],
        "top_p": provider_config["top_p"],
        "conversation": provider_config["conversation"],
        "previous_response_id": provider_config["previous_response_id"],
        "structured_output_name": provider_config["structured_output_name"],
        "provider_response_schema_sha256": schema_sha256,
    }
    return {
        "provider": provider,
        "model_id": model_id,
        "model_parameter_fingerprint": parameter_fingerprint(
            provider=provider,
            model_id=model_id,
            parameters=parameters,
        ),
    }


def load_crypto_config(repo_root: Path) -> dict[str, Any]:
    config = _load_json(repo_root / EXPANSION_CONFIG)
    if config.get("runtime_version") != RUNTIME_VERSION:
        raise CryptoPackageV13Error("crypto runtime version mismatch")
    if config.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise CryptoPackageV13Error("crypto decision protocol mismatch")
    if config.get("program_id") != PROGRAM_ID:
        raise CryptoPackageV13Error("crypto program_id mismatch")
    if config.get("status") != "package_complete_preactivation":
        raise CryptoPackageV13Error("crypto package status mismatch")
    if config.get("primary_source_name") != SOURCE_NAME:
        raise CryptoPackageV13Error("crypto source mismatch")
    if config.get("no_backfill") is not True:
        raise CryptoPackageV13Error("crypto no_backfill must remain true")
    if config.get("public_signal_exposure_enabled") is not False:
        raise CryptoPackageV13Error("crypto public signal exposure must be disabled")
    if config.get("broker_execution_enabled") is not False:
        raise CryptoPackageV13Error("crypto broker execution must be disabled")
    if config.get("activation_authority") is not False:
        raise CryptoPackageV13Error("crypto activation authority must remain false")
    if int(config.get("scheduler_target_minute")) != 4:
        raise CryptoPackageV13Error("crypto scheduler minute must remain 4")
    if config.get("snapshot_batch_freeze_before_provider_calls") is not True:
        raise CryptoPackageV13Error("batch freeze before provider calls is mandatory")

    package = config.get("offline_runtime_package") or {}
    required_complete = (
        "batch_orchestration_complete",
        "all_market_freeze_before_provider_calls",
        "crypto_feature_schema_complete",
        "top_of_book_integration_complete",
        "isolated_runtime_and_ledger_definitions_complete",
        "activation_builder_and_preview_complete",
        "activation_executor_prepared_not_run",
        "runtime_verifier_complete",
        "c1_c2_c3_observability_complete",
        "weekday_weekend_observability_complete",
        "scheduler_runner_prepared_not_installed",
        "scheduler_installer_prepared_not_run",
        "k2_package_publication_required",
    )
    if package.get("status") != "complete_verified":
        raise CryptoPackageV13Error("offline runtime package is not verified complete")
    if any(package.get(key) is not True for key in required_complete):
        raise CryptoPackageV13Error("offline runtime package completion invariant failed")
    if package.get("activation_authority") is not False:
        raise CryptoPackageV13Error("offline package must not grant activation authority")

    listed = config.get("markets")
    if not isinstance(listed, list):
        raise CryptoPackageV13Error("crypto markets must be a list")
    observed = [str(item.get("source_symbol")) for item in listed if isinstance(item, dict)]
    if observed != list(MARKETS):
        raise CryptoPackageV13Error("crypto market set/order mismatch")

    cost = config.get("execution_cost_profile") or {}
    if cost.get("numeric_cost_policy_frozen") is not True:
        raise CryptoPackageV13Error("numeric crypto cost policy must be frozen")
    if cost.get("activation_blocked_until_runtime_cost_integration_verified") is not False:
        raise CryptoPackageV13Error("crypto cost integration must be verified")
    if cost.get("activation_blocked_until_k2_package_publication") is not True:
        raise CryptoPackageV13Error("K2 publication blocker must remain active")
    return config


def crypto_market_specs(repo_root: Path) -> dict[str, CryptoMarketSpec]:
    config = load_crypto_config(repo_root)
    registry = _load_json(repo_root / "config" / "instruments.json")

    registry_by_symbol: dict[str, tuple[str, str]] = {}
    for instrument in registry.get("instruments", []):
        if not isinstance(instrument, dict):
            continue
        source = instrument.get("sources", {}).get(SOURCE_NAME)
        if not isinstance(source, dict):
            continue
        symbol = str(source.get("symbol") or "")
        status = str(source.get("status") or "")
        if symbol:
            registry_by_symbol[symbol] = (
                str(instrument.get("canonical")),
                status,
            )

    config_by_symbol = {
        str(item["source_symbol"]): item for item in config["markets"]
    }
    specs: dict[str, CryptoMarketSpec] = {}
    for symbol in MARKETS:
        expected_canonical = CANONICAL_SYMBOLS[symbol]
        item = registry_by_symbol.get(symbol)
        if item is None:
            raise CryptoPackageV13Error(f"{symbol} missing from instrument registry")
        canonical, status = item
        if canonical != expected_canonical:
            raise CryptoPackageV13Error(f"{symbol} canonical mapping mismatch")
        if status != "primary":
            raise CryptoPackageV13Error(f"{symbol} Binance status must remain primary")
        if config_by_symbol[symbol].get("canonical_symbol") != expected_canonical:
            raise CryptoPackageV13Error(f"{symbol} config canonical mismatch")
        specs[symbol] = CryptoMarketSpec(
            source_symbol=symbol,
            canonical_symbol=expected_canonical,
            database_path=repo_root / DATABASE_PATHS[symbol],
        )
    return specs


def validate_crypto_feature_schema(repo_root: Path) -> dict[str, Any]:
    schema = _load_json(repo_root / FEATURE_SCHEMA)
    props = schema.get("properties") or {}
    valid = (
        schema.get("additionalProperties") is False
        and props.get("feature_schema_version", {}).get("const") == "AI-crypto-v1.0"
        and props.get("source_symbol", {}).get("enum") == list(MARKETS)
        and props.get("canonical_symbol", {}).get("enum")
        == [CANONICAL_SYMBOLS[symbol] for symbol in MARKETS]
        and "spread_price" in schema.get("required", [])
        and "spread_atr_fraction" in schema.get("required", [])
    )
    if not valid:
        raise CryptoPackageV13Error("crypto feature schema validation failed")
    return {
        "valid": True,
        "feature_schema_version": "AI-crypto-v1.0",
        "source_symbols": list(MARKETS),
    }


def validate_crypto_guardrails(repo_root: Path) -> dict[str, Any]:
    guardrails = _load_json(repo_root / GUARDRAILS)
    valid = (
        guardrails.get("protocol_version") == DECISION_PROTOCOL_VERSION
        and guardrails.get("runtime_version") == RUNTIME_VERSION
        and guardrails.get("status") == "frozen_preactivation_crypto"
        and guardrails.get("shadow_markets") == list(MARKETS)
        and guardrails.get("cadence") == "each_completed_h1_bar_24x7"
        and float(guardrails.get("max_data_age_seconds")) == 300.0
        and float(guardrails.get("max_round_trip_cost_r")) == 0.15
        and guardrails.get("top_of_book_required") is True
        and guardrails.get("top_of_book_source") == SOURCE_NAME
        and guardrails.get("cost_policy_path") == COST_POLICY
        and guardrails.get("public_signal_exposure_enabled") is False
        and guardrails.get("broker_execution_enabled") is False
    )
    if not valid:
        raise CryptoPackageV13Error("crypto guardrail validation failed")
    return {"valid": True, "max_round_trip_cost_r": 0.15}


def validate_review_gates(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / REVIEW_GATES)
    expected = {
        "C1": {
            "purpose": "operational_audit_only",
            "valid_inferences": 100,
            "completed_shadow_trades": 20,
            "minimum_calendar_days": 0,
        },
        "C2": {
            "purpose": "interim_crypto_economic_review",
            "valid_inferences": 500,
            "completed_shadow_trades": 50,
            "minimum_calendar_days": 60,
        },
        "C3": {
            "purpose": "first_crypto_publishability_graduation_decision",
            "valid_inferences": 1000,
            "completed_shadow_trades": 100,
            "minimum_calendar_days": 120,
        },
    }
    valid = (
        payload.get("runtime_version") == RUNTIME_VERSION
        and payload.get("decision_protocol_version") == DECISION_PROTOCOL_VERSION
        and payload.get("program_id") == PROGRAM_ID
        and payload.get("markets") == list(MARKETS)
        and payload.get("gates") == expected
        and payload.get("per_market_reporting_required") is True
        and payload.get("weekday_weekend_reporting_required") is True
        and payload.get("gate_counts_may_not_pool_with_ai_v1_1") is True
        and payload.get("gate_counts_may_not_pool_with_ai_v1_2_1") is True
        and payload.get("calendar_may_not_carry_forward_from_other_lineages") is True
        and payload.get("gate_results_do_not_authorize_public_signal_exposure") is True
        and payload.get("gate_results_do_not_authorize_broker_execution") is True
    )
    if not valid:
        raise CryptoPackageV13Error("crypto review gates validation failed")
    return {"valid": True, "gates": expected}


def validate_k1_evidence(repo_root: Path) -> dict[str, Any]:
    evidence = _load_json(repo_root / K1_EVIDENCE)
    markets = evidence.get("markets")
    valid = (
        evidence.get("status") == "PASS"
        and evidence.get("runtime_version") == RUNTIME_VERSION
        and evidence.get("decision_protocol_version") == DECISION_PROTOCOL_VERSION
        and evidence.get("program_id") == PROGRAM_ID
        and evidence.get("source") == SOURCE_NAME
        and evidence.get("common_source_bar_close_utc") == "2026-10-08T22:00:00Z"
        and float(evidence.get("completed_h1_age_seconds")) <= 300.0
        and isinstance(markets, dict)
        and set(markets) == set(MARKETS)
        and all(markets[symbol].get("readiness") == "READY" for symbol in MARKETS)
        and evidence.get("safety", {}).get(
            "governed_existing_ledgers_byte_identical_before_after"
        )
        is True
        and evidence.get("safety", {}).get("openai_provider_call_made") is False
        and evidence.get("safety", {}).get("ledger_write_performed") is False
        and evidence.get("safety", {}).get("scheduler_definitions_unchanged") is True
        and evidence.get("safety", {}).get("broker_execution_enabled") is False
    )
    if not valid:
        raise CryptoPackageV13Error("K1 readiness evidence validation failed")
    return {
        "valid": True,
        "path": K1_EVIDENCE,
        "sha256": file_sha256(repo_root / K1_EVIDENCE),
        "batch_frozen_at_utc": evidence["batch_frozen_at_utc"],
    }


def _load_anchor_safety(repo_root: Path, relative: str) -> dict[str, Any]:
    anchor = _load_json(repo_root / relative)
    if anchor.get("broker_execution_enabled") is not False:
        raise CryptoPackageV13Error(f"parallel anchor enables broker execution: {relative}")
    return anchor


def preactivation_report_v1_3(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    require_clean_tracked_worktree(repo_root)
    config = load_crypto_config(repo_root)
    specs = crypto_market_specs(repo_root)
    schema = validate_crypto_feature_schema(repo_root)
    guards = validate_crypto_guardrails(repo_root)
    gates = validate_review_gates(repo_root)
    k1 = validate_k1_evidence(repo_root)
    cost_policy = load_crypto_cost_policy(repo_root / COST_POLICY)
    cost_policy_hash = canonical_policy_sha256(cost_policy)
    provider_identity = provider_identity_v1_3(repo_root)
    lineage = verify_frozen_decision_lineage(repo_root)
    core_anchor = _load_anchor_safety(repo_root, CORE_ANCHOR)
    expansion_anchor = _load_anchor_safety(repo_root, EXPANSION_ANCHOR)

    ledgers = {
        symbol: specs[symbol].database_path.exists() for symbol in MARKETS
    }
    anchors = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "research" / "forward").glob(
            "AI-v1.3-crypto-expansion-activation-*.json"
        )
    )
    artifact_hashes_now = artifact_hashes(repo_root, ARTIFACT_PATHS)

    ready = (
        lineage["match"]
        and core_anchor.get("broker_execution_enabled") is False
        and expansion_anchor.get("broker_execution_enabled") is False
        and expansion_anchor.get("runtime_version") == "AI-v1.2.1"
        and not any(ledgers.values())
        and not anchors
        and config.get("activation_authority") is False
    )
    return {
        "preactivation_check": "PASS" if ready else "FAIL",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "program_id": PROGRAM_ID,
        "repository_commit_sha": git_commit_sha(repo_root),
        "markets": {
            symbol: {
                "canonical_symbol": specs[symbol].canonical_symbol,
                "database_path": DATABASE_PATHS[symbol],
            }
            for symbol in MARKETS
        },
        "feature_schema": schema,
        "guardrails": guards,
        "review_gates": gates,
        "k1_readiness": k1,
        "cost_policy_sha256": cost_policy_hash,
        "provider_identity": provider_identity,
        "frozen_ai_v1_0_decision_lineage_match": lineage["match"],
        "parallel_core_anchor": CORE_ANCHOR,
        "parallel_core_anchor_sha256": file_sha256(repo_root / CORE_ANCHOR),
        "parallel_expansion_anchor": EXPANSION_ANCHOR,
        "parallel_expansion_anchor_sha256": file_sha256(
            repo_root / EXPANSION_ANCHOR
        ),
        "artifact_hashes": artifact_hashes_now,
        "crypto_ledger_paths_exist": ledgers,
        "crypto_activation_anchors": anchors,
        "provider_call_made": False,
        "binance_call_made": False,
        "ledger_write_performed": False,
        "activation_performed": False,
        "scheduler_changed": False,
        "public_signal_exposure_changed": False,
        "broker_execution_enabled": False,
    }


def build_activation_payload_v1_3(
    *,
    repo_root: Path,
    market: str,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    if market not in MARKETS:
        raise CryptoPackageV13Error(f"unsupported crypto market: {market}")
    if activated_at_utc.tzinfo is None:
        raise CryptoPackageV13Error("activation timestamp must be timezone-aware")
    report = preactivation_report_v1_3(repo_root)
    if report["preactivation_check"] != "PASS":
        raise CryptoPackageV13Error("AI-v1.3 preactivation report is not PASS")

    activated = activated_at_utc.astimezone(UTC)
    payload = {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "program_id": PROGRAM_ID,
        "market": market,
        "canonical_symbol": CANONICAL_SYMBOLS[market],
        "activated_at_utc": activated.isoformat(),
        "repository_commit_sha": report["repository_commit_sha"],
        "source": SOURCE_NAME,
        "feature_schema_version": "AI-crypto-v1.0",
        "feature_schema_sha256": file_sha256(repo_root / FEATURE_SCHEMA),
        "guardrails_sha256": file_sha256(repo_root / GUARDRAILS),
        "cost_policy_sha256": report["cost_policy_sha256"],
        "review_gates_sha256": file_sha256(repo_root / REVIEW_GATES),
        "expansion_config_sha256": file_sha256(repo_root / EXPANSION_CONFIG),
        "k1_readiness_sha256": report["k1_readiness"]["sha256"],
        "provider": report["provider_identity"]["provider"],
        "model_id": report["provider_identity"]["model_id"],
        "model_parameter_fingerprint": report["provider_identity"][
            "model_parameter_fingerprint"
        ],
        "provider_config_sha256": file_sha256(
            repo_root / "config/ai_v1_provider.json"
        ),
        "policy_sha256": file_sha256(repo_root / "config/ai_v1_policy.txt"),
        "decision_schema_sha256": file_sha256(
            repo_root / "config/ai_v1_decision_schema.json"
        ),
        "artifact_hashes": report["artifact_hashes"],
        "no_backfill": True,
        "gate_counts_carry_forward": False,
        "calendar_carry_forward": False,
        "snapshot_batch_freeze_before_provider_calls": True,
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
        "provider_call_made_at_activation": False,
        "binance_call_made_at_activation": False,
    }
    material = {**payload, "activation_bundle_sha256": None}
    payload["activation_bundle_sha256"] = hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    validate_activation_payload_v1_3(payload)
    return payload


def validate_activation_payload_v1_3(payload: dict[str, Any]) -> None:
    required = {
        "runtime_version",
        "decision_protocol_version",
        "program_id",
        "market",
        "canonical_symbol",
        "activated_at_utc",
        "repository_commit_sha",
        "source",
        "feature_schema_version",
        "feature_schema_sha256",
        "guardrails_sha256",
        "cost_policy_sha256",
        "review_gates_sha256",
        "expansion_config_sha256",
        "k1_readiness_sha256",
        "provider",
        "model_id",
        "model_parameter_fingerprint",
        "provider_config_sha256",
        "policy_sha256",
        "decision_schema_sha256",
        "artifact_hashes",
        "no_backfill",
        "gate_counts_carry_forward",
        "calendar_carry_forward",
        "snapshot_batch_freeze_before_provider_calls",
        "public_signal_exposure_enabled",
        "broker_execution_enabled",
        "provider_call_made_at_activation",
        "binance_call_made_at_activation",
        "activation_bundle_sha256",
    }
    if set(payload) != required:
        raise CryptoPackageV13Error("AI-v1.3 activation payload keys mismatch")
    if payload["runtime_version"] != RUNTIME_VERSION:
        raise CryptoPackageV13Error("activation runtime mismatch")
    if payload["decision_protocol_version"] != DECISION_PROTOCOL_VERSION:
        raise CryptoPackageV13Error("activation protocol mismatch")
    if payload["program_id"] != PROGRAM_ID:
        raise CryptoPackageV13Error("activation program mismatch")
    market = str(payload["market"])
    if market not in MARKETS:
        raise CryptoPackageV13Error("activation market mismatch")
    if payload["canonical_symbol"] != CANONICAL_SYMBOLS[market]:
        raise CryptoPackageV13Error("activation canonical symbol mismatch")
    if payload["source"] != SOURCE_NAME:
        raise CryptoPackageV13Error("activation source mismatch")
    if payload["feature_schema_version"] != "AI-crypto-v1.0":
        raise CryptoPackageV13Error("activation feature schema mismatch")
    if payload["provider"] != "openai":
        raise CryptoPackageV13Error("activation provider mismatch")
    if payload["model_id"] != "gpt-5.4-2026-03-05":
        raise CryptoPackageV13Error("activation model mismatch")
    if payload["no_backfill"] is not True:
        raise CryptoPackageV13Error("activation no_backfill must be true")
    if payload["gate_counts_carry_forward"] is not False:
        raise CryptoPackageV13Error("activation gate carry-forward forbidden")
    if payload["calendar_carry_forward"] is not False:
        raise CryptoPackageV13Error("activation calendar carry-forward forbidden")
    if payload["snapshot_batch_freeze_before_provider_calls"] is not True:
        raise CryptoPackageV13Error("activation batch-freeze rule mismatch")
    if payload["public_signal_exposure_enabled"] is not False:
        raise CryptoPackageV13Error("activation public exposure must be disabled")
    if payload["broker_execution_enabled"] is not False:
        raise CryptoPackageV13Error("activation broker execution must be disabled")
    if payload["provider_call_made_at_activation"] is not False:
        raise CryptoPackageV13Error("provider call at activation forbidden")
    if payload["binance_call_made_at_activation"] is not False:
        raise CryptoPackageV13Error("Binance call at activation forbidden")
    if not _COMMIT_RE.fullmatch(str(payload["repository_commit_sha"])):
        raise CryptoPackageV13Error("activation repository SHA invalid")

    for key in (
        "feature_schema_sha256",
        "guardrails_sha256",
        "cost_policy_sha256",
        "review_gates_sha256",
        "expansion_config_sha256",
        "k1_readiness_sha256",
        "model_parameter_fingerprint",
        "provider_config_sha256",
        "policy_sha256",
        "decision_schema_sha256",
        "activation_bundle_sha256",
    ):
        if not _SHA256_RE.fullmatch(str(payload[key])):
            raise CryptoPackageV13Error(f"{key} must be SHA-256 hex")

    hashes = payload.get("artifact_hashes")
    if not isinstance(hashes, dict) or set(hashes) != set(ARTIFACT_PATHS):
        raise CryptoPackageV13Error("activation artifact hash set mismatch")
    if any(not _SHA256_RE.fullmatch(str(value)) for value in hashes.values()):
        raise CryptoPackageV13Error("activation artifact hash invalid")


def build_activation_anchor_preview_v1_3(
    *,
    repo_root: Path,
    activated_at_utc: datetime,
) -> dict[str, Any]:
    report = preactivation_report_v1_3(repo_root)
    payloads = {
        symbol: build_activation_payload_v1_3(
            repo_root=repo_root,
            market=symbol,
            activated_at_utc=activated_at_utc,
        )
        for symbol in MARKETS
    }
    return {
        "anchor_preview_only": True,
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "program_id": PROGRAM_ID,
        "activated_at_utc": activated_at_utc.astimezone(UTC).isoformat(),
        "repository_commit_sha": report["repository_commit_sha"],
        "artifact_hashes": report["artifact_hashes"],
        "market_payloads": payloads,
        "ledger_records_created": 0,
        "activation_anchor_written": False,
        "provider_call_made": False,
        "binance_call_made": False,
        "scheduler_changed": False,
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
    }


def build_activation_anchor_document_v1_3(
    *,
    repo_root: Path,
    activated_at_utc: datetime,
    activation_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    expected = {
        symbol: build_activation_payload_v1_3(
            repo_root=repo_root,
            market=symbol,
            activated_at_utc=activated_at_utc,
        )
        for symbol in MARKETS
    }
    markets: dict[str, dict[str, Any]] = {}
    for symbol in MARKETS:
        record = activation_records.get(symbol)
        if not isinstance(record, dict):
            raise CryptoPackageV13Error(f"missing activation record for {symbol}")
        if record.get("record_type") != "ACTIVATION":
            raise CryptoPackageV13Error(f"{symbol} activation record type mismatch")
        if record.get("payload") != expected[symbol]:
            raise CryptoPackageV13Error(f"{symbol} activation payload mismatch")
        record_hash = str(record.get("record_hash") or "")
        if not _SHA256_RE.fullmatch(record_hash):
            raise CryptoPackageV13Error(f"{symbol} activation record hash invalid")
        markets[symbol] = {
            "record_hash": record_hash,
            "payload": record["payload"],
        }

    anchor = {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "program_id": PROGRAM_ID,
        "status": "ACTIVE_PARALLEL_SHADOW",
        "activated_at_utc": activated_at_utc.astimezone(UTC).isoformat(),
        "repository_commit_sha": git_commit_sha(repo_root),
        "source": SOURCE_NAME,
        "gate_counts_carry_forward": False,
        "calendar_carry_forward": False,
        "backfill_prior_missed": False,
        "provider_call_made": False,
        "binance_call_made_at_activation": False,
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
        "artifact_hashes": artifact_hashes(repo_root, ARTIFACT_PATHS),
        "markets": markets,
    }
    validate_activation_anchor_document_v1_3(anchor)
    return anchor


def validate_activation_anchor_document_v1_3(anchor: dict[str, Any]) -> None:
    required = {
        "runtime_version",
        "decision_protocol_version",
        "program_id",
        "status",
        "activated_at_utc",
        "repository_commit_sha",
        "source",
        "gate_counts_carry_forward",
        "calendar_carry_forward",
        "backfill_prior_missed",
        "provider_call_made",
        "binance_call_made_at_activation",
        "public_signal_exposure_enabled",
        "broker_execution_enabled",
        "artifact_hashes",
        "markets",
    }
    if set(anchor) != required:
        raise CryptoPackageV13Error("AI-v1.3 activation anchor keys mismatch")
    if anchor["runtime_version"] != RUNTIME_VERSION:
        raise CryptoPackageV13Error("anchor runtime mismatch")
    if anchor["decision_protocol_version"] != DECISION_PROTOCOL_VERSION:
        raise CryptoPackageV13Error("anchor protocol mismatch")
    if anchor["program_id"] != PROGRAM_ID:
        raise CryptoPackageV13Error("anchor program mismatch")
    if anchor["status"] != "ACTIVE_PARALLEL_SHADOW":
        raise CryptoPackageV13Error("anchor status mismatch")
    if anchor["source"] != SOURCE_NAME:
        raise CryptoPackageV13Error("anchor source mismatch")
    for key in (
        "gate_counts_carry_forward",
        "calendar_carry_forward",
        "backfill_prior_missed",
        "provider_call_made",
        "binance_call_made_at_activation",
        "public_signal_exposure_enabled",
        "broker_execution_enabled",
    ):
        expected = key == "backfill_prior_missed"
        if expected:
            if anchor[key] is not False:
                raise CryptoPackageV13Error(f"anchor {key} must be false")
        elif anchor[key] is not False:
            raise CryptoPackageV13Error(f"anchor {key} must be false")
    if not _COMMIT_RE.fullmatch(str(anchor["repository_commit_sha"])):
        raise CryptoPackageV13Error("anchor repository SHA invalid")

    hashes = anchor.get("artifact_hashes")
    if not isinstance(hashes, dict) or set(hashes) != set(ARTIFACT_PATHS):
        raise CryptoPackageV13Error("anchor artifact hash set mismatch")

    markets = anchor.get("markets")
    if not isinstance(markets, dict) or set(markets) != set(MARKETS):
        raise CryptoPackageV13Error("anchor market set mismatch")
    for symbol in MARKETS:
        item = markets[symbol]
        if not isinstance(item, dict) or set(item) != {"record_hash", "payload"}:
            raise CryptoPackageV13Error(f"{symbol} anchor item invalid")
        if not _SHA256_RE.fullmatch(str(item["record_hash"])):
            raise CryptoPackageV13Error(f"{symbol} anchor record hash invalid")
        if not isinstance(item["payload"], dict):
            raise CryptoPackageV13Error(f"{symbol} activation payload invalid")
        validate_activation_payload_v1_3(item["payload"])
        if item["payload"]["market"] != symbol:
            raise CryptoPackageV13Error(f"{symbol} activation market mismatch")
