"""Prospective AI-v1.2.1 public-product registry compatibility proof.

Never amend the historic activation anchor or suppress its immutable artifact
verification failure. This routine supplies a separate operational PUBLIC
readiness attestation only for the exact two 2026-10-08 crypto additions.
Read-only Git objects and raw local bytes; no providers, trades or file writes.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

HISTORICAL_COMMIT = "6155e3599ef907f9e29b6d52dcac045dff3837bc"
ADDITION_COMMIT = "561fcff64b96ca6eb03ef76d70db7f02f92a9625"
RELATIVE = "config/instruments.json"
EXPECTED_ARTIFACT_COUNT = 34
HISTORIC_CRLF_SHA256 = "b92b80d18f422ba012b991ca8ba5a538f9212ee2823813d29754f24a804491ca"
HISTORIC_LF_SHA256 = "ff237a840c19b6f3a009a253e122940b6be0091d7f67220a25be4d73175ca40e"
CURRENT_CRLF_SHA256 = "f2f3d993fdd171ac43edd5234e18cfbea3eb7cf8da5dc2e6e6d4529613cd1681"
CURRENT_LF_SHA256 = "18116bd612a1648371e272d610273958a088a94207c62299e308da42a5e52c74"

ADDITIONS = [
    {
        "canonical": "ETH/USDT",
        "asset_class": "crypto",
        "sources": {"binance_spot": {"symbol": "ETHUSDT", "status": "primary"}},
    },
    {
        "canonical": "SOL/USDT",
        "asset_class": "crypto",
        "sources": {"binance_spot": {"symbol": "SOLUSDT", "status": "primary"}},
    },
]
PUBLIC_TITLE = "Expansion Shadow Validation — operational compatibility (historical registry mismatch preserved)"
REQUIRED_HEALTH = (
    "ledgers_valid",
    "activation_anchor_upstream_valid",
    "scheduler_healthy",
    "public_exposure_disabled",
    "broker_execution_disabled",
)


class CompatibilityRejected(RuntimeError):
    """No relaxation is admissible outside the exact registered historical delta."""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_file(root: Path, ref: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{RELATIVE}"],
            cwd=root, check=True, capture_output=True, timeout=12,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise CompatibilityRejected("pinned Git registry object not available") from exc


def _normalized_lf(raw: bytes) -> bytes:
    if b"\r" in raw.replace(b"\r\n", b""):
        raise CompatibilityRejected("unsupported registry line ending")
    return raw.replace(b"\r\n", b"\n")


def _verify_exact_registry_provenance(root: Path) -> None:
    historic = _git_file(root, HISTORICAL_COMMIT)
    added = _git_file(root, ADDITION_COMMIT)
    checked_out = _git_file(root, "HEAD")

    if (_digest(historic) != HISTORIC_LF_SHA256
        or _digest(historic.replace(b"\n", b"\r\n")) != HISTORIC_CRLF_SHA256
        or _digest(added) != CURRENT_LF_SHA256
        or _digest(added.replace(b"\n", b"\r\n")) != CURRENT_CRLF_SHA256
        or checked_out != added):
        raise CompatibilityRejected("unapproved registry Git history or checkout")

    local = (root / RELATIVE).read_bytes()
    if _digest(local) not in (CURRENT_LF_SHA256, CURRENT_CRLF_SHA256):
        raise CompatibilityRejected("live registry not exact approved content")
    if _normalized_lf(local) != added:
        raise CompatibilityRejected("local registry is not approved Git bytes")

    try:
        old = json.loads(historic)
        new = json.loads(added)
    except (ValueError, TypeError) as exc:
        raise CompatibilityRejected("registry JSON invalid") from exc
    if (not isinstance(old, dict) or not isinstance(new, dict)
        or not isinstance(old.get("instruments"), list)
        or not isinstance(new.get("instruments"), list)
        or old.get("schema_version") != 1 or new.get("schema_version") != 1
        or {k: v for k, v in old.items() if k != "instruments"}
           != {k: v for k, v in new.items() if k != "instruments"}):
        raise CompatibilityRejected("registry non-instrument fields changed")
    retained = [entry for entry in new["instruments"] if entry not in ADDITIONS]
    if (len(new["instruments"]) != len(old["instruments"]) + 2
        or retained != old["instruments"]
        or [entry for entry in new["instruments"] if entry in ADDITIONS] != ADDITIONS):
        raise CompatibilityRejected("registry has non-additive or unapproved changes")


def prove_expansion_compatibility(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    """Operational attestation without modifying report or frozen original evidence."""
    if report.get("runtime_version") != "AI-v1.2.1":
        raise CompatibilityRejected("wrong runtime lineage")
    health = report.get("health")
    if not isinstance(health, dict) or health.get("healthy") is not False:
        raise CompatibilityRejected("historic overall-health predicate did not fail")
    if health.get("expansion_artifacts_valid") is not False:
        raise CompatibilityRejected("historic artifact mismatch absent")
    if any(health.get(flag) is not True for flag in REQUIRED_HEALTH):
        raise CompatibilityRejected("other expansion health invariant failed")
    verification = (report.get("activation") or {}).get("artifact_verification")
    if not isinstance(verification, dict):
        raise CompatibilityRejected("historic artifact verification missing")
    if (verification.get("valid") is not False
        or type(verification.get("checked")) is not int
        or verification["checked"] != EXPECTED_ARTIFACT_COUNT):
        raise CompatibilityRejected("unexpected frozen artifact verification")
    mismatches = verification.get("mismatches")
    if not isinstance(mismatches, dict) or set(mismatches) != {"instrument_registry"}:
        raise CompatibilityRejected("non-registry frozen artifact mismatch")
    mismatch = mismatches["instrument_registry"]
    if (not isinstance(mismatch, dict)
        or mismatch.get("expected") != HISTORIC_CRLF_SHA256
        or mismatch.get("actual") != CURRENT_CRLF_SHA256):
        raise CompatibilityRejected("unapproved frozen registry hash mismatch")
    if any(
        market.get("ledger_verification", {}).get("valid") is not True
        or market.get("activation_anchor_match") is not True
        for market in (report.get("markets") or {}).values()
    ) or set(report.get("markets") or {}) != {"EURUSD", "XAGUSD", "USOIL"}:
        raise CompatibilityRejected("expansion ledger or market activation mismatch")
    _verify_exact_registry_provenance(root)
    return {
        "schema_version": 1,
        "status": "prospective_exact_registry_compatibility",
        "historic_activation_artifacts_valid": False,
        "historic_registry_sha256": HISTORIC_CRLF_SHA256,
        "current_registry_sha256": CURRENT_CRLF_SHA256,
        "additive_git_commit": ADDITION_COMMIT,
        "added_symbols": ["ETHUSDT", "SOLUSDT"],
        "unchanged_frozen_artifacts_verified": EXPECTED_ARTIFACT_COUNT - 1,
    }


def build_compatibility_qualified_program(
    root: Path,
    report: dict[str, Any],
) -> dict[str, Any]:
    from trading_signal_intelligence.product.ai_insights import (
        EXPANSION_MARKET_LABELS,
        build_public_validation_program,
    )

    if report.get("health", {}).get("healthy") is True:
        raise CompatibilityRejected("legacy healthy report does not need compatibility")
    # The separate proof is required before the new public-operational
    # report is built. Do not surface extra fields: the immutable public
    # validation-program schema has additionalProperties=false, including
    # inside "health". The historical failure remains in the source report,
    # not silently marked as PASS.
    prove_expansion_compatibility(root, report)
    separate = copy.deepcopy(report)
    separate["health"]["healthy"] = True
    return build_public_validation_program(
        separate,
        program_id="market-expansion-1",
        title=PUBLIC_TITLE,
        market_labels=EXPANSION_MARKET_LABELS,
        public_signal_exposure=False,
    )
