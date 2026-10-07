from __future__ import annotations

import copy
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    verify_frozen_decision_lineage,
)
from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    SYNC_MAX_WAIT_SECONDS,
    SYNC_POLL_INTERVAL_SECONDS,
)


RUNTIME_VERSION = "AI-v1.2.1"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
PREDECESSOR_RUNTIME_VERSION = "AI-v1.2"
SOURCE_NAME = "exness_mt5_demo"
MARKETS = ("EURUSD", "XAGUSD", "USOIL")

DATABASE_PATHS = {
    "EURUSD": "data/ai_v1_2_1_eurusd.sqlite",
    "XAGUSD": "data/ai_v1_2_1_xagusd.sqlite",
    "USOIL": "data/ai_v1_2_1_usoil.sqlite",
}

PREDECESSOR_DATABASE_PATHS = {
    "EURUSD": "data/ai_v1_2_eurusd.sqlite",
    "XAGUSD": "data/ai_v1_2_xagusd.sqlite",
    "USOIL": "data/ai_v1_2_usoil.sqlite",
}

EXPANSION_CONFIG = "config/ai_v1_2_1_expansion.json"
EXPANSION_FEATURE_SCHEMA = "config/ai_v1_2_feature_schema.json"
BASE_FEATURE_SCHEMA = "config/ai_v1_feature_schema.json"
EXPANSION_GUARDRAILS = "config/ai_v1_2_1_guardrails.json"
BASE_GUARDRAILS = "config/ai_v1_guardrails.json"
REVIEW_GATES = "config/ai_v1_2_1_review_gates.json"
PREDECESSOR_FAILURE_EVIDENCE = (
    "research/forward/AI-v1.2-P2-fail-closed-2026-10-06T220043Z.json"
)
PREDECESSOR_ACTIVATION_ANCHOR = (
    "research/forward/AI-v1.2-expansion-activation-2026-10-06T200633Z.json"
)

EXPECTED_MARKETS = {
    "EURUSD": {
        "canonical_symbol": "EUR/USD",
        "asset_class": "forex",
        "digits": 5,
    },
    "XAGUSD": {
        "canonical_symbol": "XAG/USD",
        "asset_class": "metal",
        "digits": 3,
    },
    "USOIL": {
        "canonical_symbol": "WTI",
        "asset_class": "energy",
        "digits": 3,
    },
}


