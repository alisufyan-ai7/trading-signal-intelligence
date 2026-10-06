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


RUNTIME_VERSION = "AI-v1.2"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
SOURCE_NAME = "exness_mt5_demo"
MARKETS = ("EURUSD", "XAGUSD", "USOIL")
DATABASE_PATHS = {
    "EURUSD": "data/ai_v1_2_eurusd.sqlite",
    "XAGUSD": "data/ai_v1_2_xagusd.sqlite",
    "USOIL": "data/ai_v1_2_usoil.sqlite",
}
EXPANSION_CONFIG = "config/ai_v1_2_expansion.json"
EXPANSION_FEATURE_SCHEMA = "config/ai_v1_2_feature_schema.json"
BASE_FEATURE_SCHEMA = "config/ai_v1_feature_schema.json"
EXPANSION_GUARDRAILS = "config/ai_v1_2_guardrails.json"
BASE_GUARDRAILS = "config/ai_v1_guardrails.json"
REVIEW_GATES = "config/ai_v1_2_review_gates.json"

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


class ExpansionV12Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ExpansionMarketSpec:
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
        raise ExpansionV12Error(f"unable to load JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ExpansionV12Error(f"JSON root must be an object: {path}")
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
        raise ExpansionV12Error("unable to resolve repository HEAD") from exc


def _require_clean_tracked_worktree(repo_root: Path) -> None:
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ExpansionV12Error("unable to inspect repository worktree") from exc
    if output.strip():
        raise ExpansionV12Error(
            "tracked worktree is dirty; expansion preactivation proof requires "
            "an exact committed state"
        )


def load_expansion_config(repo_root: Path) -> dict[str, Any]:
    config = _load_json(repo_root / EXPANSION_CONFIG)
    if config.get("runtime_version") != RUNTIME_VERSION:
        raise ExpansionV12Error("expansion runtime_version mismatch")
    if config.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ExpansionV12Error("decision protocol mismatch")
    if config.get("status") != "pre_activation":
        raise ExpansionV12Error("expansion config must remain pre_activation")
    if config.get("source_name") != SOURCE_NAME:
        raise ExpansionV12Error("expansion source_name mismatch")
    if config.get("broker_execution_enabled") is not False:
        raise ExpansionV12Error("broker execution must remain disabled")
    if config.get("public_exposure_enabled") is not False:
        raise ExpansionV12Error("public exposure must remain disabled")
    if config.get("no_backfill") is not True:
        raise ExpansionV12Error("no_backfill must be true")
    if config.get("shares_gate_counts_with_ai_v1_1") is not False:
        raise ExpansionV12Error("AI-v1.1 gate-count pooling is forbidden")
    if config.get("guardrails_path") != EXPANSION_GUARDRAILS:
        raise ExpansionV12Error("expansion guardrails path mismatch")
    if config.get("review_gates_path") != REVIEW_GATES:
        raise ExpansionV12Error("expansion review-gates path mismatch")
    if float(config.get("sync_max_wait_seconds")) != float(
        SYNC_MAX_WAIT_SECONDS
    ):
        raise ExpansionV12Error("sync max-wait differs from AI-v1.1")
    if float(config.get("sync_poll_interval_seconds")) != float(
        SYNC_POLL_INTERVAL_SECONDS
    ):
        raise ExpansionV12Error("sync poll interval differs from AI-v1.1")

    listed = config.get("markets")
    if not isinstance(listed, list):
        raise ExpansionV12Error("markets must be a list")
    observed = {
        str(item.get("source_symbol")): item
        for item in listed
        if isinstance(item, dict)
    }
    if set(observed) != set(MARKETS):
        raise ExpansionV12Error("expansion market set mismatch")
    for symbol, expected in EXPECTED_MARKETS.items():
        item = observed[symbol]
        for key, value in expected.items():
            if item.get(key) != value:
                raise ExpansionV12Error(
                    f"{symbol} expansion config {key} mismatch"
                )
    return config


def expansion_market_specs(repo_root: Path) -> dict[str, ExpansionMarketSpec]:
    config = load_expansion_config(repo_root)
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
        str(item["source_symbol"]): item
        for item in config["markets"]
    }

    specs: dict[str, ExpansionMarketSpec] = {}
    for symbol in MARKETS:
        expected = EXPECTED_MARKETS[symbol]
        registry_item = registry_by_symbol.get(symbol)
        if registry_item is None:
            raise ExpansionV12Error(
                f"{symbol} missing from canonical instrument registry"
            )
        if registry_item["status"] != "include":
            raise ExpansionV12Error(
                f"{symbol} registry status must be include"
            )
        for key in ("canonical_symbol", "asset_class", "digits"):
            if registry_item[key] != expected[key]:
                raise ExpansionV12Error(
                    f"{symbol} registry {key} mismatch: "
                    f"{registry_item[key]!r}"
                )
            config_key = key
            if config_by_symbol[symbol][config_key] != expected[key]:
                raise ExpansionV12Error(
                    f"{symbol} config {config_key} mismatch"
                )

        digits = int(expected["digits"])
        specs[symbol] = ExpansionMarketSpec(
            source_symbol=symbol,
            canonical_symbol=str(expected["canonical_symbol"]),
            asset_class=str(expected["asset_class"]),
            digits=digits,
            point_size=10.0 ** (-digits),
            database_path=repo_root / DATABASE_PATHS[symbol],
        )

    return specs


