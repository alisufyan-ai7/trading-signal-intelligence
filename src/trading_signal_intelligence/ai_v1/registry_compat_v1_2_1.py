from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation_v1_2_1 import (
    EXPANSION_ARTIFACT_PATHS,
)
from trading_signal_intelligence.ai_v1.observability import _file_sha256
from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
    verify_expansion_artifacts_v1_2_1,
)

MANIFEST_PATH = "config/ai_v1_2_1_registry_compatibility_v0_1.json"
INSTRUMENT_REGISTRY_ARTIFACT = "instrument_registry"


class RegistryCompatibilityV121Error(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryCompatibilityV121Error(
            f"unable to load registry compatibility JSON: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise RegistryCompatibilityV121Error(
            f"registry compatibility JSON root must be object: {path}"
        )
    return payload


def load_registry_compatibility_manifest(repo_root: Path) -> dict[str, Any]:
    manifest = _load_json(repo_root / MANIFEST_PATH)
    if manifest.get("correction_version") != "AI-v1.2.1-registry-compat-v0.1":
        raise RegistryCompatibilityV121Error("correction version mismatch")
    if manifest.get("status") != "offline_candidate":
        raise RegistryCompatibilityV121Error("correction status mismatch")
    if manifest.get("runtime_version") != "AI-v1.2.1":
        raise RegistryCompatibilityV121Error("runtime version mismatch")
    if manifest.get("decision_protocol_version") != "AI-v1.0":
        raise RegistryCompatibilityV121Error("decision protocol mismatch")
    if (
        manifest.get("frozen_registry_path")
        != EXPANSION_ARTIFACT_PATHS[INSTRUMENT_REGISTRY_ARTIFACT]
    ):
        raise RegistryCompatibilityV121Error("registry path mismatch")
    if manifest.get("activation_anchor") != (
        "research/forward/"
        "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
    ):
        raise RegistryCompatibilityV121Error("activation anchor mismatch")
    if manifest.get("frozen_registry_hash_basis") != "windows_worktree_crlf":
        raise RegistryCompatibilityV121Error(
            "frozen registry hash basis mismatch"
        )

    rules = manifest.get("rules")
    if not isinstance(rules, dict):
        raise RegistryCompatibilityV121Error("compatibility rules missing")
    required_true = (
        "all_preexisting_registry_entries_must_be_byte_semantically_equal",
        "top_level_schema_and_notes_must_be_unchanged",
        "only_exact_allowed_additions_may_be_new",
        "all_other_frozen_artifacts_must_match_activation_anchor_exactly",
    )
    if any(rules.get(key) is not True for key in required_true):
        raise RegistryCompatibilityV121Error(
            "required compatibility protection disabled"
        )
    required_false = (
        "activation_anchor_rewrite_allowed",
        "decision_logic_change_allowed",
        "ledger_mutation_allowed",
        "scheduler_mutation_allowed",
        "provider_call_allowed",
        "mt5_call_allowed",
        "public_exposure_change_allowed",
        "broker_execution_change_allowed",
    )
    if any(rules.get(key) is not False for key in required_false):
        raise RegistryCompatibilityV121Error(
            "forbidden correction authority enabled"
        )
    return manifest


def _git_file_bytes(
    repo_root: Path,
    *,
    commit: str,
    relative_path: str,
) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RegistryCompatibilityV121Error(
            "unable to read frozen registry from Git history"
        ) from exc


def _windows_worktree_bytes_from_git_blob(payload: bytes) -> bytes:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistryCompatibilityV121Error(
            "frozen registry Git blob is not UTF-8"
        ) from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.replace("\n", "\r\n").encode("utf-8")


def _parse_json_bytes(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryCompatibilityV121Error(
            f"{label} registry is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise RegistryCompatibilityV121Error(
            f"{label} registry root must be object"
        )
    return value


def _index_instruments(
    registry: dict[str, Any],
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    instruments = registry.get("instruments")
    if not isinstance(instruments, list):
        raise RegistryCompatibilityV121Error(
            f"{label} registry instruments must be list"
        )
    indexed: dict[str, dict[str, Any]] = {}
    for item in instruments:
        if not isinstance(item, dict):
            raise RegistryCompatibilityV121Error(
                f"{label} registry instrument must be object"
            )
        canonical = item.get("canonical")
        if not isinstance(canonical, str) or not canonical:
            raise RegistryCompatibilityV121Error(
                f"{label} registry canonical symbol invalid"
            )
        if canonical in indexed:
            raise RegistryCompatibilityV121Error(
                f"{label} registry duplicate canonical: {canonical}"
            )
        indexed[canonical] = item
    return indexed


def validate_registry_transition(
    *,
    frozen_registry: dict[str, Any],
    current_registry: dict[str, Any],
    allowed_additions: list[dict[str, Any]],
) -> dict[str, Any]:
    frozen_top = {
        key: value
        for key, value in frozen_registry.items()
        if key != "instruments"
    }
    current_top = {
        key: value
        for key, value in current_registry.items()
        if key != "instruments"
    }
    if current_top != frozen_top:
        raise RegistryCompatibilityV121Error(
            "registry top-level metadata changed"
        )

    frozen = _index_instruments(frozen_registry, label="frozen")
    current = _index_instruments(current_registry, label="current")

    for canonical, expected in frozen.items():
        actual = current.get(canonical)
        if actual is None:
            raise RegistryCompatibilityV121Error(
                f"pre-existing registry entry deleted: {canonical}"
            )
        if actual != expected:
            raise RegistryCompatibilityV121Error(
                f"pre-existing registry entry changed: {canonical}"
            )

    allowed: dict[str, dict[str, Any]] = {}
    for item in allowed_additions:
        if not isinstance(item, dict):
            raise RegistryCompatibilityV121Error(
                "allowed registry addition must be object"
            )
        canonical = item.get("canonical")
        if not isinstance(canonical, str) or not canonical:
            raise RegistryCompatibilityV121Error(
                "allowed registry addition canonical invalid"
            )
        if canonical in allowed:
            raise RegistryCompatibilityV121Error(
                f"duplicate allowed addition: {canonical}"
            )
        allowed[canonical] = item

    added_names = set(current) - set(frozen)
    if added_names != set(allowed):
        raise RegistryCompatibilityV121Error(
            "registry additions differ from exact approved set"
        )
    for canonical, expected in allowed.items():
        if current.get(canonical) != expected:
            raise RegistryCompatibilityV121Error(
                f"approved registry addition differs: {canonical}"
            )

    return {
        "valid": True,
        "protected_preexisting_entries": len(frozen),
        "approved_additions": sorted(allowed),
    }


def verify_registry_compatibility_v1_2_1(
    repo_root: Path,
    *,
    expected_anchor_hash: str,
    actual_registry_hash: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest = load_registry_compatibility_manifest(repo_root)

    frozen_hash = str(manifest["frozen_registry_sha256"])
    approved_hash = str(manifest["approved_expanded_registry_sha256"])
    if expected_anchor_hash != frozen_hash:
        raise RegistryCompatibilityV121Error(
            "activation anchor registry hash is not the frozen approved hash"
        )
    if actual_registry_hash != approved_hash:
        raise RegistryCompatibilityV121Error(
            "current registry hash is not the exact approved expanded hash"
        )

    relative = str(manifest["frozen_registry_path"])
    frozen_bytes = _git_file_bytes(
        repo_root,
        commit=str(manifest["frozen_registry_git_commit"]),
        relative_path=relative,
    )
    frozen_worktree_bytes = _windows_worktree_bytes_from_git_blob(
        frozen_bytes
    )
    observed_frozen_hash = hashlib.sha256(
        frozen_worktree_bytes
    ).hexdigest()
    if observed_frozen_hash != frozen_hash:
        raise RegistryCompatibilityV121Error(
            "Git-history frozen registry Windows-worktree hash mismatch"
        )

    current_path = repo_root / relative
    observed_current_hash = _file_sha256(current_path)
    if observed_current_hash != approved_hash:
        raise RegistryCompatibilityV121Error(
            "checked-out registry hash mismatch"
        )

    transition = validate_registry_transition(
        frozen_registry=_parse_json_bytes(
            frozen_bytes,
            label="frozen",
        ),
        current_registry=_load_json(current_path),
        allowed_additions=list(manifest["allowed_additions"]),
    )
    return {
        "valid": True,
        "correction_version": manifest["correction_version"],
        "frozen_registry_sha256": frozen_hash,
        "approved_expanded_registry_sha256": approved_hash,
        **transition,
    }


def verify_expansion_artifacts_registry_compat_v1_2_1(
    repo_root: Path,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    original = verify_expansion_artifacts_v1_2_1(repo_root, anchor)
    if original["valid"]:
        return {
            **original,
            "compatibility_applied": False,
            "compatibility": None,
            "original_mismatches": {},
        }

    mismatches = original.get("mismatches")
    if not isinstance(mismatches, dict):
        return {
            **original,
            "compatibility_applied": False,
            "compatibility": None,
            "original_mismatches": mismatches,
        }
    if set(mismatches) != {INSTRUMENT_REGISTRY_ARTIFACT}:
        return {
            **original,
            "compatibility_applied": False,
            "compatibility": None,
            "original_mismatches": mismatches,
        }

    item = mismatches[INSTRUMENT_REGISTRY_ARTIFACT]
    expected_hash = item.get("expected")
    actual_hash = item.get("actual")
    if not isinstance(expected_hash, str) or not isinstance(actual_hash, str):
        return {
            **original,
            "compatibility_applied": False,
            "compatibility": None,
            "original_mismatches": mismatches,
        }

    try:
        compatibility = verify_registry_compatibility_v1_2_1(
            repo_root,
            expected_anchor_hash=expected_hash,
            actual_registry_hash=actual_hash,
        )
    except RegistryCompatibilityV121Error as exc:
        return {
            **original,
            "compatibility_applied": False,
            "compatibility": {
                "valid": False,
                "reason": str(exc),
            },
            "original_mismatches": mismatches,
        }

    return {
        "valid": True,
        "checked": original["checked"],
        "mismatches": {},
        "compatibility_applied": True,
        "compatibility": compatibility,
        "original_mismatches": mismatches,
    }