class ExpansionV121Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ExpansionMarketSpecV121:
    source_symbol: str
    canonical_symbol: str
    asset_class: str
    digits: int
    point_size: float
    database_path: Path


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExpansionV121Error(f"unable to load JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ExpansionV121Error(f"JSON root must be an object: {path}")
    return payload


def _git_commit_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ExpansionV121Error("unable to resolve repository HEAD") from exc


def _require_clean_tracked_worktree(repo_root: Path) -> None:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ExpansionV121Error("unable to inspect repository worktree") from exc
    if output.strip():
        raise ExpansionV121Error(
            "tracked worktree is dirty; AI-v1.2.1 preactivation proof requires "
            "an exact committed state"
        )


def load_expansion_config_v1_2_1(repo_root: Path) -> dict[str, Any]:
    config = _load_json(repo_root / EXPANSION_CONFIG)
    if config.get("runtime_version") != RUNTIME_VERSION:
        raise ExpansionV121Error("expansion runtime_version mismatch")
    if config.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ExpansionV121Error("decision protocol mismatch")
    if config.get("status") != "pre_activation_correction":
        raise ExpansionV121Error(
            "AI-v1.2.1 config must remain pre_activation_correction"
        )
    if config.get("source_name") != SOURCE_NAME:
        raise ExpansionV121Error("expansion source_name mismatch")
    if config.get("predecessor_runtime_version") != PREDECESSOR_RUNTIME_VERSION:
        raise ExpansionV121Error("predecessor runtime mismatch")
    if config.get("predecessor_failure_evidence_path") != PREDECESSOR_FAILURE_EVIDENCE:
        raise ExpansionV121Error("predecessor failure evidence path mismatch")
    if config.get("predecessor_evidence_carry_forward") is not False:
        raise ExpansionV121Error("predecessor evidence carry-forward forbidden")
    if config.get("calendar_carry_forward") is not False:
        raise ExpansionV121Error("predecessor calendar carry-forward forbidden")
    if config.get("broker_execution_enabled") is not False:
        raise ExpansionV121Error("broker execution must remain disabled")
    if config.get("public_exposure_enabled") is not False:
        raise ExpansionV121Error("public exposure must remain disabled")
    if config.get("no_backfill") is not True:
        raise ExpansionV121Error("no_backfill must be true")
    if config.get("shares_gate_counts_with_ai_v1_1") is not False:
        raise ExpansionV121Error("AI-v1.1 gate-count pooling is forbidden")
    if config.get("guardrails_path") != EXPANSION_GUARDRAILS:
        raise ExpansionV121Error("expansion guardrails path mismatch")
    if config.get("review_gates_path") != REVIEW_GATES:
        raise ExpansionV121Error("expansion review-gates path mismatch")
    if float(config.get("sync_max_wait_seconds")) != float(
        SYNC_MAX_WAIT_SECONDS
    ):
        raise ExpansionV121Error("sync max-wait differs from frozen value")
    if float(config.get("sync_poll_interval_seconds")) != float(
        SYNC_POLL_INTERVAL_SECONDS
    ):
        raise ExpansionV121Error("sync poll interval differs from frozen value")
    if int(config.get("scheduler_target_minute")) != 3:
        raise ExpansionV121Error("scheduler target minute must remain 3")
    if config.get("scheduler_cadence") != "hourly_near_completed_h1_boundary":
        raise ExpansionV121Error("scheduler cadence mismatch")
    if int(config.get("scheduler_parallel_offset_from_ai_v1_1_minutes")) != 1:
        raise ExpansionV121Error("scheduler offset mismatch")

    listed = config.get("markets")
    if not isinstance(listed, list):
        raise ExpansionV121Error("markets must be a list")
    observed = {
        str(item.get("source_symbol")): item
        for item in listed
        if isinstance(item, dict)
    }
    if set(observed) != set(MARKETS):
        raise ExpansionV121Error("expansion market set mismatch")
    for symbol, expected in EXPECTED_MARKETS.items():
        for key, value in expected.items():
            if observed[symbol].get(key) != value:
                raise ExpansionV121Error(
                    f"{symbol} expansion config {key} mismatch"
                )
    return config


def expansion_market_specs_v1_2_1(
    repo_root: Path,
) -> dict[str, ExpansionMarketSpecV121]:
    config = load_expansion_config_v1_2_1(repo_root)
    registry = _load_json(repo_root / "config" / "instruments.json")

    registry_by_symbol: dict[str, dict[str, Any]] = {}
    for instrument in registry.get("instruments", []):
        if not isinstance(instrument, dict):
            continue
        source = instrument.get("sources", {}).get(SOURCE_NAME)
        if not isinstance(source, dict):
            continue
        symbol = str(source.get("symbol") or "")
        if symbol:
            registry_by_symbol[symbol] = {
                "canonical_symbol": instrument.get("canonical"),
                "asset_class": instrument.get("asset_class"),
                "status": source.get("status"),
                "digits": source.get("digits"),
            }

    config_by_symbol = {
        str(item["source_symbol"]): item for item in config["markets"]
    }
    specs: dict[str, ExpansionMarketSpecV121] = {}
    for symbol in MARKETS:
        expected = EXPECTED_MARKETS[symbol]
        registry_item = registry_by_symbol.get(symbol)
        if registry_item is None:
            raise ExpansionV121Error(
                f"{symbol} missing from canonical instrument registry"
            )
        if registry_item["status"] != "include":
            raise ExpansionV121Error(f"{symbol} registry status must be include")
        for key in ("canonical_symbol", "asset_class", "digits"):
            if registry_item[key] != expected[key]:
                raise ExpansionV121Error(
                    f"{symbol} registry {key} mismatch"
                )
            if config_by_symbol[symbol][key] != expected[key]:
                raise ExpansionV121Error(
                    f"{symbol} config {key} mismatch"
                )

        digits = int(expected["digits"])
        specs[symbol] = ExpansionMarketSpecV121(
            source_symbol=symbol,
            canonical_symbol=str(expected["canonical_symbol"]),
            asset_class=str(expected["asset_class"]),
            digits=digits,
            point_size=10.0 ** (-digits),
            database_path=repo_root / DATABASE_PATHS[symbol],
        )
    return specs


def feature_schema_equivalence_report_v1_2_1(
    repo_root: Path,
) -> dict[str, Any]:
    base = _load_json(repo_root / BASE_FEATURE_SCHEMA)
    expansion = _load_json(repo_root / EXPANSION_FEATURE_SCHEMA)
    base_symbol_enum = (
        base.get("properties", {}).get("source_symbol", {}).get("enum")
    )
    expansion_symbol_enum = (
        expansion.get("properties", {}).get("source_symbol", {}).get("enum")
    )
    normalized_base = copy.deepcopy(base)
    normalized_expansion = copy.deepcopy(expansion)
    for payload in (normalized_base, normalized_expansion):
        payload["$id"] = "<schema-id>"
        payload["title"] = "<schema-title>"
        payload["properties"]["source_symbol"]["enum"] = ["<market-set>"]
    return {
        "equivalent_except_schema_metadata_and_source_symbol_allowlist": (
            normalized_base == normalized_expansion
        ),
        "base_source_symbol_enum": base_symbol_enum,
        "expansion_source_symbol_enum": expansion_symbol_enum,
        "feature_schema_version_preserved": (
            expansion["properties"]["feature_schema_version"].get("const")
            == "AI-v1.0"
        ),
        "expected_expansion_symbol_enum": list(MARKETS),
    }


def guardrails_equivalence_report_v1_2_1(
    repo_root: Path,
) -> dict[str, Any]:
    base = _load_json(repo_root / BASE_GUARDRAILS)
    expansion = _load_json(repo_root / EXPANSION_GUARDRAILS)
    normalized_base = copy.deepcopy(base)
    normalized_expansion = copy.deepcopy(expansion)
    normalized_base["status"] = "<status>"
    normalized_expansion["status"] = "<status>"
    normalized_base["shadow_markets"] = ["<market-set>"]
    normalized_expansion["shadow_markets"] = ["<market-set>"]
    return {
        "equivalent_except_status_and_shadow_market_allowlist": (
            normalized_base == normalized_expansion
        ),
        "base_shadow_markets": base.get("shadow_markets"),
        "expansion_shadow_markets": expansion.get("shadow_markets"),
        "expected_expansion_shadow_markets": list(MARKETS),
        "broker_execution_disabled": (
            expansion.get("broker_execution_enabled") is False
        ),
        "protocol_version_preserved": (
            expansion.get("protocol_version") == DECISION_PROTOCOL_VERSION
        ),
    }


def review_gates_report_v1_2_1(repo_root: Path) -> dict[str, Any]:
    payload = _load_json(repo_root / REVIEW_GATES)
    expected = {
        "X1": {
            "purpose": "operational_audit_only",
            "valid_inferences": 100,
            "completed_shadow_trades": 20,
            "minimum_calendar_days": 0,
        },
        "X2": {
            "purpose": "interim_expansion_economic_review",
            "valid_inferences": 500,
            "completed_shadow_trades": 50,
            "minimum_calendar_days": 60,
        },
        "X3": {
            "purpose": "first_expansion_publishability_graduation_decision",
            "valid_inferences": 1000,
            "completed_shadow_trades": 100,
            "minimum_calendar_days": 120,
        },
    }
    valid = (
        payload.get("runtime_version") == RUNTIME_VERSION
        and payload.get("decision_protocol_version")
        == DECISION_PROTOCOL_VERSION
        and payload.get("status") == "frozen_pre_activation_correction"
        and payload.get("markets") == list(MARKETS)
        and payload.get("gates") == expected
        and payload.get("gate_counts_carry_forward") is False
        and payload.get("calendar_carry_forward") is False
        and payload.get("predecessor_runtime_version")
        == PREDECESSOR_RUNTIME_VERSION
        and payload.get("per_market_reporting_required") is True
        and payload.get(
            "weak_or_low_activity_market_may_not_be_hidden_or_dropped_post_activation"
        )
        is True
        and payload.get("gate_results_do_not_authorize_broker_execution")
        is True
        and payload.get("gate_results_do_not_modify_ai_v1_1") is True
    )
    return {
        "valid": valid,
        "gates": payload.get("gates"),
        "per_market_reporting_required": payload.get(
            "per_market_reporting_required"
        ),
        "gate_results_do_not_authorize_broker_execution": payload.get(
            "gate_results_do_not_authorize_broker_execution"
        ),
    }


def predecessor_failure_report_v1_2_1(repo_root: Path) -> dict[str, Any]:
    failure = _load_json(repo_root / PREDECESSOR_FAILURE_EVIDENCE)
    anchor = _load_json(repo_root / PREDECESSOR_ACTIVATION_ANCHOR)
    valid = (
        failure.get("classification") == "FAIL_CLOSED_RUNTIME_WIRING_DEFECT"
        and failure.get("runtime_version") == PREDECESSOR_RUNTIME_VERSION
        and failure.get("overall_exit_code") == 2
        and failure.get("aggregate_after", {}).get("valid_inferences") == 0
        and failure.get("aggregate_after", {}).get("missed_inferences") == 1
        and failure.get("root_cause", {}).get("runtime_lookup")
        == "guardrails_sha256"
        and failure.get("root_cause", {}).get(
            "frozen_activation_payload_field"
        )
        == "expansion_guardrails_sha256"
        and failure.get("governance", {}).get("retry_ai_v1_2_forbidden")
        is True
        and anchor.get("runtime_version") == PREDECESSOR_RUNTIME_VERSION
        and anchor.get("status") == "ACTIVE_PARALLEL_SHADOW"
        and anchor.get("broker_execution_enabled") is False
    )
    return {
        "valid": valid,
        "failure_classification": failure.get("classification"),
        "predecessor_activation_timestamp": anchor.get("activated_at_utc"),
        "predecessor_valid_inferences": failure.get(
            "aggregate_after", {}
        ).get("valid_inferences"),
        "predecessor_missed_inferences": failure.get(
            "aggregate_after", {}
        ).get("missed_inferences"),
    }


def preactivation_report_v1_2_1(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    _require_clean_tracked_worktree(repo_root)
    config = load_expansion_config_v1_2_1(repo_root)
    specs = expansion_market_specs_v1_2_1(repo_root)
    schema = feature_schema_equivalence_report_v1_2_1(repo_root)
    guards = guardrails_equivalence_report_v1_2_1(repo_root)
    gates = review_gates_report_v1_2_1(repo_root)
    predecessor = predecessor_failure_report_v1_2_1(repo_root)
    lineage = verify_frozen_decision_lineage(repo_root)

    successor_ledgers = {
        symbol: specs[symbol].database_path.exists() for symbol in MARKETS
    }
    successor_anchors = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "research" / "forward").glob(
            "AI-v1.2.1-expansion-activation-*.json"
        )
    )

    ready = (
        lineage["match"]
        and schema[
            "equivalent_except_schema_metadata_and_source_symbol_allowlist"
        ]
        and schema["feature_schema_version_preserved"]
        and schema["expansion_source_symbol_enum"] == list(MARKETS)
        and guards[
            "equivalent_except_status_and_shadow_market_allowlist"
        ]
        and guards["expansion_shadow_markets"] == list(MARKETS)
        and guards["broker_execution_disabled"]
        and guards["protocol_version_preserved"]
        and gates["valid"]
        and predecessor["valid"]
        and not any(successor_ledgers.values())
        and not successor_anchors
    )

    return {
        "preactivation_check": "PASS" if ready else "FAIL",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "repository_commit_sha": _git_commit_sha(repo_root),
        "predecessor_runtime_version": PREDECESSOR_RUNTIME_VERSION,
        "predecessor_failure": predecessor,
        "markets": {
            symbol: {
                "canonical_symbol": specs[symbol].canonical_symbol,
                "asset_class": specs[symbol].asset_class,
                "digits": specs[symbol].digits,
                "point_size": specs[symbol].point_size,
                "database_path": DATABASE_PATHS[symbol],
            }
            for symbol in MARKETS
        },
        "frozen_ai_v1_0_decision_lineage_match": lineage["match"],
        "feature_schema_compatibility": schema,
        "guardrails_compatibility": guards,
        "review_gates": gates,
        "feature_formula_change": False,
        "decision_contract_change": False,
        "policy_change": False,
        "guard_numeric_semantics_change": False,
        "market_set_change_from_ai_v1_2": False,
        "runtime_correction_scope": (
            "activation_guard_hash_field_binding_only"
        ),
        "gate_counts_carry_forward": False,
        "calendar_carry_forward": False,
        "backfill_prior_missed": False,
        "sync_max_wait_seconds": float(config["sync_max_wait_seconds"]),
        "sync_poll_interval_seconds": float(
            config["sync_poll_interval_seconds"]
        ),
        "successor_ledger_paths_exist": successor_ledgers,
        "successor_activation_anchors": successor_anchors,
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_write_performed": False,
        "activation_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
    }
