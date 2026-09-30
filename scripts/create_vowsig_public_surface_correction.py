from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    DECISION_PROTOCOL_VERSION,
    FROZEN_DECISION_ARTIFACT_PATHS,
    RUNTIME_VERSION,
    V11_ARTIFACT_PATHS,
)
from trading_signal_intelligence.ai_v1.observability_v1_1 import (
    PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS,
    PUBLIC_SURFACE_CORRECTION_KIND,
)


CONFIRMATION = "CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def _require_clean_tracked_worktree(repo_root: Path) -> None:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()
    if status:
        raise SystemExit(
            "Tracked worktree is not clean. Refusing correction-anchor creation."
        )


def _load_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Unable to load JSON: {path}: {exc}") from None
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create one non-decision AI-v1.1 public-surface correction anchor "
            "for the VowSig rebrand. Does not touch ledgers, MT5, provider, "
            "scheduler, cloud state, or broker execution."
        )
    )
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if args.confirm != CONFIRMATION:
        raise SystemExit(
            "Refusing correction creation. Use the exact confirmation token."
        )

    repo_root = Path(__file__).resolve().parents[1]
    _require_clean_tracked_worktree(repo_root)

    existing = sorted(
        (repo_root / "research" / "forward").glob(
            "AI-v1.1-public-surface-correction-*.json"
        )
    )
    if existing:
        raise SystemExit(
            "A public-surface correction anchor already exists. Stop for review."
        )

    activation_candidates = sorted(
        (repo_root / "research" / "forward").glob(
            "AI-v1.1-activation-*.json"
        )
    )
    if len(activation_candidates) != 1:
        raise SystemExit(
            "Expected exactly one AI-v1.1 activation anchor; "
            f"found {len(activation_candidates)}."
        )

    activation_path = activation_candidates[0]
    activation = _load_json(activation_path)
    if activation.get("runtime_version") != RUNTIME_VERSION:
        raise SystemExit("Activation runtime mismatch.")
    if activation.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise SystemExit("Activation decision protocol mismatch.")
    if activation.get("broker_execution_enabled") is not False:
        raise SystemExit("Broker execution boundary is not disabled.")

    original_artifacts = activation.get("artifact_hashes")
    if not isinstance(original_artifacts, dict):
        raise SystemExit("Activation artifact hashes are missing.")

    untouched_mismatches: dict[str, dict[str, str | None]] = {}
    overrides: dict[str, str] = {}
    for name, relative in V11_ARTIFACT_PATHS.items():
        actual = _sha256(repo_root / relative)
        expected = original_artifacts.get(name)
        if name in PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS:
            if actual != expected:
                overrides[name] = actual
        elif actual != expected:
            untouched_mismatches[name] = {
                "expected": str(expected) if expected else None,
                "actual": actual,
            }

    if untouched_mismatches:
        raise SystemExit(
            "Non-correctable AI-v1.1 artifacts changed: "
            + json.dumps(untouched_mismatches, sort_keys=True)
        )

    if set(overrides) != set(PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS):
        raise SystemExit(
            "Expected exactly the frozen public-surface correction allowlist "
            "to differ from the activation anchor. Observed: "
            + json.dumps(sorted(overrides))
        )

    frozen_expected = activation.get("frozen_decision_artifact_hashes")
    if not isinstance(frozen_expected, dict):
        raise SystemExit("Frozen decision artifact hashes are missing.")

    frozen_mismatches: dict[str, dict[str, str | None]] = {}
    for name, relative in FROZEN_DECISION_ARTIFACT_PATHS.items():
        actual = _sha256(repo_root / relative)
        expected = frozen_expected.get(name)
        if actual != expected:
            frozen_mismatches[name] = {
                "expected": str(expected) if expected else None,
                "actual": actual,
            }
    if frozen_mismatches:
        raise SystemExit(
            "Frozen decision artifacts changed: "
            + json.dumps(frozen_mismatches, sort_keys=True)
        )

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H%M%SZ")
    relative_output = (
        Path("research")
        / "forward"
        / f"AI-v1.1-public-surface-correction-{stamp}.json"
    )
    output = repo_root / relative_output

    payload = {
        "correction_kind": PUBLIC_SURFACE_CORRECTION_KIND,
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "created_at_utc": now.isoformat(),
        "repository_commit_sha": _git_head(repo_root),
        "base_activation_anchor": activation_path.relative_to(
            repo_root
        ).as_posix(),
        "base_activation_anchor_sha256": _sha256(activation_path),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": dict(sorted(overrides.items())),
        "corrected_artifact_names": sorted(overrides),
        "decision_artifacts_changed": False,
        "ledger_mutation_performed": False,
        "backfill_performed": False,
        "provider_call_made": False,
        "mt5_call_made": False,
        "broker_execution_enabled": False,
        "scheduler_changed": False,
        "vowsig_ai_redirect_in_scope": False,
    }

    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(
        json.dumps(
            {
                "correction_preview": "PASS",
                "correction_file": str(relative_output),
                "runtime_version": RUNTIME_VERSION,
                "decision_protocol_version": DECISION_PROTOCOL_VERSION,
                "corrected_artifact_names": sorted(overrides),
                "decision_artifacts_changed": False,
                "ledger_mutation_performed": False,
                "provider_call_made": False,
                "mt5_call_made": False,
                "broker_execution_enabled": False,
                "scheduler_changed": False,
                "next_required_step": (
                    "Review, commit and push only the generated correction "
                    "anchor on the isolated rebrand branch. Do not merge."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
