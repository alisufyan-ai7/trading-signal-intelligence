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
    PUBLIC_SURFACE_CORRECTION_KIND_V2,
    PUBLIC_SURFACE_V2_SCHEMA_VERSION,
    _public_surface_correction,
)


CONFIRMATION = "CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION-V0.2"


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


def _tracked_web_hashes(repo_root: Path) -> dict[str, str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--", "web"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            f"Unable to enumerate tracked web files: {exc}"
        ) from None

    relative_paths = sorted(
        {
            line.strip().replace("\\", "/")
            for line in output.splitlines()
            if line.strip()
        }
    )
    if not relative_paths:
        raise SystemExit("Tracked web tree is empty.")

    return {
        relative: _sha256(repo_root / relative)
        for relative in relative_paths
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create the next governed AI-v1.1 public-surface correction "
            "using the v0.2 supersession schema. The correction may update "
            "only the frozen public-surface allowlist and the exact tracked "
            "web tree. It does not touch ledgers, MT5, provider, scheduler, "
            "cloud state, or broker execution."
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

    active_correction = _public_surface_correction(repo_root, activation)
    if (
        active_correction.get("present") is not True
        or active_correction.get("valid") is not True
        or not isinstance(active_correction.get("path"), str)
    ):
        raise SystemExit(
            "Current public-surface correction chain is not valid/upstream. "
            "Stop for review."
        )

    predecessor_rel = str(active_correction["path"])
    predecessor_path = repo_root / predecessor_rel
    predecessor_sha = _sha256(predecessor_path)
    sequence_number = int(active_correction.get("sequence_number", 0)) + 1

    original_artifacts = activation.get("artifact_hashes")
    if not isinstance(original_artifacts, dict):
        raise SystemExit("Activation artifact hashes are missing.")

    untouched_mismatches: dict[str, dict[str, str | None]] = {}
    overrides: dict[str, str] = {}
    for name, relative in V11_ARTIFACT_PATHS.items():
        actual = _sha256(repo_root / relative)
        expected = original_artifacts.get(name)
        if name in PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS:
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
            "Current correction override set does not exactly match the "
            "frozen public-surface allowlist."
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

    web_hashes = _tracked_web_hashes(repo_root)
    for artifact_name in ("ai_ui_index", "ai_ui_script"):
        relative = V11_ARTIFACT_PATHS[artifact_name]
        if web_hashes.get(relative) != overrides.get(artifact_name):
            raise SystemExit(
                "Tracked web manifest disagrees with the activation-bound "
                f"artifact hash for {artifact_name}."
            )

    previous_overrides = active_correction.get("artifact_hash_overrides")
    previous_web = active_correction.get("tracked_web_artifact_hashes")
    if (
        isinstance(previous_overrides, dict)
        and dict(previous_overrides) == overrides
        and isinstance(previous_web, dict)
        and dict(previous_web) == web_hashes
    ):
        raise SystemExit(
            "Public surface is byte-identical to the active correction. "
            "Refusing a no-op supersession."
        )

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H%M%SZ")
    relative_output = (
        Path("research")
        / "forward"
        / f"AI-v1.1-public-surface-correction-v0.2-{stamp}.json"
    )
    output = repo_root / relative_output
    if output.exists():
        raise SystemExit(f"Correction output already exists: {relative_output}")

    payload = {
        "correction_kind": PUBLIC_SURFACE_CORRECTION_KIND_V2,
        "correction_schema_version": PUBLIC_SURFACE_V2_SCHEMA_VERSION,
        "sequence_number": sequence_number,
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "created_at_utc": now.isoformat(),
        "repository_commit_sha": _git_head(repo_root),
        "base_activation_anchor": activation_path.relative_to(
            repo_root
        ).as_posix(),
        "base_activation_anchor_sha256": _sha256(activation_path),
        "supersedes_correction": predecessor_rel,
        "supersedes_correction_sha256": predecessor_sha,
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "change_scope": "VowSig missed-inference public observability correction v0.1",
        "artifact_hash_overrides": dict(sorted(overrides.items())),
        "corrected_artifact_names": sorted(overrides),
        "tracked_web_tree_mode": "git_tracked_exact",
        "tracked_web_artifact_hashes": dict(sorted(web_hashes.items())),
        "tracked_web_artifact_count": len(web_hashes),
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
                "correction_kind": PUBLIC_SURFACE_CORRECTION_KIND_V2,
                "correction_schema_version": (
                    PUBLIC_SURFACE_V2_SCHEMA_VERSION
                ),
                "sequence_number": sequence_number,
                "supersedes_correction": predecessor_rel,
                "runtime_version": RUNTIME_VERSION,
                "decision_protocol_version": DECISION_PROTOCOL_VERSION,
                "corrected_artifact_names": sorted(overrides),
                "tracked_web_artifact_count": len(web_hashes),
                "decision_artifacts_changed": False,
                "ledger_mutation_performed": False,
                "provider_call_made": False,
                "mt5_call_made": False,
                "broker_execution_enabled": False,
                "scheduler_changed": False,
                "next_required_step": (
                    "Review the generated anchor, commit/push only after "
                    "isolated tests pass, then verify the complete correction "
                    "chain upstream before any production merge."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