def feature_schema_equivalence_report(repo_root: Path) -> dict[str, Any]:
    base = _load_json(repo_root / BASE_FEATURE_SCHEMA)
    expansion = _load_json(repo_root / EXPANSION_FEATURE_SCHEMA)

    base_symbol_enum = (
        base.get("properties", {})
        .get("source_symbol", {})
        .get("enum")
    )
    expansion_symbol_enum = (
        expansion.get("properties", {})
        .get("source_symbol", {})
        .get("enum")
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



def guardrails_equivalence_report(repo_root: Path) -> dict[str, Any]:
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


def review_gates_report(repo_root: Path) -> dict[str, Any]:
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
        and payload.get("status") == "frozen_pre_activation"
        and payload.get("markets") == list(MARKETS)
        and payload.get("gates") == expected
        and payload.get("eligibility_rule")
        == "all_thresholds_for_gate_must_be_met"
        and payload.get("per_market_reporting_required") is True
        and payload.get("weak_or_low_activity_market_may_not_be_hidden_or_dropped_post_activation")
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


def preactivation_report_v1_2(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    _require_clean_tracked_worktree(repo_root)

    config = load_expansion_config(repo_root)
    specs = expansion_market_specs(repo_root)
    schema_report = feature_schema_equivalence_report(repo_root)
    guardrails_report = guardrails_equivalence_report(repo_root)
    gates_report = review_gates_report(repo_root)
    lineage = verify_frozen_decision_lineage(repo_root)

    expansion_ledgers = {
        symbol: specs[symbol].database_path.exists()
        for symbol in MARKETS
    }
    anchor_candidates = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "research" / "forward").glob(
            "AI-v1.2-expansion-activation-*.json"
        )
    )

    ready = (
        lineage["match"]
        and schema_report[
            "equivalent_except_schema_metadata_and_source_symbol_allowlist"
        ]
        and schema_report["feature_schema_version_preserved"]
        and schema_report["expansion_source_symbol_enum"] == list(MARKETS)
        and guardrails_report["equivalent_except_status_and_shadow_market_allowlist"]
        and guardrails_report["expansion_shadow_markets"] == list(MARKETS)
        and guardrails_report["broker_execution_disabled"]
        and guardrails_report["protocol_version_preserved"]
        and gates_report["valid"]
        and not any(expansion_ledgers.values())
        and not anchor_candidates
    )

    return {
        "preactivation_check": "PASS" if ready else "FAIL",
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "repository_commit_sha": _git_commit_sha(repo_root),
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
        "frozen_ai_v1_0_decision_lineage_mismatches": lineage[
            "mismatches"
        ],
        "feature_schema_compatibility": schema_report,
        "guardrails_compatibility": guardrails_report,
        "review_gates": gates_report,
        "feature_formula_change": False,
        "decision_contract_change": False,
        "policy_change": False,
        "guard_numeric_semantics_change": False,
        "market_allowlist_change": True,
        "market_allowlist_change_is_version_isolated": True,
        "sync_max_wait_seconds": float(config["sync_max_wait_seconds"]),
        "sync_poll_interval_seconds": float(
            config["sync_poll_interval_seconds"]
        ),
        "expansion_ledger_paths_exist": expansion_ledgers,
        "expansion_activation_anchors": anchor_candidates,
        "provider_call_made": False,
        "mt5_call_made": False,
        "ledger_write_performed": False,
        "activation_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
    }
